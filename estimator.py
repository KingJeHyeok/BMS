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


class Estimator:
    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, train):
        self.rest_V = train["rest_V"]
        self.rest_len = train["rest_len"]
        self.soc = train["soc"]
        return self

    @staticmethod
    def feats(v):
        r = v.shape[1]
        end = v[:, -5:].mean(1)
        return np.c_[end, end - v[:, r // 2], end - v[:, 9]]

    def predict(self, test):
        v = test["rest_V"]
        r = v.shape[1]
        ok = self.rest_len >= r
        m = XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8,
                         monotone_constraints="(1,0,0)", random_state=self.seed)
        m.fit(self.feats(self.rest_V[ok, :r]), self.soc[ok])
        return np.clip(m.predict(self.feats(v)), 0, 1)
