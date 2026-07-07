"""Plot the imperceptibility summary into deliverable figures.

Reads results/imperceptibility_summary.csv and writes PNGs to results/figures/:
  * psnr_vs_rate.png              -- PSNR global vs region, RGB and Y
  * ssim_vs_rate.png             -- SSIM global vs region, per-channel and Y
  * psnr_per_channel_vs_rate.png -- global PSNR for R, G, B
  * roundtrip_fail_vs_rate.png   -- fraction of round-trip failures vs rate

Run (from the repo root):
    python -m scripts.plot_imperceptibility
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _load(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    cols = {k: [float(r[k]) for r in rows] for k in rows[0]}
    return cols


def _line(ax, x, col, label, cols, err=True):
    y = cols[f"{col}_mean"]
    yerr = cols[f"{col}_std"] if err else None
    ax.errorbar(x, y, yerr=yerr, marker="o", capsize=3, label=label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="results/imperceptibility_summary.csv")
    ap.add_argument("--figures", default="results/figures")
    args = ap.parse_args()

    cols = _load(args.summary)
    rate = cols["rate"]
    os.makedirs(args.figures, exist_ok=True)

    # 1. PSNR vs rate: global vs region, RGB and Y
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _line(ax, rate, "psnr_global_rgb", "global RGB", cols)
    _line(ax, rate, "psnr_region_rgb", "region RGB", cols)
    _line(ax, rate, "psnr_global_y", "global Y", cols)
    _line(ax, rate, "psnr_region_y", "region Y", cols)
    ax.set_xlabel("embedding rate (fraction of capacity)")
    ax.set_ylabel("PSNR (dB)")
    ax.set_title("Baseline PSNR vs embedding rate\n(global measures coverage; region isolates distortion)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(args.figures, "psnr_vs_rate.png"), dpi=150)
    plt.close(fig)

    # 2. SSIM vs rate: global vs region, per-channel and Y
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _line(ax, rate, "ssim_global_chan", "global per-channel", cols)
    _line(ax, rate, "ssim_region_chan", "region per-channel", cols)
    _line(ax, rate, "ssim_global_y", "global Y", cols)
    _line(ax, rate, "ssim_region_y", "region Y", cols)
    ax.set_xlabel("embedding rate (fraction of capacity)")
    ax.set_ylabel("SSIM")
    ax.set_title("Baseline SSIM vs embedding rate")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(args.figures, "ssim_vs_rate.png"), dpi=150)
    plt.close(fig)

    # 3. per-channel global PSNR
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for ch, name in (("r", "R"), ("g", "G"), ("b", "B")):
        _line(ax, rate, f"psnr_global_{ch}", name, cols)
    ax.set_xlabel("embedding rate (fraction of capacity)")
    ax.set_ylabel("global PSNR (dB)")
    ax.set_title("Baseline per-channel global PSNR vs embedding rate")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(args.figures, "psnr_per_channel_vs_rate.png"), dpi=150)
    plt.close(fig)

    # 4. round-trip failure fraction
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(rate, cols["roundtrip_fail_frac"], marker="o", color="crimson")
    ax.set_xlabel("embedding rate (fraction of capacity)")
    ax.set_ylabel("round-trip failure fraction")
    ax.set_title("Baseline round-trip failures vs embedding rate\n(255-saturation bug; grows with coverage)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(args.figures, "roundtrip_fail_vs_rate.png"), dpi=150)
    plt.close(fig)

    print(f"wrote 4 figures -> {args.figures}")


if __name__ == "__main__":
    main()
