"""최종 테스트 1회 실행 (analysis/final_test_protocol.md). 결과를 본 뒤 모델·규칙을 바꾸지 않는다.

  python -I analysis/final_test.py --dry-run   # dev의 Samsung_30T를 가짜 시험 셀로 써서 코드만 점검 (최종 데이터 안 읽음)
  python -I analysis/final_test.py             # 최종 실행. analysis/final_out/RUN_DONE이 있으면 거부한다
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
import variants  # noqa: E402
from bench import data, ev  # noqa: E402

FINAL = Path("C:/BMS/data/holdout_final/rest_final.npz")
RS = [60, 300, 600]
R = ev.PRIMARY_R
METHODS = {  # 프로토콜 1절: 제안법 S_simple + 미리 정한 비교 대상
    "S_simple": (lambda s: variants.Proposed(s, multi=False, knn=False, aug_shape=False, aug_hw=False), [0, 1, 2, 3, 4]),
    "B1_reg_lookup": (lambda s: variants.RegLookup(s), [0]),
    "B2_reg_lookup_temp": (lambda s: variants.RegLookupTemp(s), [0]),
    "P_full": (lambda s: variants.Proposed(s), [0, 1, 2, 3, 4]),
}
LABEL = {"S_simple": "**제안법 (단순화, 고정)**", "B1_reg_lookup": "B1 등록 OCV 표 조회",
         "B2_reg_lookup_temp": "B2 등록 표 + 선형 온도 보정", "P_full": "P_full 전체 버전 (보조)"}


def load_test(dry):
    if dry:  # dev Samsung_30T를 시험 셀로, 나머지 4개로 학습 (최종 데이터는 읽지 않음)
        X, meta = data()
        reg = ev.reg_mask(meta)
        k = meta["dataset"] == "Samsung_30T"
        T = {"rest_V": X["rest_V"][k], "dataset": meta["dataset"][k], "cell": meta["cell"][k], "temp_c": meta["temp_c"][k],
             "soc": meta["soc"][k], "rest_len": meta["rest_len"][k], "is_reg": reg[k],
             "raw_n60": np.full(k.sum(), 60), "meas_temp": meta["temp_c"][k].astype(float)}
        return T, ~k
    z = np.load(FINAL, allow_pickle=False)
    m = z["meta"]
    T = {"rest_V": z["rest_V"], **{c: m[c] for c in ["dataset", "cell", "temp_c", "soc", "rest_len", "is_reg", "raw_n60",
                                                     "meas_temp"]}}
    return T, None


def train_dict(train_mask):
    X, meta = data()
    keep = np.ones(len(meta), bool) if train_mask is None else train_mask
    tr = {k: v[keep] for k, v in X.items()}
    tr.update({c: meta[c][keep] for c in ["dataset", "chem", "cell", "temp_c", "soc", "rest_len"]})
    tr["reg"] = ev.reg_mask(meta)[keep]
    return tr


def run(T, train):
    """표본별 예측 기록. 모델은 한 번 학습하고 온도 입력 두 가지로 예측한다:
    nominal(챔버 명목 온도, 주 분석) / measured(휴지 처음 300 s 셀 온도 중앙값, 민감도)."""
    out = {"nominal": {}, "measured": {}}
    cells = sorted({(d, c) for d, c in zip(T["dataset"], T["cell"])})
    for name, (factory, seeds) in METHODS.items():
        rec = {m: {k: [] for k in ["idx", "r", "es", "s", "pred"]} for m in out}
        for es in seeds:
            model = factory(es).fit(train)
            for d, c in cells:
                kc = (T["dataset"] == d) & (T["cell"] == c)
                rk = kc & T["is_reg"]
                ref = {"rest_V": T["rest_V"][rk], "soc": T["soc"][rk], "rest_len": T["rest_len"][rk]}
                for r in RS:
                    sel = kc & ~T["is_reg"] & (T["temp_c"] != ev.REF_T) & (T["rest_len"] >= r)
                    if not sel.any():
                        continue
                    for s in ev.SEEDS:
                        v = ev.corrupt(T["rest_V"][sel], r, 1000 * s + r)
                        noise = np.random.default_rng(5000 + 1000 * s + r).normal(0, ev.TEMP_SD, sel.sum())
                        for mode, base in (("nominal", T["temp_c"]), ("measured", T["meas_temp"])):
                            tc = base[sel].astype(float) + noise
                            p = np.clip(np.asarray(model.predict({"rest_V": v, "ref": ref, "temp_c": tc}), float), 0, 1)
                            q = rec[mode]
                            q["idx"].append(np.flatnonzero(sel))
                            q["r"] += [r] * sel.sum()
                            q["es"] += [es] * sel.sum()
                            q["s"] += [s] * sel.sum()
                            q["pred"].append(p)
        for mode in out:
            out[mode][name] = {k: (np.concatenate(v) if isinstance(v[0], np.ndarray) else np.array(v))
                               for k, v in rec[mode].items()}
        print(f"  {name} done ({time.strftime('%H:%M:%S')})", flush=True)
    return out["nominal"], out["measured"]


def per_sample(rec, T, r=R):
    """표본 idx → 시드 평균 절대오차·부호 오차."""
    k = rec["r"] == r
    idx, pred = rec["idx"][k], rec["pred"][k]
    u, inv = np.unique(idx, return_inverse=True)
    p = np.bincount(inv, pred) / np.bincount(inv)
    return u, np.abs(p - T["soc"][u]) * 100, (p - T["soc"][u]) * 100


def cell_boot(u, e, T, rng, B=2000):
    """데이터셋별 부트스트랩 평균 MAE (B,). 셀이 여럿이면 셀 단위, 하나면 표본 단위."""
    cells = T["cell"][u]
    uc = np.unique(cells)
    if len(uc) > 1:
        draw = rng.integers(0, len(uc), (B, len(uc)))
        sums = np.array([e[cells == c].sum() for c in uc])
        cnts = np.array([(cells == c).sum() for c in uc])
        return sums[draw].sum(1) / cnts[draw].sum(1)
    w = rng.multinomial(len(e), np.full(len(e), 1 / len(e)), size=B)
    return (w * e).sum(1) / len(e)


def report(res, T, sens, meta_info, path):
    ds = sorted(set(T["dataset"]))
    L = [f"# 최종 테스트 결과", "", f"- 실행: {meta_info['time']}  커밋 {meta_info['commit']}  ({meta_info['sec']:.0f} s)",
         "- 프로토콜: analysis/final_test_protocol.md. 이 표는 1회 실행 출력 그대로다.", ""]
    P = {n: {d: None for d in ds} for n in res}
    boots = {}
    for n in res:
        u, e, b = per_sample(res[n], T)
        for d in ds:
            k = T["dataset"][u] == d
            P[n][d] = (u[k], e[k], b[k])
            boots[(n, d)] = cell_boot(u[k], e[k], T, np.random.default_rng(zlib.crc32(d.encode())))
    L += ["## 표 A. 주 지표 (r = 300 s, MAE %p, 95 % CI)", "",
          "| 방법 | " + " | ".join(f"{d} MAE [CI]" for d in ds) + " | 평균 | " + " | ".join(f"{d} P95" for d in ds) + " |",
          "|---|" + "---|" * (2 * len(ds) + 1)]
    for n in res:
        cells = [f"{P[n][d][1].mean():.3f} [{np.percentile(boots[(n, d)], 2.5):.2f}, {np.percentile(boots[(n, d)], 97.5):.2f}]"
                 for d in ds]
        L.append(f"| {LABEL[n]} | " + " | ".join(cells) + f" | {np.mean([P[n][d][1].mean() for d in ds]):.3f} | "
                 + " | ".join(f"{np.percentile(P[n][d][1], 95):.2f}" for d in ds) + " |")
    L += ["", "## 표 B. 제안법 대비 차이 (짝지은 95 % CI; + 이면 제안법이 나음)", "", "| 비교 | " + " | ".join(ds) + " |",
          "|---|" + "---|" * len(ds)]
    for n in [x for x in res if x != "S_simple"]:
        L.append(f"| {LABEL[n]} − 제안법 | " + " | ".join(
            f"{P[n][d][1].mean() - P['S_simple'][d][1].mean():+.3f} [{np.percentile(boots[(n, d)] - boots[('S_simple', d)], 2.5):+.2f}, "
            f"{np.percentile(boots[(n, d)] - boots[('S_simple', d)], 97.5):+.2f}]" for d in ds) + " |")
    L += ["", "## 표 C. 휴지 길이 r (데이터셋 MAE 평균)", "", "| 방법 | r = 60 | r = 300 | r = 600 |", "|---|---|---|---|"]
    for n in res:
        row = []
        for r in RS:
            u, e, _ = per_sample(res[n], T, r)
            row.append(f"{np.mean([e[T['dataset'][u] == d].mean() for d in ds]):.3f}")
        L.append(f"| {LABEL[n]} | " + " | ".join(row) + " |")
    for d in ds:
        L += ["", f"## 표 D. {d} 온도별 MAE / 편향 (r = 300 s)", "", "| 온도 | n | " + " | ".join(LABEL[n] for n in res) + " |",
              "|---|---|" + "---|" * len(res)]
        u0 = P["S_simple"][d][0]
        for t in sorted(set(T["temp_c"][u0].tolist())):
            cells = []
            for n in res:
                u, e, b = P[n][d]
                k = T["temp_c"][u] == t
                cells.append(f"{e[k].mean():.2f} / {b[k].mean():+.2f}")
            L.append(f"| {t:g} °C | {(T['temp_c'][u0] == t).sum()} | " + " | ".join(cells) + " |")
        L += ["", f"### {d} SOC 구간별 MAE", "", "| SOC | n | " + " | ".join(LABEL[n] for n in res) + " |",
              "|---|---|" + "---|" * len(res)]
        for bb in range(5):
            cells = []
            for n in res:
                u, e, _ = P[n][d]
                k = np.clip(np.floor(T["soc"][u] * 5 + 1e-9), 0, 4) == bb
                cells.append(f"{e[k].mean():.2f}" if k.any() else "—")
            L.append(f"| {bb / 5:.1f}–{(bb + 1) / 5:.1f} | {int((np.clip(np.floor(T['soc'][u0] * 5 + 1e-9), 0, 4) == bb).sum())} | "
                     + " | ".join(cells) + " |")
    L += ["", "## 표 E. 하위 집단: 휴지 처음 60 s가 실제 1 s 기록 (원시 점 ≥ 30)", "", "| 방법 | " + " | ".join(ds) + " |",
          "|---|" + "---|" * len(ds)]
    for n in res:
        cells = []
        for d in ds:
            u, e, _ = P[n][d]
            k = T["raw_n60"][u] >= 30
            cells.append(f"{e[k].mean():.3f} (n={k.sum()})")
        L.append(f"| {LABEL[n]} | " + " | ".join(cells) + " |")
    if sens is not None:
        L += ["", "## 표 F. 민감도: 온도 입력 = 측정 셀 온도 (휴지 처음 300 s 중앙값)", "",
              "| 방법 | " + " | ".join(f"{d} (명목 → 측정)" for d in ds) + " |", "|---|" + "---|" * len(ds)]
        for n in res:
            u2, e2, _ = per_sample(sens[n], T)
            L.append(f"| {LABEL[n]} | " + " | ".join(
                f"{P[n][d][1].mean():.3f} → {e2[T['dataset'][u2] == d].mean():.3f}" for d in ds) + " |")
        d = "Molicel_P42A"
        if d in ds:
            L += ["", "P42A 5 °C 시험의 셀별 측정 온도와 제안법 MAE (명목 / 측정 온도 입력):", ""]
            u, e, _ = P["S_simple"][d]
            u2, e2, _ = per_sample(sens["S_simple"], T)
            for c in sorted(set(T["cell"][u].tolist())):
                k = (T["cell"][u] == c) & (T["temp_c"][u] == 5)
                k2 = (T["cell"][u2] == c) & (T["temp_c"][u2] == 5)
                if k.any():
                    L.append(f"- {c}: T_meas {np.nanmedian(T['meas_temp'][u[k]]):.1f} °C, MAE {e[k].mean():.2f} / {e2[k2].mean():.2f}")
    L += ["", "## 표본 수", "", "| 데이터셋 | 셀 | 채점 표본 (r = 300) | 등록 표본 |", "|---|---|---|---|"]
    for d in ds:
        k = T["dataset"] == d
        L.append(f"| {d} | {len(set(T['cell'][k].tolist()))} | {len(P['S_simple'][d][0])} | {int((k & T['is_reg']).sum())} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    outdir = HERE / ("tmp/final_dry" if a.dry_run else "final_out")
    outdir.mkdir(parents=True, exist_ok=True)
    done = outdir / "RUN_DONE"
    if done.exists() and not a.dry_run:
        sys.exit(f"이미 실행함: {done.read_text(encoding='utf-8')}  (프로토콜 7절: 1회만)")
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "analysis", "estimator.py"], cwd=ROOT, capture_output=True,
                           text=True).stdout.strip()
    if dirty and not a.dry_run:
        sys.exit("analysis/ 또는 estimator.py에 커밋 안 된 변경이 있음. 커밋 후 실행할 것:\n" + dirty)
    t0 = time.time()
    T, train_mask = load_test(a.dry_run)
    train = train_dict(train_mask)
    print(f"test n={len(T['soc'])}, train n={len(train['soc'])}", flush=True)
    res, sens = run(T, train)
    info = dict(time=datetime.now().strftime("%Y-%m-%d %H:%M"), commit=commit, sec=time.time() - t0, dry_run=a.dry_run)
    for tag, R_ in (("nominal", res), ("measured", sens)):
        for n, rec in R_.items():
            np.savez_compressed(outdir / f"{tag}_{n}.npz", **rec)
    out_md = (outdir / "final_results.md") if a.dry_run else (HERE / "final_results.md")
    report(res, T, sens, info, out_md)
    if not a.dry_run:
        done.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    print("wrote", out_md)


if __name__ == "__main__":
    main()
