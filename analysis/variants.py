"""논문용 비교 추정기: 같은 입력 조건의 기준선 4종 + 제안법 ablation.

인터페이스는 estimator.py와 같다(fit(train) / predict({"rest_V", "ref", "temp_c"})).
제안법(Proposed)은 estimator.py(동결 커밋 fdfb160 = 718da07)의 로직을 플래그로 끌 수 있게 옮긴 것이다.
플래그를 모두 켜면 estimator.py와 같은 예측을 낸다(check_equivalence로 확인).
"""
import importlib.util
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("estimator_frozen", ROOT / "estimator.py")
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
feats, pts, ref_map, ref_multi, ref_knn = E.Estimator.feats, E.pts, E.ref_map, E.ref_multi, E.ref_knn


def _ref(test, r):
    ref = test["ref"]
    rk = ref["rest_len"] >= r
    return ref["rest_V"][rk, :r], ref["soc"][rk]


# ---------------------------------------------------------------- 기준선
class IsoGlobal:
    """B0 (원래 기준선 643c1e7): 학습 셀 전체를 합친 단조 OCV 표, 마지막 전압 1점. 등록·온도 안 씀."""

    def __init__(self, seed=0, **_):
        pass

    def fit(self, train):
        self.rest_V, self.rest_len, self.soc = train["rest_V"], train["rest_len"], train["soc"]
        return self

    def predict(self, test):
        v = test["rest_V"]
        r = v.shape[1]
        ok = self.rest_len >= r
        iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(self.rest_V[ok, r - 1], self.soc[ok])
        return iso.predict(v[:, -1])


class RegLookup:
    """B1: 시험 셀의 등록 시험(25 °C HPPC)으로 만든 단조 OCV 표에 끝 전압(15 s 평균)을 넣는다. 학습 안 함."""

    def __init__(self, seed=0, **_):
        pass

    def fit(self, train):
        return self

    def predict(self, test):
        v = test["rest_V"]
        Vr, sr = _ref(test, v.shape[1])
        return ref_map(feats(Vr)[:, 0], sr, feats(v)[:, 0])


class RegLookupTemp:
    """B2: B1 + 온도 보정. 잔차 soc − rs를 [ΔT, ΔT², ΔT·rs]의 선형식으로 학습 셀에서 맞춘다(최소제곱)."""

    def __init__(self, seed=0, **_):
        self._b = {}

    def fit(self, train):
        self.t = train
        return self

    @staticmethod
    def _X(dT, rs):
        return np.c_[np.ones_like(dT), dT, dT ** 2, dT * rs]

    def _coef(self, r):
        t = self.t
        ok = t["rest_len"] >= r
        X, y = [], []
        for d in np.unique(t["dataset"][ok]):
            i = ok & (t["dataset"] == d)
            rr = i & t["reg"]
            tg = i & ~t["reg"]
            if rr.sum() < 3 or tg.sum() == 0:
                continue
            rs = ref_map(feats(t["rest_V"][rr, :r])[:, 0], t["soc"][rr], feats(t["rest_V"][tg, :r])[:, 0])
            X.append(self._X(t["temp_c"][tg] - E.REF_T, rs))
            y.append(t["soc"][tg] - rs)
        return np.linalg.lstsq(np.vstack(X), np.concatenate(y), rcond=None)[0]

    def predict(self, test):
        v = test["rest_V"]
        r = v.shape[1]
        if r not in self._b:
            self._b[r] = self._coef(r)
        Vr, sr = _ref(test, r)
        rs = ref_map(feats(Vr)[:, 0], sr, feats(v)[:, 0])
        return np.clip(rs + self._X(test["temp_c"] - E.REF_T, rs) @ self._b[r], 0, 1)


def vinf_2rc(V):
    """2RC 이완 V(t) = V∞ + a1·e^(−t/τ1) + a2·e^(−t/τ2) 적합으로 V∞ 외삽.
    τ 격자(τ1 ∈ [1, r/10], τ2 ∈ [r/10, 2r], 로그 간격)마다 선형 최소제곱, 표본마다 잔차 최소인 쌍을 고른다.
    첫 1 s는 전류 차단 과도 구간이라 뺀다."""
    r = V.shape[1]
    t = np.arange(1, r, dtype=float)
    Y = V[:, 1:].T
    best_sse = np.full(V.shape[0], np.inf)
    best_v = V[:, -1].copy()
    for t1 in np.geomspace(1, r / 10, 8):
        for t2 in np.geomspace(r / 10, 2 * r, 10):
            if t2 <= t1 * 1.5:
                continue
            A = np.c_[np.ones_like(t), np.exp(-t / t1), np.exp(-t / t2)]
            c, *_ = np.linalg.lstsq(A, Y, rcond=None)
            sse = ((A @ c - Y) ** 2).sum(0)
            b = sse < best_sse
            best_sse[b], best_v[b] = sse[b], c[0, b]
    return best_v


