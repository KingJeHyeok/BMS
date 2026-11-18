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


class ESC2Cold(ESC2):
    """ESC2 + RM2P와 같은 따뜻한 쪽 규칙(a = max(a, 0)). 보조(분해용)."""

    def predict(self, test):
        t = dict(test)
        t["temp_c"] = np.minimum(test["temp_c"], 25.0)
        return super().predict(t)


class ESC2Inv:
    """RM2P와 같은 표(전압 → SOC 단조 회귀)를 뒤집어 전압 영역에서 내삽, 따뜻한 쪽 규칙도 같음. 보조(내삽 영역만 다름)."""
    VG = np.linspace(2.0, 4.5, 2501)

    def __init__(self, seed=0, **_):
        pass

    def fit(self, train):
        return self

    def _vz(self, ref, r):
        k = ref["rest_len"] >= r
        end = variants.feats(ref["rest_V"][k, :r])[:, 0]
        g = IsotonicRegression(out_of_bounds="clip").fit(end, ref["soc"][k]).predict(self.VG) + np.arange(len(self.VG)) * 1e-9
        return np.interp(Z, g, self.VG)

    def predict(self, test):
        v = test["rest_V"]
        r = v.shape[1]
        V25, Vlo = self._vz(test["ref"], r), self._vz(test["ref2"], r)
        a = np.maximum((test["temp_c"] - 25) / (test["t_low"] - 25), 0)
        end = variants.feats(v)[:, 0]
        out = []
        for ai, e in zip(a, end):
            Vz = np.maximum.accumulate(V25 + ai * (Vlo - V25) + np.arange(len(Z)) * 1e-9)
            out.append(np.interp(e, Vz, Z))
        return np.clip(np.array(out), 0, 1)


class ESCEq2:
    """기존 방법(평형 OCV): 셀의 25 °C·T_low 저속 방전(C/20) 의사 OCV 곡선 V_T(z)로 OCV(z,T)를 만들고(양쪽 선형),
    휴지 끝 전압을 역변환. 등록 휴지 표는 쓰지 않는다. 곡선이 없는 셀은 NaN."""

    def __init__(self, seed=0, **_):
        pass

    def fit(self, train):
        return self

    def predict(self, test):
        if test.get("ocv25") is None or test.get("ocvlo") is None:
            return np.full(len(test["rest_V"]), np.nan)
        V25, Vlo = test["ocv25"], test["ocvlo"]
        a = (test["temp_c"] - 25) / (test["t_low"] - 25)
        end = variants.feats(test["rest_V"])[:, 0]
        out = []
        for ai, e in zip(a, end):
            Vz = np.maximum.accumulate(V25 + ai * (Vlo - V25) + np.arange(len(Z)) * 1e-9)
            out.append(np.interp(e, Vz, Z))
        return np.clip(np.array(out), 0, 1)


class RM2PType:
    """보조(유형 등록): 같은 데이터셋의 다른 셀 등록 표로 RM2P. 다른 셀이 여럿이면 예측 평균. 다른 셀이 없으면 NaN."""

    def __init__(self, seed=0, **_):
        pass

    def fit(self, train):
        return self

    def predict(self, test):
        others = test.get("others") or []
        if not others:
            return np.full(len(test["rest_V"]), np.nan)
        ps = [f3.TwoPointCold().predict({**test, "ref": a, "ref2": b}) for a, b in others]
        return np.mean(ps, 0)


METHODS = {  # 프로토콜 2절 (11-18 수정 1: 리뷰 1차 반영, 시험 데이터로 아무것도 돌리기 전)
    "T2_cold": (lambda s: f3.TwoPointCold(s), [0]),
    "B1_reg_lookup": (lambda s: variants.RegLookup(s), [0]),
    "ESC2_voltage_domain": (lambda s: ESC2(s), [0]),
    "B2_reg_lookup_temp": (lambda s: variants.RegLookupTemp(s), [0]),
    "ESC_eq2_c20": (lambda s: ESCEq2(s), [0]),
    "ESC2_cold": (lambda s: ESC2Cold(s), [0]),
    "ESC2_inv": (lambda s: ESC2Inv(s), [0]),
    "RM2P_type": (lambda s: RM2PType(s), [0]),
    "B3_2rc_extrap": (lambda s: variants.RC2Extrap(s), [0]),
    "S_simple": (lambda s: variants.Proposed(s, multi=False, knn=False, aug_shape=False, aug_hw=False), [0, 1, 2, 3, 4]),
}
LABEL = {"T2_cold": "**제안 RM2P (T2_cold)**", "B1_reg_lookup": "B1 25 °C 조회", "ESC2_voltage_domain": "ESC2 전압 영역(휴지 표)",
         "B2_reg_lookup_temp": "B2 B1 + 선형 온도 보정", "ESC_eq2_c20": "ESC_eq2 평형 OCV(C/20)", "ESC2_cold": "ESC2_cold (보조)",
         "ESC2_inv": "ESC2_inv (보조)", "RM2P_type": "RM2P 유형 등록 (보조)", "B3_2rc_extrap": "B3 2RC 외삽 (보조)",
         "S_simple": "S 학습 보정 (보조)"}
