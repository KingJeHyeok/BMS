"""[사람 전용 - 에이전트 실행 금지] 홀드아웃 평가.

각 폴드 D에 대해: 개발 데이터에서 D를 뺀 나머지로 학습하고, D의 홀드아웃 온도 표본으로 시험한다.
결과는 C:/BMS/data/holdout/holdout_log.tsv에 추가한다(에이전트는 읽지 못하는 위치).
사용법: python -I eval/holdout.py
"""
import importlib.util
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as R  # noqa: E402

LOG = Path("C:/BMS/data/holdout/holdout_log.tsv")


def main():
    spec = importlib.util.spec_from_file_location("estimator", R.ROOT / "estimator.py")
    est = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(est)
    X, meta = R.load(R.ROOT / "data" / "rest_dev.npz")
    H, hmeta = R.load(Path("C:/BMS/data/holdout/rest_holdout.npz"))
    res = {}
    REG = R.reg_mask(meta)
    for fold in R.FOLDS:
        tr = np.isin(meta["dataset"], R.FOLDS) & (meta["dataset"] != fold)
        train = {k: v[tr] for k, v in X.items()}
        train.update({c: meta[c][tr] for c in ["dataset", "chem", "cell", "temp_c", "soc", "rest_len"]})
        train["reg"] = REG[tr]
        sel = (hmeta["dataset"] == fold) & (hmeta["rest_len"] >= R.PRIMARY_R)
        reg = (meta["dataset"] == fold) & REG  # 등록 데이터: 개발 셋의 같은 셀 25 °C HPPC 한 번
        ref = {"rest_V": X["rest_V"][reg], "soc": meta["soc"][reg], "rest_len": meta["rest_len"][reg]}
        errs = []
        for es in R.EST_SEEDS:  # run.py와 같이 추정기 시드 평균
            model = est.Estimator(seed=es)
            model.fit(train)
            errs += [np.abs(np.clip(model.predict({"rest_V": R.corrupt(H["rest_V"][sel], R.PRIMARY_R, 7000 + s), "ref": ref,
                                                   "temp_c": hmeta["temp_c"][sel] + np.random.default_rng(9000 + s).normal(0, R.TEMP_SD, sel.sum())}),
                                    0, 1) - hmeta["soc"][sel]) * 100 for s in R.SEEDS]
        res[fold] = float(np.concatenate(errs).mean())
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=R.ROOT, capture_output=True,
                            text=True).stdout.strip()
    mean = np.mean(list(res.values()))
    new = not LOG.exists()
    with LOG.open("a", encoding="utf-8") as f:
        if new:
            f.write("time\tcommit\tholdout_mae\t" + "\t".join(R.FOLDS) + "\n")
        f.write(f"{datetime.now():%m-%d %H:%M}\t{commit}\t{mean:.3f}\t" + "\t".join(f"{res[k]:.3f}" for k in R.FOLDS) + "\n")
    print(f"HOLDOUT mae={mean:.3f}  " + "  ".join(f"{k}={v:.2f}" for k, v in res.items()))


if __name__ == "__main__":
    main()
