"""예측 1건 지연(ms) 측정. S_simple·P_full·B1·B2를 dev 첫 폴드에서 학습하고, 표본 1건씩 predict를 반복 호출한다."""
import sys, time, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench, variants
ev = bench.ev

X, meta = bench.data()
REG = ev.reg_mask(meta)
key, fold, tr, te, _ = bench.folds(meta)[0]
reg = (meta["dataset"] == fold) & REG
ref = {"rest_V": X["rest_V"][reg], "soc": meta["soc"][reg], "rest_len": meta["rest_len"][reg]}
train = {k: v[tr] for k, v in X.items()}
train.update({c: meta[c][tr] for c in ["dataset", "chem", "cell", "temp_c", "soc", "rest_len"]})
train["reg"] = REG[tr]
sel = np.where(te & (meta["rest_len"] >= 300))[0][:200]
V = ev.corrupt(X["rest_V"][sel], 300, 300)
T = meta["temp_c"][sel].astype(float)

M = {"S_simple": lambda: variants.Proposed(seed=0, multi=False, knn=False, aug_shape=False, aug_hw=False),
     "P_full": lambda: variants.Proposed(seed=0),
     "B1": lambda: variants.RegLookup(seed=0), "B2": lambda: variants.RegLookupTemp(seed=0)}
print(f"fold {key}, n_train={tr.sum()}, n_query={len(sel)}")
for name, mk in M.items():
    t0 = time.perf_counter(); m = mk().fit(train); tfit = time.perf_counter() - t0
    m.predict({"rest_V": V[:1], "ref": ref, "temp_c": T[:1]})  # warm-up
    ts = []
    for i in range(len(sel)):
        t0 = time.perf_counter()
        m.predict({"rest_V": V[i:i + 1], "ref": ref, "temp_c": T[i:i + 1]})
        ts.append((time.perf_counter() - t0) * 1e3)
    ts = np.array(ts)
    print(f"{name:9s} fit {tfit:6.1f} s | predict 1건 median {np.median(ts):6.2f} ms, P95 {np.percentile(ts, 95):6.2f} ms, max {ts.max():6.2f} ms")
