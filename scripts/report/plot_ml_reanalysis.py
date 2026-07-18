"""Before/after figures for the ML re-analysis + the full-spectrum summary.

Reads the baseline summaries and the ML re-analysis CSVs; writes to
results/figures/:
  * ml_pe_beforeafter.png      -- ensemble P_E vs rate, baseline + 4 configs (error bars)
  * ml_auc_beforeafter.png     -- ensemble AUC vs rate
  * ml_group_beforeafter.png   -- spatial vs color P_E (the flag-footprint test)
  * stegexpose_beforeafter.png -- StegExpose P_E vs rate, baseline + 4 configs
  * all_attacks_comparison_beforeafter.png -- CENTRAL: chi2/RS/SPA/ML/StegExpose,
                                              baseline (solid) vs all (dashed), P_E vs rate

Run (from the repo root):
    python -m scripts.report.plot_ml_reanalysis
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


def _ml_series(csv_name, col_mean, col_std, model="ensemble"):
    """{config: (rates, means, stds)} from a config-tagged ML CSV (test protocol)."""
    out = {}
    by = defaultdict(list)
    for r in _rows(os.path.join(RES, csv_name)):
        if r.get("model", model) == model:
            by[r["config"]].append(r)
    for cfg, rs in by.items():
        rs.sort(key=lambda r: float(r["rate"]))
        out[cfg] = ([float(r["rate"]) for r in rs],
                    [float(r[col_mean]) for r in rs],
                    [float(r[col_std]) for r in rs])
    return out


def ml_fig(series, ylabel, title, out, ylim=None):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for cfg in ORDER:
        if cfg in series:
            xs, ys, es = series[cfg]
            ax.errorbar(xs, ys, yerr=es, marker="o", capsize=3,
                        color=COLORS[cfg], label=cfg)
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


def group_fig(out):
    rows = _rows(os.path.join(RES, "ml_group_reanalysis.csv"))
    fig, (axs, axc) = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, group in ((axs, "spatial"), (axc, "color")):
        by = defaultdict(list)
        for r in rows:
            if r["group"] == group:
                by[r["config"]].append(r)
        for cfg in ORDER:
            if cfg in by:
                rs = sorted(by[cfg], key=lambda r: float(r["rate"]))
                ax.plot([float(r["rate"]) for r in rs], [float(r["pe_mean"]) for r in rs],
                        marker="o", color=COLORS[cfg], label=cfg)
        ax.set_xlabel("embedding rate")
        ax.set_title(f"{group} submodels")
        ax.grid(True, alpha=0.3)
    axs.set_ylabel("ensemble P_E")
    axs.legend()
    fig.suptitle("Group P_E before/after -- P3 lifts SPATIAL most (flag periodicity); "
                 "P2 lowers COLOR (matching)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def stegexpose_fig(out):
    rows = [r for r in _rows(os.path.join(RES, "stegexpose_reanalysis.csv"))
            if r["eval_set"] == "test250"]
    by = defaultdict(list)
    for r in rows:
        by[r["config"]].append(r)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for cfg in ORDER:
        if cfg in by:
            rs = sorted(by[cfg], key=lambda r: float(r["rate"]))
            ax.plot([float(r["rate"]) for r in rs], [float(r["pe"]) for r in rs],
                    marker="o", color=COLORS[cfg], label=cfg)
    ax.axhline(0.5, color="lightgray", ls=":", lw=1, label="chance (0.5)")
    ax.set_xlabel("embedding rate")
    ax.set_ylabel("StegExpose P_E")
    ax.set_title("StegExpose (Fusion) P_E before/after")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _pe_test250(rows, config=None):
    """(rates, pe) for test250 rows; filter by config if the CSV is config-tagged."""
    sel = [r for r in rows if r.get("eval_set", "test250") == "test250"
           and (config is None or r.get("config") == config)]
    sel.sort(key=lambda r: float(r["rate"]))
    return [float(r["rate"]) for r in sel], [float(r["pe"]) for r in sel]


def _ml_pe(rows, config):
    sel = [r for r in rows if r["config"] == config and r["model"] == "ensemble"]
    sel.sort(key=lambda r: float(r["rate"]))
    return [float(r["rate"]) for r in sel], [float(r["pe_mean"]) for r in sel]


def all_attacks_fig(out):
    """CENTRAL figure: every attack, baseline (solid) vs all (dashed), P_E vs rate."""
    chi_b = _pe_test250(_rows(os.path.join(RES, "chisquare_summary.csv")))
    chi_a = _pe_test250(_rows(os.path.join(RES, "chisquare_reanalysis.csv")), "all")
    rs_b = _pe_test250(_rows(os.path.join(RES, "rs_summary.csv")))
    rs_a = _pe_test250(_rows(os.path.join(RES, "rs_reanalysis.csv")), "all")
    spa_b = _pe_test250(_rows(os.path.join(RES, "spa_summary.csv")))
    spa_a = _pe_test250(_rows(os.path.join(RES, "spa_reanalysis.csv")), "all")
    ml_rows = _rows(os.path.join(RES, "ml_reanalysis.csv"))
    ml_b = _ml_pe(ml_rows, "baseline")
    ml_a = _ml_pe(ml_rows, "all")
    se_rows = _rows(os.path.join(RES, "stegexpose_reanalysis.csv"))
    se_b = _pe_test250(se_rows, "baseline")
    se_a = _pe_test250(se_rows, "all")

    attacks = [("chi2", chi_b, chi_a, "tab:purple"),
               ("RS", rs_b, rs_a, "tab:blue"),
               ("SPA", spa_b, spa_a, "tab:cyan"),
               ("ML (ensemble)", ml_b, ml_a, "tab:red"),
               ("StegExpose", se_b, se_a, "tab:brown")]

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    for name, b, a, col in attacks:
        if b[0]:
            ax.plot(b[0], b[1], marker="o", ls="-", color=col, label=f"{name} (baseline)")
        if a[0]:
            ax.plot(a[0], a[1], marker="s", ls="--", color=col, label=f"{name} (all)")
    ax.axhline(0.5, color="lightgray", ls=":", lw=1)
    ax.set_xlabel("embedding rate")
    ax.set_ylabel("P_E (lower = more detectable)")
    ax.set_ylim(0, 0.55)
    ax.set_title("Full-spectrum detectability before/after\n"
                 "solid = baseline, dashed = all (P1+P2+P3)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--figures", default="results/figures/working")
    args = ap.parse_args()
    os.makedirs(args.figures, exist_ok=True)

    pe = _ml_series("ml_reanalysis.csv", "pe_mean", "pe_std")
    ml_fig(pe, "ensemble P_E", "ML P_E before/after (P3 helps most; P2 slightly hurts)",
           os.path.join(args.figures, "ml_pe_beforeafter.png"), ylim=(0, 0.5))
    auc = _ml_series("ml_reanalysis.csv", "auc_mean", "auc_std")
    ml_fig(auc, "ensemble AUC", "ML AUC before/after",
           os.path.join(args.figures, "ml_auc_beforeafter.png"), ylim=(0.5, 1.0))
    group_fig(os.path.join(args.figures, "ml_group_beforeafter.png"))
    stegexpose_fig(os.path.join(args.figures, "stegexpose_beforeafter.png"))
    all_attacks_fig(os.path.join(args.figures, "all_attacks_comparison_beforeafter.png"))
    print(f"wrote 5 figures -> {args.figures}")


if __name__ == "__main__":
    main()
