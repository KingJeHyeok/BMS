"""Plett 원시 OCV 시험 → 셀·온도별 평형 OCV 곡선 (심사자 요청 기준선용 자료). 모델·추정기는 돌리지 않는다.

Plett processOCV(ESCtoolbox, BMS Vol. I 2장)의 절차를 따른다:
- script1: 시험 온도 T에서 C/30 방전(step 2), script3: T에서 C/30 충전(step 2). script2·4: 25 °C 정리 단계.
- 쿨롱 효율: eta25 = 25 °C 파일 4개 script의 총 방전 Ah / 총 충전 Ah.
  다른 온도 T: eta_T = (총 방전 − eta25·(s2 충전 + s4 충전)) / (s1 충전 + s3 충전). 충전 Ah에 곱한다.
- IR 보정: step 2 시작·끝의 전압 점프로 IR을 잡고, 방전 곡선에는 더하고 충전 곡선에서는 빼며, 처음→끝을 선형으로 섞는다.
  min(IR1D, 2·IR2C) 같은 Plett의 상한 규칙도 그대로 적용한다.
- SOC: 방전 z = 1 − disAh/Q25(첫 점을 1로 맞춤), 충전 z = eta_T·chgAh/Q25(첫 점을 0으로 맞춤).
- 평형 OCV: z = 0.5에서 충전−방전 차 ΔV50를 구한다. z < 0.5는 충전 곡선 − z·ΔV50, z > 0.5는 방전 곡선 + (1 − z)·ΔV50.
  두 곡선을 이어 201점 격자(0..1)에 선형 보간한다(격자 밖은 선형 외삽, Plett의 interp1 'extrap'과 같음).

Plett와 다른 점(final3_data_notes.md "평형 OCV 곡선"에 기록):
- SOC 기준 용량 = rest_final3의 Q25(25 °C OCV script1+2 순방전, eta 없이). Plett의 Q25(충전에 eta25를 곱함)와 비교값도 저장한다.
- Plett는 온도별 곡선(rawocv)을 OCV0 + T·OCVrel로 최소제곱 근사해 모델에 넣는다. 여기서는 근사 전의 온도별 곡선을 그대로 저장한다.
- V_dis = IR 보정한 방전 곡선만(민감도용).

  python -I analysis/prepare_ocv_final3.py   → C:/BMS/data/holdout_final3/ocv_eq.npz + E2를 Plett 모델과 비교
"""
import re
import sys
from pathlib import Path

import numpy as np
import scipy.io as sio
from scipy.interpolate import interp1d

BASE = Path("C:/BMS/data/holdout_final3")
OCV = BASE / "raw" / "plett_esctoolbox" / "ocv"
GRID = np.linspace(0, 1, 201)


def load(p):
    m = sio.loadmat(p)
    D = m["OCVData"][0, 0]
    return {s: {c: np.asarray(D[s][0, 0][c]).ravel().astype(float) for c in D[s][0, 0].dtype.names} for s in D.dtype.names}


def temp_of(name):
    g = re.search(r"_([NP])(\d\d)\.mat$", name)
    return (-1 if g.group(1) == "N" else 1) * int(g.group(2))


def tot(d, k):
    return sum(d[s][k][-1] for s in ("script1", "script2", "script3", "script4"))


def ext(x, y):
    o = np.argsort(x)
    x, y = x[o], y[o]
    keep = np.r_[True, np.diff(x) > 0]
    return interp1d(x[keep], y[keep], bounds_error=False, fill_value="extrapolate")


