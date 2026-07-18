"""Plot RS detection + estimation results into deliverable figures.

Reads results/csv/rs_summary.csv (and, if present, results/csv/chisquare_summary.csv for
an overlay); writes to results/figures/:
  * rs_auc_vs_rate.png            -- RS detection AUC vs rate (250 vs 500, +chi2)
  * rs_estimated_vs_true_rate.png -- estimated p_hat vs true rate (+ideal diagonal)
  * rs_pe_vs_rate.png             -- RS P_E vs rate (250 vs 500)
  * rs_per_channel_estimate.png   -- mean p_hat per channel vs true rate

Run (from the repo root):
    python -m scripts.report.plot_rs
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


def auc_vs_rate(summary, chi, out):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for eval_set, (xs, ys) in _by_set(summary, "auc").items():
        ax.plot(xs, ys, marker="o", label=f"RS {eval_set}")
    if chi:
        c = _by_set(chi, "auc").get("test250")
        if c:
            ax.plot(c[0], c[1], marker="s", ls="--", color="gray", label="chi2 test250")
    ax.axhline(0.5, color="lightgray", ls=":", lw=1)
    ax.set_xlabel("embedding rate (fraction of capacity)")
    ax.set_ylabel("detection AUC")
    ax.set_title("RS detection AUC vs embedding rate")
    ax.set_ylim(0.0, 1.02)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def estimated_vs_true(summary, out):
    test = [r for r in summary if r["eval_set"] == "test250"]
    rate = [float(r["rate"]) for r in test]
    mean = [float(r["mean_phat_stego"]) for r in test]
    std = [float(r["std_phat_stego"]) for r in test]
    cover = [float(r["mean_phat_cover"]) for r in test]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot([0, 1], [0, 1], color="gray", ls="--", lw=1, label="ideal (unbiased)")
    ax.errorbar(rate, mean, yerr=std, marker="o", capsize=3, label="RS estimate (stego)")
    ax.plot(rate, cover, marker="x", ls=":", color="green", label="RS on covers (~0)")
    ax.set_xlabel("true embedding rate")
    ax.set_ylabel("estimated rate  p_hat")
    ax.set_title("RS rate estimate vs true rate (test-250)\n(gap from the diagonal = bias from the '+1' mismatch)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def pe_vs_rate(summary, out):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for eval_set, (xs, ys) in _by_set(summary, "pe").items():
        ax.plot(xs, ys, marker="o", label=f"RS {eval_set}")
    ax.set_xlabel("embedding rate (fraction of capacity)")
    ax.set_ylabel("P_E (detection error)")
    ax.set_title("RS detection error vs embedding rate")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def per_channel_estimate(scores, out):
    rates = sorted({r["rate"] for r in scores if r["label"] == "stego"}, key=float)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for ch, color in (("r", "red"), ("g", "green"), ("b", "blue")):
        ys = []
        for rate in rates:
            vals = [float(r[f"phat_{ch}"]) for r in scores
                    if r["label"] == "stego" and r["rate"] == rate and r["split"] == "test"]
            ys.append(sum(vals) / len(vals))
        ax.plot([float(x) for x in rates], ys, marker="o", color=color, label=f"{ch.upper()} channel")
    ax.plot([0, 1], [0, 1], color="gray", ls="--", lw=1, label="ideal")
    ax.set_xlabel("true embedding rate")
    ax.set_ylabel("mean estimated p_hat")
    ax.set_title("RS per-channel rate estimate vs true rate (test-250)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="results/csv/rs_summary.csv")
    ap.add_argument("--scores", default="results/csv/rs_scores.csv")
    ap.add_argument("--chisquare", default="results/csv/chisquare_summary.csv")
    ap.add_argument("--figures", default="results/figures/working")
    args = ap.parse_args()
    os.makedirs(args.figures, exist_ok=True)

    summary = _rows(args.summary)
    chi = _rows(args.chisquare) if os.path.exists(args.chisquare) else None
    auc_vs_rate(summary, chi, os.path.join(args.figures, "rs_auc_vs_rate.png"))
    estimated_vs_true(summary, os.path.join(args.figures, "rs_estimated_vs_true_rate.png"))
    pe_vs_rate(summary, os.path.join(args.figures, "rs_pe_vs_rate.png"))
    per_channel_estimate(_rows(args.scores), os.path.join(args.figures, "rs_per_channel_estimate.png"))
    print(f"wrote 4 figures -> {args.figures}")


if __name__ == "__main__":
    main()
