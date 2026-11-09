"""[잠금 파일 - 에이전트 수정 금지] T1 귀환 SOC 평가기.

스테이션은 비행 중 전압·전류를 보지 못한다. 착륙 후 휴지 전압만 본다.
  학습 입력: 개발 데이터의 rest_V(깨끗한 값), pre_V, pre_I, 메타(dataset, chem, cell, temp_c), soc
  시험 입력: rest_V의 처음 r초만, 저가 측정 체인 오차를 입힌 값. 메타·온도·pre 구간 없음.
분할: 데이터셋 하나를 빼고 학습(LODO). 폴드 = LG_HG2, Panasonic_PF, CALCE_INR20R.
주 지표: r = 300 s에서 폴드별 MAE(%p)의 평균 (낮을수록 좋음). 추정기 시드 3개 × 오차 시드 3개 평균.
판정 기준: 가장 최근 baseline 행 이후의 baseline/improved 기록만 비교한다 (지표 정의가 바뀌면 baseline을 다시 찍는다).

사용법 (에이전트): python -I eval/run.py --tag <변경유형> --desc "<한 줄 가설>"
  변경유형: hparam | model | feature | train | other
결과는 results.tsv에 자동으로 한 줄 추가된다. status는 현재 HEAD 이력의 최고 기록 대비 자동 판정.
"""
import argparse
import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FOLDS = ["LG_HG2", "Panasonic_PF", "CALCE_INR20R"]
RS = [60, 300, 600]
PRIMARY_R = 300
SEEDS = [0, 1, 2]
EST_SEEDS = [0, 1, 2]  # 추정기 시드. 시드 운(약 0.08 %p)이 MIN_GAIN보다 크게 작용하지 않게 평균한다
MIN_GAIN = 0.05  # %p. 이보다 작게 좋아지면 개선으로 치지 않는다
TIMEOUT_S = 600
LSB = 3.3 / 4096 * (115 / 15)  # 분압 100k/15k + 12 bit ADC, 약 6.2 mV
COLS = ["time", "commit", "primary_mae", "mae_r60", "mae_r600", "fold_lg", "fold_pan", "fold_inr",
        "p95_r300", "sec", "status", "tag", "desc"]


def load(path):
    z = np.load(path, allow_pickle=False)
    meta = z["meta"]
    return {k: z[k] for k in ["pre_V", "pre_I", "rest_V"]}, meta


def corrupt(rest_V, r, seed):
    """저가 체인: 채널 이득(2점 보정 후 0.2 %), 오프셋 5 mV, 잡음 2 mV, 6.2 mV 양자화, 1 Hz."""
    g = np.random.default_rng(seed)
    n = len(rest_V)
    v = rest_V[:, :r].copy()
    v = v * (1 + g.normal(0, 0.002, (n, 1))) + g.normal(0, 0.005, (n, 1)) + g.normal(0, 0.002, v.shape)
    return np.round(v / LSB) * LSB


