"""Generate the final (print) figures. Full-page spec only, SVG + 1200-DPI PNG.

Every number comes from results/csv/master_matrix.csv, except a few figures that need data
the matrix does not carry (flagged with SOURCE comments): positional chi2
(chisquare_positional_reanalysis.csv) and the ML group breakdown
(ml_group_reanalysis.csv). Style/colours/labels come from scripts.report.style.

Run (from the repo root):
    python -m scripts.report.make_final_figures
    python -m scripts.report.make_final_figures --only ml_pe_vs_rate
"""
import argparse
import csv
import os
from collections import defaultdict

import matplotlib.pyplot as plt

from scripts.report import style

RES = "results/csv"
RATES = [0.05, 0.1, 0.25, 0.5, 1.0]
ALLV = style.ORDER
OURS = style.OURS
REFS = ["lsbr", "lsbm", "hill"]


def _matrix():
    d = defaultdict(list)
    with open(os.path.join(RES, "master_matrix.csv"), newline="") as f:
        for r in csv.DictReader(f):
            d[(r["attack"], r["metric"], r["version"])].append((float(r["rate"]), float(r["value"])))
    return {k: sorted(v) for k, v in d.items()}


def _csv(name):
    p = os.path.join(RES, name)
    return list(csv.DictReader(open(p, newline=""))) if os.path.exists(p) else []


# ---- generic line-vs-rate --------------------------------------------------------
def line_vs_rate(mat, attack, metric, title, ylabel, versions, ylim=None, chance=None):
    p = style.apply_style("full")
    fig, ax = plt.subplots(figsize=p["figsize"])
    for v in versions:
        pts = mat.get((attack, metric, v))
        if pts:
            xs, ys = zip(*pts)
            style.plot_version(ax, v, xs, ys, p)
    if chance is not None:
        ax.axhline(chance, color="lightgray", ls=":", lw=1)
    ax.set_xlabel(style.AXIS["rate"]); ax.set_ylabel(ylabel); ax.set_title(title)
    if ylim:
        ax.set_ylim(*ylim)
    style.rate_ticks(ax)
    style.legend_in_order(ax, ncol=1, loc="best")
    return fig


# ---- specials --------------------------------------------------------------------
def positional(mat):  # SOURCE: chisquare_positional_reanalysis.csv (not in matrix)
    p = style.apply_style("full")
    rows = [r for r in _csv("chisquare_positional_reanalysis.csv") if r["rate"] == "0.5"]
    agg = defaultdict(lambda: defaultdict(list))
    for r in rows:
        agg[r["config"]][float(r["position"])].append(float(r["p_embed"]))
    fig, ax = plt.subplots(figsize=p["figsize"])
    for v in ("baseline", "p1", "all"):
        if v not in agg:
            continue
        xs = sorted(agg[v])
        ys = [sum(agg[v][x]) / len(agg[v][x]) for x in xs]
        col, marker, ls = style.STYLE[v]
        ax.plot(xs, ys, color=col, ls=ls, label=style.DISPLAY[v], lw=p["lw"])
    ax.axvline(0.5, color="gray", ls=":", lw=0.8)
    ax.set_xlabel("položaj (udio slike)"); ax.set_ylabel("χ² p-vrijednost")
    ax.set_title("Pozicijski χ² profil (stopa 0.5)")
    style.legend_in_order(ax, ncol=1, loc="best")
    return fig


def rs_estimate(mat):  # RS estimated rate vs actual (our configs); identity line
    p = style.apply_style("full")
    fig, ax = plt.subplots(figsize=p["figsize"])
    for v in OURS:
        pts = mat.get(("rs", "phat", v))
        if pts:
            xs, ys = zip(*pts)
            style.plot_version(ax, v, xs, ys, p)
    ax.plot([0, 1], [0, 1], color="gray", ls=":", lw=1, label="prava stopa")
    ax.set_xlabel(style.AXIS["rate"]); ax.set_ylabel(style.AXIS["phat"])
    ax.set_title("RS: procijenjena stopa (naše verzije)")
    style.rate_ticks(ax)
    style.legend_in_order(ax, ncol=1, loc="best")
    return fig


