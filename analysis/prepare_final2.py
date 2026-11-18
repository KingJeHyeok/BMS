"""2차 최종 테스트(2점 등록) 휴지 표본 변환: Univ. Malaya NCR18650B(NCA)·Murata VTC6(NMC). 모델은 돌리지 않는다.

데이터: Mendeley doi:10.17632/29kw38kzwj.1 (CC BY 4.0), "Battery Test Data.rar" sha256 60dac826…57df07.
규칙은 analysis/prepare_final.py(= eval/prepare_rest.py)와 같다: 방전 직후 휴지 ≥300 s, 앞 300 s 기록, to_1hz,
I_REST = C_nom/150, 만충 기준점부터 전류 적분, SOC = 1 + Ah / (같은 셀 25 °C 파일에서 기준점 이후 방전된 최대 Ah).
다른 점 (analysis/final2_data_notes.md에 근거):
  - 기준점: dev 규칙(파일 시작이 만충 휴지, 또는 만충 CC-CV 충전 블록의 끝)에 더해, 파일이 **방전으로 바로 시작**하면
    첫 기록 전압이 vmax − 0.20 V 이상일 때 시작점을 만충으로 본다(데이터 설명: 모든 시험은 만충 뒤 시작).
    이 경우는 시작부터 첫 컷오프까지 방전 Ah를 같은 온도 다른 시험과 비교해 점검한다(--inventory 출력).
  - 장비 Ah 칸은 스텝마다 0으로 리셋되므로 쓰지 않고 전류를 적분한다.
  - 셀 온도 기록이 없다(VTC6 −5 °C 시트의 Temp 칸은 명목값 −5 상수). meas_temp = NaN.
  - 25 °C 폴더의 칸 이름은 "30D"다. 명목 온도는 폴더 이름(25)을 쓰고 temp_label_file에 30을 남긴다.

  python -I analysis/prepare_final2.py              → C:/BMS/data/holdout_final2/rest_final2.npz + 점검 출력
  python -I analysis/prepare_final2.py --inventory  → 파일별 시작 상태·휴지 수·샘플링 점검만
추가 메타: reg25, reg2(등록 후보), ftype(PCPD/HPPC/DST/…), temp_label_file, raw_n60, kinks60
"""
import importlib.util
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("prep", ROOT / "eval" / "prepare_rest.py")
prep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prep)
PRE_S, REST_S, MIN_REST_S = prep.PRE_S, prep.REST_S, prep.MIN_REST_S

_spec2 = importlib.util.spec_from_file_location("pf", ROOT / "analysis" / "prepare_final.py")
pf = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(pf)

BASE = Path("C:/BMS/data/holdout_final2")
RAW = BASE / "raw" / "Battery Test Data"
CACHE = BASE / "cache"

CELLS = {  # 폴더 → (dataset, chem, cell, C_nom Ah, vmax, vmin)
    "NCA - NCR18650B": ("UM_NCR18650B", "NCA", "NCR18650B", 3.35, 4.2, 2.5),
    "NMC - Murata VTC6 18650 3000mAh 15A": ("UM_VTC6", "NMC", "VTC6", 3.0, 4.2, 2.0),
}
SKIP_FILES = {
    # N5 폴더의 두 Neware 파일은 데이터가 한 점도 다르지 않은 복사본이고, 내용은 −5 °C가 아니라 5 °C 시험으로 보인다:
    # 율 방전 구간(1.5C·1C·0.33C)이 5 °C 폴더의 "1.5C 1.0C 0.5C.xlsx" 시트와 첫 점 V·I와 방전 Ah(1.946/2.259/2.415)까지 같고,
    # 1 s 저항(82.8 mΩ)이 5 °C PCPD(81.7)와 같으며, 0.33C 용량 2.41 Ah가 −5 °C 주행 시트(≈2.0–2.1 Ah)보다 5 °C 값과 맞는다.
    # 온도 라벨을 믿을 수 없으므로 뺀다(analysis/final2_data_notes.md).
    "NCA - NCR18650B/N5 Degree/0.5C_1.0C_1.5C_PD.xls",
    "NCA - NCR18650B/N5 Degree/PCPD.xls",
}
SKIP_SHEETS = re.compile(r"^(Info|Cycle_.*|Statis_.*|OCV.*|Sheet\d*)$")
# 파일 이름과 내용이 다른 것: VTC6 45 °C "DST FUDS UDDS HPPC WLTS US06.xls"의 실제 내용은 PCPD(12 min 방전 + 30 min 휴지 × 10, 이어서 충전 계단)
FTYPE_OVERRIDE = {"NMC - Murata VTC6 18650 3000mAh 15A/45 degree/DST FUDS UDDS HPPC WLTS US06.xls": "PCPD"}
START_REST_DV = 0.10  # dev는 0.08. 5 °C NCA PCPD는 만충 1 h 휴지 뒤 4.118 V라 0.08로는 빠진다(점검: 같은 온도 다른 시험과 방전 용량 일치)