PRIMARY = [("H5", "B1_reg_lookup"), ("H6", "ESC2_voltage_domain"), ("H7", "B2_reg_lookup_temp"), ("H8", "ESC_eq2_c20")]
OCV = Path("C:/BMS/data/holdout_final4/ocv_c20.npz")


def load_test(dry):
    if dry:
        return f3.load_test(True)
    z = np.load(FINAL, allow_pickle=False)
    m = z["meta"]
    T = {"rest_V": z["rest_V"], **{c: m[c] for c in ["dataset", "cell", "temp_c", "soc", "rest_len", "is_reg", "is_reg2", "raw_n60",
                                                     "ttype"]}}
    T["ocv"] = {}
    if OCV.exists():
        o = np.load(OCV, allow_pickle=False)
        for c, t, vz in zip(o["cell"], o["temp_c"], o["V"]):
            T["ocv"][(str(c), float(t))] = np.interp(Z, o["soc_grid"], vz)
    return T, None


def cluster_boot(u, e, T, draw=None, clusters=None):
    """(셀, 온도) 묶음 부트스트랩 MAE (B,). 묶음은 이 표본(u)에 있는 것만 쓴다.
    추출은 묶음 목록으로 정해지므로(시드 = crc32("final4|" + 묶음 목록)), 같은 표본을 쓰는 방법끼리는 같은 추출로 짝지어진다."""
    key = np.array([f"{c}|{t}" for c, t in zip(T["cell"][u], T["temp_c"][u])])
    cl = sorted(set(key.tolist()))
    dr = np.random.default_rng(zlib.crc32(("final4|" + ",".join(cl)).encode())).integers(0, len(cl), (B, len(cl)))
    sums = np.array([e[key == c].sum() for c in cl])
    cnts = np.array([(key == c).sum() for c in cl])
    return sums[dr].sum(1) / np.maximum(cnts[dr].sum(1), 1)


def holm(pvals):
    order = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    run = 0
    for i, j in enumerate(order):
        run = max(run, (m - i) * pvals[j])
        adj[j] = min(run, 1)
    return adj


def run(T, train):
    """f3.run과 같은 표본·잡음 규칙. 추가 입력: 평형 OCV 곡선(ocv25/ocvlo), 같은 데이터셋 다른 셀의 등록 표(others)."""
    out = {}
    cells = sorted({(d, c) for d, c in zip(T["dataset"], T["cell"])})
    regs = {}
    for d, c in cells:
        kc = (T["dataset"] == d) & (T["cell"] == c)
        rk, rk2 = kc & T["is_reg"], kc & T["is_reg2"]

        def mk(m):
            return {"rest_V": T["rest_V"][m], "soc": T["soc"][m], "rest_len": T["rest_len"][m]}

        tl = float(np.unique(T["temp_c"][rk2])[0]) if rk2.any() else np.nan
        regs[(d, c)] = (mk(rk), mk(rk2), int(rk.sum()), int(rk2.sum()), tl)
    for name, (factory, seeds) in METHODS.items():
        rec = {k: [] for k in ["idx", "r", "es", "s", "pred"]}
        for es in seeds:
            model = factory(es).fit(train)
            for d, c in cells:
                ref, ref2, n1, n2, t_low = regs[(d, c)]
                if n1 < 3 or n2 < 3:
                    print(f"  {d}/{c}: 등록 표본 부족 ({n1}, {n2}) → 제외")
                    continue
                others = [(regs[k][0], regs[k][1]) for k in cells
                          if k[0] == d and k != (d, c) and regs[k][2] >= 3 and regs[k][3] >= 3]
                ocv = T.get("ocv", {})
                kc = (T["dataset"] == d) & (T["cell"] == c)
                for r in RS:
                    sel = (kc & ~T["is_reg"] & ~T["is_reg2"] & (T["temp_c"] != ev.REF_T) & (T["temp_c"] != t_low)
                           & (T["rest_len"] >= r))
                    if not sel.any():
                        continue
                    for s in ev.SEEDS:
                        v = ev.corrupt(T["rest_V"][sel], r, 1000 * s + r)
                        tc = T["temp_c"][sel].astype(float) + np.random.default_rng(5000 + 1000 * s + r).normal(0, ev.TEMP_SD, sel.sum())
                        test = {"rest_V": v, "ref": ref, "ref2": ref2, "t_low": t_low, "temp_c": tc, "others": others,
                                "ocv25": ocv.get((str(c), 25.0)), "ocvlo": ocv.get((str(c), t_low))}
                        p = np.clip(np.asarray(model.predict(test), float), 0, 1)
                        rec["idx"].append(np.flatnonzero(sel))
                        rec["r"] += [r] * int(sel.sum())
                        rec["es"] += [es] * int(sel.sum())
                        rec["s"] += [s] * int(sel.sum())
                        rec["pred"].append(p)
        out[name] = {k: (np.concatenate(v) if isinstance(v[0], np.ndarray) else np.array(v)) for k, v in rec.items()}
        print(f"  {name} done ({time.strftime('%H:%M:%S')})", flush=True)
    return out


