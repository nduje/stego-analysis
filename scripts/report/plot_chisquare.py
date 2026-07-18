"""Plot the chi-square detection results into deliverable figures.

Reads results/csv/chisquare_summary.csv, results/csv/chisquare_scores.csv and
results/csv/chisquare_positional.csv; writes to results/figures/:
  * chisquare_auc_vs_rate.png        -- AUC vs rate, test-250 vs all-500
  * chisquare_roc_by_rate.png        -- ROC per rate (test-250)
  * chisquare_positional_example.png -- p-value vs raster position (the "cliff")

Run (from the repo root):
    python -m scripts.report.plot_chisquare
"""
import argparse
import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analysis.detection import roc_points


def _rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def auc_vs_rate(summary, out):
    by_set = defaultdict(lambda: ([], []))
    for r in summary:
        xs, ys = by_set[r["eval_set"]]
        xs.append(float(r["rate"]))
        ys.append(float(r["auc"]))
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for eval_set, (xs, ys) in by_set.items():
        ax.plot(xs, ys, marker="o", label=eval_set)
    ax.axhline(0.5, color="gray", ls="--", lw=1, label="chance (0.5)")
    ax.set_xlabel("embedding rate (fraction of capacity)")
    ax.set_ylabel("AUC")
    ax.set_title("Chi-square (global) detection AUC vs embedding rate")
    ax.set_ylim(0.45, 1.02)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def roc_by_rate(scores, out):
    fig, ax = plt.subplots(figsize=(6, 6))
    cover = [float(r["score_comb"]) for r in scores if r["label"] == "cover" and r["split"] == "test"]
    rates = sorted({r["rate"] for r in scores if r["label"] == "stego"}, key=float)
    for rate in rates:
        stego = [float(r["score_comb"]) for r in scores
                 if r["label"] == "stego" and r["rate"] == rate and r["split"] == "test"]
        fpr, tpr = roc_points(cover, stego)
        ax.plot(fpr, tpr, label=f"rate {rate}")
    ax.plot([0, 1], [0, 1], color="gray", ls="--", lw=1)
    ax.set_xlabel("false-positive rate")
    ax.set_ylabel("true-positive rate")
    ax.set_title("Chi-square ROC by embedding rate (test-250)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def positional_example(positional, out):
    # aggregate mean p-value vs position, per rate
    agg = defaultdict(lambda: defaultdict(list))
    for r in positional:
        agg[r["rate"]][float(r["position"])].append(float(r["p_embed"]))
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for rate in sorted(agg, key=float):
        xs = sorted(agg[rate])
        ys = [sum(agg[rate][x]) / len(agg[rate][x]) for x in xs]
        ax.plot(xs, ys, label=f"rate {rate}")
        ax.axvline(float(rate), color="gray", ls=":", lw=0.8)
    ax.set_xlabel("raster position (fraction of image)")
    ax.set_ylabel("chi-square p-value (probability of embedding)")
    ax.set_title("Positional chi-square: the 'cliff' localizes the payload\n(dotted = embedding rate; mean over subset)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="results/csv/chisquare_summary.csv")
    ap.add_argument("--scores", default="results/csv/chisquare_scores.csv")
    ap.add_argument("--positional", default="results/csv/chisquare_positional.csv")
    ap.add_argument("--figures", default="results/figures/working")
    args = ap.parse_args()
    os.makedirs(args.figures, exist_ok=True)

    auc_vs_rate(_rows(args.summary), os.path.join(args.figures, "chisquare_auc_vs_rate.png"))
    roc_by_rate(_rows(args.scores), os.path.join(args.figures, "chisquare_roc_by_rate.png"))
    positional_example(_rows(args.positional), os.path.join(args.figures, "chisquare_positional_example.png"))
    print(f"wrote 3 figures -> {args.figures}")


if __name__ == "__main__":
    main()