def group_single(version, title):  # SOURCE: ml_group_reanalysis.csv
    """One version's SCRM feature groups (all / spatial / color) -- coloured by group."""
    p = style.apply_style("full")
    rows = _csv("ml_group_reanalysis.csv")
    fig, ax = plt.subplots(figsize=p["figsize"])
    groups = {"all": ("black", "sve značajke"), "spatial": ("tab:blue", "prostorne"),
              "color": ("tab:red", "color")}
    for grp, (gcol, gname) in groups.items():
        pts = sorted((float(r["rate"]), float(r["pe_mean"])) for r in rows
                     if r["config"] == version and r["group"] == grp)
        if pts:
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=gcol, ls="-", marker="o",
                    markersize=p["ms"], lw=p["lw"], label=gname)
    ax.set_xlabel(style.AXIS["rate"]); ax.set_ylabel(style.AXIS["pe"]); ax.set_title(title)
    style.rate_ticks(ax)
    ax.legend(loc="best")
    return fig


def group_beforeafter():  # SOURCE: ml_group_reanalysis.csv ; 2 panels spatial|color
    p = style.apply_style("full")
    rows = _csv("ml_group_reanalysis.csv")
    fig, (axs, axc) = plt.subplots(1, 2, figsize=(9.5, 4.2), sharey=True)
    for ax, grp in ((axs, "spatial"), (axc, "color")):
        for v in OURS:
            pts = sorted((float(r["rate"]), float(r["pe_mean"])) for r in rows
                         if r["config"] == v and r["group"] == grp)
            if pts:
                xs, ys = zip(*pts)
                style.plot_version(ax, v, xs, ys, p)
        ax.set_title(f"{grp}"); ax.set_xlabel(style.AXIS["rate"]); style.rate_ticks(ax)
    axs.set_ylabel(style.AXIS["pe"])
    style.side_legend(fig, axc)
    fig.suptitle("ML značajke: prostorne i color, prije i poslije")
    return fig


def reference_attacks(mat):  # 3 panels chi2/RS/SPA AUC, reference methods
    p = style.apply_style("full")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
    for ax, (atk, nm) in zip(axes, (("chi2", "χ²"), ("rs", "RS"), ("spa", "SPA"))):
        for v in REFS:
            pts = mat.get((atk, "auc", v))
            if pts:
                xs, ys = zip(*pts)
                style.plot_version(ax, v, xs, ys, p)
        ax.axhline(0.5, color="lightgray", ls=":", lw=1)
        ax.set_title(nm); ax.set_xlabel(style.AXIS["rate"]); style.rate_ticks(ax)
        ax.set_ylim(0.4, 1.02)
    axes[0].set_ylabel(style.AXIS["auc"])
    style.side_legend(fig, axes[-1])
    fig.suptitle("Napadi na referentne metode (LSB-R = pozitivna kontrola)")
    return fig


def central_multi(mat):  # 5 panels, P_E vs rate, all versions
    p = style.apply_style("full")
    fig, axes = plt.subplots(1, 5, figsize=(20, 4.4), sharey=True)
    for ax, (atk, nm) in zip(axes, (("chi2", "χ²"), ("rs", "RS"), ("spa", "SPA"),
                                    ("stegexpose", "StegExpose"), ("ml", "ML"))):
        for v in ALLV:
            pts = mat.get((atk, "pe", v))
            if pts:
                xs, ys = zip(*pts)
                style.plot_version(ax, v, xs, ys, p)
        ax.axhline(0.5, color="lightgray", ls=":", lw=1)
        ax.set_title(nm); ax.set_xlabel(style.AXIS["rate"])
        style.rate_ticks(ax); ax.set_ylim(0, 0.55)
    axes[0].set_ylabel(style.AXIS["pe"])
    style.side_legend(fig, axes[-1])
    fig.suptitle("Usporedba svih metoda i napada: P_E po stopi ugradnje")
    return fig