def inner():
    spec = importlib.util.spec_from_file_location("estimator", ROOT / "estimator.py")
    est_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(est_mod)
    X, meta = load(ROOT / "data" / "rest_dev.npz")
    keep = np.isin(meta["dataset"], FOLDS)
    X = {k: v[keep] for k, v in X.items()}
    meta = meta[keep]
    out = {}
    for fold in FOLDS:
        tr, te = meta["dataset"] != fold, meta["dataset"] == fold
        train = {k: v[tr] for k, v in X.items()}
        train.update({c: meta[c][tr] for c in ["dataset", "chem", "cell", "temp_c", "soc", "rest_len"]})
        errs = {r: [] for r in RS}
        for es in EST_SEEDS:
            model = est_mod.Estimator(seed=es)
            model.fit(train)
            for r in RS:
                sel = te & (meta["rest_len"] >= r)
                for s in SEEDS:
                    v = corrupt(X["rest_V"][sel], r, 1000 * s + r)
                    pred = np.asarray(model.predict({"rest_V": v}), float)
                    if pred.shape != (sel.sum(),) or not np.isfinite(pred).all():
                        raise ValueError(f"predict가 길이 {sel.sum()}의 유한한 배열을 반환해야 함")
                    errs[r].append(np.abs(np.clip(pred, 0, 1) - meta["soc"][sel]) * 100)
        for r in RS:
            e = np.concatenate(errs[r])
            n = int((te & (meta["rest_len"] >= r)).sum())
            out[f"{fold}|{r}"] = (float(e.mean()), float(np.percentile(e, 95)), n)
    print("__RESULT__" + json.dumps(out))


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def best_in_history(rows):
    """현재 HEAD의 조상 커밋 중, 가장 최근 baseline 행 이후의 baseline/improved 최저값."""
    def anc(c):
        return subprocess.run(["git", "merge-base", "--is-ancestor", c, "HEAD"], cwd=ROOT).returncode == 0
    rows = [r for r in rows if r["status"] in ("baseline", "improved") and r["commit"] != "dirty"
            and r.get("primary_mae") and anc(r["commit"])]
    last_base = max((i for i, r in enumerate(rows) if r["status"] == "baseline"), default=0)
    vals = [float(r["primary_mae"]) for r in rows[last_base:]]
    return min(vals) if vals else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="other", choices=["hparam", "model", "feature", "train", "other", "baseline"])
    ap.add_argument("--desc", default="")
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args()
    if a.inner:
        return inner()
    dirty = bool(git("status", "--porcelain", "--", "estimator.py"))
    commit = "dirty" if dirty else git("rev-parse", "--short", "HEAD")
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-I", __file__, "--inner"], capture_output=True, text=True,
                           timeout=TIMEOUT_S, cwd=ROOT)
        line = [x for x in p.stdout.splitlines() if x.startswith("__RESULT__")]
        res = json.loads(line[-1][10:]) if line else None
        err = p.stderr[-2000:]
    except subprocess.TimeoutExpired:
        res, err = None, f"timeout {TIMEOUT_S}s"
    sec = round(time.time() - t0, 1)
    tsv = ROOT / "results.tsv"
    if not tsv.exists():
        tsv.write_text("\t".join(COLS) + "\n", encoding="utf-8")
    rows = [dict(zip(COLS, l.split("\t"))) for l in tsv.read_text(encoding="utf-8").splitlines()[1:] if l]
    if res is None:
        status, vals = "crash", {}
        print(err)
    else:
        m = lambda r: np.mean([res[f"{f}|{r}"][0] for f in FOLDS])  # noqa: E731
        vals = dict(primary_mae=m(PRIMARY_R), mae_r60=m(60), mae_r600=m(600),
                    fold_lg=res[f"LG_HG2|{PRIMARY_R}"][0], fold_pan=res[f"Panasonic_PF|{PRIMARY_R}"][0],
                    fold_inr=res[f"CALCE_INR20R|{PRIMARY_R}"][0],
                    p95_r300=np.mean([res[f"{f}|{PRIMARY_R}"][1] for f in FOLDS]))
        best = best_in_history(rows)
        if a.tag == "baseline" or best is None:
            status = "baseline"
        elif dirty:
            status = "uncommitted"  # 판정하려면 먼저 커밋할 것
        else:
            status = "improved" if vals["primary_mae"] < best - MIN_GAIN else "not_improved"
    row = dict(time=datetime.now().strftime("%m-%d %H:%M"), commit=commit, sec=sec, status=status,
               tag=a.tag, desc=a.desc.replace("\t", " ")[:200])
    row.update({k: f"{v:.3f}" for k, v in vals.items()})
    with tsv.open("a", encoding="utf-8") as f:
        f.write("\t".join(str(row.get(c, "")) for c in COLS) + "\n")
    print(f"METRIC primary_mae={row.get('primary_mae', 'NA')} status={status} "
          f"(r60={row.get('mae_r60', 'NA')} r600={row.get('mae_r600', 'NA')} "
          f"LG={row.get('fold_lg', 'NA')} PAN={row.get('fold_pan', 'NA')} INR={row.get('fold_inr', 'NA')} "
          f"p95={row.get('p95_r300', 'NA')} {sec}s)")
    if res:
        for k, (mae, p95, n) in sorted(res.items()):
            print(f"  {k:22s} MAE {mae:6.2f}  P95 {p95:6.2f}  n={n}")


if __name__ == "__main__":
    main()
