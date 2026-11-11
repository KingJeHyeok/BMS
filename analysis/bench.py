"""논문용 분석 실행기 (개선 루프 밖 작업). 홀드아웃은 쓰지 않는다.

eval/run.py와 같은 프로토콜(LODO 5폴드 + 온도 외삽 폴드, 저가 체인 오차, 온도 잡음)로 variants.py의 추정기를 돌리고
표본별 예측을 analysis/out/<name>.npz에 저장한다. 평가기 함수는 eval/run.py에서 그대로 가져온다(복사 안 함).

  python -I analysis/bench.py --name P_full [--rs 300] [--est-seeds 0,1,2] [--ext-seeds 0,1,2] [--n-jobs 2]
  python -I analysis/bench.py --check   # Proposed(기본값)와 estimator.py의 예측이 같은지 확인
"""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))  # -I는 스크립트 폴더를 sys.path에 넣지 않는다
import variants  # noqa: E402

_spec = importlib.util.spec_from_file_location("evalrun", ROOT / "eval" / "run.py")
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)


def data():
    X, meta = ev.load(ROOT / "data" / "rest_dev.npz")
    keep = np.isin(meta["dataset"], ev.FOLDS)
    return {k: v[keep] for k, v in X.items()}, meta[keep]


def folds(meta):
    T = meta["temp_c"]
    out = []
    for f in ev.FOLDS:
        out.append((f, f, meta["dataset"] != f, (meta["dataset"] == f) & (T != ev.REF_T), "in"))
    for f in ev.FOLDS:
        te = (meta["dataset"] == f) & ((T < ev.EXT_TRAIN[0]) | (T > ev.EXT_TRAIN[1]))
        if te.sum():
            tr = (meta["dataset"] != f) & (T >= ev.EXT_TRAIN[0]) & (T <= ev.EXT_TRAIN[1])
            out.append(("EXT_" + f, f, tr, te, "ext"))
    return out


def run(factory, rs, est_seeds, ext_seeds, n_jobs):
    X, meta = data()
    REG = ev.reg_mask(meta)
    rec = {k: [] for k in ["key", "idx", "r", "es", "s", "pred", "soc"]}
    for key, fold, tr, te, kind in folds(meta):
        reg = (meta["dataset"] == fold) & REG
        ref = {"rest_V": X["rest_V"][reg], "soc": meta["soc"][reg], "rest_len": meta["rest_len"][reg]}
        train = {k: v[tr] for k, v in X.items()}
        train.update({c: meta[c][tr] for c in ["dataset", "chem", "cell", "temp_c", "soc", "rest_len"]})
        train["reg"] = REG[tr]
        for es in (est_seeds if kind == "in" else ext_seeds):
            model = factory(es, n_jobs)
            model.fit(train)
            for r in rs:
                sel = te & (meta["rest_len"] >= r)
                idx = np.flatnonzero(sel)
                for s in ev.SEEDS:
                    v = ev.corrupt(X["rest_V"][sel], r, 1000 * s + r)
                    tc = meta["temp_c"][sel] + np.random.default_rng(5000 + 1000 * s + r).normal(0, ev.TEMP_SD, sel.sum())
                    pred = np.clip(np.asarray(model.predict({"rest_V": v, "ref": ref, "temp_c": tc}), float), 0, 1)
                    n = len(idx)
                    rec["key"] += [key] * n
                    rec["idx"].append(idx)
                    rec["r"] += [r] * n
                    rec["es"] += [es] * n
                    rec["s"] += [s] * n
                    rec["pred"].append(pred)
                    rec["soc"].append(meta["soc"][sel])
    return {k: (np.concatenate(v) if isinstance(v[0], np.ndarray) else np.array(v)) for k, v in rec.items()}


def summarize(rec, r=ev.PRIMARY_R):
    """run.py와 같은 집계: 키별 MAE(시드 전체 평균) → 0.5·범위 안 평균 + 0.5·외삽 평균."""
    k = rec["r"] == r
    err = np.abs(rec["pred"][k] - rec["soc"][k]) * 100
    keys = rec["key"][k]
    per = {key: float(err[keys == key].mean()) for key in np.unique(keys)}
    m_in = np.mean([per[f] for f in ev.FOLDS])
    ext = [x for x in per if x.startswith("EXT_")]
    m_ext = np.mean([per[x] for x in ext]) if ext else float("nan")
    return dict(primary=0.5 * m_in + 0.5 * m_ext, mae_in=m_in, mae_ext=m_ext, folds=per)


def check():
    """Proposed(기본값)와 estimator.py가 한 폴드에서 같은 예측을 내는지."""
    X, meta = data()
    REG = ev.reg_mask(meta)
    key, fold, tr, te, _ = folds(meta)[0]
    reg = (meta["dataset"] == fold) & REG
    ref = {"rest_V": X["rest_V"][reg], "soc": meta["soc"][reg], "rest_len": meta["rest_len"][reg]}
    train = {k: v[tr] for k, v in X.items()}
    train.update({c: meta[c][tr] for c in ["dataset", "chem", "cell", "temp_c", "soc", "rest_len"]})
    train["reg"] = REG[tr]
    sel = te & (meta["rest_len"] >= 300)
    test = {"rest_V": ev.corrupt(X["rest_V"][sel], 300, 300), "ref": ref, "temp_c": meta["temp_c"][sel].astype(float)}
    a = variants.E.Estimator(seed=0).fit(train).predict(test)
    b = variants.Proposed(seed=0).fit(train).predict(test)
    print(f"check {key}: max |diff| = {np.abs(a - b).max():.2e}  (n={len(a)})")
    return np.allclose(a, b, atol=1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name")
    ap.add_argument("--rs", default="300")
    ap.add_argument("--est-seeds", default="0,1,2")
    ap.add_argument("--ext-seeds", default="0,1,2")
    ap.add_argument("--n-jobs", type=int, default=2)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if check() else 1)
    ints = lambda s: [int(x) for x in s.split(",")]  # noqa: E731
    t0 = time.time()
    rec = run(variants.VARIANTS[a.name], ints(a.rs), ints(a.est_seeds), ints(a.ext_seeds), a.n_jobs)
    sec = time.time() - t0
    (HERE / "out").mkdir(exist_ok=True)
    np.savez_compressed(HERE / "out" / f"{a.name}.npz", **rec)
    summ = {r: summarize(rec, r) for r in ints(a.rs)}
    json.dump({"name": a.name, "sec": sec, "args": vars(a), "summary": summ},
              open(HERE / "out" / f"{a.name}.json", "w", encoding="utf-8"), indent=1)
    s = summ[ev.PRIMARY_R] if ev.PRIMARY_R in summ else next(iter(summ.values()))
    print(f"{a.name:20s} primary {s['primary']:.3f}  IN {s['mae_in']:.3f}  EXT {s['mae_ext']:.3f}  ({sec:.0f}s)  "
          + " ".join(f"{k}={v:.2f}" for k, v in s["folds"].items()))


if __name__ == "__main__":
    main()
