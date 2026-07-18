"""Reference-method figures: methods (LSB-R / LSB-M / HILL) vs our algorithm.

Reads the *_reference.csv plus our own summaries for context; writes to
results/figures/:
  * reference_chisquare_rs_spa.png -- classical attacks on the 3 references
      (LSB-R = positive control, strongly detected; LSB-M/HILL blind)
  * reference_ml_pe.png -- ML ensemble P_E vs rate: lsbr/lsbm/hill, with our
      `all` and `baseline` overlaid (the yardstick)

Run (from the repo root):
    python -m scripts.report.plot_reference
"""
import argparse
import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RES = "results/csv"
COLORS = {"lsbr": "tab:blue", "lsbm": "tab:orange", "hill": "tab:green",
          "all": "tab:red", "baseline": "black"}


def _rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _series_test250(path, key, valcol):
    out = defaultdict(list)
    for r in _rows(path):
        if r.get("eval_set", "test250") == "test250":
            out[r[key]].append((float(r["rate"]), float(r[valcol])))
    return {k: sorted(v) for k, v in out.items()}


def classical_fig(out):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    for ax, (name, csvf) in zip(axes, [("chi-square", "chisquare_reference.csv"),
                                       ("RS", "rs_reference.csv"),
                                       ("SPA", "spa_reference.csv")]):
        s = _series_test250(os.path.join(RES, csvf), "method", "auc")
        for m in ("lsbr", "lsbm", "hill"):
            if m in s:
                xs, ys = zip(*s[m])
                ax.plot(xs, ys, marker="o", color=COLORS[m], label=m)
        ax.axhline(0.5, color="lightgray", ls=":", lw=1)
        ax.set_xlabel("embedding rate")
        ax.set_title(f"{name} AUC")
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0.4, 1.02)
    axes[0].set_ylabel("detection AUC")
    axes[0].legend()
    fig.suptitle("Classical attacks on the reference methods "
                 "(LSB-R = positive control; LSB-M / HILL evade)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def ml_fig(out):
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ref = defaultdict(list)
    for r in _rows(os.path.join(RES, "ml_reference.csv")):
        if r["model"] == "ensemble":
            ref[r["config"]].append((float(r["rate"]), float(r["pe_mean"])))
    for m in ("lsbr", "lsbm", "hill"):
        if m in ref:
            xs, ys = zip(*sorted(ref[m]))
            ax.plot(xs, ys, marker="o", color=COLORS[m], label=m)
    # our algorithm for context (from ml_reanalysis.csv)
    ours = defaultdict(list)
    for r in _rows(os.path.join(RES, "ml_reanalysis.csv")):
        if r["model"] == "ensemble" and r["config"] in ("all", "baseline"):
            ours[r["config"]].append((float(r["rate"]), float(r["pe_mean"])))
    for c in ("all", "baseline"):
        if c in ours:
            xs, ys = zip(*sorted(ours[c]))
            ax.plot(xs, ys, marker="s", ls="--", color=COLORS[c], label=f"ours: {c}")
    ax.set_xlabel("embedding rate")
    ax.set_ylabel("ensemble P_E (higher = harder to detect)")
    ax.set_title("ML detectability: references vs our algorithm\n"
                 "HILL (adaptive) is hardest; our `all` ~ plain LSB")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--figures", default="results/figures/working")
    args = ap.parse_args()
    os.makedirs(args.figures, exist_ok=True)
    classical_fig(os.path.join(args.figures, "reference_chisquare_rs_spa.png"))
    ml_fig(os.path.join(args.figures, "reference_ml_pe.png"))
    print(f"wrote 2 figures -> {args.figures}")


if __name__ == "__main__":
    main()
