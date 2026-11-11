"""최종 테스트 휴지 표본 변환 (analysis/final_test_protocol.md 2·3절). 모델은 돌리지 않는다.

eval/prepare_rest.py와 같은 규칙: 방전 직후 휴지(≥300 s, 앞에 300 s 기록), 1 Hz(to_1hz), 만충 기준점부터 Ah 적분,
셀 기준 용량 = 같은 셀 25 °C 파일에서 기준점 이후 방전된 최대 Ah. 다른 점은 휴지 전류 문턱을 C-rate로 맞춘 것(C_nom/150)뿐.

  python -I analysis/prepare_final.py            → C:/BMS/data/holdout_final/rest_final.npz + 점검 출력
추가 메타: is_reg(등록 시험 표본), raw_n60(휴지 처음 60 s의 원시 기록 점 수), meas_temp(휴지 처음 300 s 셀 온도 중앙값), nom_src
"""
import importlib.util
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io as sio

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("prep", ROOT / "eval" / "prepare_rest.py")
prep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prep)
PRE_S, REST_S, MIN_REST_S = prep.PRE_S, prep.REST_S, prep.MIN_REST_S
BASE = Path("C:/BMS/data/holdout_final")
RAW = BASE / "raw"


# ---------------------------------------------------------------- 읽기
def clean(t, V, I, job, ah=None, T=None):
    """기록 오류 제거 + Ah 정리.
    장비 Ah가 있으면 dev(prepare_rest.read_mat)와 같은 규칙: 방전 중 카운터가 0으로 리셋되면 이어 붙인다.
    단, 리셋이나 10 min 넘는 기록 공백 직후 셀이 만충(V ≥ vmax − 0.08, 전류 ≈ 0)이면 파일 밖에서 재충전한 것이므로
    이어 붙이지 않고 그 시점을 새 기준점(restart)으로 둔다. 장비 Ah가 없으면 전류를 적분한다(사다리꼴)."""
    df = pd.DataFrame({"t": t, "V": V, "I": I, "T": T if T is not None else np.nan})
    if ah is not None:
        df["Ah"] = ah
    ok = np.isfinite(df.t) & np.isfinite(df.V) & np.isfinite(df.I) & (df.V > 2.0) & (df.V < 4.5)  # 8 V 같은 기록 오류 제거
    df = df[ok].sort_values("t").drop_duplicates("t").reset_index(drop=True)
    tt, II, VV = df.t.to_numpy(), df.I.to_numpy(), df.V.to_numpy()
    dt = np.diff(tt)
    full = (VV[1:] >= job["vmax"] - 0.08) & (np.abs(II[1:]) <= 2.5 * job["i_rest"])
    if "Ah" in df:
        a = df.Ah.to_numpy()
        d = np.diff(a)
        trap = 0.5 * (II[1:] + II[:-1]) * dt / 3600
        nan = ~np.isfinite(d)
        # 리셋 = 카운터가 0이 되고 그 변화가 전류 적분과 안 맞음 (dev는 위쪽 리셋만 봤다; E66은 충전 뒤 아래쪽 리셋도 있음)
        reset = ~nan & (np.abs(a[1:]) < 0.01) & (np.abs(d - trap) > 0.02 + 1.5 * np.abs(trap))
        restart = (reset | (dt > 600)) & full
        inc = np.where(nan, trap, d)
        inc = np.where(reset & ~restart, trap, inc)
        inc = np.where(restart, 0.0, inc)
        df.attrs["ah_fix"] = f"reset {int(reset.sum())} restart {int(restart.sum())} nan {int(nan.sum())}"
    else:
        inc = 0.5 * (II[1:] + II[:-1]) * dt / 3600
        restart = (dt > 600) & full
        df.attrs["ah_fix"] = f"integrated, restart {int(restart.sum())}"
    df["Ah"] = np.r_[0, np.cumsum(inc)]
    df.attrs["restarts"] = tt[1:][restart].tolist()
    return df


def read_e66(p, job):
    m = sio.loadmat(p, squeeze_me=True, struct_as_record=False)["meas"]
    g = lambda k: np.asarray(getattr(m, k), float)  # noqa: E731
    return clean(g("Time"), g("Voltage"), g("Current"), job, g("Ah"), g("Battery_Temp_degC"))