class RC2Extrap:
    """B3 (고전 물리 기반): 2RC 적합으로 OCV(V∞)를 외삽하고, 등록 시험도 같은 방법으로 V∞를 구해 만든 단조 표로 SOC."""

    def __init__(self, seed=0, **_):
        pass

    def fit(self, train):
        return self

    def predict(self, test):
        v = test["rest_V"]
        Vr, sr = _ref(test, v.shape[1])
        return ref_map(vinf_2rc(Vr), sr, vinf_2rc(v))


# ---------------------------------------------------------------- 제안법 + ablation
class Proposed:
    """estimator.py와 같은 로직. 플래그로 구성 요소를 끈다.
    temp: 주변 온도 특징 / multi: 시점별 등록 표 SOC 차이 / knn: 등록 표본 kNN SOC 차이
    residual: rs 기준 잔차 학습(끄면 SOC 직접 회귀, rs는 특징으로 남음)
    aug_amp: 과전압 진폭 증강 / aug_shape: OCV 모양 무작위화 / aug_hw: 저가 체인 오차 증강
    balance: 데이터셋·SOC 구간 균형 가중치 / bag: 배깅 모델 수
    B4(일반 XGB, 같은 입력) = Proposed(residual, multi, knn, aug_*, balance 모두 False, bag=1)
    """

    def __init__(self, seed=0, temp=True, multi=True, knn=True, residual=True, aug_amp=True, aug_shape=True,
                 aug_hw=True, balance=True, bag=5, K=6, n_jobs=None):
        self.seed = seed
        self.f = dict(temp=temp, multi=multi, knn=knn, residual=residual, aug_amp=aug_amp, aug_shape=aug_shape,
                      aug_hw=aug_hw, balance=balance)
        self.bag, self.K, self.n_jobs = bag, K, n_jobs

    def fit(self, train):
        self.rest_V, self.rest_len, self.soc = train["rest_V"], train["rest_len"], train["soc"]
        self.dataset, self.temp_c = train["dataset"], train["temp_c"]
        self.reg = train.get("reg", train["temp_c"] == E.REF_T)
        self._models = {}
        return self

    def _F(self, Fv, rs, tc, rm, rn):
        cols = [Fv, rs[:, None]]
        if self.f["temp"]:
            cols.append(tc[:, None])
        if self.f["multi"]:
            cols.append(rm)
        if self.f["knn"]:
            cols.append(rn[:, None])
        return np.hstack(cols)

    def _mono(self, nfeat, npt):
        m = ["1"] * (nfeat - 1) + ["0", "0"]  # 끝 전압·Δ +1, frac·rs 자유
        if self.f["temp"]:
            m.append("0")
        if self.f["multi"]:
            m += ["0"] * npt
        if self.f["knn"]:
            m.append("0")
        return "(" + ",".join(m) + ")"

    def predict(self, test):
        v = test["rest_V"]
        r = v.shape[1]
        if r not in self._models:
            self._models[r] = [self._train(r, 5 * self.seed + k) for k in range(self.bag)]
        Vr, sr = _ref(test, r)
        Fr, Fv = feats(Vr), feats(v)
        rs = ref_map(Fr[:, 0], sr, Fv[:, 0])
        rm = ref_multi(pts(Vr), sr, pts(v)) - rs[:, None] if self.f["multi"] else None
        rn = ref_knn(Fr, sr, Fv) - rs if self.f["knn"] else None
        F = self._F(Fv, rs, test["temp_c"], rm, rn)
        p = np.mean([m.predict(F) for m in self._models[r]], 0)
        return np.clip(rs + p if self.f["residual"] else p, 0, 1)

    def _train(self, r, seed):
        f = self.f
        ok = self.rest_len >= r
        npt = pts(self.rest_V[:1, :r]).shape[1]
        nfeat = feats(self.rest_V[:1, :r]).shape[1]
        m = XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, objective="reg:absoluteerror",
                         monotone_constraints=self._mono(nfeat, npt), random_state=seed, n_jobs=self.n_jobs)
        g = np.random.default_rng(seed)
        x = self.rest_V[ok, :r]
        any_aug = f["aug_amp"] or f["aug_shape"] or f["aug_hw"]
        K = self.K if any_aug else 1
        n = len(x)
        full = self.rest_V[ok]
        last = np.minimum(self.rest_len[ok], full.shape[1])
        vinf = np.array([row[l - 5:l].mean() for row, l in zip(full, last)])[:, None]
        if f["aug_amp"]:
            aug = [vinf - np.exp(g.uniform(np.log(0.1), np.log(4.0), (n, 1))) * (vinf - x) for _ in range(K)]
        else:
            aug = [x.copy() for _ in range(K)]
        s, dsk = self.soc[ok], self.dataset[ok]
        shift = np.zeros((K, n))
        if f["aug_shape"]:
            for a, sh in zip(aug, shift):
                for d in np.unique(dsk):
                    c = g.normal(0, 0.015, 2)
                    sh[dsk == d] = c[0] * np.sin(np.pi * s[dsk == d]) + c[1] * np.sin(2 * np.pi * s[dsk == d])
                a += sh[:, None]
        if f["aug_hw"]:
            aug = [a * (1 + g.normal(0, 0.005, (n, 1))) + g.normal(0, 0.010, (n, 1))
                   + g.normal(0, 1, x.shape) * g.uniform(0.001, 0.004) for a in aug]
            aug = [np.round(a / q) * q for a, q in zip(aug, g.uniform(0.003, 0.012, K))]
        reg = self.reg[ok]
        tgt = ~reg
        F0 = feats(x)
        end0 = F0[:, 0]
        P0 = pts(x)
        ds = dsk
        sb = np.clip((s * 10).astype(int), 0, 9)
        if f["balance"]:
            w = np.array([1.0 / (tgt & (ds == d) & (sb == b)).sum() / len(set(sb[tgt & (ds == d)])) if t else 0.0
                          for d, b, t in zip(ds, sb, tgt)])
        else:
            w = tgt.astype(float)
        g6 = np.random.default_rng(40_000 + seed)
        Fs, ys, ws = [], [], []
        for a, sh in zip(aug, shift):
            F = feats(a)
            rs, rm, rn = np.zeros(n), np.zeros((n, npt)), np.zeros(n)
            Pa = pts(a)
            for d in np.unique(dsk):
                i, rr = dsk == d, (dsk == d) & reg
                if rr.sum() >= 3:
                    rs[i] = ref_map(end0[rr] + sh[rr], s[rr], F[i, 0])
                    if f["multi"]:
                        rm[i] = ref_multi(P0[rr] + sh[rr, None], s[rr], Pa[i]) - rs[i, None]
                    if f["knn"]:
                        Fr = F0[rr].copy()
                        Fr[:, 0] += sh[rr]
                        rn[i] = ref_knn(Fr, s[rr], F[i]) - rs[i]
            keep = tgt & np.isin(dsk, [d for d in np.unique(dsk) if (reg & (dsk == d)).sum() >= 3])
            tcn = self.temp_c[ok] + g6.normal(0, 2.0, n)
            Fs.append(self._F(F, rs, tcn, rm, rn)[keep])
            ys.append(((s - rs) if f["residual"] else s)[keep])
            ws.append(w[keep])
        wv = np.concatenate(ws)
        m.fit(np.vstack(Fs), np.concatenate(ys), sample_weight=wv / wv.mean())
        return m


