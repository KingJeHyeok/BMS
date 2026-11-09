"""[잠금 파일 - 에이전트 수정 금지] T1 귀환 SOC 평가용 휴지 표본을 만든다.

표본 하나 = 방전 직후의 휴지 구간 하나.
  pre_V, pre_I : 휴지 직전 300 s (1 Hz)
  rest_V       : 휴지 시작부터 최대 1800 s (1 Hz, 휴지가 끝나면 NaN)
  soc          : 휴지 시점 SOC = 1 + (기준점부터 정밀 적분 Ah) / 셀 기준 용량
기준점: 파일 시작이 만충(V0 >= vmax-0.08)이면 파일 시작, 아니면 만충 충전 블록의 끝.
셀 기준 용량: 같은 셀 25 °C 파일에서 기준점 이후 방전된 최대 Ah.

출력: autoresearch/data/rest_dev.npz (개발용), C:/BMS/data/holdout/rest_holdout.npz (홀드아웃)
사용법: python -I eval/prepare_rest.py <C:/BMS/data/raw>
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io as sio

PRE_S, REST_S, MIN_REST_S = 300, 1800, 300
I_REST = 0.02  # A
HOLDOUT = {("LG_HG2", 10), ("Panasonic_PF", 10), ("CALCE_INR20R", 45), ("CALCE_A123", 30)}
HERE = Path(__file__).resolve().parents[1]
HOLD_DIR = Path("C:/BMS/data/holdout")


def temp_from(s):
    m = re.search(r"(n|-|N)?(\d+)", s)
    return -int(m.group(2)) if m.group(1) else int(m.group(2))


def read_mat(p):
    m = sio.loadmat(p, squeeze_me=True, struct_as_record=False)["meas"]
    # 원본 로그에 긴 공백이 있어 직접 적분하면 Ah가 빠진다(Panasonic HPPC 25 °C: 1.34 vs 2.77 Ah). 장비 Ah를 쓴다.
    return pd.DataFrame({"t": m.Time.astype(float), "V": m.Voltage.astype(float), "I": m.Current.astype(float),
                         "Ah": m.Ah.astype(float)})


def read_arbin(p):
    x = pd.ExcelFile(p)
    df = pd.concat([pd.read_excel(x, s) for s in x.sheet_names if s.startswith("Channel")])
    out = pd.DataFrame({"t": df["Test_Time(s)"].astype(float), "V": df["Voltage(V)"].astype(float),
                        "I": df["Current(A)"].astype(float)})
    return out.sort_values("t").drop_duplicates("t").reset_index(drop=True)


def files(raw):
    lg = raw / "lg_hg2" / "LG_HG2_Original_Dataset_McMasterUniversity_Jan_2020"
    for p in sorted(lg.glob("*/*.mat")):
        if "_HPPC_" in p.name or "_PausCycl_" in p.name:
            yield dict(path=p, reader="mat", dataset="LG_HG2", chem="NMC", vmax=4.2, cell="LG_HG2",
                       temp_c=temp_from(p.parent.name))
    pan = raw / "panasonic_18650pf" / "Panasonic 18650PF Data"
    for p in sorted(pan.glob("*/*/*.mat")):
        if re.search(r"5pulse_HPPC", p.name, re.I):
            yield dict(path=p, reader="mat", dataset="Panasonic_PF", chem="NCA", vmax=4.2, cell="PAN_1",
                       temp_c=temp_from(p.parent.parent.name))
    for p in sorted((raw / "calce_inr18650_20r" / "extracted").glob("SP1_*C_*_OCV_*/*.xls*")):
        yield dict(path=p, reader="arbin", dataset="CALCE_INR20R", chem="NMC", vmax=4.2, cell="INR_SP20-1",
                   temp_c=int(re.search(r"SP1_(\d+)C", p.parent.name).group(1)))
    for p in sorted((raw / "calce_inr18650_20r" / "extracted").glob("SP2_*C_*/*.xls*")):
        yield dict(path=p, reader="arbin", dataset="CALCE_INR20R", chem="NMC", vmax=4.2, cell="INR_SP20-2",
                   temp_c=int(re.search(r"SP2_(\d+)C", p.parent.name).group(1)))
    for p in sorted((raw / "calce_a123" / "extracted").glob("A123_DST-US06-FUDS-*/*/*.xls*")):
        if p.name.startswith("~$"):
            continue
        t = p.parent.name.rsplit("-", 1)[1]
        yield dict(path=p, reader="arbin", dataset="CALCE_A123", chem="LFP", vmax=3.6,
                   cell="A123_" + p.name.split("-")[1], temp_c=-int(t[1:]) if t.startswith("N") else int(t))
    for p in sorted((raw / "calce_a123" / "extracted").glob("A123_OCV*/*/*.xlsx")):
        if p.name.startswith("~$"):
            continue
        t = re.search(r"OCV(-?\d+)", p.parent.parent.name.replace("OCV-", "OCV-")).group(1)
        yield dict(path=p, reader="arbin", dataset="CALCE_A123", chem="LFP", vmax=3.6,
                   cell="A123_" + p.name.split("-")[1], temp_c=int(t))


def to_1hz(df, t0):
    t = df.t.to_numpy() - t0
    I = df.I.to_numpy()
    if "Ah" in df:
        ah = df.Ah.to_numpy() - df.Ah.iat[0]
    else:
        ah = np.r_[0, np.cumsum(np.diff(t) * 0.5 * (I[1:] + I[:-1]))] / 3600
    g = pd.DataFrame({"sec": np.floor(t).astype(int), "V": df.V.to_numpy(), "I": I, "ah": ah}).groupby("sec").mean()
    g = g.reindex(np.arange(g.index.min(), g.index.max() + 1)).interpolate(limit_direction="both")
    return g


def anchor(df, vmax):
    """정밀 적분을 시작할 만충 시점들 (각 기준점부터 다음 충전 시작 전까지가 한 구간)."""
    if df.V.iat[0] >= vmax - 0.08 and df.I.iat[0] <= 0.05:
        return [df.t.iat[0]]
    chg = (df.I > I_REST).to_numpy()
    e = np.flatnonzero(np.diff(np.r_[0, chg.astype(int), 0]))
    t, out = df.t.to_numpy(), []
    for a, b in zip(e[::2], e[1::2]):
        if t[b - 1] - t[a] > 300 and df.V.iat[b - 1] >= vmax - 0.05:
            out.append(t[b - 1])
    return out


def long_charge_before(I, a):
    c = (I[:a] > 0.05).astype(int)
    e = np.flatnonzero(np.diff(np.r_[0, c, 0]))
    return any(b - x > 600 for x, b in zip(e[::2], e[1::2]))


def samples(job):
    df = read_mat(job["path"]) if job["reader"] == "mat" else read_arbin(job["path"])
    out = []
    for k, t0 in enumerate(anchor(df, job["vmax"])):
        seg = df[df.t >= t0]
        g = to_1hz(seg, t0)
        V, I, ah = g.V.to_numpy(), g.I.to_numpy(), g.ah.to_numpy()
        rest = np.abs(I) < I_REST
        e = np.flatnonzero(np.diff(np.r_[0, rest.astype(int), 0]))
        for a, b in zip(e[::2], e[1::2]):
            if b - a < MIN_REST_S or a < PRE_S:
                continue
            if I[a - 60:a].mean() > -I_REST:  # 방전 직후 휴지만
                continue
            if long_charge_before(I, a):  # 중간 재충전(600 s 넘는 충전) 이후는 제외
                break
            rv = np.full(REST_S, np.nan)
            n = min(b - a, REST_S)
            rv[:n] = V[a:a + n]
            out.append(dict(dataset=job["dataset"], chem=job["chem"], cell=job["cell"], temp_c=job["temp_c"],
                            file=job["path"].name, rest_len=int(b - a), ah=float(ah[a]),
                            pre_V=V[a - PRE_S:a], pre_I=I[a - PRE_S:a], rest_V=rv))
    return out, float(ah.min()) if len(df) else 0.0


def save(path, S):
    np.savez_compressed(path, pre_V=np.stack(S.pre_V), pre_I=np.stack(S.pre_I), rest_V=np.stack(S.rest_V),
                        meta=S.drop(columns=["pre_V", "pre_I", "rest_V"]).to_records(
                            index=False, column_dtypes={c: "U96" for c in S.columns if S[c].dtype == object
                                                        and c not in ("pre_V", "pre_I", "rest_V")}))


def main():
    raw = Path(sys.argv[1])
    rows, caps = [], {}
    for job in files(raw):
        try:
            s, ahmin = samples(job)
        except Exception as e:  # noqa: BLE001
            print("fail", job["path"].name, e)
            continue
        print(f"{len(s):3d} rests  {job['dataset']:13s} {job['temp_c']:4d}  {job['path'].name}", flush=True)
        if job["temp_c"] == 25 and "OCV" in job["path"].name:
            caps[job["cell"]] = max(caps.get(job["cell"], 0), -ahmin)
        rows += s
    S = pd.DataFrame(rows)
    # 기준 용량 = 25 °C 컷오프까지 방전한 Ah. LG 주행 사이클은 약 3.2 V에서 멈춰서 25 °C HPPC 값(2.774)을 쓴다
    caps.update({"LG_HG2": 2.774, "PAN_1": 2.799, "INR_SP20-2": 2.055, "A123_007": 1.036, "A123_008": 1.058})
    print("기준 용량(Ah):", {k: round(v, 3) for k, v in caps.items()})
    # A123 두 셀은 25 °C가 각자 있음. 없는 셀은 같은 데이터셋 최대값
    for c in S.cell.unique():
        if c not in caps:
            ds = S[S.cell == c].dataset.iat[0]
            caps[c] = max(v for k, v in caps.items() if S[S.cell == k].dataset.iat[0] == ds)
    S["cap_ah"] = S.cell.map(caps)
    S["soc"] = 1 + S.ah / S.cap_ah
    S = S[(S.soc > -0.02) & (S.soc < 1.02)].reset_index(drop=True)
    S["sid"] = [f"{d}|{t}|{f}|{i}" for i, (d, t, f) in enumerate(zip(S.dataset, S.temp_c, S.file))]
    hold = np.array([(d, t) in HOLDOUT for d, t in zip(S.dataset, S.temp_c)])
    save(HERE / "data" / "rest_dev.npz", S[~hold])
    HOLD_DIR.mkdir(parents=True, exist_ok=True)
    save(HOLD_DIR / "rest_holdout.npz", S[hold])
    summ = S.assign(split=np.where(hold, "holdout", "dev")).groupby(["split", "dataset", "temp_c"]).agg(
        n=("soc", "size"), soc_lo=("soc", "min"), soc_hi=("soc", "max"), rest_med=("rest_len", "median"))
    print(summ.round(2).to_string())


if __name__ == "__main__":
    main()
