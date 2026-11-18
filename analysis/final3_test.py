"""2점 등록 확증 시험 1회 실행 (analysis/final3_test_protocol.md). 결과를 본 뒤 모델·규칙을 바꾸지 않는다.

  python -I analysis/final3_test.py --dry-run   # dev Samsung_30T를 가짜 시험 셀로(25 + 0 °C 등록), 최종 데이터 안 읽음
  python -I analysis/final3_test.py             # 확증 실행. analysis/final3_out/RUN_DONE이 있으면 거부한다
"""
import argparse
import json
import subprocess
import sys
import time
import zlib
from datetime import datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import two_point as tp  # noqa: E402
import variants  # noqa: E402
from bench import data, ev  # noqa: E402

FINAL = Path("C:/BMS/data/holdout_final3/rest_final3.npz")
RS = [60, 300, 600]
R = ev.PRIMARY_R
B = 2000


class TwoPointCold:
    """T2_cold (커밋 7d4bbc5): 25 °C 등록 표와 저온 등록 표의 SOC를 주변 온도로 내삽. 25 °C 위로는 외삽하지 않는다. 학습 없음."""

    def __init__(self, seed=0, **_):
        pass

    def fit(self, train):
        return self

    def predict(self, test):
        v = test["rest_V"]
        r = v.shape[1]
        p25 = variants.RegLookup().predict({"rest_V": v, "ref": test["ref"]})
        plo = variants.RegLookup().predict({"rest_V": v, "ref": test["ref2"]})
        w = np.maximum((test["temp_c"] - 25) / (test["t_low"] - 25), 0)
        return np.clip(p25 + w * (plo - p25), 0, 1)


METHODS = {  # 프로토콜 2절
    "T2_cold": (lambda s: TwoPointCold(s), [0]),
    "S_simple": (lambda s: variants.Proposed(s, multi=False, knn=False, aug_shape=False, aug_hw=False), [0, 1, 2, 3, 4]),
    "B1_reg_lookup": (lambda s: variants.RegLookup(s), [0]),
    "B2_reg_lookup_temp": (lambda s: variants.RegLookupTemp(s), [0]),
    "P_full": (lambda s: variants.Proposed(s), [0, 1, 2, 3, 4]),
}
LABEL = {"T2_cold": "**2점 등록 T2_cold**", "S_simple": "S_simple 학습 보정(동결)", "B1_reg_lookup": "B1 25 °C 등록 표 조회",
         "B2_reg_lookup_temp": "B2 B1 + 선형 온도 보정", "P_full": "P_full (보조)"}
PRIMARY = ["S_simple", "B1_reg_lookup"]  # H3, H4


def load_test(dry):
    if dry:
        X, meta = data()
        k = meta["dataset"] == "Samsung_30T"
        reg = ev.reg_mask(meta)[k]
        reg2 = tp.reg_at(meta, "Samsung_30T", 0.0)[k]
        T = {"rest_V": X["rest_V"][k], **{c: meta[c][k] for c in ["dataset", "cell", "temp_c", "soc", "rest_len"]},
             "is_reg": reg, "is_reg2": reg2, "raw_n60": np.full(k.sum(), 60)}
        return T, ~k
    z = np.load(FINAL, allow_pickle=False)
    m = z["meta"]
    T = {"rest_V": z["rest_V"], **{c: m[c] for c in ["dataset", "cell", "temp_c", "soc", "rest_len", "is_reg", "is_reg2", "raw_n60"]}}
    return T, None


def train_dict(train_mask):
    X, meta = data()
    keep = np.ones(len(meta), bool) if train_mask is None else train_mask
    tr = {k: v[keep] for k, v in X.items()}
    tr.update({c: meta[c][keep] for c in ["dataset", "chem", "cell", "temp_c", "soc", "rest_len"]})
    tr["reg"] = ev.reg_mask(meta)[keep]
    return tr


