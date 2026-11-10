"""[에이전트가 고치는 유일한 파일] T1 귀환 SOC 추정기.

인터페이스 (eval/run.py가 호출):
  Estimator(seed).fit(train)  train: dict
      rest_V (N,1800) 휴지 전압, 휴지가 끝나면 NaN / pre_V, pre_I (N,300) 휴지 직전
      dataset, chem, cell, temp_c, rest_len, soc (N,)   ※ 시험 때는 rest_V, ref, temp_c(주변 온도, ±2 °C 잡음)만 주어진다
  Estimator.predict({"rest_V": (M, r), "ref": {...}, "temp_c": (M,)}) -> (M,) SOC 0~1
      r초까지만 보인다(60/300/600). 시험 전압에는 저가 측정 체인 오차가 들어 있다.
      ref = 시험 셀 종류의 등록 시험(25 °C HPPC 한 번; 깨끗한 rest_V, soc, rest_len). 채점은 25 °C 외 온도만.
      train["reg"] = 학습 셀의 같은 등록 시험 표본 표시.

방법: 등록 곡선 SOC(끝 전압 단조 표)를 기준으로 잔차를 학습한다. 특징 = 휴지 모양 + 시점별 등록 표 SOC 차이 + 등록 표본 kNN SOC 차이.
학습 셀도 각자 자기 등록 시험을 등록 곡선으로 쓰고, 등록 시험 외 표본 전부가 학습 대상이다.
"""
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.neighbors import KNeighborsRegressor
from xgboost import XGBRegressor

REF_T = 25


def ref_map(ref_end, ref_soc, end):
    """등록 곡선의 단조 OCV 표로 끝 전압 → SOC."""
    iso = IsotonicRegression(out_of_bounds="clip").fit(ref_end, ref_soc)
    return iso.predict(end)


