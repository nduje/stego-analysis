"""Before/after figures for the classical attacks (chi2 / RS / SPA) on the configs.

Reads the baseline summaries and the re-analysis CSVs; writes to
results/figures/:
  * chisquare_aucB_beforeafter.png   -- AUC_B (blue) vs rate  [KEY: flag removal]
  * chisquare_auc_beforeafter.png    -- combined chi2 AUC vs rate
  * chisquare_positional_beforeafter.png -- positional p-value (baseline cliff vs prng flat)
  * rs_spa_beforeafter.png           -- RS and SPA AUC vs rate (the pm_one surprise)

Run (from the repo root):
    python -m scripts.report.plot_attacks_reanalysis
"""
import argparse
import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORDER = ["baseline", "p1", "p2", "p3", "p13", "all"]
COLORS = {"baseline": "black", "p1": "tab:blue", "p2": "tab:orange",
          "p3": "tab:green", "p13": "tab:brown", "all": "tab:red"}
RES = "results/csv"


def _rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _series(baseline_csv, reanalysis_csv, col):
    """{config: (rates, values)} for test250, baseline + 4 configs."""
    out = {}
    b = [r for r in _rows(os.path.join(RES, baseline_csv)) if r["eval_set"] == "test250"]
    if b:
        out["baseline"] = ([float(r["rate"]) for r in b], [float(r[col]) for r in b])
    re = [r for r in _rows(os.path.join(RES, reanalysis_csv)) if r["eval_set"] == "test250"]
    by = defaultdict(list)
    for r in re:
        by[r["config"]].append(r)
    for cfg, rs in by.items():
        rs.sort(key=lambda r: float(r["rate"]))
        out[cfg] = ([float(r["rate"]) for r in rs], [float(r[col]) for r in rs])
    return out


def _line_fig(series, ylabel, title, out, hline=None, ylim=None):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for cfg in ORDER:
        if cfg in series:
            xs, ys = series[cfg]
            ax.plot(xs, ys, marker="o", color=COLORS[cfg], label=cfg)
    if hline is not None:
        ax.axhline(hline, color="lightgray", ls=":", lw=1, label=f"chance ({hline})")
    ax.set_xlabel("embedding rate")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if ylim:
        ax.set_ylim(*ylim)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def positional_fig(out, rate=0.5):
    rows = [r for r in _rows(os.path.join(RES, "chisquare_positional_reanalysis.csv"))
            if float(r["rate"]) == rate]
    agg = defaultdict(lambda: defaultdict(list))
    for r in rows:
        agg[r["config"]][float(r["position"])].append(float(r["p_embed"]))
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for cfg in ["baseline", "p1", "all"]:
        if cfg not in agg:
            continue
        xs = sorted(agg[cfg])
        ys = [sum(agg[cfg][x]) / len(agg[cfg][x]) for x in xs]
        ax.plot(xs, ys, marker=".", color=COLORS[cfg], label=cfg)
    ax.axvline(rate, color="gray", ls=":", lw=0.8, label=f"rate {rate}")
    ax.set_xlabel("raster position (fraction of image)")
    ax.set_ylabel("chi-square p-value")
    ax.set_title(f"Positional chi-square @ rate {rate}\nbaseline 'cliff' vs prng (p1/all) flat")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def rs_spa_fig(out):
    fig, (axr, axs) = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, base, rean, name in ((axr, "rs_summary.csv", "rs_reanalysis.csv", "RS"),
                                 (axs, "spa_summary.csv", "spa_reanalysis.csv", "SPA")):
        s = _series(base, rean, "auc")
        for cfg in ORDER:
            if cfg in s:
                xs, ys = s[cfg]
                ax.plot(xs, ys, marker="o", color=COLORS[cfg], label=cfg)
        ax.axhline(0.5, color="lightgray", ls=":", lw=1)
        ax.set_xlabel("embedding rate")
        ax.set_title(f"{name} AUC")
        ax.grid(True, alpha=0.3)
    axr.set_ylabel("detection AUC")
    axr.legend()
    fig.suptitle("RS / SPA before/after -- note pm_one (p2) becomes detectable")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--figures", default="results/figures/working")
    args = ap.parse_args()
    os.makedirs(args.figures, exist_ok=True)

    aucB = _series("chisquare_summary.csv", "chisquare_reanalysis.csv", "auc_b")
    _line_fig(aucB, "chi-square AUC (blue channel)",
              "AUC_B before/after -- P3 removes the flag (0.03 -> ~0.5)",
              os.path.join(args.figures, "chisquare_aucB_beforeafter.png"), hline=0.5, ylim=(0, 1))
    auc = _series("chisquare_summary.csv", "chisquare_reanalysis.csv", "auc")
    _line_fig(auc, "chi-square AUC (combined)", "Chi-square AUC before/after",
              os.path.join(args.figures, "chisquare_auc_beforeafter.png"), hline=0.5, ylim=(0, 1))
    positional_fig(os.path.join(args.figures, "chisquare_positional_beforeafter.png"))
    rs_spa_fig(os.path.join(args.figures, "rs_spa_beforeafter.png"))
    print(f"wrote 4 figures -> {args.figures}")


if __name__ == "__main__":
    main()