def curve(d, eta, q25):
    s1, s3 = d["script1"], d["script3"]
    iD = np.flatnonzero(s1["step"] == 2)
    iC = np.flatnonzero(s3["step"] == 2)
    v1, v3 = s1["voltage"], s3["voltage"]
    IR1Da, IR2Da = v1[iD[0] - 1] - v1[iD[0]], v1[iD[-1] + 1] - v1[iD[-1]]
    IR1Ca, IR2Ca = v3[iC[0]] - v3[iC[0] - 1], v3[iC[-1]] - v3[iC[-1] + 1]
    IR1D, IR2D = min(IR1Da, 2 * IR2Ca), min(IR2Da, 2 * IR1Ca)
    IR1C, IR2C = min(IR1Ca, 2 * IR2Da), min(IR2Ca, 2 * IR1Da)
    bD = np.linspace(0, 1, len(iD))
    disV = v1[iD] + IR1D + (IR2D - IR1D) * bD
    disZ = 1 - s1["disAh"][iD] / q25
    disZ = disZ + (1 - disZ[0])
    bC = np.linspace(0, 1, len(iC))
    chgV = v3[iC] - (IR1C + (IR2C - IR1C) * bC)
    chgZ = s3["chgAh"][iC] * eta / q25
    chgZ = chgZ - chgZ[0]
    # Plett: 결합점 z_s = 0.5. 저온에서 충전 곡선이 0.5에 못 미치면(E2 −25 °C: 최대 0.37) 0.5에서의 값이 외삽이 되므로
    # z_s = min(0.5, 충전 z 최대 − 0.02)로 내린다(같은 식: 충전쪽 − z·ΔV(z_s), 방전쪽 + (1 − z)·ΔV(z_s), z_s에서 연속).
    zs = float(min(0.5, chgZ.max() - 0.02))
    dV = float(ext(chgZ, chgV)(zs) - ext(disZ, disV)(zs))
    a = chgZ < zs
    b = disZ > zs
    z = np.r_[chgZ[a], disZ[b]]
    v = np.r_[chgV[a] - chgZ[a] * dV, disV[b] + (1 - disZ[b]) * dV]
    return ext(z, v)(GRID), ext(disZ, disV)(GRID), dict(dV50=dV, split_z=zs, zchg_max=float(chgZ.max()),
                                                      zdis_min=float(disZ.min()), IR=(IR1D, IR2D, IR1C, IR2C))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    z3 = np.load(BASE / "rest_final3.npz")
    m3 = z3["meta"]
    Q25 = {c: float(m3["cap_ah"][m3["cell"] == c][0]) for c in np.unique(m3["cell"])}
    out = {k: [] for k in ("cell", "temp_c", "V", "V_dis", "eta", "dV50", "split_z", "zchg_max", "zdis_min")}
    q25_plett = {}
    for c in sorted(Q25):
        d25 = load(OCV / f"{c}_OCV_P25.mat")
        eta25 = tot(d25, "disAh") / tot(d25, "chgAh")
        q25_plett[c] = (d25["script1"]["disAh"][-1] + d25["script2"]["disAh"][-1]
                        - eta25 * (d25["script1"]["chgAh"][-1] + d25["script2"]["chgAh"][-1]))
        print(f"{c}: Q25(rest_final3) {Q25[c]:.4f} Ah, Q25(Plett, eta25 {eta25:.4f}) {q25_plett[c]:.4f} Ah")
        for p in sorted(OCV.glob(f"{c}_OCV_*.mat"), key=lambda p: temp_of(p.name)):
            T = temp_of(p.name)
            d = load(p)
            if T == 25:
                eta = eta25
            else:
                eta = (tot(d, "disAh") - eta25 * (d["script2"]["chgAh"][-1] + d["script4"]["chgAh"][-1])) / (
                    d["script1"]["chgAh"][-1] + d["script3"]["chgAh"][-1])
            V, Vd, info = curve(d, eta, Q25[c])
            for k, v in (("cell", c), ("temp_c", T), ("V", V), ("V_dis", Vd), ("eta", eta), ("dV50", info["dV50"]), ("split_z", info["split_z"]),
                         ("zchg_max", info["zchg_max"]), ("zdis_min", info["zdis_min"])):
                out[k].append(v)
            print(f"   T={T:+3d} eta={eta:.4f} z_s={info['split_z']:.2f} dV(z_s)={info['dV50'] * 1000:6.1f} mV  충전 z 최대 {info['zchg_max']:.2f}  "
                  f"방전 z 최소 {info['zdis_min']:.2f}  OCV(0.1/0.5/0.9) = {np.interp(0.1, GRID, V):.4f}/"
                  f"{np.interp(0.5, GRID, V):.4f}/{np.interp(0.9, GRID, V):.4f}")
    notes = ("Plett processOCV 절차(eta25, eta_T, IR 혼합 보정, z=0.5 ΔV50 결합). SOC 기준 = rest_final3 Q25(25 °C OCV s1+s2 순방전, eta 없이). "
             "V = 충전(z<z_s)·방전(z>z_s) 결합 평형 OCV(z_s = min(0.5, 충전 z 최대 − 0.02); 0.5 미만이면 split_z에 기록, E2 −25 °C 0.35), dV50 = z_s에서의 충전−방전 차, V_dis = IR 보정 방전 곡선만. 격자 밖은 선형 외삽. "
             "Plett의 OCV0+T·OCVrel 근사 전의 온도별 곡선(rawocv)이다.")
    np.savez_compressed(BASE / "ocv_eq.npz", cell=np.array(out["cell"]), temp_c=np.array(out["temp_c"]), soc_grid=GRID,
                        V=np.array(out["V"]), V_dis=np.array(out["V_dis"]), eta=np.array(out["eta"]),
                        dV50=np.array(out["dV50"]), split_z=np.array(out["split_z"]), zchg_max=np.array(out["zchg_max"]), zdis_min=np.array(out["zdis_min"]),
                        q25=np.array([Q25[c] for c in out["cell"]]), q25_plett=np.array([q25_plett[c] for c in out["cell"]]),
                        notes=np.array(notes))
    print("저장:", BASE / "ocv_eq.npz", len(out["cell"]), "곡선")
    # E2 vs Plett 모델(OCV0 + T·OCVrel). 모델 SOC는 Plett Q25 기준 → 우리 격자로 환산해 비교(두 방식 모두 출력)
    M = sio.loadmat(BASE / "raw" / "plett_esctoolbox" / "models" / "E2model_BMS2_ESCEKF.mat", squeeze_me=True,
                    struct_as_record=False)["model"]
    zm, o0, orel = (np.asarray(getattr(M, k), float) for k in ("SOC", "OCV0", "OCVrel"))
    print("\nE2: 우리 곡선 − Plett 모델 OCV0+T·OCVrel (mV), SOC 0.05–0.95 / 전체 0–1")
    r = Q25["E2"] / q25_plett["E2"]
    for i in [j for j, c in enumerate(out["cell"]) if c == "E2"]:
        T = out["temp_c"][i]
        mod = np.interp(GRID, zm, o0 + T * orel)
        mod_q = np.interp(GRID * r, zm, o0 + T * orel)  # 우리 SOC → Plett SOC 환산(같은 Ah 위치)
        mid = (GRID >= 0.05) & (GRID <= 0.95)
        dd, dq = (out["V"][i] - mod) * 1000, (out["V"][i] - mod_q) * 1000
        print(f"  T={T:+3d}: 격자 그대로 max {np.abs(dd[mid]).max():6.1f} mean {np.abs(dd[mid]).mean():5.1f} (전체 max {np.abs(dd).max():6.1f}) | "
              f"Q 환산 max {np.abs(dq[mid]).max():6.1f} mean {np.abs(dq[mid]).mean():5.1f} (전체 max {np.abs(dq).max():6.1f})")


if __name__ == "__main__":
    main()
