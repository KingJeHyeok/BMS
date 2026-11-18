"""시험 3 (사전 등록, analysis/final4_test_protocol.md): 제안 T2_cold vs 기존 방법. 1회 실행.

  python -I analysis/final4_test.py --dry-run   # dev Samsung_30T를 가짜 시험 셀로(25 + 0 °C 등록), 시험 데이터 안 읽음
  python -I analysis/final4_test.py             # 확증 실행. analysis/final4_out/RUN_DONE이 있으면 거부
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
from sklearn.isotonic import IsotonicRegression

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import final3_test as f3  # noqa: E402
import two_point as tp  # noqa: E402
import variants  # noqa: E402
from bench import data, ev  # noqa: E402

FINAL = Path("C:/BMS/data/holdout_final4/rest_final4.npz")
RS = [60, 300, 600]
R = ev.PRIMARY_R
B = 2000
Z = np.linspace(0, 1, 201)


class ESC2:
    """기존 방법: 전압 영역 온도 OCV 모델(Plett ESC의 OCV(z,T) = OCV0(z) + T·OCVrel(z) 형태)을 등록 표 2개로 만든 것.
    V(z,T) = V25(z) + a·(Vlow(z) − V25(z)), a = (T − 25)/(T_low − 25), 양쪽 선형. 끝 전압을 역변환. (esc_compare.py와 같음)"""

    def __init__(self, seed=0, **_):
        pass

    def fit(self, train):
        return self

    @staticmethod
    def _vz(ref, r):
        k = ref["rest_len"] >= r
        end = variants.feats(ref["rest_V"][k, :r])[:, 0]
        return IsotonicRegression(out_of_bounds="clip").fit(ref["soc"][k], end).predict(Z)

    def predict(self, test):
        v = test["rest_V"]
        r = v.shape[1]
        V25, Vlo = self._vz(test["ref"], r), self._vz(test["ref2"], r)
        a = (test["temp_c"] - 25) / (test["t_low"] - 25)
        end = variants.feats(v)[:, 0]
        out = []
        for ai, e in zip(a, end):
            Vz = V25 + ai * (Vlo - V25)
            Vz = np.maximum.accumulate(Vz + np.arange(len(Vz)) * 1e-9)
            out.append(np.interp(e, Vz, Z))
        return np.clip(np.array(out), 0, 1)


METHODS = {  # 프로토콜 2절
    "T2_cold": (lambda s: f3.TwoPointCold(s), [0]),
    "B1_reg_lookup": (lambda s: variants.RegLookup(s), [0]),
    "ESC2_voltage_domain": (lambda s: ESC2(s), [0]),
    "B2_reg_lookup_temp": (lambda s: variants.RegLookupTemp(s), [0]),
    "B3_2rc_extrap": (lambda s: variants.RC2Extrap(s), [0]),
    "S_simple": (lambda s: variants.Proposed(s, multi=False, knn=False, aug_shape=False, aug_hw=False), [0, 1, 2, 3, 4]),
}
LABEL = {"T2_cold": "**제안 T2_cold**", "B1_reg_lookup": "B1 25 °C OCV 조회", "ESC2_voltage_domain": "ESC2 전압 영역 온도 OCV",
         "B2_reg_lookup_temp": "B2 B1 + 선형 온도 보정", "B3_2rc_extrap": "B3 2RC 외삽", "S_simple": "S 학습 보정 (보조)"}
PRIMARY = [("H5", "B1_reg_lookup"), ("H6", "ESC2_voltage_domain"), ("H7", "B2_reg_lookup_temp")]


def load_test(dry):
    if dry:
        return f3.load_test(True)
    z = np.load(FINAL, allow_pickle=False)
    m = z["meta"]
    T = {"rest_V": z["rest_V"], **{c: m[c] for c in ["dataset", "cell", "temp_c", "soc", "rest_len", "is_reg", "is_reg2", "raw_n60"]}}
    return T, None


def cluster_boot(u, e, T, draw, clusters):
    """(셀, 온도) 묶음 부트스트랩 MAE. draw는 방법 간 공유(짝지음)."""
    key = np.array([f"{c}|{t}" for c, t in zip(T["cell"][u], T["temp_c"][u])])
    sums = np.array([e[key == c].sum() for c in clusters])
    cnts = np.array([(key == c).sum() for c in clusters])
    return sums[draw].sum(1) / np.maximum(cnts[draw].sum(1), 1)


def holm(pvals):
    order = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    run = 0
    for i, j in enumerate(order):
        run = max(run, (m - i) * pvals[j])
        adj[j] = min(run, 1)
    return adj


def report(res, T, info, path):
    S = {n: f3.per_sample(res[n], T) for n in res}
    u0 = S["T2_cold"][0]
    for n in res:
        assert np.array_equal(S[n][0], u0), f"{n}: 채점 표본이 다름"
    clusters = sorted({f"{c}|{t}" for c, t in zip(T["cell"][u0], T["temp_c"][u0])})
    draw = np.random.default_rng(zlib.crc32(b"final4")).integers(0, len(clusters), (B, len(clusters)))
    bs = {n: cluster_boot(u0, S[n][1], T, draw, clusters) for n in res}
    L = ["# 시험 3 결과 (사전 등록)", "", f"- 실행: {info['time']}  커밋 {info['commit']}  ({info['sec']:.0f} s)",
         "- 프로토콜: analysis/final4_test_protocol.md. 이 표는 1회 실행 출력 그대로다.", "",
         f"## 표 A. 전체 (r = 300 s, n = {len(u0)}, 셀 {len(set(T['cell'][u0].tolist()))}개, (셀×온도) 묶음 {len(clusters)}개)", "",
         "| 방법 | MAE [95 % CI] | 편향 | P95 | 방법 − T2_cold [짝지은 CI] |", "|---|---|---|---|---|"]
    for n in res:
        d = bs[n] - bs["T2_cold"]
        diff = "—" if n == "T2_cold" else f"{S[n][1].mean() - S['T2_cold'][1].mean():+.3f} [{np.percentile(d, 2.5):+.2f}, {np.percentile(d, 97.5):+.2f}]"
        L.append(f"| {LABEL[n]} | {S[n][1].mean():.3f} [{np.percentile(bs[n], 2.5):.2f}, {np.percentile(bs[n], 97.5):.2f}] | "
                 f"{S[n][2].mean():+.2f} | {np.percentile(S[n][1], 95):.2f} | {diff} |")
    pv = []
    for h, n in PRIMARY:
        d = bs[n] - bs["T2_cold"]
        pv.append(min(1.0, max(2 * min((d <= 0).mean(), (d >= 0).mean()), 1 / B)))  # 하한 1/B
    adj = holm(np.array(pv))
    L += ["", "## 가설 판정 (프로토콜 5절: 부트스트랩 양측 p를 Holm 보정, 보정 p < 0.05이고 차이 > 0이면 지지)", ""]
    for (h, n), p, pa in zip(PRIMARY, pv, adj):
        dm = S[n][1].mean() - S["T2_cold"][1].mean()
        L.append(f"- {h} T2_cold < {LABEL[n]}: 차이 {dm:+.3f}, p = {p:.4f}, Holm p = {pa:.4f} → "
                 f"{'**지지**' if (pa < 0.05 and dm > 0) else '**지지 안 됨**'}")
    L += ["", "## 표 B. 휴지 길이 r (전체 MAE)", "", "| 방법 | r = 60 | r = 300 | r = 600 |", "|---|---|---|---|"]
    for n in res:
        L.append(f"| {LABEL[n]} | " + " | ".join(f"{f3.per_sample(res[n], T, r)[1].mean():.3f}" for r in RS) + " |")
    for key, title in [("dataset", "데이터셋별"), ("temp_c", "온도별"), ("cell", "셀별")]:
        L += ["", f"## 표 C. {title} MAE / 편향 (r = 300 s)", "", "| 값 | n | " + " | ".join(LABEL[n] for n in res) + " |",
              "|---|---|" + "---|" * len(res)]
        vals = T[key][u0]
        for v in sorted(set(vals.tolist())):
            k = vals == v
            L.append(f"| {v} | {k.sum()} | " + " | ".join(f"{S[n][1][k].mean():.2f} / {S[n][2][k].mean():+.2f}" for n in res) + " |")
    L += ["", "## 표 D. 하위 집단: 처음 60 s 원시 점 ≥ 30 (S 비교가 공정한 표본)", "", "| 방법 | MAE (n) |", "|---|---|"]
    k = T["raw_n60"][u0] >= 30
    for n in res:
        L.append(f"| {LABEL[n]} | {S[n][1][k].mean():.3f} ({k.sum()}) |" if k.any() else f"| {LABEL[n]} | — (0) |")
    L += ["", "## 표본 수", "", "| 셀 | 채점 (r = 300) | 25 °C 등록 | 저온 등록 | 저온 등록 온도 |", "|---|---|---|---|---|"]
    for c in sorted(set(T["cell"].tolist())):
        kc = T["cell"] == c
        L.append(f"| {c} | {(T['cell'][u0] == c).sum()} | {(kc & T['is_reg']).sum()} | {(kc & T['is_reg2']).sum()} | "
                 f"{', '.join(f'{t:g}' for t in np.unique(T['temp_c'][kc & T['is_reg2']]))} °C |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    outdir = HERE / ("tmp/final4_dry" if a.dry_run else "final4_out")
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
    train = f3.train_dict(train_mask)
    f3.METHODS = METHODS  # f3.run이 이 방법들을 돌린다
    print(f"test n={len(T['soc'])}, train n={len(train['soc'])}", flush=True)
    res = f3.run(T, train)
    info = dict(time=datetime.now().strftime("%Y-%m-%d %H:%M"), commit=commit, sec=time.time() - t0, dry_run=a.dry_run)
    for n, rec in res.items():
        np.savez_compressed(outdir / f"{n}.npz", **rec)
    out_md = (outdir / "final4_results.md") if a.dry_run else (HERE / "final4_results.md")
    report(res, T, info, out_md)
    if not a.dry_run:
        done.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    print("wrote", out_md)


if __name__ == "__main__":
    main()
