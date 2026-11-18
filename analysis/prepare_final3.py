"""2점 등록 확증 시험 데이터 변환: Plett ESC toolbox(UCCS) 셀 6종의 DYN 시험. 모델은 돌리지 않는다.

규칙은 analysis/prepare_final.py와 같다(같은 clean·anchor·samples 함수를 그대로 가져다 쓴다):
방전 직후 휴지(≥300 s, 앞에 300 s 기록, 직전 60 s 평균이 방전), 1 Hz(to_1hz), rest_V 최대 1800 s,
SOC = 1 + (만충 기준점부터 Ah) / 셀 25 °C 최대 방전 Ah, SOC (−0.02, 1.02) 밖은 뺀다, I_REST = C/150.

Plett 데이터에 맞춘 부분:
- 부호: Plett 파일은 방전 전류가 +. dev 규칙(방전 −)에 맞춰 I = −current, 장비 Ah = chgAh − disAh로 넣는다.
- 쓰는 구간: DYN 파일의 script1만 쓴다. script1은 시험 온도에서 돈다(25 °C 만충 → 시험 온도에서 담금 → 동적 방전).
  script2(25 °C에서 잔량 방전)와 script3(25 °C 충전)은 파일 이름의 온도가 아니라 25 °C에서 돌므로 넣지 않는다.
- 기준점: script1은 만충 휴지에서 시작한다(첫 전압이 셀 vmax − 0.08 이상, 전류 ≈ 0).
  prepare_final.anchor의 "파일 시작이 만충" 규칙이 그대로 적용된다. 셀별 vmax = 25 °C OCV 시험 script1 시작 전압.
- 셀 기준 용량: Plett 25 °C OCV 시험(OCV_P25)의 script1(C/30 방전, 만충 → Vmin) + script2(25 °C 잔량 방전)의 순방전 Ah.
  "25 °C에서 만충 기준점 이후 방전된 최대 Ah"에 해당한다. script1만의 값도 점검용으로 출력한다.
- I_REST = 셀 기준 용량 / 150(공칭 용량 정보가 없어 25 °C 기준 용량을 쓴다).
- 셀 온도 채널이 없다 → meas_temp = NaN, nom_src = "filename"(파일 이름의 N/P 온도).
- 등록: is_reg = 셀의 25 °C DYN 파일(여러 개면 이름순 첫 번째), is_reg2 = 셀의 −5 °C DYN 파일.
  −5 °C는 있는 온도 중 0 °C에 가장 가깝고(5 °C와 동률), 동률이면 추운 쪽을 고르는 규칙에 따른 것이다.
  채점 후보 = 그 밖의 온도(−25, −15, 5, 15, 35, 45 °C).
- dataset = "Plett_ESC", cell = 파일 접두어(A123, ATL, E1, E2, P14, SAM).
  chem: A123·ATL은 전압 창(≈2.0/2.6–3.6 V)으로 보아 "LFP", 나머지는 화학계 미확인이라 "Li-ion"(4.1–4.2 V급).

  python -I analysis/prepare_final3.py   → C:/BMS/data/holdout_final3/rest_final3.npz + 점검 출력
"""
import importlib.util
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io as sio
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("pf", HERE / "prepare_final.py")
pf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pf)
prep = pf.prep
BASE = Path("C:/BMS/data/holdout_final3")
RAW = BASE / "raw" / "plett_esctoolbox"
CHEM = {"A123": "LFP", "ATL": "LFP"}
REG2_T = -5


def scripts(p):
    m = sio.loadmat(p)
    key = [k for k in m if not k.startswith("__")][0]
    D = m[key][0, 0]
    return {s: {c: np.asarray(D[s][0, 0][c]).ravel().astype(float) for c in D[s][0, 0].dtype.names} for s in D.dtype.names}


def temp_of(name):
    g = re.search(r"_([NP])(\d\d)\.mat$", name)
    return (-1 if g.group(1) == "N" else 1) * int(g.group(2))


