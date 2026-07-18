"""Central figure: full-spectrum detectability, all versions x all attacks.

Reads results/csv/master_matrix.csv (source of truth) and draws P_E vs rate as a 5-panel
figure (one panel per attack: chi2, RS, SPA, StegExpose, ML). Each panel shows all nine
versions -- our six configs (solid) and the three reference methods (dashed) -- so the
whole comparison is one read. ("+1-aware" is NOT here: it is a negative result, not a
detector; it lives in the text.)

Run (from the repo root):
    python -m scripts.report.plot_matrix
"""
import argparse
import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ATTACKS = [("chi2", "chi-square"), ("rs", "RS"), ("spa", "SPA"),
           ("stegexpose", "StegExpose"), ("ml", "ML (ensemble)")]
STYLE = {
    "baseline": ("black", "-"), "p1": ("tab:blue", "-"), "p2": ("tab:orange", "-"),
    "p3": ("tab:green", "-"), "p13": ("tab:brown", "-"), "all": ("tab:red", "-"),
    "lsbr": ("tab:purple", "--"), "lsbm": ("tab:pink", "--"), "hill": ("tab:cyan", "--"),
}
ORDER = list(STYLE)


def load(path):
    """{(attack, version): [(rate, pe)...]} from the master matrix."""
    series = defaultdict(list)
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["metric"] == "pe":
                series[(r["attack"], r["version"])].append((float(r["rate"]), float(r["value"])))
    return {k: sorted(v) for k, v in series.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", default="results/csv/master_matrix.csv")
    ap.add_argument("--out", default="results/figures/working/all_attacks_comparison_full.png")
    args = ap.parse_args()
    series = load(args.matrix)

    fig, axes = plt.subplots(1, 5, figsize=(20, 4.6), sharey=True)
    for ax, (atk, title) in zip(axes, ATTACKS):
        for v in ORDER:
            pts = series.get((atk, v))
            if not pts:
                continue
            xs, ys = zip(*pts)
            col, ls = STYLE[v]
            ax.plot(xs, ys, marker="o", ms=4, color=col, ls=ls, label=v)
        ax.axhline(0.5, color="lightgray", ls=":", lw=1)
        ax.set_title(title)
        ax.set_xlabel("embedding rate")
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 0.55)
    axes[0].set_ylabel("P_E (lower = more detectable)")
    axes[-1].legend(fontsize=8, ncol=1, loc="lower left")
    fig.suptitle("Full-spectrum detectability: our configs (solid) vs reference methods (dashed) "
                 "-- P_E vs embedding rate", y=1.02)
    fig.tight_layout()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
