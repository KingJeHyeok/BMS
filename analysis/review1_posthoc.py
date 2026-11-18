"""리뷰 1차 대응 사후 분석 (확증 판정은 바꾸지 않음).

(a) RM2P 지연(ms)  (b) 측정 체인 오차 없음 vs 있음  (c) 온도 입력 편향 −5/+5/+10 °C (Plett, 시험 2 표본, 사후)
(d) 부하 이력 불일치: dev에서 HPPC 등록 표로 주행 사이클·용량 휴지를 채점  (e) 시험 2 셀별 짝지은 차이 + 정확 부호 검정·부호 뒤집기 순열 검정
"""
import os
import sys
import time
from itertools import product
from math import comb

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b1_gap  # noqa: E402
import bench  # noqa: E402
import final3_test as f3  # noqa: E402
import multi_reg as mr  # noqa: E402
import variants  # noqa: E402

ev = bench.ev
HERE = os.path.dirname(os.path.abspath(__file__))
R = 300
L = ["# 리뷰 1차 대응 사후 분석", "", "모든 항목은 사후 분석이다. 사전 등록 판정은 바꾸지 않는다. MAE %p, r = 300 s.", ""]


def rm2p(p25, plo, tc, t_low):
    return np.clip(p25 + np.maximum((tc - 25) / (t_low - 25), 0) * (plo - p25), 0, 1)


# (a) 지연
X, meta = bench.data()
REG = ev.reg_mask(meta)
d = meta["dataset"] == "Samsung_30T"
r25, r0 = d & REG, mr.tp.reg_at(meta, "Samsung_30T", 0.0)
mk = lambda m: {"rest_V": X["rest_V"][m], "soc": meta["soc"][m], "rest_len": meta["rest_len"][m]}
sel = np.flatnonzero(d & (meta["temp_c"] != 25) & (meta["rest_len"] >= R))[:200]
V = ev.corrupt(X["rest_V"][sel], R, 300)
model = f3.TwoPointCold()
ts = []
for i in range(len(sel)):
    t0 = time.perf_counter()
    model.predict({"rest_V": V[i:i + 1], "ref": mk(r25), "ref2": mk(r0), "t_low": 0.0, "temp_c": meta["temp_c"][sel[i:i + 1]].astype(float)})
    ts.append((time.perf_counter() - t0) * 1e3)
ts = np.array(ts)
L += ["## (a) RM2P 지연 (표본 1건씩 200회, 노트북 CPU, 등록 표 맞춤 포함)", "",
      f"median {np.median(ts):.2f} ms, P95 {np.percentile(ts, 95):.2f} ms, max {ts.max():.2f} ms", ""]

# (b) 측정 체인 오차 유무 (dev IN, 25·0 °C 제외; Plett 시험 2 표본)
def clean_vs_noisy(run_fn):
    orig = ev.corrupt
    out = {}
    for tag, fn in [("오차 있음", orig), ("오차 없음", lambda v, r, s: v[:, :r].copy())]:
        ev.corrupt = fn
        E, T = run_fn(R)
        out[tag] = {k: np.abs(E[k]).mean() for k in ["B1", "T2_cold"]}
    ev.corrupt = orig
    return out


L += ["## (b) 저가 측정 체인 오차 유무", "", "| 데이터 | 조건 | B1 | RM2P |", "|---|---|---|---|"]
for name, fn in [("dev", mr.run_dev), ("Plett (사후)", mr.run_plett)]:
    for tag, m in clean_vs_noisy(fn).items():
        L.append(f"| {name} | {tag} | {m['B1']:.2f} | {m['T2_cold']:.2f} |")
L.append("")

# (c) 온도 입력 편향 (Plett 시험 2 표본, 사후): RM2P, B2, S
z = np.load("C:/BMS/data/holdout_final3/rest_final3.npz", allow_pickle=False)
m3 = z["meta"]
T3 = {"rest_V": z["rest_V"], **{c: m3[c] for c in ["dataset", "cell", "temp_c", "soc", "rest_len", "is_reg", "is_reg2", "raw_n60"]}}
train = f3.train_dict(None)
models = {"RM2P": f3.TwoPointCold(), "B2": variants.RegLookupTemp().fit(train),
          "S": [variants.Proposed(s, multi=False, knn=False, aug_shape=False, aug_hw=False).fit(train) for s in range(5)]}
res = {(k, b): [] for k in models for b in (-5, 0, 5, 10)}
for c in sorted(set(m3["cell"].tolist())):
    kc = m3["cell"] == c
    rk, rk2 = kc & m3["is_reg"], kc & m3["is_reg2"]
    ref = {"rest_V": T3["rest_V"][rk], "soc": m3["soc"][rk], "rest_len": m3["rest_len"][rk]}
    ref2 = {"rest_V": T3["rest_V"][rk2], "soc": m3["soc"][rk2], "rest_len": m3["rest_len"][rk2]}
    sel = kc & ~m3["is_reg"] & ~m3["is_reg2"] & (m3["temp_c"] != 25) & (m3["temp_c"] != -5) & (m3["rest_len"] >= R)
    acc = {key: [] for key in res}
    for s in ev.SEEDS:
        v = ev.corrupt(T3["rest_V"][sel], R, 1000 * s + R)
        tc0 = m3["temp_c"][sel].astype(float) + np.random.default_rng(5000 + 1000 * s + R).normal(0, ev.TEMP_SD, sel.sum())
        for b in (-5, 0, 5, 10):
            test = {"rest_V": v, "ref": ref, "ref2": ref2, "t_low": -5.0, "temp_c": tc0 + b}
            for k, mm in models.items():
                p = np.mean([x.predict(test) for x in mm], 0) if isinstance(mm, list) else mm.predict(test)
                acc[(k, b)].append(np.clip(p, 0, 1))
    for key in res:  # 시험 2와 같게: 오차 시드 평균 예측의 절대 오차
        res[key].append(np.abs(np.mean(acc[key], 0) - m3["soc"][sel]))
