"""Before/after imperceptibility figures: baseline + p1/p2/p3/all on one plot.

Reads results/csv/imperceptibility_summary.csv (baseline, E1) and
results/csv/imperceptibility_reanalysis.csv (the 4 configs); writes to results/figures/:
  * psnr_beforeafter_vs_rate.png   -- global (left) and region (right) PSNR vs rate
  * ssim_beforeafter_vs_rate.png   -- global SSIM vs rate

Run (from the repo root):
    python -m scripts.report.plot_imperceptibility_reanalysis
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORDER = ["baseline", "p1", "p2", "p3", "all"]
COLORS = {"baseline": "black", "p1": "tab:blue", "p2": "tab:orange",
          "p3": "tab:green", "all": "tab:red"}


def _load(baseline_csv, reanalysis_csv):
    series = {c: {} for c in ORDER}
    for r in csv.DictReader(open(baseline_csv)):
        series["baseline"][float(r["rate"])] = r
    for r in csv.DictReader(open(reanalysis_csv)):
        series[r["config"]][float(r["rate"])] = r
    return series


def _xy(series, config, col):
    rates = sorted(series[config])
    return rates, [float(series[config][x][col]) for x in rates]


def psnr_fig(series, out):
    fig, (axg, axr) = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for cfg in ORDER:
        if not series[cfg]:
            continue
        xs, yg = _xy(series, cfg, "psnr_global_rgb_mean")
        _, yr = _xy(series, cfg, "psnr_region_rgb_mean")
        axg.plot(xs, yg, marker="o", color=COLORS[cfg], label=cfg)
        axr.plot(xs, yr, marker="o", color=COLORS[cfg], label=cfg)
    axg.set_title("Global PSNR (coverage)")
    axr.set_title("Region PSNR (distortion intensity)\np3/all higher: freed 9th channel")
    for ax in (axg, axr):
        ax.set_xlabel("embedding rate")
        ax.grid(True, alpha=0.3)
    axg.set_ylabel("PSNR (dB)")
    axg.legend()
    fig.suptitle("Imperceptibility before/after (baseline vs P1/P2/P3/all)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def ssim_fig(series, out):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for cfg in ORDER:
        if not series[cfg]:
            continue
        xs, ys = _xy(series, cfg, "ssim_global_chan_mean")
        ax.plot(xs, ys, marker="o", color=COLORS[cfg], label=cfg)
    ax.set_xlabel("embedding rate")
    ax.set_ylabel("global SSIM")
    ax.set_title("Global SSIM before/after")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="results/csv/imperceptibility_summary.csv")
    ap.add_argument("--reanalysis", default="results/csv/imperceptibility_reanalysis.csv")
    ap.add_argument("--figures", default="results/figures/working")
    args = ap.parse_args()
    os.makedirs(args.figures, exist_ok=True)
    series = _load(args.baseline, args.reanalysis)
    psnr_fig(series, os.path.join(args.figures, "psnr_beforeafter_vs_rate.png"))
    ssim_fig(series, os.path.join(args.figures, "ssim_beforeafter_vs_rate.png"))
    print(f"wrote 2 figures -> {args.figures}")


if __name__ == "__main__":
    main()
