"""Plot the ML detection results + the whole-spectrum attack comparison.

Reads results/csv/ml_summary.csv (+ ml_group.csv, and the chi2/RS/SPA/StegExpose
summaries if present); writes to results/figures/:
  * ml_pe_vs_rate.png        -- ensemble vs SVM P_E, +/- std
  * ml_auc_vs_rate.png       -- ensemble vs SVM AUC, +/- std
  * ml_roc_by_rate.png       -- ensemble ROC per rate (recomputed on split seed 0)
  * ml_group_pe.png          -- spatial vs color vs all feature groups
  * all_attacks_comparison.png -- chi2 / RS / SPA / ML / StegExpose, P_E vs rate

Run (from the repo root):
    python -m scripts.report.plot_ml
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lib.rates import EMBEDDING_RATES
from analysis.ml_features import load_feature_set, random_paired_split, assemble
from analysis.ml_classifier import ensemble_detector, stego_scores
from analysis.detection import roc_points


def _rows(path):
    if not os.path.exists(path):
        return None
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _series(rows, key_filter, x_col, y_col, ystd_col=None):
    xs, ys, es = [], [], []
    for r in rows:
        if all(r[k] == v for k, v in key_filter.items()):
            xs.append(float(r[x_col])); ys.append(float(r[y_col]))
            if ystd_col:
                es.append(float(r[ystd_col]))
    return xs, ys, (es or None)


def ml_vs_rate(ml, metric, out, ylabel, title):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for model, color in (("ensemble", "tab:blue"), ("svm", "tab:orange")):
        xs, ys, es = _series(ml, {"model": model}, "rate", f"{metric}_mean", f"{metric}_std")
        if xs:
            ax.errorbar(xs, ys, yerr=es, marker="o", capsize=3, color=color, label=model)
    ax.set_xlabel("embedding rate (fraction of capacity)")
    ax.set_ylabel(ylabel); ax.set_title(title)
    ax.grid(True, alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)


def ml_roc(features_dir, out):
    Xc, fc = load_feature_set(os.path.join(features_dir, "covers"))
    fig, ax = plt.subplots(figsize=(6, 6))
    for rate in EMBEDDING_RATES:
        Xs, _ = load_feature_set(os.path.join(features_dir, f"stego_r{rate}"))
        tr, te = random_paired_split(len(Xc), 0)
        Xtr, ytr = assemble(Xc, Xs, tr)
        Xte, yte = assemble(Xc, Xs, te)
        m = ensemble_detector(seed=0); m.fit(Xtr, ytr)
        s = stego_scores(m, Xte)
        fpr, tpr = roc_points(s[yte == 0], s[yte == 1])
        ax.plot(fpr, tpr, label=f"rate {rate}")
    ax.plot([0, 1], [0, 1], color="gray", ls="--", lw=1)
    ax.set_xlabel("false-positive rate"); ax.set_ylabel("true-positive rate")
    ax.set_title("Ensemble ROC by embedding rate (test split, seed 0)")
    ax.grid(True, alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)


def ml_group(group_rows, out):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for grp, color in (("all", "black"), ("spatial", "tab:green"), ("color", "tab:purple")):
        xs, ys, es = _series(group_rows, {"group": grp}, "rate", "pe_mean", "pe_std")
        if xs:
            ax.errorbar(xs, ys, yerr=es, marker="o", capsize=3, color=color, label=grp)
    ax.set_xlabel("embedding rate (fraction of capacity)")
    ax.set_ylabel("ensemble P_E"); ax.set_title("Where is the signal? SCRM feature groups\n(spatial vs cross-channel color)")
    ax.grid(True, alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)


def all_attacks(out, results_dir):
    fig, ax = plt.subplots(figsize=(7.5, 5))
    sources = [
        ("chi-square", "chisquare_summary.csv", {"eval_set": "test250"}, "pe"),
        ("RS", "rs_summary.csv", {"eval_set": "test250"}, "pe"),
        ("SPA", "spa_summary.csv", {"eval_set": "test250"}, "pe"),
        ("ML (ensemble)", "ml_summary.csv", {"model": "ensemble"}, "pe_mean"),
        ("StegExpose", "stegexpose_summary.csv", {"eval_set": "test250"}, "pe"),
    ]
    for label, fname, kf, ycol in sources:
        rows = _rows(os.path.join(results_dir, fname))
        if not rows:
            continue
        xs, ys, _ = _series(rows, kf, "rate", ycol)
        if xs:
            ax.plot(xs, ys, marker="o", label=label)
    ax.axhline(0.5, color="lightgray", ls=":", lw=1, label="chance (P_E 0.5)")
    ax.set_xlabel("embedding rate (fraction of capacity)")
    ax.set_ylabel("detection error  P_E  (lower = better detector)")
    ax.set_title("Whole-spectrum detectability of the baseline '+1' algorithm")
    ax.grid(True, alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/csv")
    ap.add_argument("--features", default="data/alaska/features")
    ap.add_argument("--figures", default="results/figures/working")
    args = ap.parse_args()
    os.makedirs(args.figures, exist_ok=True)

    ml = _rows(os.path.join(args.results, "ml_summary.csv"))
    if ml:
        ml_vs_rate(ml, "pe", os.path.join(args.figures, "ml_pe_vs_rate.png"),
                   "P_E (detection error)", "ML detection error vs embedding rate")
        ml_vs_rate(ml, "auc", os.path.join(args.figures, "ml_auc_vs_rate.png"),
                   "AUC", "ML detection AUC vs embedding rate")
    ml_roc(args.features, os.path.join(args.figures, "ml_roc_by_rate.png"))
    grp = _rows(os.path.join(args.results, "ml_group.csv"))
    if grp:
        ml_group(grp, os.path.join(args.figures, "ml_group_pe.png"))
    all_attacks(os.path.join(args.figures, "all_attacks_comparison.png"), args.results)
    print(f"wrote figures -> {args.figures}")


if __name__ == "__main__":
    main()
