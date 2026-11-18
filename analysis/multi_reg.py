"""사후 분석: 등록 온도를 늘리면 얼마나 좋아지나 (다점 등록 상한, leave-one-temperature-out).

TN_loto: 시험 셀의 등록 표를 "시험 표본의 온도를 뺀" 모든 온도에서 만들고, 주변 온도로 SOC를 구간 선형 내삽한다.
  - 가장 추운 표보다 추우면 가장 추운 두 표로 선형 외삽, 가장 따뜻한 표보다 따뜻하면 가장 따뜻한 표 그대로(T2_cold와 같은 규칙).
  - 시험 표본의 명목 온도와 같은 온도의 표는 쓰지 않는다(자기 조회 방지).
비교: B1(25 °C), T2_cold(25 °C + 저온 1개). 채점 표본·잡음 시드는 각 시험의 정의와 같다.
dev(IN 폴드), E66(이미 쓴 시험, 사후), Plett(확증 시험 데이터, 사후). 확증 판정은 바꾸지 않는다.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench  # noqa: E402
import two_point as tp  # noqa: E402
import variants  # noqa: E402

ev = bench.ev
HERE = os.path.dirname(os.path.abspath(__file__))
RS = (60, 300, 600)


def lookup(tab, r, v):
    Vr, sr, ln = tab
    k = ln >= r
    return variants.ref_map(variants.feats(Vr[k, :r])[:, 0], sr[k], variants.feats(v)[:, 0])


def interp(P, temps, tc):
    """P: (n_tab, n) 표별 SOC, temps 오름차순. tc: (n,) 입력 온도. 구간 선형, 추운 쪽 외삽, 따뜻한 쪽 평탄."""
    out = np.empty(P.shape[1])
    for i, t in enumerate(tc):
        if t >= temps[-1]:
            out[i] = P[-1, i]
        elif t <= temps[0]:
            if len(temps) == 1:
                out[i] = P[0, i]
            else:
                w = (t - temps[0]) / (temps[1] - temps[0])
                out[i] = P[0, i] + w * (P[1, i] - P[0, i])
        else:
            j = np.searchsorted(temps, t) - 1
            w = (t - temps[j]) / (temps[j + 1] - temps[j])
            out[i] = P[j, i] + w * (P[j + 1, i] - P[j, i])
    return np.clip(out, 0, 1)


def evaluate(V, soc, Tnom, tables, t_low, r, seed_sel):
    """한 셀(또는 데이터셋)의 채점 표본 V(깨끗한 값)에 대해 방법별 오차(시드 평균, %p)."""
    errs = {"B1": [], "T2_cold": [], "TN_loto": []}
    for s in ev.SEEDS:
        v = ev.corrupt(V, r, 1000 * s + r)
        tc = Tnom + np.random.default_rng(5000 + 1000 * s + r).normal(0, ev.TEMP_SD, len(Tnom))
        P = {t: lookup(tab, r, v) for t, tab in tables.items()}
        p25, plo = P[25], P[t_low]
        errs["B1"].append(np.clip(p25, 0, 1) - soc)
        errs["T2_cold"].append(np.clip(p25 + np.maximum((tc - 25) / (t_low - 25), 0) * (plo - p25), 0, 1) - soc)
        pn = np.empty(len(soc))
        for t0 in np.unique(Tnom):
            j = Tnom == t0
            ts = np.array(sorted(t for t in tables if t != t0))
            pn[j] = interp(np.array([P[t][j] for t in ts]), ts, tc[j])
        errs["TN_loto"].append(pn - soc)
    return {k: np.mean(v, 0) * 100 for k, v in errs.items()}


def tab_of(V, soc, ln, m):
    return (V[m], soc[m], ln[m])


def run_dev(r):
    X, meta = bench.data()
    REG = ev.reg_mask(meta)
    E, Tall = {}, []
    for fold in ev.FOLDS:
        d = meta["dataset"] == fold
        temps = sorted({float(t) for t in meta["temp_c"][d]})
        tables = {}
        for t in temps:
            m = REG & d if t == 25 else tp.reg_at(meta, fold, t)
            if m is not None and (m & (meta["rest_len"] >= r)).sum() >= 3:
                tables[t] = tab_of(X["rest_V"], meta["soc"], meta["rest_len"], m)
        if 0.0 not in tables:
            continue
        sel = d & (meta["temp_c"] != ev.REF_T) & (meta["rest_len"] >= r)  # bench IN 폴드와 같은 선택(잡음 같게)
        e = evaluate(X["rest_V"][sel], meta["soc"][sel], meta["temp_c"][sel].astype(float), tables, 0.0, r, None)
        keep = meta["temp_c"][sel] != 0
        for k in e:
            E.setdefault(k, []).append(e[k][keep])
        Tall.append(meta["temp_c"][sel][keep])
    return {k: np.concatenate(v) for k, v in E.items()}, np.concatenate(Tall)


def run_e66(r):
    z = np.load("C:/BMS/data/holdout_final/rest_final.npz", allow_pickle=False)
    m, V = z["meta"], z["rest_V"]
    e66 = m["dataset"] == "LG_E66"
    gitt = np.char.endswith(m["file"].astype(str), "_GITT.mat")
    tables = {}
    for t in sorted({float(t) for t in m["temp_c"][e66]}):
        mm = e66 & m["is_reg"] if t == 25 else e66 & gitt & (m["temp_c"] == t)
        if (mm & (m["rest_len"] >= r)).sum() >= 3:
            tables[t] = tab_of(V, m["soc"], m["rest_len"], mm)
    sel = e66 & ~m["is_reg"] & (m["temp_c"] != ev.REF_T) & (m["rest_len"] >= r)
    e = evaluate(V[sel], m["soc"][sel], m["temp_c"][sel].astype(float), tables, 0.0, r, None)
    keep = m["temp_c"][sel] != 0
    return {k: v[keep] for k, v in e.items()}, m["temp_c"][sel][keep]


def run_plett(r):
    z = np.load("C:/BMS/data/holdout_final3/rest_final3.npz", allow_pickle=False)
    m, V = z["meta"], z["rest_V"]
    E, Tall = {}, []
    for c in sorted(set(m["cell"].tolist())):
        kc = m["cell"] == c
        tables = {}
        for t in sorted({float(t) for t in m["temp_c"][kc]}):
            mm = kc & (m["is_reg"] if t == 25 else m["is_reg2"] if t == -5 else (m["temp_c"] == t))
            if (mm & (m["rest_len"] >= r)).sum() >= 3:
                tables[t] = tab_of(V, m["soc"], m["rest_len"], mm)
        sel = kc & ~m["is_reg"] & ~m["is_reg2"] & (m["temp_c"] != 25) & (m["temp_c"] != -5) & (m["rest_len"] >= r)
        e = evaluate(V[sel], m["soc"][sel], m["temp_c"][sel].astype(float), tables, -5.0, r, None)
        for k in e:
            E.setdefault(k, []).append(e[k])
        Tall.append(m["temp_c"][sel])
    return {k: np.concatenate(v) for k, v in E.items()}, np.concatenate(Tall)


def main():
    L = ["# 사후 분석: 다점 등록 상한 (leave-one-temperature-out)", "",
         "TN_loto = 시험 온도를 뺀 모든 온도의 등록 표를 구간 선형 내삽(추운 쪽 외삽, 따뜻한 쪽 평탄). MAE %p / 편향.",
         "E66·Plett는 이미 쓴 시험 데이터라 사후 분석이다. 사전 등록 판정은 바꾸지 않는다.", ""]
    for name, fn in [("dev (IN, 25·0 °C 제외)", run_dev), ("LG E66 (0 °C 제외, 사후)", run_e66), ("Plett ESC (확증 채점 표본, 사후)", run_plett)]:
        for r in RS:
            E, T = fn(r)
            L += [f"## {name}, r = {r} s (n = {len(T)})", "", "| 온도 | n | B1 | T2_cold | TN_loto |", "|---|---|---|---|---|"]
            for g, k in [("전체", np.ones(len(T), bool))] + [(f"{t:g} °C", T == t) for t in np.unique(T)]:
                L.append(f"| {g} | {k.sum()} | " + " | ".join(f"{np.abs(E[mm][k]).mean():.2f} / {E[mm][k].mean():+.2f}"
                                                            for mm in ["B1", "T2_cold", "TN_loto"]) + " |")
            L.append("")
    txt = "\n".join(L)
    open(os.path.join(HERE, "multi_reg.md"), "w", encoding="utf-8").write(txt + "\n")
    sys.stdout.buffer.write(txt.encode("utf-8"))


if __name__ == "__main__":
    main()
