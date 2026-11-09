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
from sklearn.linear_model import LogisticRegression
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
        return self

    @staticmethod
    def feats(v):
        r = v.shape[1]
        end = v[:, -5:].mean(1)
        idx = sorted({9, min(29, r - 6), min(59, r - 6), r // 2})
        return np.c_[end, end[:, None] - v[:, idx]]

    def predict(self, test):
        v = test["rest_V"]
        r = v.shape[1]
        ok = self.rest_len >= r
        m = XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, objective="reg:absoluteerror",
                         monotone_constraints="(1" + ",0" * (self.feats(v[:1]).shape[1] - 1) + ")",
                         random_state=self.seed)
        g = np.random.default_rng(self.seed)
        x, K = self.rest_V[ok, :r], 8
        n = len(x)
        aug = [x * (1 + g.normal(0, 0.003, (n, 1))) + g.normal(0, 0.006, (n, 1)) + g.normal(0, 0.002, x.shape)
               for _ in range(K)]
        aug = [np.round(a / LSB) * LSB for a in aug]
        ds = self.dataset[ok]
        w = np.array([1.0 / (ds == d).sum() for d in ds])  # 데이터셋마다 같은 총 가중치
        F, Y = self.feats(np.vstack(aug)), np.tile(self.soc[ok], K)
        D, W = np.tile(ds, K), np.tile(w / w.mean(), K)
        m.fit(F, Y, sample_weight=W)
        # 데이터셋별 전문가 + 전류 불변 형태(로그 비율 Δt/Δ9) 게이트
        doms = np.unique(ds)
        ex = [XGBRegressor(**m.get_params()).fit(F[D == d], Y[D == d]) for d in doms]
        gx = lambda A: np.log((np.maximum(A[:, 2:], 0) + LSB) / (np.maximum(A[:, 1:2], 0) + LSB))  # noqa: E731
        gate = LogisticRegression(C=0.1, max_iter=1000).fit(gx(F), D, sample_weight=W)
        Ft = self.feats(v)
        P = gate.predict_proba(gx(Ft))
        moe = sum(P[:, k] * e.predict(Ft) for k, e in enumerate(ex))
        return np.clip(0.5 * m.predict(Ft) + 0.5 * moe, 0, 1)
