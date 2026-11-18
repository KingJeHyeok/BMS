"""2점 등록(25 °C + 저온 등록 시험 하나) 조회 T2를 dev에서 평가한다. 학습 없음.

T2: 시험 셀의 25 °C 등록 표와 저온(T_low) 등록 표에 같은 끝 전압을 넣어 SOC 두 개를 얻고,
    입력 주변 온도 T(명목 + N(0, 2 °C))로 선형 내삽·외삽한다.
        w = (T − 25) / (T_low − 25),   SOC = clip(SOC_25 + w·(SOC_low − SOC_25), 0, 1)
    사전에 고정: T 선형, 외삽 제한 없음. 민감도: 1/T(K) 선형(T2_invT), w를 [0, 1]로 자름(T2_clip).
dev 설정: T_low = 0 °C, 저온 등록 = 같은 데이터셋 0 °C의 등록 종류 파일(HPPC/incremental OCV) 이름순 첫 번째.
채점: 0 °C 등록 파일이 있는 데이터셋의 IN 폴드 표본 중 25 °C·0 °C가 아닌 것(0 °C의 다른 파일도 뺀다).
비교: B1·T2는 여기서 직접 계산(bench.py와 같은 오차·온도 잡음 시드). B2·S_simple은 analysis/out의 저장 예측(IN 폴드).
홀드아웃·최종 테스트 데이터는 읽지 않는다.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench  # noqa: E402
import variants  # noqa: E402

ev = bench.ev
HERE = os.path.dirname(os.path.abspath(__file__))
T_LOW = 0.0
RS = (60, 300, 600)
SAVED = {"B2": "B2_reg_lookup_temp", "S": "S_simple"}


def reg_at(meta, d, t):
    k = (meta["dataset"] == d) & (meta["temp_c"] == t)
    f = sorted({x for x in meta["file"][k] if ev.REG_FILE.search(x)})
    return (k & (meta["file"] == f[0])) if f else None


def lookup(X, meta, m, r, v):
    rk = m & (meta["rest_len"] >= r)
    return variants.ref_map(variants.feats(X["rest_V"][rk, :r])[:, 0], meta["soc"][rk], variants.feats(v)[:, 0])


def t2(p25, plo, tc, mode):
    if mode == "invT":
        w = (1 / (tc + 273.15) - 1 / 298.15) / (1 / (T_LOW + 273.15) - 1 / 298.15)
    else:
        w = (tc - 25) / (T_LOW - 25)
    if mode == "clip":
        w = np.clip(w, 0, 1)
    if mode == "cold":  # 25 °C 위로는 외삽하지 않는다(따뜻한 쪽은 25 °C 표 그대로)
        w = np.maximum(w, 0)
    return np.clip(p25 + w * (plo - p25), 0, 1)


def compute():
    X, meta = bench.data()
    REG = ev.reg_mask(meta)
    rows = []
    for key, fold, tr, te, kind in bench.folds(meta):
        if kind != "in":
            continue
        rlo = reg_at(meta, fold, T_LOW)
        if rlo is None or rlo.sum() < 3:
            print(f"{fold}: {T_LOW:.0f} °C 등록 파일 없음 → 제외")
            continue
        r25 = (meta["dataset"] == fold) & REG
        lo_file = meta["file"][rlo][0]
        for r in RS:
            sel = te & (meta["rest_len"] >= r)
            idx = np.flatnonzero(sel)
            for s in ev.SEEDS:
                v = ev.corrupt(X["rest_V"][sel], r, 1000 * s + r)
                tc = meta["temp_c"][sel] + np.random.default_rng(5000 + 1000 * s + r).normal(0, ev.TEMP_SD, sel.sum())
                p25, plo = lookup(X, meta, r25, r, v), lookup(X, meta, rlo, r, v)
                out = {"B1": np.clip(p25, 0, 1), "T2": t2(p25, plo, tc, "lin"),
                       "T2_invT": t2(p25, plo, tc, "invT"), "T2_clip": t2(p25, plo, tc, "clip"),
                       "T2_cold": t2(p25, plo, tc, "cold")}
                for m, p in out.items():
                    rows.append(pd.DataFrame({"idx": idx, "r": r, "s": s, "m": m, "err": (p - meta["soc"][sel]) * 100}))
        print(f"{fold}: 저온 등록 = {lo_file} ({rlo.sum()} 표본)")
    D = pd.concat(rows)
    D = D.groupby(["idx", "r", "m"])["err"].mean().unstack("m")
    for m, name in SAVED.items():
        z = np.load(os.path.join(HERE, "out", f"{name}.npz"))
        k = ~np.char.startswith(z["key"].astype(str), "EXT_") & np.isin(z["es"], [0, 1, 2])
        g = pd.DataFrame({"idx": z["idx"][k], "r": z["r"][k], m: (z["pred"][k] - z["soc"][k]) * 100}).groupby(["idx", "r"])[m].mean()
        D = D.join(g, how="left")
    D = D.reset_index()
    D["ds"] = meta["dataset"][D["idx"]]
    D["T"] = meta["temp_c"][D["idx"]]
    D["soc"] = meta["soc"][D["idx"]]
    D = D[(D["T"] != 25) & (D["T"] != T_LOW)]
    return D


def boot_diff(a, b, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    d = np.abs(a) - np.abs(b)
    bs = rng.integers(0, len(d), (B, len(d)))
    return d.mean(), np.percentile(d[bs].mean(1), [2.5, 97.5])


def main():
    D = compute()
    M = ["B1", "B2", "S", "T2", "T2_invT", "T2_clip", "T2_cold"]
    L = ["# 2점 등록 조회 T2 (dev, 학습 없음)", "",
         "T2 = 25 °C 등록 표 + 0 °C 등록 표, 주변 온도로 선형 내삽·외삽. IN 폴드, 25·0 °C 제외 채점. MAE %p, 시드 평균.",
         "B2·S는 저장된 예측(analysis/out), B1·T2는 같은 잡음 시드로 직접 계산.", ""]
    for r in RS:
        Q = D[D["r"] == r].dropna(subset=["S", "B2"])
        L += [f"## r = {r} s (n = {len(Q)})", "", "| 묶음 | n | " + " | ".join(M) + " |", "|---|---|" + "---|" * len(M)]
        groups = [("전체", Q)] + [(f"{d}", g) for d, g in Q.groupby("ds")] + [(f"{t:.0f} °C", g) for t, g in Q.groupby("T")]
        for name, g in groups:
            L.append(f"| {name} | {len(g)} | " + " | ".join(f"{g[m].abs().mean():.2f}" for m in M) + " |")
        L += ["", "편향(전체): " + ", ".join(f"{m} {Q[m].mean():+.2f}" for m in M), ""]
        for t in ["T2", "T2_cold"]:
            for b in ["B1", "B2", "S"]:
                mu, ci = boot_diff(Q[b].values, Q[t].values)
                L.append(f"- {b} − {t} = {mu:+.3f} [{ci[0]:+.2f}, {ci[1]:+.2f}] (표본 부트스트랩, + 이면 {t}가 나음)")
        L.append("")
    txt = "\n".join(L)
    open(os.path.join(HERE, "two_point_dev.md"), "w", encoding="utf-8").write(txt + "\n")
    sys.stdout.buffer.write(txt.encode("utf-8"))


if __name__ == "__main__":
    main()
