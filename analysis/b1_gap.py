"""B1(등록 표 조회) dev 3.40 vs 최종 1.41 차이 분해 (개선 루프 밖 기술 분석). 홀드아웃(rest_holdout.npz)은 안 읽는다.

새 모델 학습 없음: dev 예측은 bench.py가 저장한 analysis/out/*.npz(표본별)를 쓰고, 최종 테스트는 이미 저장된
analysis/final_out/nominal_*.npz를 읽기만 한다(재실행 아님). B1 재구성 실험(등록 표를 다른 조건으로 다시 만들기)만
학습 없는 표 조회라 여기서 직접 계산한다.

  python -I analysis/b1_gap.py            # 표를 출력하고 analysis/b1_gap_tables.md에 저장
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import variants  # noqa: E402
from bench import data, ev, folds  # noqa: E402

R = ev.PRIMARY_R
FINAL = Path("C:/BMS/data/holdout_final/rest_final.npz")
METH = {"B1": "B1_reg_lookup", "B2": "B2_reg_lookup_temp", "S": "S_simple", "P": "P_full"}
SHORT = {"LG_HG2": "LG", "Panasonic_PF": "PAN", "CALCE_INR20R": "INR", "Samsung_30T": "SAM", "Turnigy_GR": "TUR",
         "LG_E66": "E66", "Molicel_P42A": "P42A"}


def test_type(f):
    f = f.lower()
    if "hppc" in f or "pulse" in f:
        return "HPPC"
    if "ocv" in f or "gitt" in f:
        return "OCV/GITT"
    if re.search(r"cap_|dis_|c20dis|dis_0p5c|dis_2c|hcgt|cdt|capacity", f):
        return "용량·정전류"
    return "주행 사이클"


def kinks(V, n=60):
    """처음 n초에서 2차 차분이 0이 아닌 점 수. 선형 보간 구간은 2차 차분이 0이다."""
    d2 = np.abs(np.diff(V[:, :n], 2, axis=1))
    return (d2 > 1e-7).sum(1)


def pre_stats(pre_I, cap):
    """휴지 직전 300 s 중 60–300 s 전 구간(인덱스 0:240)의 평균 |I|와 표준편차, 직전 60 s 평균 I. C-rate 단위."""
    a = pre_I[:, :240] / cap[:, None]
    b = pre_I[:, 240:] / cap[:, None]
    return np.abs(a).mean(1), a.std(1), b.mean(1)


def sample_attrs():
    X, meta = data()
    REG = ev.reg_mask(meta)
    cap = meta["cap_ah"].astype(float)
    mI, sI, last = pre_stats(X["pre_I"], cap)
    A = pd.DataFrame({"ds": [SHORT[d] for d in meta["dataset"]], "T": meta["temp_c"], "type": [test_type(f) for f in meta["file"]],
                      "file": meta["file"], "soc": meta["soc"], "mI": mI, "sI": sI, "last": last,
                      "k60": kinks(X["rest_V"]), "reg": REG, "rest_len": meta["rest_len"]})
    return X, meta, A


def dev_errors(A):
    """표본×폴드 그룹(in/ext)별, 방법별 오차(시드 평균, %p, 부호 있음)."""
    out = None
    for m, name in METH.items():
        z = np.load(HERE / "out" / f"{name}.npz")
        k = z["r"] == R
        if m == "P":
            k &= np.isin(z["es"], [0, 1, 2])
        df = pd.DataFrame({"idx": z["idx"][k], "grp": ["ext" if x.startswith("EXT_") else "in" for x in z["key"][k]],
                           m: (z["pred"][k] - z["soc"][k]) * 100})
        g = df.groupby(["idx", "grp"])[m].mean()
        out = g.to_frame() if out is None else out.join(g, how="outer")
    out = out.reset_index()
    return out.join(A, on="idx")


def tab(E, by, ms=("B1", "B2", "S", "P")):
    rows = []
    for key, g in E.groupby(by, observed=True):
        r = {"n": len(g)}
        for m in ms:
            r[f"{m} MAE"] = g[m].abs().mean()
        for m in ("B1", "S"):
            r[f"{m} 편향"] = g[m].mean()
        r["B1−S"] = r["B1 MAE"] - r["S MAE"]
        rows.append(pd.Series(r, name=key))
    return pd.DataFrame(rows)


def fmt(df, title):
    df = df.copy()
    if isinstance(df.index, pd.MultiIndex):
        df.index = [" / ".join(map(str, i)) for i in df.index]
    s = [f"### {title}", "", "| 그룹 | " + " | ".join(df.columns) + " |", "|---" * (len(df.columns) + 1) + "|"]
    for i, r in df.iterrows():
        s.append(f"| {i} | " + " | ".join(f"{int(v)}" if c == "n" else f"{v:+.2f}" if ("편향" in c or "−" in c) else f"{v:.2f}"
                                          for c, v in r.items()) + " |")
    return "\n".join(s) + "\n"


def b1_rebuild(X, meta, A, E):
    """B1 표를 다른 조건으로 다시 만들어 IN 표본(25 °C 외)에 적용. 학습 없는 조회라 직접 계산."""
    REG = ev.reg_mask(meta)
    rows = []
    for fold in ev.FOLDS:
        d = SHORT[fold]
        te = (meta["dataset"] == fold) & (meta["temp_c"] != ev.REF_T) & (meta["rest_len"] >= R)
        same = meta["dataset"] == fold
        variants_ref = {
            "기본 (25 °C HPPC 첫 파일)": same & REG,
            "25 °C 전체 휴지 (모든 파일)": same & (meta["temp_c"] == ev.REF_T),
            "같은 온도 HPPC (오라클 온도 표)": None,
        }
        for name, rm in variants_ref.items():
            errs = []
            for s in ev.SEEDS:
                v = ev.corrupt(X["rest_V"][te], R, 1000 * s + R)
                if rm is not None:
                    rk = rm & (meta["rest_len"] >= R)
                    p = variants.ref_map(variants.feats(X["rest_V"][rk, :R])[:, 0], meta["soc"][rk], variants.feats(v)[:, 0])
                else:
                    p = np.full(te.sum(), np.nan)
                    T = meta["temp_c"][te]
                    for t in np.unique(T):
                        rk = same & (meta["temp_c"] == t) & (meta["rest_len"] >= R) & np.array(
                            [bool(re.search(ev.REG_FILE, f)) for f in meta["file"]])
                        if rk.sum() < 3:
                            continue
                        j = T == t
                        p[j] = variants.ref_map(variants.feats(X["rest_V"][rk, :R])[:, 0], meta["soc"][rk],
                                                variants.feats(v[j])[:, 0])
                errs.append(np.clip(p, 0, 1) - meta["soc"][te])
            e = np.nanmean(np.abs(np.array(errs)), 0) * 100
            rows.append({"데이터셋": d, "등록 표": name, "n": int(np.isfinite(e).sum()), "B1 MAE": np.nanmean(e)})
    return pd.DataFrame(rows).pivot(index="데이터셋", columns="등록 표", values="B1 MAE")


def final_attrs():
    z = np.load(FINAL, allow_pickle=False)
    m = z["meta"]
    cap = m["cap_ah"].astype(float)
    mI, sI, last = pre_stats(z["pre_I"], cap)
    F = pd.DataFrame({"ds": [SHORT[d] for d in m["dataset"]], "T": m["temp_c"], "type": [test_type(f) for f in m["file"]],
                      "file": m["file"], "soc": m["soc"], "mI": mI, "sI": sI, "last": last, "raw_n60": m["raw_n60"],
                      "reg": m["is_reg"], "rest_len": m["rest_len"]})
    return F


def final_errors(F):
    out = None
    for mth, name in METH.items():
        z = np.load(HERE / "final_out" / f"nominal_{name}.npz")
        k = z["r"] == R
        if mth == "P":
            k &= np.isin(z["es"], [0, 1, 2])
        df = pd.DataFrame({"idx": z["idx"][k], mth: z["pred"][k]})
        g = df.groupby("idx")[mth].mean()
        out = g.to_frame() if out is None else out.join(g, how="outer")
    out = out.join(F, how="left")
    for mth in METH:
        out[mth] = (out[mth] - out["soc"]) * 100
    return out.reset_index()


def main():
    X, meta, A = sample_attrs()
    E = dev_errors(A)
    E["T25"] = np.where(E["T"] == 25, "25", "≠25")
    E["Tband"] = E["T"].astype(int)
    E["crate"] = pd.cut(E["last"].abs(), [0, 0.3, 0.7, 1.5, 99], labels=["<0.3C", "0.3–0.7C", "0.7–1.5C", "≥1.5C"])
    E["steady"] = np.where(E["sI"] < 0.05, "일정 전류", "변동 전류")
    E["k60g"] = np.where(E["k60"] >= 30, "1 s 기록(≥30)", "보간(<30)")
    E["regq"] = np.where(E["ds"].isin(["PAN", "INR"]), "등록 깨끗(PAN·INR)", "등록 보간(LG·SAM·TUR)")
    In = E[E.grp == "in"]

    out = ["# B1 dev/최종 차이 분해 표 (자동 생성: analysis/b1_gap.py)", "",
           f"r = {R} s. 표본 단위 풀링 MAE(%p, 오차 시드·추정기 시드 평균). B1−S > 0이면 S_simple이 나음. P = P_full(시드 0–2).", ""]
    out.append(fmt(tab(E, "grp"), "1. 폴드 그룹 (in = LODO 25 °C 외, ext = 온도 외삽 −20·40 °C; 같은 표본이 둘 다에 들어감)"))
    out.append(fmt(tab(In, "ds"), "2a. IN 데이터셋별"))
    out.append(fmt(tab(In, "Tband"), "2b. IN 온도별"))
    out.append(fmt(tab(In, ["ds", "Tband"]), "2c. IN 데이터셋 × 온도"))
    out.append(fmt(tab(In, "type"), "3a. IN 시험 종류(파일 이름)"))
    out.append(fmt(tab(In, "crate"), "3b. IN 휴지 직전 60 s 방전 C-rate"))
    out.append(fmt(tab(In, "steady"), "3c. IN 60–300 s 전 전류 변동 (std < 0.05C = 일정)"))
    out.append(fmt(tab(In, ["type", "crate"]), "3d. IN 시험 종류 × C-rate"))
    out.append(fmt(tab(In, "regq"), "4a. IN 등록 시험 품질(데이터셋 단위)"))
    out.append(fmt(tab(In, "k60g"), "5. IN 시험 표본 자체의 처음 60 s 기록(꺾임점)"))

    # 등록 시험 꺾임점
    rq = A[A.reg].groupby("ds")["k60"].median()
    out.append("### 4b. 등록 시험 표본의 처음 60 s 꺾임점 중앙값\n\n" + " · ".join(f"{d} {v:.0f}" for d, v in rq.items()) + "\n")
    rb = b1_rebuild(X, meta, A, E)
    rb["n"] = In.groupby("ds").size()
    out.append(fmt(rb, "4c. B1 등록 표 바꾸기 (IN 표본 B1 MAE, 학습 없음; INR은 0 °C 등록 파일이 정규식에 안 걸려 오라클 없음)"))

    # 최종 테스트 기술 통계
    F = final_attrs()
    FE = final_errors(F)
    FE = FE[~FE.reg & (FE["T"] != 25) & (FE.rest_len >= R)]
    FE["crate"] = pd.cut(FE["last"].abs(), [0, 0.3, 0.7, 1.5, 99], labels=["<0.3C", "0.3–0.7C", "0.7–1.5C", "≥1.5C"])
    FE["steady"] = np.where(FE["sI"] < 0.05, "일정 전류", "변동 전류")
    out.append(fmt(tab(FE, "ds"), "6a. 최종 테스트 (저장된 1회 실행 예측, 재실행 아님) 데이터셋별"))
    out.append(fmt(tab(FE, ["ds", "type"]), "6b. 최종 테스트 데이터셋 × 시험 종류"))
    out.append(fmt(tab(FE, ["ds", "crate"]), "6c. 최종 테스트 데이터셋 × 직전 C-rate"))
    out.append(fmt(tab(FE, ["ds", "T"]), "6d. 최종 테스트 데이터셋 × 온도"))

    # 온도 구성만 최종 테스트에 맞춘 dev 기대 차이 (dev IN 온도별 B1−S를 최종 온도 비율로 가중)
    gT = tab(In, "Tband")
    gT.loc[10] = np.nan
    gT = gT.sort_index().interpolate()  # 10 °C는 0·40 °C 선형 보간
    m = FE.assign(Td=FE["T"].replace({5: 0}))  # P42A 명목 5 °C(실측 6–15 °C)는 dev 0 °C로 → 상한 쪽 추정
    rows = []
    for d, g in m.groupby("ds"):
        w = g["Td"].value_counts(normalize=True)
        rows.append(pd.Series({"n": len(g),
                               "dev 기대 B1−S": sum(w[t] * gT.loc[t, "B1−S"] for t in w.index),
                               "dev 기대 B1 편향": sum(w[t] * gT.loc[t, "B1 편향"] for t in w.index),
                               "실제 B1−S": g["B1"].abs().mean() - g["S"].abs().mean(),
                               "실제 B1 편향": g["B1"].mean()}, name=d))
    out.append(fmt(pd.DataFrame(rows), "6e. 온도 구성만 맞춘 dev 기대치 vs 실제 (10 °C 보간, P42A 5 °C → dev 0 °C)"))

    def mix(D, name):
        c = pd.crosstab(D["ds"], D["crate"], normalize="index") * 100
        t = pd.crosstab(D["ds"], D["type"], normalize="index") * 100
        s = [f"### {name}", "", "직전 60 s C-rate 비율(%): " + "; ".join(
            f"{d}: " + ", ".join(f"{k} {v:.0f}" for k, v in r.items()) for d, r in c.iterrows()),
             "", "시험 종류 비율(%): " + "; ".join(f"{d}: " + ", ".join(f"{k} {v:.0f}" for k, v in r.items() if v > 0)
                                           for d, r in t.iterrows()), ""]
        return "\n".join(s)
    out.append(mix(In, "7a. dev IN 표본 구성"))
    out.append(mix(FE, "7b. 최종 테스트 채점 표본 구성"))

    # 반사실: dev에서 최종 테스트를 닮은 부분집합
    sub = {
        "IN 전체": In,
        "IN, 직전 < 0.7C": In[In["last"].abs() < 0.7],
        "IN, 일정 전류 & 직전 < 0.7C": In[(In.sI < 0.05) & (In["last"].abs() < 0.7)],
        "IN, HPPC 제외": In[In.type != "HPPC"],
        "IN, 등록 깨끗(PAN·INR)": In[In.regq.str.startswith("등록 깨끗")],
        "IN, 등록 깨끗 & 직전 < 0.7C": In[In.regq.str.startswith("등록 깨끗") & (In["last"].abs() < 0.7)],
        "IN, −20 °C 제외": In[In["T"] != -20],
        "IN, −20 °C 제외 & 직전 < 0.7C": In[(In["T"] != -20) & (In["last"].abs() < 0.7)],
    }
    rows = [tab(d.assign(_=k), "_") for k, d in sub.items() if len(d)]
    out.append(fmt(pd.concat(rows), "8. 반사실: 최종 테스트를 닮은 dev 부분집합"))

    txt = "\n".join(out)
    (HERE / "b1_gap_tables.md").write_text(txt, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