def pts(v):
    """Δ 시점들의 5점 평균 전압 (feats와 같은 시점, 끝 제외)."""
    r = v.shape[1]
    idx = sorted({9, min(29, r - 6), min(59, r - 6), r // 2})
    return np.stack([v[:, max(i - 2, 0):i + 3].mean(1) for i in idx], 1)


def ref_multi(Pr, sr, P):
    """시점마다 등록 곡선 단조 표: 같은 시점 전압 → SOC."""
    return np.stack([ref_map(Pr[:, j], sr, P[:, j]) for j in range(P.shape[1])], 1)


def ref_knn(Fr, sr, F):
    """등록 표본 공간(끝 전압, Δ9, 늦은 Δ; Δ는 ×3)에서 최근접 5개 거리 가중 SOC."""
    z = lambda A: A[:, [0, 2, -2]] * np.array([1.0, 3.0, 3.0])  # noqa: E731
    return KNeighborsRegressor(min(5, len(sr)), weights="distance").fit(z(Fr), sr).predict(z(F))


class Estimator:
    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, train):
        self.rest_V = train["rest_V"]
        self.rest_len = train["rest_len"]
        self.soc = train["soc"]
        self.dataset = train["dataset"]
        self.temp_c = train["temp_c"]
        self.reg = train.get("reg", train["temp_c"] == REF_T)  # 학습 셀의 등록 시험(25 °C HPPC 한 번) 표본
        self._models = {}
        return self

    @staticmethod
    def feats(v):
        r = v.shape[1]
        end = v[:, -15:].mean(1)
        idx = sorted({4, 9, min(29, r - 6), min(59, r - 6), r // 2})
        pts = np.stack([v[:, max(i - 2, 0):i + 3].mean(1) for i in idx], 1)  # 5점 평균: 양자화·잡음 완화
        d = end[:, None] - pts  # d[:,0]=Δ4, d[:,1]=Δ9, d[:,-1]=가장 늦은 시점
        den = np.copysign(np.maximum(np.abs(d[:, 1]), 0.006), d[:, 1])  # 분모 하한 6 mV
        frac = np.clip(d[:, -1] / den, -0.5, 1.5)  # 늦은 이완 비율: 진폭·부호에 불변 (방전 말단에서 이완이 느림)
        return np.c_[end, d, frac]

    def predict(self, test):
        v = test["rest_V"]
        r = v.shape[1]
        if r not in self._models:  # 창 길이 r마다 한 번만 학습 (서버에서 예측 1건 100 ms 제약)
            self._models[r] = [self._train(r, 5 * self.seed + k) for k in range(5)]  # 증강 난수만 다른 5개 배깅
        ref = test["ref"]
        rk = ref["rest_len"] >= r
        rs = ref_map(self.feats(ref["rest_V"][rk, :r])[:, 0], ref["soc"][rk], self.feats(v)[:, 0])
        Fr, Fv = self.feats(ref["rest_V"][rk, :r]), self.feats(v)
        F = np.c_[Fv, rs, test["temp_c"], ref_multi(pts(ref["rest_V"][rk, :r]), ref["soc"][rk], pts(v)) - rs[:, None],
                  ref_knn(Fr, ref["soc"][rk], Fv) - rs]
        return np.clip(rs + np.mean([m.predict(F) for m in self._models[r]], 0), 0, 1)  # 등록 곡선 SOC + 보정

    def _train(self, r, seed):
        ok = self.rest_len >= r
        npt = pts(self.rest_V[:1, :r]).shape[1]
        nf = self.feats(self.rest_V[:1, :r]).shape[1] + 3 + pts(self.rest_V[:1, :r]).shape[1]
        m = XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, objective="reg:absoluteerror",
                         monotone_constraints="(" + ",".join(["1"] * (nf - 4 - npt) + ["0", "0", "0"] + ["0"] * (npt + 1)) + ")",  # 끝 전압·Δ +1, 나머지 자유
                         random_state=seed)
        g = np.random.default_rng(seed)
        x, K = self.rest_V[ok, :r], 6  # 11-10 사용자 결정: 8→6 (평가 시간)
        n = len(x)
        full = self.rest_V[ok]
        last = np.minimum(self.rest_len[ok], full.shape[1])
        vinf = np.array([row[l - 5:l].mean() for row, l in zip(full, last)])[:, None]  # 긴 휴지 끝 ≈ OCV
        # 직전 전류 크기 증강: 과전압 η = vinf − V를 log 균등 0.1–4.0배(저온 큰 과전압까지) (저전류 OCV 시험까지 덮음)
        aug = [vinf - np.exp(g.uniform(np.log(0.1), np.log(4.0), (n, 1))) * (vinf - x) for _ in range(K)]
        # OCV 곡선 모양 무작위화: 사본·데이터셋마다 SOC의 매끄러운 함수로 전압 이동 (등록 곡선에도 같은 이동을 준다)
        s, dsk = self.soc[ok], self.dataset[ok]
        shift = np.zeros((K, n))
        for a, sh in zip(aug, shift):
            for d in np.unique(dsk):
                c = g.normal(0, 0.015, 2)
                sh[dsk == d] = c[0] * np.sin(np.pi * s[dsk == d]) + c[1] * np.sin(2 * np.pi * s[dsk == d])
            a += sh[:, None]
        # 하드웨어 불확실성: 체인마다 LSB 3–12 mV, 이득 0.5 %, 오프셋 10 mV, 잡음 1–4 mV (평가기 가정에 맞추지 않음)
        aug = [a * (1 + g.normal(0, 0.005, (n, 1))) + g.normal(0, 0.010, (n, 1))
               + g.normal(0, 1, x.shape) * g.uniform(0.001, 0.004) for a in aug]
        aug = [np.round(a / q) * q for a, q in zip(aug, g.uniform(0.003, 0.012, K))]
        # 등록 곡선: 데이터셋마다 자기 등록 시험 표본(깨끗한 전압 + 같은 곡선 이동). 학습 대상은 등록 시험 외 전부
        reg = self.reg[ok]  # 시험과 같은 등록 시험 표본만 등록 곡선으로
        tgt = ~reg  # 등록 시험 외 모든 표본이 학습 대상 (25 °C 주행 사이클 휴지 포함)
        F0 = self.feats(x)
        end0 = F0[:, 0]
        P0 = pts(x)
        Fs, ys, ws = [], [], []
        ds = dsk
        sb = np.clip((s * 10).astype(int), 0, 9)
        # 데이터셋마다 같은 총 가중치, 그 안에서 SOC 구간(0.1)마다 같은 가중치 (학습 대상 표본 기준)
        w = np.array([1.0 / (tgt & (ds == d) & (sb == b)).sum() / len(set(sb[tgt & (ds == d)])) if t else 0.0
                      for d, b, t in zip(ds, sb, tgt)])
        g6 = np.random.default_rng(40_000 + seed)
        for a, sh in zip(aug, shift):
            F = self.feats(a)
            rs, rm, rn = np.zeros(n), np.zeros((n, npt)), np.zeros(n)
            Pa = pts(a)
            for d in np.unique(dsk):
                i, rr = dsk == d, (dsk == d) & reg
                if rr.sum() >= 3:
                    rs[i] = ref_map(end0[rr] + sh[rr], s[rr], F[i, 0])
                    rm[i] = ref_multi(P0[rr] + sh[rr, None], s[rr], Pa[i]) - rs[i, None]
                    Fr = F0[rr].copy()
                    Fr[:, 0] += sh[rr]
                    rn[i] = ref_knn(Fr, s[rr], F[i]) - rs[i]
            keep = tgt & np.isin(dsk, [d for d in np.unique(dsk) if (reg & (dsk == d)).sum() >= 3])
            tcn = self.temp_c[ok] + g6.normal(0, 2.0, n)  # 주변 온도 + 센서 잡음 2 °C
            Fs.append(np.c_[F, rs, tcn, rm, rn][keep]); ys.append((s - rs)[keep]); ws.append(w[keep])  # 잔차 학습
        wv = np.concatenate(ws)
        m.fit(np.vstack(Fs), np.concatenate(ys), sample_weight=wv / wv.mean())
        return m