def folder_temp(name):
    m = re.match(r"(N|Negative )?(\d+)", name)
    return -int(m.group(2)) if m.group(1) else int(m.group(2))


def sheet(rel, sh):
    key = re.sub(r"[^A-Za-z0-9.]+", "_", rel.replace("/", "\\") + "__" + sh)
    p = CACHE / f"{key}.pkl"
    if p.exists():
        return pd.read_pickle(p)
    df = pd.read_excel(RAW / rel, sheet_name=sh)
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_pickle(p)
    return df


# ---------------------------------------------------------------- 읽기
def read_neware(rel, sheets):
    """Neware Detail 시트(엑셀 행 제한으로 여러 장) → t, V, I. t = 스텝 시작 + 스텝 상대 시간."""
    d = pd.concat([sheet(rel, s) for s in sheets], ignore_index=True)
    rt = pd.to_timedelta(d["Relative Time(h:min:s.ms)"].astype(str)).dt.total_seconds().to_numpy()
    new = np.r_[True, (np.diff(d.Step.to_numpy()) != 0) | (np.diff(d.Cycle.to_numpy()) != 0)]
    t = np.empty(len(d))
    start = 0.0
    for i in range(len(d)):
        if new[i] and i > 0:
            start = t[i - 1] + 0.001  # 새 스텝 첫 점(상대 0)은 앞 스텝 끝 바로 뒤
        t[i] = start + rt[i]
    absd = (d["Absolute Time"].iloc[-1] - d["Absolute Time"].iloc[0]).total_seconds()
    return t, d["Voltage(V)"].to_numpy(float), d["Cur(mA)"].to_numpy(float) / 1000, f"neware drift {t[-1] - absd:+.0f}s"


def read_xlsx_sheet(rel, sh):
    d = sheet(rel, sh)
    cols = list(d.columns)
    tc = cols[0]
    vc = next(c for c in cols if re.match(r"(Voltage|Volatge)", str(c)))
    ic = next(c for c in cols if re.match(r"(Current|Cur\(mA\))", str(c)) and "(A)" not in str(c))
    d = d[[tc, vc, ic]].apply(pd.to_numeric, errors="coerce").dropna()
    return d[tc].to_numpy(float), d[vc].to_numpy(float), d[ic].to_numpy(float) / 1000, "xlsx"


def ftype_of(rel, sh):
    name = (sh or Path(rel).stem).upper()
    for k in ("PCPD", "HPPC", "DST", "FUDS", "UDDS", "WLTS", "US06"):
        if k in name:
            return k
    if "CAPACITY" in name:
        return "CAP"
    if re.match(r"^[\d.]+C$", name):
        return "RATE"
    return "OTHER"


