"""bench.py 결과(analysis/out/*.npz)로 논문용 표를 만든다 → analysis/results.md

- 주 지표는 run.py와 같은 집계(0.5·범위 안 5폴드 평균 + 0.5·외삽 폴드 평균), r = 300 s.
- 비교는 모두 추정기 시드 {0,1,2} 공통 부분으로 맞춘다(P_full 공식 값 5시드는 따로 적음).
- 95 % CI: 데이터셋 안에서 표본(휴지 1건)을 복원 추출하는 부트스트랩(B = 2000). 한 표본의 범위 안·외삽 오차는 같이 뽑힌다.
  모든 방법에 같은 추출을 써서 차이의 CI는 짝지은(paired) CI다.
  주의: 데이터셋마다 셀이 1개(INR 2개)라 이 CI는 '같은 셀의 다른 휴지'에 대한 불확실성만 반영한다. 셀 간 변동은 폴드별 값으로 본다.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bench import data, ev  # noqa: E402

OUT = HERE / "out"
R = 300
B = 2000
SEEDS = (0, 1, 2)
BASE = ["B0_iso_global", "B1_reg_lookup", "B2_reg_lookup_temp", "B3_2rc_extrap", "B4_xgb_plain"]
ABL = ["A_no_temp", "A_no_multi", "A_no_knn", "A_no_multi_knn", "A_no_residual", "A_no_aug_amp", "A_no_aug_shape",
       "A_no_aug_hw", "A_no_aug_all", "A_no_balance", "S_simple"]
LABEL = {
    "B0_iso_global": "B0 전역 OCV 표(등록·온도 없음, 원래 기준선)",
    "B1_reg_lookup": "B1 등록 OCV 표 조회",
    "B2_reg_lookup_temp": "B2 등록 OCV 표 + 선형 온도 보정",
    "B3_2rc_extrap": "B3 2RC 이완 적합 OCV 외삽 + 등록 표",
    "B4_xgb_plain": "B4 일반 XGB(같은 입력, 증강·잔차 없음)",
    "P_full": "**제안법**",
    "A_no_temp": "− 주변 온도 특징",
    "A_no_multi": "− 시점별 등록 표 특징",
    "A_no_knn": "− 등록 kNN 특징",
    "A_no_multi_knn": "− 시점별 표 + kNN",
    "A_no_residual": "− 잔차 학습(SOC 직접 회귀)",
    "A_no_aug_amp": "− 과전압 진폭 증강",
    "A_no_aug_shape": "− OCV 모양 무작위화",
    "A_no_aug_hw": "− 저가 체인 오차 증강",
    "A_no_aug_all": "− 증강 전부",
    "A_no_balance": "− 균형 가중치",
    "S_simple": "단순화(시점별 표·kNN·모양·체인 증강 모두 뺌)",
}


def load(name, r=R, seeds=SEEDS):
    z = np.load(OUT / f"{name}.npz")
    k = (z["r"] == r) & np.isin(z["es"], seeds)
    key, idx = z["key"][k], z["idx"][k]
    err = np.abs(z["pred"][k] - z["soc"][k]) * 100
    out = {}
    for kk in np.unique(key):
        m = key == kk
        u, inv = np.unique(idx[m], return_inverse=True)
        out[kk] = dict(zip(u.tolist(), (np.bincount(inv, err[m]) / np.bincount(inv)).tolist()))
    return out  # key -> {표본 idx: 시드 평균 절대오차}


def primary(per_key):
    m_in = np.mean([np.mean(list(per_key[f].values())) for f in ev.FOLDS])
    ext = [k for k in per_key if k.startswith("EXT_")]
    m_ext = np.mean([np.mean(list(per_key[k].values())) for k in ext])
    return 0.5 * m_in + 0.5 * m_ext, m_in, m_ext


def boot_weights(keys_idx, meta, rng):
    """데이터셋마다 표본 복원 추출 횟수 (B, n_d)."""
    W = {}
    for d in ev.FOLDS:
        pool = sorted({i for k, ids in keys_idx.items() if k.replace("EXT_", "") == d for i in ids})
        W[d] = (np.array(pool), rng.multinomial(len(pool), np.full(len(pool), 1 / len(pool)), size=B))
    return W


def boot_primary(per_key, W):
    """부트스트랩 B개의 주 지표."""
    def key_means(k):
        d = k.replace("EXT_", "")
        pool, cnt = W[d]
        e = np.array([per_key[k].get(i, np.nan) for i in pool])
        ok = ~np.isnan(e)
        c = cnt[:, ok]
        return (c * e[ok]).sum(1) / np.maximum(c.sum(1), 1)
    m_in = np.mean([key_means(f) for f in ev.FOLDS], 0)
    ext = [k for k in per_key if k.startswith("EXT_")]
    m_ext = np.mean([key_means(k) for k in ext], 0)
    return 0.5 * m_in + 0.5 * m_ext


def ci(x):
    return np.percentile(x, [2.5, 97.5])


def fmt_ci(x):
    lo, hi = ci(x)
    return f"[{lo:.2f}, {hi:.2f}]"


def main():
    have = {p.stem for p in OUT.glob("*.npz")}
    names = [n for n in BASE + ["P_full"] + ABL if n in have]
    per = {n: load(n) for n in names}
    X, meta = data()
    rng = np.random.default_rng(0)
    W = boot_weights({k: list(v) for k, v in per["P_full"].items()}, meta, rng)
    bs = {n: boot_primary(per[n], W) for n in names}
    full = per["P_full"]
    off = json.load(open(OUT / "P_full.json", encoding="utf-8"))["summary"][str(R)]
    L = ["# 기준선·ablation 결과 (dev, 홀드아웃 미사용)", "",
         f"동결 커밋 fdfb160 (estimator = 718da07). r = {R} s. 주 지표 = 0.5·범위 안 5폴드 + 0.5·온도 외삽 폴드 (eval/run.py와 같음).",
         f"제안법 재현 값(추정기 시드 5개, results.tsv 기록은 2.107): **{off['primary']:.3f}** (IN {off['mae_in']:.3f}, EXT {off['mae_ext']:.3f}). "
         "아래 비교는 모두 시드 {0,1,2} 공통.", "",
         "95 % CI = 데이터셋 안 표본 부트스트랩(B = 2000, 짝지음). 데이터셋마다 셀 1개(INR 2개)라 셀 간 변동은 반영 안 됨.", ""]

    def table(rows, title):
        folds = ev.FOLDS
        L.append(f"## {title}")
        L.append("")
        L.append("| 방법 | 주 지표 | 95 % CI | Δ 제안법 대비 | Δ 95 % CI | IN | EXT | " + " | ".join(f.split("_")[0] for f in folds)
                 + " | 제안법이 나은 폴드 |")
        L.append("|---|---|---|---|---|---|---|" + "---|" * len(folds) + "---|")
        p0 = primary(full)[0]
        for n in rows:
            p, mi, me = primary(per[n])
            fm = [np.mean(list(per[n][f].values())) for f in folds]
            keys = [k for k in full]
            better = sum(np.mean(list(full[k].values())) < np.mean(list(per[n][k].values())) for k in keys)
            d = bs[n] - bs["P_full"]
            L.append(f"| {LABEL[n]} | {p:.3f} | {fmt_ci(bs[n])} | "
                     + ("— | — " if n == "P_full" else f"{p - p0:+.3f} | {fmt_ci(d)} ")
                     + f"| {mi:.3f} | {me:.3f} | " + " | ".join(f"{x:.2f}" for x in fm)
                     + ("| — |" if n == "P_full" else f"| {better}/{len(keys)} |"))
        L.append("")

    table([n for n in BASE if n in per] + ["P_full"], "표 1. 기준선 비교")
    table(["P_full"] + [n for n in ABL if n in per], "표 2. Ablation (하나씩 뺌)")

    # r 의존성
    L += ["## 표 3. 휴지 길이 r 의존성 (주 지표, 시드 {0,1,2})", "", "| 방법 | r = 60 s | r = 300 s | r = 600 s |", "|---|---|---|---|"]
    for n in [x for x in BASE + ["P_full"] if x in per]:
        cells = []
        for r in (60, 300, 600):
            try:
                cells.append(f"{primary(load(n, r))[0]:.3f}")
            except (KeyError, ValueError):
                cells.append("—")
        L.append(f"| {LABEL[n]} | " + " | ".join(cells) + " |")
    L.append("")

    # 분해: 범위 안 폴드, 온도·SOC 구간별
    T, S, D = meta["temp_c"], meta["soc"], meta["dataset"]
    show = [n for n in ["B1_reg_lookup", "B2_reg_lookup_temp", "B3_2rc_extrap", "P_full"] if n in per]

    def pooled(n, mask_fn):
        e = [v for f in ev.FOLDS for i, v in per[n][f].items() if mask_fn(i)]
        return (np.mean(e), np.percentile(e, 95), len(e)) if e else (np.nan, np.nan, 0)

    L += ["## 표 4. 온도별 오차 (범위 안 5폴드 표본 합산, MAE / P95)", "",
          "| 온도 | n | " + " | ".join(LABEL[n] for n in show) + " |", "|---|---|" + "---|" * len(show)]
    for t in sorted(set(T.tolist()) - {ev.REF_T}):
        row = [pooled(n, lambda i, t=t: T[i] == t) for n in show]
        L.append(f"| {t:g} °C | {row[0][2]} | " + " | ".join(f"{m:.2f} / {p:.1f}" for m, p, _ in row) + " |")
    L.append("")
    L += ["## 표 5. SOC 구간별 오차 (범위 안 5폴드 표본 합산, MAE / P95)", "",
          "| SOC | n | " + " | ".join(LABEL[n] for n in show) + " |", "|---|---|" + "---|" * len(show)]
    sbin = np.clip(np.floor(S * 5 + 1e-9), 0, 4).astype(int)
    for b in range(5):
        row = [pooled(n, lambda i, b=b: sbin[i] == b) for n in show]
        L.append(f"| {b / 5:.1f}–{(b + 1) / 5:.1f} | {row[0][2]} | " + " | ".join(f"{m:.2f} / {p:.1f}" for m, p, _ in row) + " |")
    L.append("")

    # 편향: 온도별 평균 부호 오차 (제안법)
    z = np.load(OUT / "P_full.npz")
    k = (z["r"] == R) & np.isin(z["es"], SEEDS) & ~np.char.startswith(z["key"].astype(str), "EXT_")
    bias = (z["pred"][k] - z["soc"][k]) * 100
    tt = T[z["idx"][k]]
    L += ["## 표 6. 제안법 온도별 편향 (예측 − 참값, %p, 범위 안)", "", "| 온도 | 평균 편향 |", "|---|---|"]
    for t in sorted(set(tt.tolist())):
        L.append(f"| {t:g} °C | {bias[tt == t].mean():+.2f} |")
    L.append("")
    L += ["## 데이터 규모", "", "| 데이터셋 | 화학계 | 셀 | 채점 표본(범위 안) | 외삽 표본 | 등록 표본 |", "|---|---|---|---|---|---|"]
    REG = ev.reg_mask(meta)
    for f in ev.FOLDS:
        m = D == f
        L.append(f"| {f} | {meta['chem'][m][0]} | {len(np.unique(meta['cell'][m]))} | {len(full[f])} | "
                 f"{len(full.get('EXT_' + f, {}))} | {int((m & REG).sum())} |")
    L.append("")
    (HERE / "results.md").write_text("\n".join(L), encoding="utf-8")
    print("wrote", HERE / "results.md")


if __name__ == "__main__":
    main()
