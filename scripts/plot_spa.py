"""Plot SPA detection + estimation, plus a RS-vs-SPA estimate comparison.

Reads results/spa_summary.csv (and results/rs_summary.csv for the comparison);
writes to results/figures/:
  * spa_auc_vs_rate.png            -- SPA detection AUC vs rate (250 vs 500)
  * spa_estimated_vs_true_rate.png -- estimated p_hat vs true rate (+ideal diagonal)
  * rs_vs_spa_estimate.png         -- RS vs SPA rate estimate on one plot (test-250)

Run (from the repo root):
    python -m scripts.plot_spa
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _by_set(rows, col):
    out = {}
    for r in rows:
        out.setdefault(r["eval_set"], ([], []))
        out[r["eval_set"]][0].append(float(r["rate"]))
        out[r["eval_set"]][1].append(float(r[col]))
    return out


def _test(rows):
    return [r for r in rows if r["eval_set"] == "test250"]


def auc_vs_rate(summary, out):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for eval_set, (xs, ys) in _by_set(summary, "auc").items():
        ax.plot(xs, ys, marker="o", label=f"SPA {eval_set}")
    ax.axhline(0.5, color="lightgray", ls=":", lw=1)
    ax.set_xlabel("embedding rate (fraction of capacity)")
    ax.set_ylabel("detection AUC")
    ax.set_title("SPA detection AUC vs embedding rate")
    ax.set_ylim(0.0, 1.02)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def estimated_vs_true(summary, out):
    t = _test(summary)
    rate = [float(r["rate"]) for r in t]
    mean = [float(r["mean_phat_stego"]) for r in t]
    std = [float(r["std_phat_stego"]) for r in t]
    cover = [float(r["mean_phat_cover"]) for r in t]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot([0, 1], [0, 1], color="gray", ls="--", lw=1, label="ideal (unbiased)")
    ax.errorbar(rate, mean, yerr=std, marker="o", capsize=3, label="SPA estimate (stego)")
    ax.plot(rate, cover, marker="x", ls=":", color="green", label="SPA on covers (~0)")
    ax.set_xlabel("true embedding rate")
    ax.set_ylabel("estimated rate  p_hat")
    ax.set_title("SPA rate estimate vs true rate (test-250)\n(gap from the diagonal = bias from the '+1' mismatch)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def rs_vs_spa(spa_summary, rs_summary, out):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot([0, 1], [0, 1], color="gray", ls="--", lw=1, label="ideal")
    for name, rows, color in (("SPA", spa_summary, "tab:blue"), ("RS", rs_summary, "tab:orange")):
        t = _test(rows)
        ax.plot([float(r["rate"]) for r in t], [float(r["mean_phat_stego"]) for r in t],
                marker="o", color=color, label=f"{name} estimate")
    ax.set_xlabel("true embedding rate")
    ax.set_ylabel("mean estimated p_hat")
    ax.set_title("RS vs SPA rate estimate on the '+1' baseline (test-250)\n(both collapse to ~cover -> internal consistency)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="results/spa_summary.csv")
    ap.add_argument("--rs", default="results/rs_summary.csv")
    ap.add_argument("--figures", default="results/figures")
    args = ap.parse_args()
    os.makedirs(args.figures, exist_ok=True)

    spa = _rows(args.summary)
    auc_vs_rate(spa, os.path.join(args.figures, "spa_auc_vs_rate.png"))
    estimated_vs_true(spa, os.path.join(args.figures, "spa_estimated_vs_true_rate.png"))
    if os.path.exists(args.rs):
        rs_vs_spa(spa, _rows(args.rs), os.path.join(args.figures, "rs_vs_spa_estimate.png"))
        print(f"wrote 3 figures -> {args.figures}")
    else:
        print(f"wrote 2 figures -> {args.figures} (rs_summary.csv missing; skipped comparison)")


if __name__ == "__main__":
    main()