def jobs():
    for folder, (ds, chem, cell, cap, vmax, vmin) in CELLS.items():
        for p in sorted((RAW / folder).rglob("*.xls*")):
            rel = p.relative_to(RAW).as_posix()
            if rel in SKIP_FILES:
                continue
            tdir = p.parent.name
            temp = folder_temp(tdir)
            base = dict(dataset=ds, chem=chem, cell=cell, vmax=vmax, vmin=vmin, cap_nom=cap, i_rest=cap / 150,
                        temp_c=temp, temp_label_file=30 if temp == 25 else temp, tdir=tdir)
            xl = pd.ExcelFile(p)
            det = [s for s in xl.sheet_names if s.startswith("Detail_")]
            if det:
                ft = FTYPE_OVERRIDE.get(rel) or ftype_of(rel, None)
                yield dict(base, file=rel, sheet="+".join(det), ftype=ft, read=lambda r=rel, s=det: read_neware(r, s))
            else:
                for sh in xl.sheet_names:
                    if SKIP_SHEETS.match(sh):
                        continue
                    yield dict(base, file=rel, sheet=sh, ftype=ftype_of(rel, sh),
                               read=lambda r=rel, s=sh: read_xlsx_sheet(r, s))


# ---------------------------------------------------------------- 기준점·표본
def anchors(df, job):
    """dev 규칙 + 방전으로 바로 시작하는 파일의 시작점."""
    A = pf.anchor(df, job["vmax"], job["i_rest"])
    if abs(df.I.iat[0]) <= 2.5 * job["i_rest"] and df.V.iat[0] >= job["vmax"] - START_REST_DV:
        A = sorted({df.t.iat[0], *A})
    if df.I.iat[0] < -job["i_rest"] and df.V.iat[0] >= job["vmax"] - 0.20:
        A = sorted({df.t.iat[0], *A})
    return A


def kinks(v):
    """1 Hz 격자에서 기울기가 바뀌는 점 수(보간이면 적다). 처음 60 s."""
    d = np.diff(v[:61])
    return int(np.sum(np.abs(np.diff(d)) > 1e-6))


def samples(df, job):
    out, caps = [], []
    A = anchors(df, job)
    for k, t0 in enumerate(A):
        seg = df[(df.t >= t0) & (df.t < (A[k + 1] if k + 1 < len(A) else np.inf))]
        g = prep.to_1hz(seg[["t", "V", "I"]], t0)
        V, I, ah = g.V.to_numpy(), g.I.to_numpy(), g.ah.to_numpy()
        caps.append(-float(np.nanmin(ah)))
        sec0 = g.index[0]
        traw = seg.t.to_numpy() - t0
        rest = np.abs(I) < job["i_rest"]
        e = np.flatnonzero(np.diff(np.r_[0, rest.astype(int), 0]))
        for a, b in zip(e[::2], e[1::2]):
            if b - a < MIN_REST_S or a < PRE_S:
                continue
            if I[a - 60:a].mean() > -job["i_rest"]:
                continue
            rv = np.full(REST_S, np.nan)
            n = min(b - a, REST_S)
            rv[:n] = V[a:a + n]
            s0 = sec0 + a
            dis = np.flatnonzero(I[:a] >= -job["i_rest"])  # 휴지 직전 연속 방전 길이
            pre_dis_s = int(a - (dis[-1] + 1 if len(dis) else 0))
            ft = job["ftype"]
            if ft == "PCPD" and pre_dis_s > 1500:  # PCPD 파일 안의 완전 방전(용량·율 시험) 뒤 휴지는 계단 시험이 아님
                ft = "RATE"
            out.append(dict(dataset=job["dataset"], chem=job["chem"], cell=job["cell"], temp_c=job["temp_c"],
                            temp_label_file=job["temp_label_file"], file=f"{job['file']}:{job['sheet']}",
                            ftype=ft, pre_dis_s=pre_dis_s, anchor_k=k, rest_len=int(b - a), ah=float(ah[a]),
                            pre_V=V[a - PRE_S:a], pre_I=I[a - PRE_S:a], rest_V=rv,
                            raw_n60=int(((traw >= s0) & (traw < s0 + 60)).sum()), kinks60=kinks(rv),
                            meas_temp=np.nan, pre_I60=float(I[a - 60:a].mean())))
    return out, caps, A


def load(job):
    t, V, I, note = job["read"]()
    df = pf.clean(t, V, I, job)
    df.attrs["note"] = note
    return df


