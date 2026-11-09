"""[에이전트가 고치는 유일한 파일] T1 귀환 SOC 추정기.

인터페이스 (eval/run.py가 호출):
  Estimator(seed).fit(train)  train: dict
      rest_V (N,1800) 휴지 전압, 휴지가 끝나면 NaN / pre_V, pre_I (N,300) 휴지 직전
      dataset, chem, cell, temp_c, rest_len, soc (N,)   ※ 시험 때는 rest_V만 주어진다
  Estimator.predict({"rest_V": (M, r)}) -> (M,) SOC 0~1
      r초까지만 보인다(60/300/600). 시험 전압에는 저가 측정 체인 오차가 들어 있다.

기준선: 마지막 휴지 전압 하나 → 학습 셀 전체를 합친 단조(isotonic) OCV 곡선.
"""
import numpy as np
from xgboost import XGBRegressor

LSB = 3.3 / 4096 * (115 / 15)  # 일반 저가 체인 가정: 12 bit ADC + 100k/15k 분압

class Estimator:
    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, train):
        self.rest_V = train["rest_V"]
        self.rest_len = train["rest_len"]
        self.soc = train["soc"]
        self.dataset = train["dataset"]
        self._models = {}
        return self

    @staticmethod
    def feats(v):
        r = v.shape[1]
        end = v[:, -15:].mean(1)
        idx = sorted({9, min(29, r - 6), min(59, r - 6), r // 2})
        pts = np.stack([v[:, max(i - 2, 0):i + 3].mean(1) for i in idx], 1)  # 5점 평균: 양자화·잡음 완화
        return np.c_[end, end[:, None] - pts]

    def predict(self, test):
        v = test["rest_V"]
        r = v.shape[1]
        if r not in self._models:  # 창 길이 r마다 한 번만 학습 (서버에서 예측 1건 100 ms 제약)
            self._models[r] = self._train(r)
        return np.clip(self._models[r].predict(self.feats(v)), 0, 1)

    def _train(self, r):
        ok = self.rest_len >= r
        nf = self.feats(self.rest_V[:1, :r]).shape[1]
        m = XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, objective="reg:absoluteerror",
                         monotone_constraints="(" + ",".join(["1"] * nf) + ")",  # 끝 전압↑·남은 이완↑ → SOC↑
                         random_state=self.seed)
        g = np.random.default_rng(self.seed)
        x, K = self.rest_V[ok, :r], 8
        n = len(x)
        full = self.rest_V[ok]
        last = np.minimum(self.rest_len[ok], full.shape[1])
        vinf = np.array([row[l - 5:l].mean() for row, l in zip(full, last)])[:, None]  # 긴 휴지 끝 ≈ OCV
        # 직전 전류 크기 증강: 과전압 η = vinf − V를 log 균등 0.1–1.5배 (저전류 OCV 시험까지 덮음)
        aug = [vinf - np.exp(g.uniform(np.log(0.1), np.log(1.5), (n, 1))) * (vinf - x) for _ in range(K)]
        # OCV 곡선 모양 무작위화: 사본·데이터셋마다 SOC의 매끄러운 함수로 전압 이동 → 처음 보는 화학계 흉내
        s, dsk = self.soc[ok], self.dataset[ok]
        for a in aug:
            for d in np.unique(dsk):
                c = g.normal(0, 0.015, 2)
                a[dsk == d] += (c[0] * np.sin(np.pi * s[dsk == d]) + c[1] * np.sin(2 * np.pi * s[dsk == d]))[:, None]
        # 하드웨어 불확실성: 체인마다 LSB 3–12 mV, 이득 0.5 %, 오프셋 10 mV, 잡음 1–4 mV (평가기 가정에 맞추지 않음)
        aug = [a * (1 + g.normal(0, 0.005, (n, 1))) + g.normal(0, 0.010, (n, 1))
               + g.normal(0, 1, x.shape) * g.uniform(0.001, 0.004) for a in aug]
        aug = [np.round(a / q) * q for a, q in zip(aug, g.uniform(0.003, 0.012, K))]
        ds = self.dataset[ok]
        w = np.array([1.0 / (ds == d).sum() for d in ds])  # 데이터셋마다 같은 총 가중치
        m.fit(self.feats(np.vstack(aug)), np.tile(self.soc[ok], K), sample_weight=np.tile(w / w.mean(), K))
        return m
