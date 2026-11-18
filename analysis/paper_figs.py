"""논문 그림 (paper/figs/*.png, 300 dpi). 저장된 예측과 데이터만 읽는다. 모델 학습·실행 없음(B1·T2_cold 표 조회는 재계산)."""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench  # noqa: E402
import two_point as tp  # noqa: E402

ev = bench.ev
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "paper", "figs")
os.makedirs(OUT, exist_ok=True)
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3dd"
R = 300
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "lines.linewidth": 1.6,
                     "legend.frameon": False, "legend.fontsize": 7})
FINAL = "C:/BMS/data/holdout_final/rest_final.npz"
FINAL3 = "C:/BMS/data/holdout_final3/rest_final3.npz"
SHORT = {"LG_HG2": "LG HG2", "Panasonic_PF": "Panasonic PF", "CALCE_INR20R": "CALCE INR20R", "Samsung_30T": "Samsung 30T",
         "Turnigy_GR": "Turnigy GR"}


def pred_mean(path, n, r=R, keyfilter=None):
    z = np.load(path)
    k = z["r"] == r
    if keyfilter is not None:
        k &= keyfilter(z)
    if "es" in z:
        pass
    acc, cnt = np.zeros(n), np.zeros(n)
    np.add.at(acc, z["idx"][k], z["pred"][k])
    np.add.at(cnt, z["idx"][k], 1)
    with np.errstate(invalid="ignore"):
        return acc / cnt


def bias_curves():
    """셀(데이터셋)별 B1 편향(%p) vs 온도."""
    X, meta = bench.data()
    p = pred_mean(os.path.join(HERE, "out", "B1_reg_lookup.npz"), len(meta),
                  keyfilter=lambda z: ~np.char.startswith(z["key"].astype(str), "EXT_"))
    dev = {}
    for d in ev.FOLDS:
        k = (meta["dataset"] == d) & np.isfinite(p)
        T = meta["temp_c"][k]
        dev[SHORT[d]] = {t: (p[k][T == t] - meta["soc"][k][T == t]).mean() * 100 for t in np.unique(T) if (T == t).sum() >= 5}
    z = np.load(FINAL, allow_pickle=False)
    m = z["meta"]
    p = pred_mean(os.path.join(HERE, "final_out", "nominal_B1_reg_lookup.npz"), len(m))
    fin = {}
    for d, lab in [("LG_E66", "LG E66"), ("Molicel_P42A", "Molicel P42A (12 cells)")]:
        k = (m["dataset"] == d) & np.isfinite(p)
        T = m["temp_c"][k]
        fin[lab] = {t: (p[k][T == t] - m["soc"][k][T == t]).mean() * 100 for t in np.unique(T)}
    z3 = np.load(FINAL3, allow_pickle=False)
    m3 = z3["meta"]
    p = pred_mean(os.path.join(HERE, "final3_out", "B1_reg_lookup.npz"), len(m3))
    pl = {}
    for c in sorted(set(m3["cell"].tolist())):
        k = (m3["cell"] == c) & np.isfinite(p)
        T = m3["temp_c"][k]
        pl[c] = {t: (p[k][T == t] - m3["soc"][k][T == t]).mean() * 100 for t in np.unique(T)}
    return dev, fin, pl


def fig_bias():
    dev, fin, pl = bias_curves()
    fig, axs = plt.subplots(1, 3, figsize=(7.16, 2.5), sharey=True)
    for ax, (title, D) in zip(axs, [("(a) Development cells", dev), ("(b) Test 1: E66, P42A", fin), ("(c) Test 2: Plett ESC", pl)]):
        for i, (lab, dd) in enumerate(D.items()):
            ts = sorted(dd)
            ax.plot(ts, [dd[t] for t in ts], "-o", color=CAT[i], ms=3.5, label=lab, mec="white", mew=0.6)
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.axvline(25, color=GRID, lw=3, zorder=0)
        ax.set_title(title, fontsize=8, color=INK, loc="left")
        ax.set_xlabel("Temperature (°C)")
        ax.legend(loc="lower right", handlelength=1.2)
    axs[0].set_ylabel("Bias of 25 °C lookup (B1), pp")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_bias_vs_temp.png"), dpi=300)
    plt.close(fig)


def e66_methods():
    z = np.load(FINAL, allow_pickle=False)
    m, V = z["meta"], z["rest_V"]
    e66 = m["dataset"] == "LG_E66"
    r25 = e66 & m["is_reg"]
    lo = e66 & (m["temp_c"] == 0) & np.char.endswith(m["file"].astype(str), "_GITT.mat")
    sel = e66 & ~m["is_reg"] & (m["temp_c"] != 25) & (m["rest_len"] >= R)
    idx = np.flatnonzero(sel)
    errs = []
    for s in ev.SEEDS:
        v = ev.corrupt(V[sel], R, 1000 * s + R)
        tc = m["temp_c"][sel].astype(float) + np.random.default_rng(5000 + 1000 * s + R).normal(0, ev.TEMP_SD, sel.sum())
        errs.append(tp.t2(tp.lookup({"rest_V": V}, m, r25, R, v), tp.lookup({"rest_V": V}, m, lo, R, v), tc, "cold") - m["soc"][sel])
    E = {"T2_cold": np.abs(np.mean(errs, 0)) * 100}
    for k, f in [("B1", "B1_reg_lookup"), ("B2", "B2_reg_lookup_temp"), ("S_simple", "S_simple")]:
        p = pred_mean(os.path.join(HERE, "final_out", f"nominal_{f}.npz"), len(m))
        E[k] = np.abs(p[idx] - m["soc"][idx]) * 100
    keep = m["temp_c"][idx] != 0
    return {k: v[keep] for k, v in E.items()}, m["temp_c"][idx][keep]