VARIANTS = {
    # 기준선 (같은 입력 조건: 등록 시험 ref + 주변 온도; B0만 예외)
    "B0_iso_global": lambda s, nj: IsoGlobal(s),
    "B1_reg_lookup": lambda s, nj: RegLookup(s),
    "B2_reg_lookup_temp": lambda s, nj: RegLookupTemp(s),
    "B3_2rc_extrap": lambda s, nj: RC2Extrap(s),
    "B4_xgb_plain": lambda s, nj: Proposed(s, residual=False, multi=False, knn=False, aug_amp=False, aug_shape=False,
                                           aug_hw=False, balance=False, bag=1, n_jobs=nj),
    # 제안법과 하나씩 뺀 ablation
    "P_full": lambda s, nj: Proposed(s, n_jobs=nj),
    "A_no_temp": lambda s, nj: Proposed(s, temp=False, n_jobs=nj),
    "A_no_multi": lambda s, nj: Proposed(s, multi=False, n_jobs=nj),
    "A_no_knn": lambda s, nj: Proposed(s, knn=False, n_jobs=nj),
    "A_no_multi_knn": lambda s, nj: Proposed(s, multi=False, knn=False, n_jobs=nj),
    "A_no_residual": lambda s, nj: Proposed(s, residual=False, n_jobs=nj),
    "A_no_aug_amp": lambda s, nj: Proposed(s, aug_amp=False, n_jobs=nj),
    "A_no_aug_shape": lambda s, nj: Proposed(s, aug_shape=False, n_jobs=nj),
    "A_no_aug_hw": lambda s, nj: Proposed(s, aug_hw=False, n_jobs=nj),
    "A_no_aug_all": lambda s, nj: Proposed(s, aug_amp=False, aug_shape=False, aug_hw=False, n_jobs=nj),
    "A_no_balance": lambda s, nj: Proposed(s, balance=False, n_jobs=nj),
    # ablation에서 기여가 0 이하였던 넷을 한꺼번에 뺀 단순화 (분석 결과를 보고 만든 것 → dev 선택 편향 있음)
    "S_simple": lambda s, nj: Proposed(s, multi=False, knn=False, aug_shape=False, aug_hw=False, n_jobs=nj),
}
