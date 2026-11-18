"""기존 방법 비교: 전압 영역 온도 OCV 모델(ESC식) vs 제안 T2_cold(SOC 영역 내삽).

ESC2 (Plett ESC의 OCV(z,T) = OCV0(z) + T·OCVrel(z) 형태를 등록 표 2개로 만든 것):
  - 25 °C, T_low 등록 표로 SOC 격자 z에서 전압 V25(z), Vlow(z)를 단조 보간으로 구한다.
  - V(z,T) = V25(z) + a(T)·(Vlow(z) − V25(z)), a = (T − 25)/(T_low − 25). ESC처럼 양쪽 모두 선형(외삽 제한 없음).
  - 끝 전압 v를 V(z,T)에 대해 역변환(z 격자에서 단조 보간)해 SOC를 얻는다.
ESC2_cold: a = max(a, 0) (T2_cold와 같은 따뜻한 쪽 규칙) — 영역 차이만 보려는 대조.
dev는 개발 데이터(판단에 써도 됨). E66·Plett는 이미 쓴 시험 데이터라 사후 분석이다.
"""
import os
import sys

import numpy as np
from sklearn.isotonic import IsotonicRegression

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench  # noqa: E402
import multi_reg as mr  # noqa: E402
import variants  # noqa: E402

ev = bench.ev
HERE = os.path.dirname(os.path.abspath(__file__))
Z = np.linspace(0, 1, 201)


def v_of_z(tab, r):
    Vr, sr, ln = tab
    k = ln >= r
    end = variants.feats(Vr[k, :r])[:, 0]
    iso = IsotonicRegression(out_of_bounds="clip").fit(sr[k], end)  # SOC → 전압 (단조 증가)
    return iso.predict(Z)


def invert(Vz, v):
    Vz = np.maximum.accumulate(Vz + np.arange(len(Vz)) * 1e-9)  # 엄격 단조
    return np.interp(v, Vz, Z)


def esc_pred(tables, t_low, r, v, tc, cold):
    V25, Vlo = v_of_z(tables[25], r), v_of_z(tables[t_low], r)
    a = (tc - 25) / (t_low - 25)
    if cold:
        a = np.maximum(a, 0)
    end = variants.feats(v)[:, 0]
    return np.array([invert(V25 + ai * (Vlo - V25), e) for ai, e in zip(a, end)])


VG = np.linspace(2.0, 4.5, 2501)


def v_of_z_inv(tab, r):
    """RM2P와 같은 표(전압 → SOC 단조 회귀 g_T)를 뒤집어 V_T(z)를 얻는다. 회귀 방향 차이를 없앤 대조."""
    Vr, sr, ln = tab
    k = ln >= r
    end = variants.feats(Vr[k, :r])[:, 0]
    g = IsotonicRegression(out_of_bounds="clip").fit(end, sr[k]).predict(VG)
    g = g + np.arange(len(g)) * 1e-9
    return np.interp(Z, g, VG)


def esc_inv_pred(tables, t_low, r, v, tc):
    V25, Vlo = v_of_z_inv(tables[25], r), v_of_z_inv(tables[t_low], r)
    a = np.maximum((tc - 25) / (t_low - 25), 0)
    end = variants.feats(v)[:, 0]
    return np.array([invert(V25 + ai * (Vlo - V25), e) for ai, e in zip(a, end)])


def evaluate(V, soc, Tnom, tables, t_low, r):
    out = {"B1": [], "T2_cold": [], "ESC2": [], "ESC2_cold": [], "ESC2_inv": []}
    for s in ev.SEEDS:
        v = ev.corrupt(V, r, 1000 * s + r)
        tc = Tnom + np.random.default_rng(5000 + 1000 * s + r).normal(0, ev.TEMP_SD, len(Tnom))
        p25, plo = mr.lookup(tables[25], r, v), mr.lookup(tables[t_low], r, v)
        out["B1"].append(np.clip(p25, 0, 1) - soc)
        out["T2_cold"].append(np.clip(p25 + np.maximum((tc - 25) / (t_low - 25), 0) * (plo - p25), 0, 1) - soc)
        out["ESC2"].append(esc_pred(tables, t_low, r, v, tc, False) - soc)
        out["ESC2_cold"].append(esc_pred(tables, t_low, r, v, tc, True) - soc)
        out["ESC2_inv"].append(esc_inv_pred(tables, t_low, r, v, tc) - soc)
    return {k: np.mean(x, 0) * 100 for k, x in out.items()}


mr.evaluate = lambda V, soc, Tnom, tables, t_low, r, _: evaluate(V, soc, Tnom, tables, t_low, r)  # multi_reg의 표본 선택 재사용


def main():
    L = ["# 기존 방법 비교: 전압 영역 ESC식 온도 OCV(ESC2) vs SOC 영역 T2_cold", "",
         "같은 등록 표 2개(25 °C + 저온). MAE %p / 편향. dev는 개발 데이터, E66·Plett는 사후 분석.",
         "ESC2_inv = RM2P와 같은 표(전압→SOC)를 뒤집어 전압 영역에서 내삽, 따뜻한 쪽 규칙도 같음 → RM2P와 차이는 '내삽 영역'뿐(리뷰 1차 R3).", ""]
    for name, fn in [("dev (IN, 25·0 °C 제외)", mr.run_dev), ("LG E66 (사후)", mr.run_e66), ("Plett ESC (사후)", mr.run_plett)]:
        for r in (60, 300, 600):
            E, T = fn(r)
            M = ["B1", "T2_cold", "ESC2", "ESC2_cold", "ESC2_inv"]
            L += [f"## {name}, r = {r} s (n = {len(T)})", "", "| 온도 | n | " + " | ".join(M) + " |", "|---|---|" + "---|" * len(M)]
            for g, k in [("전체", np.ones(len(T), bool))] + [(f"{t:g} °C", T == t) for t in np.unique(T)]:
                L.append(f"| {g} | {k.sum()} | " + " | ".join(f"{np.abs(E[m][k]).mean():.2f} / {E[m][k].mean():+.2f}" for m in M) + " |")
            L.append("")
            for mm in ["ESC2", "ESC2_cold", "ESC2_inv"]:
                d = np.abs(E[mm]) - np.abs(E["T2_cold"])
                bs = np.random.default_rng(0).integers(0, len(d), (2000, len(d)))
                lo, hi = np.percentile(d[bs].mean(1), [2.5, 97.5])
                L.append(f"- {mm} − T2_cold = {d.mean():+.3f} [{lo:+.2f}, {hi:+.2f}] (표본 부트스트랩, + 이면 T2_cold가 나음)")
            L.append("")
    txt = "\n".join(L)
    open(os.path.join(HERE, "esc_compare.md"), "w", encoding="utf-8").write(txt + "\n")
    sys.stdout.buffer.write(txt.encode("utf-8"))


if __name__ == "__main__":
    main()