def plett_methods():
    z = np.load(FINAL3, allow_pickle=False)
    m = z["meta"]
    E = {}
    for k, f in [("B1", "B1_reg_lookup"), ("B2", "B2_reg_lookup_temp"), ("S_simple", "S_simple"), ("T2_cold", "T2_cold")]:
        p = pred_mean(os.path.join(HERE, "final3_out", f"{f}.npz"), len(m))
        E[k] = p
    idx = np.flatnonzero(np.isfinite(E["T2_cold"]))
    return {k: np.abs(v[idx] - m["soc"][idx]) * 100 for k, v in E.items()}, m["temp_c"][idx]


def fig_methods():
    import esc_compare  # noqa: F401  (multi_reg.evaluate를 ESC2 포함 버전으로 바꾼다)
    import multi_reg as mr
    fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.6), sharey=False)
    lab = {"B1": "B1: 25 °C lookup", "B2": "B2: B1 + linear temp. corr.", "S_simple": "Learned residual (S)",
           "ESC2": "ESC2: voltage-domain OCV(z,T)", "T2_cold": "RM2P (proposed)"}
    col = {"B1": CAT[1], "B2": CAT[3], "S_simple": CAT[0], "ESC2": CAT[6], "T2_cold": CAT[2]}
    for ax, (title, (E, T), run) in zip(axs, [("(a) LG E66, post hoc (0 °C excluded)", e66_methods(), mr.run_e66),
                                               ("(b) Plett ESC, preregistered Test 2 (ESC2 post hoc)", plett_methods(), mr.run_plett)]):
        Ee, Te = run(R)
        ts = np.unique(T)
        for k in ["B1", "B2", "S_simple", "ESC2", "T2_cold"]:
            if k == "ESC2":
                y = [np.abs(Ee["ESC2"][Te == t]).mean() for t in ts]
            else:
                y = [E[k][T == t].mean() for t in ts]
            ax.plot(ts, y, "-o", color=col[k], ms=3.5, label=lab[k], mec="white", mew=0.6, lw=2.2 if k == "T2_cold" else 1.4)
        ax.set_title(title, fontsize=8, color=INK, loc="left")
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("MAE, pp (r = 300 s)")
        ax.set_ylim(bottom=0)
    axs[1].legend(loc="upper right", handlelength=1.2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_mae_vs_temp.png"), dpi=300)
    plt.close(fig)


def fig_rest():
    z = np.load(FINAL3, allow_pickle=False)
    m, V = z["meta"], z["rest_V"]
    c = "E2"
    ramp = ["#104281", "#256abf", "#5598e7", "#86b6ef", "#e8a07a", "#d95926", "#a33a12", "#6b2408"]
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    temps = sorted(set(m["temp_c"][m["cell"] == c].tolist()))
    for i, t in enumerate(temps):
        k = np.flatnonzero((m["cell"] == c) & (m["temp_c"] == t) & (m["rest_len"] >= 600))
        if not len(k):
            continue
        j = k[np.argmin(np.abs(m["soc"][k] - 0.5))]
        ax.plot(np.arange(600), V[j, :600], color=ramp[i], lw=1.4, label=f"{t:g} °C (SOC {m['soc'][j]:.2f})")
    ax.axvline(300, color=MUTED, lw=0.8, ls="--")
    ax.set_xlabel("Time since rest start (s)")
    ax.set_ylabel("Cell voltage (V)")
    ax.set_title("Plett ESC cell E2, rests near SOC 0.5", fontsize=8, color=INK, loc="left")
    ax.legend(fontsize=6, loc="lower right", ncol=2, handlelength=1.0)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_rest_curves.png"), dpi=300)
    plt.close(fig)


def fig_design():
    fig, ax = plt.subplots(figsize=(7.16, 1.7))
    ax.axis("off")
    boxes = [("Development\n5 datasets, 6 cells\nLODO + temp. CV", CAT[0]),
             ("Test 1 (prereg.)\nLG E66 + Molicel P42A\n13 cells, 1 run", CAT[1]),
             ("Diagnosis\ncell-specific low-T\nrest-voltage drop", CAT[3]),
             ("Two-point lookup\nfixed on dev\n(E66 post hoc)", CAT[2]),
             ("Test 2 (prereg.)\nPlett ESC\n6 cells, 1 run", CAT[6])]
    w, gap = 0.165, 0.035
    for i, (txt, cc) in enumerate(boxes):
        x = i * (w + gap) + 0.01
        ax.add_patch(matplotlib.patches.FancyBboxPatch((x, 0.15), w, 0.7, boxstyle="round,pad=0.01,rounding_size=0.02",
                                                       fc="white", ec=cc, lw=1.6, transform=ax.transAxes))
        ax.text(x + w / 2, 0.5, txt, ha="center", va="center", fontsize=6, color=INK, transform=ax.transAxes)
        if i < len(boxes) - 1:
            ax.annotate("", xy=(x + w + gap - 0.004, 0.5), xytext=(x + w + 0.004, 0.5), xycoords="axes fraction",
                        arrowprops=dict(arrowstyle="->", color=MUTED, lw=1))
    fig.savefig(os.path.join(OUT, "fig_design.png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_design()
    fig_bias()
    fig_methods()
    fig_rest()
    print("figs ->", os.path.abspath(OUT))
