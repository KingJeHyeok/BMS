"""[에이전트가 고치는 유일한 파일] T1 귀환 SOC 추정기.

인터페이스 (eval/run.py가 호출):
  Estimator(seed).fit(train)  train: dict
      rest_V (N,1800) 휴지 전압, 휴지가 끝나면 NaN / pre_V, pre_I (N,300) 휴지 직전
      dataset, chem, cell, temp_c, rest_len, soc (N,)   ※ 시험 때는 rest_V와 ref만 주어진다
  Estimator.predict({"rest_V": (M, r), "ref": {...}}) -> (M,) SOC 0~1
      r초까지만 보인다(60/300/600). 시험 전압에는 저가 측정 체인 오차가 들어 있다.
      ref = 시험 셀 종류의 25 °C 등록 데이터(깨끗한 rest_V, soc, rest_len). 채점은 25 °C 외 온도만.

방법: 등록 곡선(25 °C 끝 전압 → SOC)의 단조 OCV 표를 특징 하나로 넣고, 학습 셀도 각자 자기 25 °C 데이터를 등록 곡선으로 쓴다.
"""
import numpy as np
from sklearn.isotonic import IsotonicRegression
from xgboost import XGBRegressor

REF_T = 25


def ref_map(ref_end, ref_soc, end):
    """등록 곡선의 단조 OCV 표로 끝 전압 → SOC."""
    iso = IsotonicRegression(out_of_bounds="clip").fit(ref_end, ref_soc)
    return iso.predict(end)


class Estimator:
    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, train):
        self.rest_V = train["rest_V"]
        self.rest_len = train["rest_len"]
        self.soc = train["soc"]
        self.dataset = train["dataset"]
        self.temp_c = train["temp_c"]
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
        F = np.c_[self.feats(v), rs]
        return np.clip(np.mean([m.predict(F) for m in self._models[r]], 0), 0, 1)

    def _train(self, r, seed):
        ok = self.rest_len >= r
        nf = self.feats(self.rest_V[:1, :r]).shape[1] + 1
        m = XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, objective="reg:absoluteerror",
                         monotone_constraints="(" + ",".join(["1"] * (nf - 2) + ["0", "1"]) + ")",  # 끝 전압·Δ +1, frac 자유, 등록 SOC +1
                         random_state=seed)
        g = np.random.default_rng(seed)
        x, K = self.rest_V[ok, :r], 8
        n = len(x)
        full = self.rest_V[ok]
        last = np.minimum(self.rest_len[ok], full.shape[1])
        vinf = np.array([row[l - 5:l].mean() for row, l in zip(full, last)])[:, None]  # 긴 휴지 끝 ≈ OCV
        # 직전 전류 크기 증강: 과전압 η = vinf − V를 log 균등 0.1–1.5배 (저전류 OCV 시험까지 덮음)
        aug = [vinf - np.exp(g.uniform(np.log(0.1), np.log(1.5), (n, 1))) * (vinf - x) for _ in range(K)]
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
        # 등록 곡선: 데이터셋마다 자기 25 °C 표본(깨끗한 전압 + 같은 곡선 이동). 학습 대상은 시험과 같이 25 °C 외만
        reg = self.temp_c[ok] == REF_T
        tgt = ~reg
        end0 = self.feats(x)[:, 0]
        Fs, ys, ws = [], [], []
        ds = dsk
        sb = np.clip((s * 10).astype(int), 0, 9)
        # 데이터셋마다 같은 총 가중치, 그 안에서 SOC 구간(0.1)마다 같은 가중치 (25 °C 외 표본 기준)
        w = np.array([1.0 / (tgt & (ds == d) & (sb == b)).sum() / len(set(sb[tgt & (ds == d)])) if t else 0.0
                      for d, b, t in zip(ds, sb, tgt)])
        for a, sh in zip(aug, shift):
            F = self.feats(a)
            rs = np.zeros(n)
            for d in np.unique(dsk):
                i, rr = dsk == d, (dsk == d) & reg
                if rr.sum() >= 3:
                    rs[i] = ref_map(end0[rr] + sh[rr], s[rr], F[i, 0])
            keep = tgt & np.isin(dsk, [d for d in np.unique(dsk) if (reg & (dsk == d)).sum() >= 3])
            Fs.append(np.c_[F, rs][keep]); ys.append(s[keep]); ws.append(w[keep])
        wv = np.concatenate(ws)
        m.fit(np.vstack(Fs), np.concatenate(ys), sample_weight=wv / wv.mean())
        return m