L += ["## (c) 온도 입력 편향 민감도 (Plett 시험 2 표본, 사후). 입력 = 명목 + N(0, 2 °C) + 편향", "",
      "| 방법 | −5 °C | 0 | +5 °C | +10 °C |", "|---|---|---|---|---|"]
for k in models:
    L.append(f"| {k} | " + " | ".join(f"{np.concatenate(res[(k, b)]).mean() * 100:.2f}" for b in (-5, 0, 5, 10)) + " |")
L.append("")

# (d) 부하 이력 불일치 (dev): 등록은 HPPC, 채점 휴지의 시험 종류별 MAE
L += ["## (d) 부하 이력: dev에서 등록(HPPC) 표로 시험 종류별 채점 휴지를 읽은 MAE (IN, 25·0 °C 제외)", "",
      "| 시험 종류 | n | B1 | RM2P |", "|---|---|---|---|"]
E_all, idx_all = {"B1": [], "T2_cold": []}, []
for fold in ev.FOLDS:
    dd = meta["dataset"] == fold
    if mr.tp.reg_at(meta, fold, 0.0) is None:
        continue
    sel = dd & (meta["temp_c"] != 25) & (meta["rest_len"] >= R)
    tables = {25: mr.tab_of(X["rest_V"], meta["soc"], meta["rest_len"], dd & REG),
              0.0: mr.tab_of(X["rest_V"], meta["soc"], meta["rest_len"], mr.tp.reg_at(meta, fold, 0.0))}
    errs = {"B1": [], "T2_cold": []}
    for s in ev.SEEDS:
        v = ev.corrupt(X["rest_V"][sel], R, 1000 * s + R)
        tc = meta["temp_c"][sel] + np.random.default_rng(5000 + 1000 * s + R).normal(0, ev.TEMP_SD, sel.sum())
        p25, plo = mr.lookup(tables[25], R, v), mr.lookup(tables[0.0], R, v)
        errs["B1"].append(np.abs(np.clip(p25, 0, 1) - meta["soc"][sel]))
        errs["T2_cold"].append(np.abs(rm2p(p25, plo, tc, 0.0) - meta["soc"][sel]))
    keep = meta["temp_c"][sel] != 0
    for k in errs:
        E_all[k].append(np.mean(errs[k], 0)[keep] * 100)
    idx_all.append(np.flatnonzero(sel)[keep])
idx_all = np.concatenate(idx_all)
types = np.array([b1_gap.test_type(f) for f in meta["file"][idx_all]])
E_all = {k: np.concatenate(v) for k, v in E_all.items()}
for t in sorted(set(types.tolist())):
    k = types == t
    L.append(f"| {t} | {k.sum()} | {E_all['B1'][k].mean():.2f} | {E_all['T2_cold'][k].mean():.2f} |")
L.append("")

# (e) 시험 2 셀별 짝지은 차이와 셀 단위 검정
def per(name):
    q = dict(np.load(os.path.join(HERE, "final3_out", f"{name}.npz")))
    return f3.per_sample(q, {"soc": m3["soc"]})


u, eT, _ = per("T2_cold")
L += ["## (e) 시험 2 셀별 MAE와 짝지은 차이 (방법 − RM2P), 셀 단위 검정", "",
      "| 셀 | RM2P | B1 | B2 | S | B1 − RM2P | B2 − RM2P | S − RM2P |", "|---|---|---|---|---|---|---|---|"]
D = {}
for name, lab in [("B1_reg_lookup", "B1"), ("B2_reg_lookup_temp", "B2"), ("S_simple", "S")]:
    u2, e2, _ = per(name)
    assert np.array_equal(u, u2)
    D[lab] = e2
cells = sorted(set(m3["cell"][u].tolist()))
diffs = {k: [] for k in D}
for c in cells:
    k = m3["cell"][u] == c
    row = [eT[k].mean()] + [D[x][k].mean() for x in D]
    for x in D:
        diffs[x].append(D[x][k].mean() - eT[k].mean())
    L.append(f"| {c} | " + " | ".join(f"{v:.2f}" for v in row) + " | " + " | ".join(f"{diffs[x][-1]:+.2f}" for x in D) + " |")
L.append("")
n = len(cells)
for x in D:
    dv = np.array(diffs[x])
    pos = int((dv > 0).sum())
    p_sign = min(1.0, 2 * sum(comb(n, i) for i in range(max(pos, n - pos), n + 1)) / 2 ** n)
    flips = np.array(list(product([-1, 1], repeat=n)))
    null = (flips * dv).mean(1)
    p_perm = (np.abs(null) >= abs(dv.mean()) - 1e-12).mean()
    L.append(f"- {x} − RM2P: 셀 평균 차이 {dv.mean():+.2f}, RM2P가 나은 셀 {pos}/{n}, 정확 부호 검정 p = {p_sign:.3f}, "
             f"부호 뒤집기 순열 검정(2^{n}) p = {p_perm:.3f}")
L += ["", "주: 셀 6개로 가능한 최소 양측 p는 부호 검정 0.031, 순열 검정 0.031이다."]
txt = "\n".join(L)
open(os.path.join(HERE, "review1_posthoc.md"), "w", encoding="utf-8").write(txt + "\n")
sys.stdout.buffer.write(txt.encode("utf-8"))