# ---------------------------------------------------------------- 표본 (prepare_rest.samples와 같은 규칙, 문턱만 인자)
def anchor(df, vmax, i_rest):
    """dev 규칙(파일 시작이 만충이면 시작점, 아니면 만충 충전 블록의 끝) + 파일 밖 재충전 뒤 만충 시작점(restart)."""
    out = list(df.attrs.get("restarts", []))
    if df.V.iat[0] >= vmax - 0.08 and abs(df.I.iat[0]) <= 2.5 * i_rest:
        return sorted({df.t.iat[0], *out})
    chg = (df.I > i_rest).to_numpy()
    e = np.flatnonzero(np.diff(np.r_[0, chg.astype(int), 0]))
    t = df.t.to_numpy()
    for a, b in zip(e[::2], e[1::2]):
        if t[b - 1] - t[a] > 300 and df.V.iat[b - 1] >= vmax - 0.05:
            out.append(t[b - 1])
    return sorted(set(out))


def samples(df, job):
    i_rest = job["i_rest"]
    out, ahmin = [], 0.0
    A = anchor(df, job["vmax"], i_rest)
    for k, t0 in enumerate(A):
        seg = df[(df.t >= t0) & (df.t < (A[k + 1] if k + 1 < len(A) else np.inf))]
        g = prep.to_1hz(seg[["t", "V", "I", "Ah"]] if "Ah" in seg else seg[["t", "V", "I"]], t0)
        V, I, ah = g.V.to_numpy(), g.I.to_numpy(), g.ah.to_numpy()
        ahmin = min(ahmin, float(np.nanmin(ah)))
        sec0 = g.index[0]
        traw = seg.t.to_numpy() - t0
        Traw = seg["T"].to_numpy()
        rest = np.abs(I) < i_rest
        e = np.flatnonzero(np.diff(np.r_[0, rest.astype(int), 0]))
        for a, b in zip(e[::2], e[1::2]):
            if b - a < MIN_REST_S or a < PRE_S:
                continue
            if I[a - 60:a].mean() > -i_rest:  # 방전 직후 휴지만
                continue
            rv = np.full(REST_S, np.nan)
            n = min(b - a, REST_S)
            rv[:n] = V[a:a + n]
            s0 = sec0 + a
            w60 = (traw >= s0) & (traw < s0 + 60)
            w300 = (traw >= s0) & (traw < s0 + 300)
            out.append(dict(dataset=job["dataset"], chem=job["chem"], cell=job["cell"], temp_c=job["temp_c"],
                            file=job["file"], rest_len=int(b - a), ah=float(ah[a]), pre_V=V[a - PRE_S:a],
                            pre_I=I[a - PRE_S:a], rest_V=rv, is_reg=job["is_reg"], raw_n60=int(w60.sum()),
                            meas_temp=float(np.nanmedian(Traw[w300])) if np.isfinite(Traw[w300]).any() else np.nan,
                            nom_src=job["nom_src"]))
    return out, ahmin


# ---------------------------------------------------------------- 데이터셋별 작업 목록
def e66_jobs():
    root = RAW / "e66" / "Cell Data"
    for p in sorted(root.rglob("*.mat")):
        if re.search(r"mastchg|Charge|TS\d+", p.name):  # 충전·시퀀스 파일 제외 (dev도 충전 파일 제외)
            continue
        folder = next(x for x in p.parts if x.endswith("degC"))
        t = int(folder[:-4])  # "-20degC" → −20
        nom, src = t, "folder"
        # README: 각 온도 폴더의 C/20 방전(C20Dis)은 40 °C에서 함. 예외: 25 °C Part 1의 C20Dis는 25 °C
        if p.name.endswith("_C20Dis.mat") and not ("25degC" in p.parts and "Part 1" in str(p)):
            nom, src = 40, "readme_c20_at_40"
        yield dict(path=p, reader=read_e66, dataset="LG_E66", chem="NMC", vmax=4.2, cell="E66", temp_c=nom,
                   file=str(p.relative_to(root)), i_rest=65.0 / 150, cap_nom=65.0,
                   is_reg=(nom == 25 and p.name.endswith("_GITT.mat")), nom_src=src)


