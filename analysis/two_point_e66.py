"""탐색적(사후) 분석: 2점 등록 조회 T2_cold를 이미 쓴 최종 테스트 셀 LG E66에 적용한다.

- 확증 시험이 아니다. E66은 11-11 사전 등록 시험에 이미 썼다. 그래서 결과는 "사후 분석"으로만 보고한다.
- T2_cold는 커밋 7d4bbc5에서 dev만 보고 고정했다. 학습할 매개변수가 없어 E66에 맞출 것이 없다.
- 저온 등록 = E66 0 °C GITT 파일(25 °C 등록이 GITT라 같은 종류). 채점 = 25·0 °C가 아닌 표본(−20, −10, 10, 40 °C).
- 비교 대상은 저장된 1회 실행 예측(analysis/final_out/nominal_*.npz)을 읽기만 한다. B1은 다시 계산해 저장값과 같은지 확인한다.
- P42A는 저온 등록 후보가 5 °C뿐이라 채점이 40 °C만 남고, 거기서 T2_cold = B1이라 뺀다.
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
FINAL = "C:/BMS/data/holdout_final/rest_final.npz"
SAVED = {"B1": "B1_reg_lookup", "B2": "B2_reg_lookup_temp", "S": "S_simple", "P": "P_full"}


def main():
    z = np.load(FINAL, allow_pickle=False)
    m, V = z["meta"], z["rest_V"]
    e66 = m["dataset"] == "LG_E66"
    r25 = e66 & m["is_reg"]
    lo = e66 & (m["temp_c"] == 0) & np.char.endswith(m["file"].astype(str), "_GITT.mat")
    print("25 °C 등록:", r25.sum(), " 0 °C 등록(GITT):", lo.sum())
    soc = m["soc"]
    L = ["# 탐색적: 2점 등록 조회 T2_cold를 LG E66에 적용 (사후 분석, 확증 아님)", "",
         "T2_cold(커밋 7d4bbc5에서 dev로 고정) = 25 °C GITT 표 + 0 °C GITT 표, 25 °C 위로는 외삽 안 함.",
         "채점 = −20, −10, 10, 40 °C(0 °C 전부 제외). 비교 대상은 11-11 1회 실행의 저장 예측. MAE %p, 오차 시드 평균.", ""]
    for r in (60, 300, 600):
        sel = e66 & ~m["is_reg"] & (m["temp_c"] != ev.REF_T) & (m["rest_len"] >= r)  # final_test.py와 같은 선택(잡음 같게)
        idx = np.flatnonzero(sel)
        err = {"B1*": [], "T2_cold": [], "T2": []}
        for s in ev.SEEDS:
            v = ev.corrupt(V[sel], r, 1000 * s + r)
            tc = m["temp_c"][sel].astype(float) + np.random.default_rng(5000 + 1000 * s + r).normal(0, ev.TEMP_SD, sel.sum())
            p25, plo = tp.lookup({"rest_V": V}, m, r25, r, v), tp.lookup({"rest_V": V}, m, lo, r, v)
            err["B1*"].append(np.clip(p25, 0, 1) - soc[sel])
            err["T2_cold"].append(tp.t2(p25, plo, tc, "cold") - soc[sel])
            err["T2"].append(tp.t2(p25, plo, tc, "lin") - soc[sel])
        E = {k: np.mean(v, 0) * 100 for k, v in err.items()}
        for k, name in SAVED.items():
            q = np.load(os.path.join(HERE, "final_out", f"nominal_{name}.npz"))
            kk = q["r"] == r
            acc = np.zeros(len(m)); cnt = np.zeros(len(m))
            np.add.at(acc, q["idx"][kk], q["pred"][kk]); np.add.at(cnt, q["idx"][kk], 1)
            E[k] = (acc[idx] / cnt[idx] - soc[idx]) * 100
        keep = m["temp_c"][idx] != 0
        T = m["temp_c"][idx][keep]
        E = {k: v[keep] for k, v in E.items()}
        M = ["B1", "B2", "S", "P", "T2_cold", "T2"]
        L += [f"## r = {r} s (n = {keep.sum()})", "", f"B1 재계산 확인: max |B1* − B1| = {np.abs(E['B1*'] - E['B1']).max():.2e} %p", "",
              "| 온도 | n | " + " | ".join(M) + " |", "|---|---|" + "---|" * len(M)]
        for name, g in [("전체", np.ones(len(T), bool))] + [(f"{t:.0f} °C", T == t) for t in np.unique(T)]:
            L.append(f"| {name} | {g.sum()} | " + " | ".join(f"{np.abs(E[k][g]).mean():.2f} / {E[k][g].mean():+.2f}" for k in M) + " |")
        L.append("")
        for b in ["B1", "B2", "S", "P"]:
            mu, ci = tp.boot_diff(E[b], E["T2_cold"])
            L.append(f"- {b} − T2_cold = {mu:+.3f} [{ci[0]:+.2f}, {ci[1]:+.2f}] (표본 부트스트랩, + 이면 T2_cold가 나음)")
        L.append("")
    L.append("칸 = MAE / 편향(예측 − 참값).")
    txt = "\n".join(L)
    open(os.path.join(HERE, "two_point_e66.md"), "w", encoding="utf-8").write(txt + "\n")
    sys.stdout.buffer.write(txt.encode("utf-8"))


if __name__ == "__main__":
    main()
