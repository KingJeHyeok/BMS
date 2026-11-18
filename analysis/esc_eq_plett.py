"""사후 분석 (리뷰 1차 R2): 평형 OCV 기반 기존 방법 vs RM2P, Plett 시험 2 채점 표본.

평형 OCV 곡선 = Plett processOCV 방식(C/30 충·방전 평균, `prepare_ocv_final3.py` → ocv_eq.npz).
- ESC_eq2:      25 °C·−5 °C 평형 곡선으로 V(z,T) = V25 + a(V−5 − V25), a 양쪽 선형. 휴지 끝 전압(15 s 평균)을 역변환. RM2P와 같은 정보량(두 온도).
- ESC_eq2_b3:   같은 모델에 2RC 외삽 점근 전압(B3)을 넣는다(휴지 미완료 보정).
- ESC_eq_full:  8개 온도 평형 곡선으로 OCV0(z) + T·OCVrel(z) 최소제곱(Plett ESC 그대로). 채점 온도의 평형 OCV도 쓰므로
                 RM2P보다 정보가 많다(완전 특성화 기준선; 채점 DYN 파일은 쓰지 않음).
- ESC_eq_full_b3: 위 + 2RC 점근 전압.
채점 표본·잡음 시드는 시험 2(final3_test.py)와 같다. 확증 판정은 바꾸지 않는다.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench  # noqa: E402
import final3_test as f3  # noqa: E402
import variants  # noqa: E402

ev = bench.ev
HERE = os.path.dirname(os.path.abspath(__file__))
R = 300


def invert(Vz, Z, v):
    Vz = np.maximum.accumulate(Vz + np.arange(len(Vz)) * 1e-9)
    return np.interp(v, Vz, Z)


def main():
    z = np.load("C:/BMS/data/holdout_final3/rest_final3.npz", allow_pickle=False)
    m, V = z["meta"], z["rest_V"]
    o = np.load("C:/BMS/data/holdout_final3/ocv_eq.npz", allow_pickle=False)
    Z = o["soc_grid"]
    curves = {(str(c), float(t)): v for c, t, v in zip(o["cell"], o["temp_c"], o["V"])}
    dis = {(str(c), float(t)): v for c, t, v in zip(o["cell"], o["temp_c"], o["V_dis"])}
    rows = {k: [] for k in ["RM2P", "B1", "ESC_eq2", "ESC_eq2_b3", "ESC_eq_full", "ESC_eq_full_b3", "ESC_dis2", "ESC_dis2_b3", "ESC_dis2_cold", "ESC_dis2_cold_b3"]}
    T_all, C_all = [], []
    for c in sorted(set(m["cell"].tolist())):
        kc = m["cell"] == c
        rk, rk2 = kc & m["is_reg"], kc & m["is_reg2"]
        ref = {"rest_V": V[rk], "soc": m["soc"][rk], "rest_len": m["rest_len"][rk]}
        ref2 = {"rest_V": V[rk2], "soc": m["soc"][rk2], "rest_len": m["rest_len"][rk2]}
        sel = kc & ~m["is_reg"] & ~m["is_reg2"] & (m["temp_c"] != 25) & (m["temp_c"] != -5) & (m["rest_len"] >= R)
        temps = np.array(sorted(t for (cc, t) in curves if cc == c))
        Vs = np.array([curves[(c, t)] for t in temps])
        A = np.c_[np.ones_like(temps), temps]
        coef = np.linalg.lstsq(A, Vs, rcond=None)[0]  # OCV0, OCVrel (z마다)
        V25, Vm5 = curves[(c, 25.0)], curves[(c, -5.0)]
        D25, Dm5 = dis[(c, 25.0)], dis[(c, -5.0)]
        acc = {k: [] for k in rows}
        for s in ev.SEEDS:
            v = ev.corrupt(V[sel], R, 1000 * s + R)
            tc = m["temp_c"][sel].astype(float) + np.random.default_rng(5000 + 1000 * s + R).normal(0, ev.TEMP_SD, sel.sum())
            test = {"rest_V": v, "ref": ref, "ref2": ref2, "t_low": -5.0, "temp_c": tc}
            acc["RM2P"].append(f3.TwoPointCold().predict(test))
            acc["B1"].append(np.clip(variants.RegLookup().predict(test), 0, 1))
            end = variants.feats(v)[:, 0]
            vinf = variants.vinf_2rc(v)
            for tag, vv in [("", end), ("_b3", vinf)]:
                a = (tc - 25) / (-5 - 25)
                acc["ESC_eq2" + tag].append(np.clip([invert(V25 + ai * (Vm5 - V25), Z, e) for ai, e in zip(a, vv)], 0, 1))
                acc["ESC_eq_full" + tag].append(np.clip([invert(coef[0] + t * coef[1], Z, e) for t, e in zip(tc, vv)], 0, 1))
                acc["ESC_dis2" + tag].append(np.clip([invert(D25 + ai * (Dm5 - D25), Z, e) for ai, e in zip(a, vv)], 0, 1))
                acc["ESC_dis2_cold" + tag].append(np.clip([invert(D25 + max(ai, 0) * (Dm5 - D25), Z, e) for ai, e in zip(a, vv)], 0, 1))
        for k in rows:
            rows[k].append(np.mean(acc[k], 0) - m["soc"][sel])
        T_all.append(m["temp_c"][sel])
        C_all.append(m["cell"][sel])
    E = {k: np.concatenate(v) * 100 for k, v in rows.items()}
    T, C = np.concatenate(T_all), np.concatenate(C_all)
    M = list(rows)
    L = ["# 사후 분석: 평형 OCV 기반 기존 방법 vs RM2P (Plett 시험 2 채점 표본, r = 300 s)", "",
         "ESC_eq2 = 25·−5 °C 평형 OCV(Plett processOCV 방식)로 만든 OCV(z,T), 휴지 끝 전압 역변환. _b3 = 2RC 점근 전압 사용.",
         "ESC_eq_full = 8개 온도 평형 OCV로 OCV0 + T·OCVrel 적합(완전 특성화, 채점 온도 OCV 포함 → RM2P보다 정보 많음).",
         "ESC_dis2 = 25·−5 °C C/30 방전 가지(IR 보정) 곡선만 사용: 방전 뒤 휴지의 히스테리시스 가지에 맞춘 공정한 대조. _cold = RM2P와 같은 따뜻한 쪽 규칙. MAE %p / 편향.", "",
         "| 온도 | n | " + " | ".join(M) + " |", "|---|---|" + "---|" * len(M)]
    for g, k in [("전체", np.ones(len(T), bool))] + [(f"{t:g} °C", T == t) for t in np.unique(T)]:
        L.append(f"| {g} | {k.sum()} | " + " | ".join(f"{np.abs(E[x][k]).mean():.2f} / {E[x][k].mean():+.2f}" for x in M) + " |")
    L += ["", "| 셀 | " + " | ".join(M) + " |", "|---|" + "---|" * len(M)]
    for c in sorted(set(C.tolist())):
        k = C == c
        L.append(f"| {c} | " + " | ".join(f"{np.abs(E[x][k]).mean():.2f}" for x in M) + " |")
    L.append("")
    for x in M[1:]:
        cd = np.array([np.abs(E[x][C == c]).mean() - np.abs(E["RM2P"][C == c]).mean() for c in sorted(set(C.tolist()))])
        L.append(f"- {x} − RM2P: 전체 {np.abs(E[x]).mean() - np.abs(E['RM2P']).mean():+.2f}, 셀 평균 {cd.mean():+.2f}, RM2P가 나은 셀 {(cd > 0).sum()}/{len(cd)}")
    txt = "\n".join(L)
    open(os.path.join(HERE, "esc_eq_plett.md"), "w", encoding="utf-8").write(txt + "\n")
    sys.stdout.buffer.write(txt.encode("utf-8"))


if __name__ == "__main__":
    main()