def report(res, T, info, path):
    S = {n: f3.per_sample(res[n], T) for n in res}
    u0 = S["T2_cold"][0]
    for n in res:
        assert np.array_equal(S[n][0], u0), f"{n}: 채점 표본이 다름"
    clusters = sorted({f"{c}|{t}" for c, t in zip(T["cell"][u0], T["temp_c"][u0])})
    draw = np.random.default_rng(zlib.crc32(b"final4")).integers(0, len(clusters), (B, len(clusters)))
    ok = {n: np.isfinite(S[n][1]) for n in res}
    t_low = float(np.min(T["temp_c"][T["is_reg2"]])) if T["is_reg2"].any() else 0.0

    def cmp(n, g):
        """방법 n과 RM2P를, n이 정의된 표본(g ∩ ok[n])에서 짝지어 비교."""
        k = g & ok[n]
        d = cluster_boot(u0[k], S[n][1][k], T, draw, clusters) - cluster_boot(u0[k], S["T2_cold"][1][k], T, draw, clusters)
        return k, S[n][1][k].mean() - S["T2_cold"][1][k].mean(), np.percentile(d, [2.5, 97.5]), d

    L = ["# 시험 3 결과 (사전 등록)", "", f"- 실행: {info['time']}  커밋 {info['commit']}  ({info['sec']:.0f} s)",
         "- 프로토콜: analysis/final4_test_protocol.md (수정 1 포함). 이 표는 1회 실행 출력 그대로다.", ""]
    T_ = T["temp_c"][u0]
    subsets = [("전체", np.ones(len(u0), bool)), (f"T < {t_low:g} °C (추운 쪽 외삽)", T_ < t_low),
               (f"{t_low:g} < T < 25 °C (내삽)", (T_ > t_low) & (T_ < 25)), ("T > 25 °C", T_ > 25), ("T < 25 °C", T_ < 25)]
    for gname, g in subsets:
        if not g.any():
            continue
        L += [f"## 표 A. {gname} (r = 300 s, n = {g.sum()})", "",
              "| 방법 | n | MAE [95 % CI] | 편향 | 방법 − RM2P [짝지은 CI] |", "|---|---|---|---|---|"]
        for n in res:
            k = g & ok[n]
            if not k.any():
                L.append(f"| {LABEL[n]} | 0 | — | — | — |")
                continue
            b = cluster_boot(u0[k], S[n][1][k], T, draw, clusters)
            if n == "T2_cold":
                diff = "—"
            else:
                _, dm, ci, _ = cmp(n, g)
                diff = f"{dm:+.3f} [{ci[0]:+.2f}, {ci[1]:+.2f}]"
            L.append(f"| {LABEL[n]} | {k.sum()} | {S[n][1][k].mean():.3f} [{np.percentile(b, 2.5):.2f}, {np.percentile(b, 97.5):.2f}] | "
                     f"{S[n][2][k].mean():+.2f} | {diff} |")
        L.append("")
    pv, rows = [], []
    for h, n in PRIMARY:
        k, dm, ci, d = cmp(n, np.ones(len(u0), bool))
        p = min(1.0, max(2 * min((d <= 0).mean(), (d >= 0).mean()), 1 / B))
        pv.append(p)
        rows.append((h, n, k.sum(), dm, ci, p))
    adj = holm(np.array(pv))
    L += ["## 가설 판정 (프로토콜 5절: 묶음 부트스트랩 양측 p를 Holm 보정; 보정 p < 0.05이고 차이 > 0이면 지지)", ""]
    for (h, n, nn, dm, ci, p), pa in zip(rows, adj):
        if nn == 0:
            L.append(f"- {h} RM2P < {LABEL[n]}: 비교할 표본 없음 → **판정 불가**")
            continue
        L.append(f"- {h} RM2P < {LABEL[n]} (n = {nn}): 차이 {dm:+.3f} [{ci[0]:+.2f}, {ci[1]:+.2f}], p = {p:.4f}, Holm p = {pa:.4f} → "
                 f"{'**지지**' if (pa < 0.05 and dm > 0) else '**지지 안 됨**'}")
    L += ["", "## 표 B. 휴지 길이 r (전체 MAE, 방법이 정의된 표본)", "", "| 방법 | r = 60 | r = 300 | r = 600 |", "|---|---|---|---|"]
    for n in res:
        L.append(f"| {LABEL[n]} | " + " | ".join(f"{np.nanmean(f3.per_sample(res[n], T, r)[1]):.3f}" for r in RS) + " |")
    for key, title in [("dataset", "데이터셋(셀 유형)별"), ("temp_c", "온도별"), ("cell", "셀별"), ("ttype", "시험 종류별")]:
        if key not in T:
            continue
        L += ["", f"## 표 C. {title} MAE / 편향 (r = 300 s)", "", "| 값 | n | " + " | ".join(LABEL[n] for n in res) + " |",
              "|---|---|" + "---|" * len(res)]
        vals = T[key][u0]
        for v in sorted(set(vals.tolist())):
            k = vals == v
            L.append(f"| {v} | {k.sum()} | " + " | ".join(
                (f"{np.nanmean(S[n][1][k]):.2f} / {np.nanmean(S[n][2][k]):+.2f}" if np.isfinite(S[n][1][k]).any() else "—")
                for n in res) + " |")
    L += ["", "## 표 E. 셀별 짝지은 차이 (방법 − RM2P, r = 300 s): 부호 일치 확인", "",
          "| 셀 | " + " | ".join(LABEL[n] for _, n in PRIMARY) + " |", "|---|" + "---|" * len(PRIMARY)]
    for c in sorted(set(T["cell"][u0].tolist())):
        k = T["cell"][u0] == c
        L.append(f"| {c} | " + " | ".join(
            (f"{S[n][1][k & ok[n]].mean() - S['T2_cold'][1][k & ok[n]].mean():+.2f}" if (k & ok[n]).any() else "—")
            for _, n in PRIMARY) + " |")
    L += ["", "## 표 D. 하위 집단: 처음 60 s 원시 점 ≥ 30 (S·B3 비교가 공정한 표본)", "", "| 방법 | MAE (n) |", "|---|---|"]
    k = T["raw_n60"][u0] >= 30
    for n in res:
        kk = k & ok[n]
        L.append(f"| {LABEL[n]} | {S[n][1][kk].mean():.3f} ({kk.sum()}) |" if kk.any() else f"| {LABEL[n]} | — (0) |")
    L += ["", "## 표본 수", "", "| 셀 | 채점 (r = 300) | 25 °C 등록 | 저온 등록 | 저온 등록 온도 | 평형 OCV 곡선 (25 °C / 저온) |",
          "|---|---|---|---|---|---|"]
    oc = T.get("ocv", {})
    for c in sorted(set(T["cell"].tolist())):
        kc = T["cell"] == c
        tl = np.unique(T["temp_c"][kc & T["is_reg2"]])
        lo = "O" if len(tl) and (str(c), float(tl[0])) in oc else "X"
        L.append(f"| {c} | {(T['cell'][u0] == c).sum()} | {(kc & T['is_reg']).sum()} | {(kc & T['is_reg2']).sum()} | "
                 f"{', '.join(f'{t:g}' for t in tl)} °C | {'O' if (str(c), 25.0) in oc else 'X'} / {lo} |")
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
    print(f"test n={len(T['soc'])}, train n={len(train['soc'])}", flush=True)
    res = run(T, train)
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