P42A = RAW / "p42a"
_hcgt_cache = {}


def _hcgt(temp):
    if temp not in _hcgt_cache:
        _hcgt_cache[temp] = sio.loadmat(P42A / "hcgt_mat" / f"HCGT_{temp}degC.mat", squeeze_me=True,
                                        struct_as_record=False)["hcgt_data"]
    return _hcgt_cache[temp]


def read_p42a(p, job):
    h = getattr(_hcgt(job["temp_c"]), job["cell"])
    return clean(np.asarray(h.time, float), np.asarray(h.voltage, float), np.asarray(h.current, float), job,
                 T=np.asarray(h.T_cell, float))


def p42a_jobs():
    cells = list(_hcgt(25)._fieldnames)
    for temp in (5, 25, 40):
        avail = set(_hcgt(temp)._fieldnames)
        for c in cells:
            if c in avail:
                yield dict(path=P42A / "hcgt_mat" / f"HCGT_{temp}degC.mat", reader=read_p42a, dataset="Molicel_P42A",
                           chem="NMC", vmax=4.2, cell=c, temp_c=temp, file=f"HCGT_{temp}degC.mat:{c}", i_rest=4.2 / 150,
                           cap_nom=4.2, is_reg=(temp == 25), nom_src="folder")


def p42a_caps():
    """셀 기준 용량 = 같은 셀 25 °C CDT의 C/20 방전 용량(만충에서 컷오프까지)."""
    out = {}
    for f in sorted((P42A / "cdt_mat").glob("*_CDT_25degC.mat")):
        c = sio.loadmat(f, squeeze_me=True, struct_as_record=False)["cby20"]
        out[f.name.split("_")[0]] = float(np.nanmax(np.abs(np.asarray(c.capacity_dis, float))))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    which = sys.argv[1:] or ["e66", "p42a"]
    rows, caps = [], {}
    for job in [j for w in which for j in {"e66": e66_jobs, "p42a": p42a_jobs}[w]()]:
        df = job["reader"](job["path"], job)
        s, ahmin = samples(df, job)
        dT = [abs(x["meas_temp"] - x["temp_c"]) for x in s if np.isfinite(x["meas_temp"])]
        print(f"{len(s):3d} rests  {job['dataset']:7s} {job['temp_c']:4d}  {df.attrs.get('ah_fix', ''):28s} ahmin={ahmin:7.2f}  "
              f"max|T_meas−T_nom|={max(dT) if dT else float('nan'):5.1f}  {job['file']}", flush=True)
        if job["dataset"] == "LG_E66" and job["temp_c"] == 25 and "25degC" in str(job["path"]):
            caps[job["cell"]] = max(caps.get(job["cell"], 0), -ahmin)
        rows += s
    S = pd.DataFrame(rows)
    if "p42a" in which:
        caps.update(p42a_caps())
    print("기준 용량(Ah):", {k: round(v, 3) for k, v in caps.items()})
    S["cap_ah"] = S.cell.map(caps)
    S["soc"] = 1 + S.ah / S.cap_ah
    n0 = len(S)
    S = S[(S.soc > -0.02) & (S.soc < 1.02)].reset_index(drop=True)
    print(f"SOC 범위 밖 제거: {n0 - len(S)}")
    S["sid"] = [f"{d}|{c}|{t}|{f}|{i}" for i, (d, c, t, f) in enumerate(zip(S.dataset, S.cell, S.temp_c, S.file))]
    out = BASE / "rest_final.npz"
    prep.save(out, S)
    summ = S.assign(n1s=S.raw_n60 >= 30).groupby(["dataset", "temp_c", "is_reg"]).agg(
        n=("soc", "size"), soc_lo=("soc", "min"), soc_hi=("soc", "max"), rest_med=("rest_len", "median"),
        true1s=("n1s", "mean"), Tmeas=("meas_temp", "median"))
    print(summ.round(2).to_string())
    print("저장:", out)


if __name__ == "__main__":
    main()