def first_cutoff_ah(df, job, t0):
    """시작점부터 처음 컷오프(V ≤ vmin + 0.02)까지 방전 Ah (기준점 점검용)."""
    s = df[df.t >= t0]
    hit = np.flatnonzero(s.V.to_numpy() <= job["vmin"] + 0.02)
    if not len(hit):
        return np.nan
    s = s.iloc[:hit[0] + 1]
    return float(-(s.Ah.iat[-1] - s.Ah.iat[0]))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    inv = "--inventory" in sys.argv
    rows, caps25, inv_rows = [], {}, []
    for job in jobs():
        df = load(job)
        s, caps, A = samples(df, job)
        dt = np.diff(df.t.to_numpy())
        startA = bool(A) and A[0] == df.t.iat[0]
        how = ("start-rest" if startA and abs(df.I.iat[0]) <= 2.5 * job["i_rest"] else
               "start-dchg" if startA else "chg-block" if A else "none")
        cut = first_cutoff_ah(df, job, A[0]) if A else np.nan
        inv_rows.append(dict(cell=job["cell"], T=job["temp_c"], ftype=job["ftype"], file=job["file"].split("/")[-1],
                             sheet=job["sheet"][:14], n=len(df), dur_h=round(df.t.iat[-1] / 3600, 1),
                             dt_med=float(np.median(dt)), dt_p99=float(np.percentile(dt, 99)),
                             V0=round(df.V.iat[0], 3), I0=round(df.I.iat[0], 2), anchor=how, nA=len(A),
                             cut_ah=round(cut, 3), maxdis=round(max(caps) if caps else np.nan, 3), rests=len(s),
                             note=df.attrs["note"]))
        if job["temp_c"] == 25:
            caps25[job["cell"]] = max(caps25.get(job["cell"], 0), max(caps) if caps else 0)
        rows += s
    I_ = pd.DataFrame(inv_rows)
    pd.set_option("display.width", 250)
    print(I_.to_string(index=False))
    if inv:
        return
    S = pd.DataFrame(rows)
    print("기준 용량(Ah, 25 °C 최대 방전):", {k: round(v, 4) for k, v in caps25.items()})
    S["cap_ah"] = S.cell.map(caps25)
    S["soc"] = 1 + S.ah / S.cap_ah
    n0 = len(S)
    S = S[(S.soc > -0.02) & (S.soc < 1.02)].reset_index(drop=True)
    print(f"SOC 범위 밖 제거: {n0 - len(S)}")
    # 등록 후보: 25 °C PCPD, 그리고 0 °C에 가장 가까운 온도(같으면 더 추운 쪽)의 PCPD 중 원시 기록이 있는 것
    S["reg25"] = (S.temp_c == 25) & (S.ftype == "PCPD")
    S["reg2"] = False
    S["reg2_temp"] = np.nan
    for c in S.cell.unique():
        temps = sorted(S[(S.cell == c) & (S.ftype == "PCPD") & (S.temp_c != 25)].temp_c.unique(),
                       key=lambda x: (abs(x), x))
        if temps:
            m = (S.cell == c) & (S.ftype == "PCPD") & (S.temp_c == temps[0])
            S.loc[m, "reg2"] = True
            S.loc[S.cell == c, "reg2_temp"] = temps[0]
    S["is_reg"] = S.reg25 | S.reg2
    S["sid"] = [f"{d}|{c}|{t}|{f}|{i}" for i, (d, c, t, f) in enumerate(zip(S.dataset, S.cell, S.temp_c, S.file))]
    out = BASE / "rest_final2.npz"
    prep.save(out, S)
    summ = S.assign(n1s=S.raw_n60 >= 30).groupby(["cell", "temp_c", "ftype", "reg25", "reg2"]).agg(
        n=("soc", "size"), soc_lo=("soc", "min"), soc_hi=("soc", "max"), rest_med=("rest_len", "median"),
        true1s=("n1s", "mean"), kinks=("kinks60", "median"), preI=("pre_I60", "median"))
    print(summ.round(2).to_string())
    print("저장:", out)


if __name__ == "__main__":
    main()