def cell_info(c):
    o = scripts(RAW / f"{c}_OCV_P25.mat")
    s1, s2 = o["script1"], o["script2"]
    q1 = s1["disAh"][-1] - s1["chgAh"][-1]
    q12 = q1 + s2["disAh"][-1] - s2["chgAh"][-1]
    return dict(cap=float(q12), cap_s1=float(q1), vmax=float(s1["voltage"][:50].max()))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    files = sorted(RAW.glob("*_DYN_*.mat"))
    cells = sorted({p.name.split("_")[0] for p in files})
    info = {c: cell_info(c) for c in cells}
    for c, d in info.items():
        print(f"{c:5s} 기준 용량 {d['cap']:.3f} Ah (script1만 {d['cap_s1']:.3f}), vmax {d['vmax']:.3f} V")
    rows = []
    for c in cells:
        cf = sorted([p for p in files if p.name.startswith(c + "_")], key=lambda p: (temp_of(p.name), p.name))
        reg25 = next(p for p in cf if temp_of(p.name) == 25)
        reg2 = next(p for p in cf if temp_of(p.name) == REG2_T)
        for p in cf:
            T = temp_of(p.name)
            s = scripts(p)["script1"]
            job = dict(dataset="Plett_ESC", chem=CHEM.get(c, "Li-ion"), cell=c, temp_c=T, file=p.name,
                       vmax=info[c]["vmax"], i_rest=info[c]["cap"] / 150, is_reg=(p == reg25), nom_src="filename")
            df = pf.clean(s["time"], s["voltage"], -s["current"], job, ah=s["chgAh"] - s["disAh"])
            integ = np.r_[0, np.cumsum(0.5 * (-s["current"][1:] - s["current"][:-1]) * np.diff(s["time"]) / 3600)]
            dev_ah = (s["chgAh"] - s["disAh"]) - (s["chgAh"][0] - s["disAh"][0])
            smp, ahmin = pf.samples(df, job)
            for x in smp:
                x["is_reg2"] = p == reg2
            a0 = pf.anchor(df, job["vmax"], job["i_rest"])
            print(f"  {p.name:22s} T={T:+3d} 휴지 {len(smp):2d}  기준점 {len(a0)} (t0={a0[0] - df.t.iat[0]:.0f}s)  "
                  f"V0={df.V.iat[0]:.3f}  ahmin={ahmin:6.3f}  |장비Ah−적분| 최대 {np.abs(dev_ah - integ).max():.4f} Ah  "
                  f"{df.attrs.get('ah_fix', '')}  {'REG25' if p == reg25 else ''}{'REG2' if p == reg2 else ''}", flush=True)
            rows += smp
    S = pd.DataFrame(rows)
    S["cap_ah"] = S.cell.map({c: d["cap"] for c, d in info.items()})
    S["soc"] = 1 + S.ah / S.cap_ah
    S["meas_temp"] = np.nan
    n0 = len(S)
    S = S[(S.soc > -0.02) & (S.soc < 1.02)].reset_index(drop=True)
    print(f"SOC 범위 밖 제거: {n0 - len(S)}")
    S["sid"] = [f"{d}|{c}|{t}|{f}|{i}" for i, (d, c, t, f) in enumerate(zip(S.dataset, S.cell, S.temp_c, S.file))]
    S["is_reg2"] = S["is_reg2"].astype(bool)
    out = BASE / "rest_final3.npz"
    save(out, S)
    return S


META = ["dataset", "chem", "cell", "temp_c", "file", "rest_len", "ah", "is_reg", "raw_n60", "meas_temp", "nom_src",
        "cap_ah", "soc", "sid", "is_reg2"]


def save(out, S):
    """prep.save와 같은 배치(pre_V, pre_I, rest_V, meta). meta 열 순서는 rest_final.npz와 같고 끝에 is_reg2."""
    prep.save(out, S[META + ["pre_V", "pre_I", "rest_V"]])
    print("저장:", out, len(S), "표본")


def checks(S):
    """모델 없는 점검: 셀×온도 표본 수, SOC 범위, V300–SOC 순위 상관, raw_n60, 휴지 길이, 직전 전류."""
    V300 = np.stack(S.rest_V.to_numpy())[:, 285:300].mean(1)
    preI = np.stack(S.pre_I.to_numpy())
    S = S.assign(V300=V300, preI60=-preI[:, -60:].mean(1) / S.cap_ah, preIsd=preI[:, -300:].std(1) / S.cap_ah,
                 preImax=-preI[:, -300:].min(1) / S.cap_ah)
    L = []
    g = S.groupby(["cell", "temp_c"])
    tab = g.agg(n=("soc", "size"), soc_lo=("soc", "min"), soc_hi=("soc", "max"), rest_min=("rest_len", "min"),
                rest_med=("rest_len", "median"), n60_min=("raw_n60", "min"), preI60_C=("preI60", "median"),
                preImax_C=("preImax", "median"), reg=("is_reg", "any"), reg2=("is_reg2", "any"))
    tab["rho_V300"] = g.apply(lambda d: spearmanr(d.V300, d.soc)[0] if len(d) > 3 else np.nan)
    return S, tab


if __name__ == "__main__":
    S = main()
    S, tab = checks(S)
    pd.set_option("display.width", 200)
    print(tab.round(3).to_string())
    piv = S.assign(role=np.where(S.is_reg, "reg25", np.where(S.is_reg2, "reg2", "score"))).pivot_table(
        index="cell", columns="temp_c", values="soc", aggfunc="size", fill_value=0)
    print(piv.to_string())