def run(T, train):
    out = {}
    cells = sorted({(d, c) for d, c in zip(T["dataset"], T["cell"])})
    for name, (factory, seeds) in METHODS.items():
        rec = {k: [] for k in ["idx", "r", "es", "s", "pred"]}
        for es in seeds:
            model = factory(es).fit(train)
            for d, c in cells:
                kc = (T["dataset"] == d) & (T["cell"] == c)
                rk, rk2 = kc & T["is_reg"], kc & T["is_reg2"]
                if rk.sum() < 3 or rk2.sum() < 3:
                    print(f"  {d}/{c}: 등록 표본 부족 ({rk.sum()}, {rk2.sum()}) → 제외")
                    continue
                t_low = float(np.unique(T["temp_c"][rk2])[0])
                ref = {"rest_V": T["rest_V"][rk], "soc": T["soc"][rk], "rest_len": T["rest_len"][rk]}
                ref2 = {"rest_V": T["rest_V"][rk2], "soc": T["soc"][rk2], "rest_len": T["rest_len"][rk2]}
                for r in RS:
                    sel = kc & ~T["is_reg"] & ~T["is_reg2"] & (T["temp_c"] != ev.REF_T) & (T["temp_c"] != t_low) & (T["rest_len"] >= r)
                    if not sel.any():
                        continue
                    for s in ev.SEEDS:
                        v = ev.corrupt(T["rest_V"][sel], r, 1000 * s + r)
                        tc = T["temp_c"][sel].astype(float) + np.random.default_rng(5000 + 1000 * s + r).normal(0, ev.TEMP_SD, sel.sum())
                        p = np.clip(np.asarray(model.predict({"rest_V": v, "ref": ref, "ref2": ref2, "t_low": t_low, "temp_c": tc}),
                                               float), 0, 1)
                        rec["idx"].append(np.flatnonzero(sel))
                        rec["r"] += [r] * sel.sum()
                        rec["es"] += [es] * sel.sum()
                        rec["s"] += [s] * sel.sum()
                        rec["pred"].append(p)
        out[name] = {k: (np.concatenate(v) if isinstance(v[0], np.ndarray) else np.array(v)) for k, v in rec.items()}
        print(f"  {name} done ({time.strftime('%H:%M:%S')})", flush=True)
    return out


def per_sample(rec, T, r=R):
    k = rec["r"] == r
    u, inv = np.unique(rec["idx"][k], return_inverse=True)
    p = np.bincount(inv, rec["pred"][k]) / np.bincount(inv)
    return u, np.abs(p - T["soc"][u]) * 100, (p - T["soc"][u]) * 100


def boot(u, e, T, draw):
    """셀 단위 부트스트랩 MAE (B,): 뽑힌 셀의 표본을 모아 평균(표본 가중). draw는 방법 간 공유(짝지음)."""
    cells = T["cell"][u]
    uc = np.unique(T["cell"])
    sums = np.array([e[cells == c].sum() for c in uc])
    cnts = np.array([(cells == c).sum() for c in uc])
    return sums[draw].sum(1) / np.maximum(cnts[draw].sum(1), 1)