def central_single(mat):  # single panel, r=1.0 profile: attacks x versions
    p = style.apply_style("full")
    attacks = [("chi2", "χ²"), ("rs", "RS"), ("spa", "SPA"),
               ("stegexpose", "StegExpose"), ("ml", "ML")]
    fig, ax = plt.subplots(figsize=(8.0, 4.5))
    n = len(ALLV)
    for j, v in enumerate(ALLV):
        col, marker, _ = style.STYLE[v]
        xs, ys = [], []
        for i, (atk, _) in enumerate(attacks):
            pts = dict(mat.get((atk, "pe", v), []))
            if 1.0 in pts:
                xs.append(i + (j - n / 2) * 0.06)
                ys.append(pts[1.0])
        ax.scatter(xs, ys, color=col, marker=marker, s=p["ms"] ** 2 * 3,
                   label=style.DISPLAY[v], edgecolors="none", zorder=3)
    ax.axhline(0.5, color="lightgray", ls=":", lw=1)
    ax.set_xticks(range(len(attacks)))
    ax.set_xticklabels([nm for _, nm in attacks])
    ax.set_ylabel(style.AXIS["pe"]); ax.set_ylim(0, 0.55)
    ax.set_title("Profil pri punoj ugradnji (stopa 1.0)")
    style.legend_in_order(ax, ncol=1, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    return fig


def build_all(mat):
    return {
        "psnr_vs_rate": lambda: line_vs_rate(mat, "imperceptibility", "psnr_global",
            "PSNR (globalni) po stopi", style.AXIS["psnr"], ALLV),
        "psnr_beforeafter": lambda: line_vs_rate(mat, "imperceptibility", "psnr_region",
            "PSNR (regija): prije i poslije", style.AXIS["psnr"], OURS),
        "ssim_beforeafter": lambda: line_vs_rate(mat, "imperceptibility", "ssim_global",
            "SSIM: prije i poslije", style.AXIS["ssim"], OURS),
        "chisquare_auc_vs_rate": lambda: line_vs_rate(mat, "chi2", "auc",
            "χ²: AUC i inverzija na osnovnom", style.AXIS["auc"], OURS, (0, 1), 0.5),
        "chisquare_positional": lambda: positional(mat),
        "rs_vs_spa_estimate": lambda: rs_estimate(mat),
        "ml_pe_vs_rate": lambda: line_vs_rate(mat, "ml", "pe",
            "ML: detektabilnost svih verzija", style.AXIS["pe"], ALLV, (0, 0.5)),
        "ml_group_pe": lambda: group_single("baseline", "ML značajke: osnovni algoritam"),
        "chisquare_aucB_beforeafter": lambda: line_vs_rate(mat, "chi2", "auc_b",
            "χ² u plavom kanalu (AUC_B): prije i poslije", style.AXIS["auc"], OURS, (0, 1), 0.5),
        "chisquare_pe_beforeafter": lambda: line_vs_rate(mat, "chi2", "pe",
            "χ²: prije i poslije", style.AXIS["pe"], OURS, (0, 0.5), 0.5),
        "rs_pe_beforeafter": lambda: line_vs_rate(mat, "rs", "pe",
            "RS: prije i poslije", style.AXIS["pe"], OURS, (0, 0.5), 0.5),
        "ml_pe_beforeafter": lambda: line_vs_rate(mat, "ml", "pe",
            "ML: prije i poslije", style.AXIS["pe"], OURS, (0, 0.5)),
        "ml_group_beforeafter": lambda: group_beforeafter(),
        "reference_chisquare_rs_spa": lambda: reference_attacks(mat),
        "all_attacks_comparison_multi": lambda: central_multi(mat),
        "all_attacks_comparison_single": lambda: central_single(mat),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    mat = _matrix()
    builders = build_all(mat)
    names = [args.only] if args.only else list(builders)
    for name in names:
        fig = builders[name]()
        base = style.save_figure(fig, name)
        print(f"wrote {base}.svg / .png")


if __name__ == "__main__":
    main()