def report(res, T, info, path):
    uc = np.unique(T["cell"])
    draw = np.random.default_rng(zlib.crc32(b"final3")).integers(0, len(uc), (B, len(uc)))
    L = ["# 2점 등록 확증 시험 결과", "", f"- 실행: {info['time']}  커밋 {info['commit']}  ({info['sec']:.0f} s)",
         "- 프로토콜: analysis/final3_test_protocol.md. 이 표는 1회 실행 출력 그대로다.", ""]
    S = {n: per_sample(res[n], T) for n in res}
    u0 = S["T2_cold"][0]
    for n in res:
        assert np.array_equal(S[n][0], u0), f"{n}: 채점 표본이 다름"
    cold = T["temp_c"][u0] < np.min(T["temp_c"][T["is_reg2"]])
    groups = [("전체", np.ones(len(u0), bool)), ("저온 등록보다 추운 표본", cold)]
    for gname, g in groups:
        bs = {n: boot(u0[g], S[n][1][g], T, draw) for n in res}
        L += [f"## 표 A{'' if gname == '전체' else '2'}. {gname} (r = 300 s, n = {g.sum()}, 셀 {len(uc)}개, MAE %p [셀 부트스트랩 95 % CI])", "",
              "| 방법 | MAE [CI] | 편향 | P95 | 방법 − T2_cold [짝지은 CI] |", "|---|---|---|---|---|"]
        for n in res:
            e, b = S[n][1][g], S[n][2][g]
            d = bs[n] - bs["T2_cold"]
            diff = "—" if n == "T2_cold" else (f"{e.mean() - S['T2_cold'][1][g].mean():+.3f} "
                                               f"[{np.percentile(d, 2.5):+.2f}, {np.percentile(d, 97.5):+.2f}]")
            L.append(f"| {LABEL[n]} | {e.mean():.3f} [{np.percentile(bs[n], 2.5):.2f}, {np.percentile(bs[n], 97.5):.2f}] | "
                     f"{b.mean():+.2f} | {np.percentile(e, 95):.2f} | {diff} |")
        L.append("")
    bs = {n: boot(u0, S[n][1], T, draw) for n in res}
    L += ["## 가설 판정 (프로토콜 5절: 짝지은 CI 하한 > 0 이면 지지)", ""]
    for h, n in zip(["H3", "H4"], PRIMARY):
        d = bs[n] - bs["T2_cold"]
        lo, hi = np.percentile(d, [2.5, 97.5])
        L.append(f"- {h} T2_cold < {LABEL[n]}: 차이 {S[n][1].mean() - S['T2_cold'][1].mean():+.3f} [{lo:+.2f}, {hi:+.2f}] → "
                 f"{'**지지**' if lo > 0 else '**지지 안 됨**'}")
    L += ["", "## 표 B. 휴지 길이 r (전체 MAE)", "", "| 방법 | r = 60 | r = 300 | r = 600 |", "|---|---|---|---|"]
    for n in res:
        L.append(f"| {LABEL[n]} | " + " | ".join(f"{per_sample(res[n], T, r)[1].mean():.3f}" for r in RS) + " |")
    for key, title, fmt in [("temp_c", "온도별", lambda t: f"{t:g} °C"), ("cell", "셀별", str)]:
        L += ["", f"## 표 C. {title} MAE / 편향 (r = 300 s)", "", f"| {title[:-1]} | n | " + " | ".join(LABEL[n] for n in res) + " |",
              "|---|---|" + "---|" * len(res)]
        vals = T[key][u0]
        for v in sorted(set(vals.tolist())):
            k = vals == v
            L.append(f"| {fmt(v)} | {k.sum()} | " + " | ".join(f"{S[n][1][k].mean():.2f} / {S[n][2][k].mean():+.2f}" for n in res) + " |")
    L += ["", "## 표 D. SOC 구간별 MAE (r = 300 s)", "", "| SOC | n | " + " | ".join(LABEL[n] for n in res) + " |",
          "|---|---|" + "---|" * len(res)]
    bins = np.clip(np.floor(T["soc"][u0] * 5 + 1e-9), 0, 4)
    for bb in range(5):
        k = bins == bb
        if k.any():
            L.append(f"| {bb / 5:.1f}–{(bb + 1) / 5:.1f} | {k.sum()} | " + " | ".join(f"{S[n][1][k].mean():.2f}" for n in res) + " |")
    L += ["", "## 표본 수", "", "| 셀 | 채점 (r = 300) | 25 °C 등록 | 저온 등록 | 저온 등록 온도 |", "|---|---|---|---|---|"]
    for c in uc:
        kc = T["cell"] == c
        L.append(f"| {c} | {(T['cell'][u0] == c).sum()} | {(kc & T['is_reg']).sum()} | {(kc & T['is_reg2']).sum()} | "
                 f"{', '.join(f'{t:g}' for t in np.unique(T['temp_c'][kc & T['is_reg2']]))} °C |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    outdir = HERE / ("tmp/final3_dry" if a.dry_run else "final3_out")
    outdir.mkdir(parents=True, exist_ok=True)
    done = outdir / "RUN_DONE"
    if done.exists() and not a.dry_run:
        sys.exit(f"이미 실행함: {done.read_text(encoding='utf-8')}  (프로토콜: 1회만)")
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "analysis", "estimator.py"], cwd=ROOT, capture_output=True,
                           text=True).stdout.strip()
    if dirty and not a.dry_run:
        sys.exit("analysis/ 또는 estimator.py에 커밋 안 된 변경이 있음. 커밋 후 실행할 것:\n" + dirty)
    t0 = time.time()
    T, train_mask = load_test(a.dry_run)
    train = train_dict(train_mask)
    print(f"test n={len(T['soc'])}, train n={len(train['soc'])}", flush=True)
    res = run(T, train)
    info = dict(time=datetime.now().strftime("%Y-%m-%d %H:%M"), commit=commit, sec=time.time() - t0, dry_run=a.dry_run)
    for n, rec in res.items():
        np.savez_compressed(outdir / f"{n}.npz", **rec)
    out_md = (outdir / "final3_results.md") if a.dry_run else (HERE / "final3_results.md")
    report(res, T, info, out_md)
    if not a.dry_run:
        done.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    print("wrote", out_md)


if __name__ == "__main__":
    main()
