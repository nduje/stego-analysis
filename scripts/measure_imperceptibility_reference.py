"""Imperceptibility for the reference methods (LSB-R / LSB-M / HILL) -- the Day-20 gap.

Same payload alignment as everything else. Unlike our configs (whose "region" is the
embedding block-region), a reference method's region is simply the pixels it actually
changed (|delta|>0), per the Day-20 decision. Round-trip is N/A (we never decode the
references). LSB-R/LSB-M are generated in memory (fast); HILL via its Octave simulator
into a folder (then measured and deleted).

Output: results/imperceptibility_reference.csv (config = method, one row per rate).
Metrics kept are the ones the master matrix needs: global PSNR/MSE/SSIM (comparable
across methods) + region PSNR (changed pixels) + the changed-pixel fraction.

Run (from the repo root):
    python -m scripts.measure_imperceptibility_reference --octave <octave-cli>
"""
import argparse
import csv
import glob
import os
import shutil

import numpy as np
from PIL import Image

from lib.rates import EMBEDDING_RATES
from lib.metrics import mse, psnr_from_mse, ssim
from reference import payload
from scripts.make_reference_sets import _payload, _embed, generate

METHODS = ("lsbr", "lsbm", "hill")
FIELDS = ["config", "rate", "n", "roundtrip_fail_frac",
          "psnr_global_rgb_mean", "psnr_global_rgb_std",
          "psnr_region_rgb_mean", "ssim_global_chan_mean",
          "mse_global_rgb_mean", "changed_frac_mean"]


def _metrics(cover, stego):
    mask = np.any(cover != stego, axis=2)                 # changed pixels
    g = mse(cover, stego)
    r = mse(cover, stego, mask) if mask.any() else 0.0
    return {"psnr_global_rgb": psnr_from_mse(g) if g else 99.0,
            "psnr_region_rgb": psnr_from_mse(r) if r else 99.0,
            "ssim_global_chan": ssim(cover, stego),
            "mse_global_rgb": g,
            "changed_frac": float(mask.mean())}


def _stego_inmem(method, cover, idx, rate):
    h, w = cover.shape[:2]
    positions, bits = _payload(idx, rate, w * h * 3, w, h)
    return _embed(method, cover, positions, bits, idx, rate)


def measure_method(method, covers_dir, stego_root, octave):
    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))
    rows = []
    for rate in EMBEDDING_RATES:
        folder = None
        if method == "hill":
            folder = os.path.join(stego_root, method, f"r{rate}")
            generate(method, covers_dir, stego_root, rate, 0, octave)
        acc = {k: [] for k in ("psnr_global_rgb", "psnr_region_rgb",
                               "ssim_global_chan", "mse_global_rgb", "changed_frac")}
        for idx, p in enumerate(paths):
            cover = np.array(Image.open(p).convert("RGB"), dtype=np.uint8)
            if method == "hill":
                stego = np.array(Image.open(os.path.join(folder, os.path.basename(p))
                                            ).convert("RGB"), dtype=np.uint8)
            else:
                stego = _stego_inmem(method, cover, idx, rate)
            for k, v in _metrics(cover, stego).items():
                acc[k].append(v)
        if folder:
            shutil.rmtree(folder, ignore_errors=True)
        pg = np.array(acc["psnr_global_rgb"])
        rows.append({
            "config": method, "rate": rate, "n": len(paths), "roundtrip_fail_frac": "",
            "psnr_global_rgb_mean": round(float(pg.mean()), 6),
            "psnr_global_rgb_std": round(float(pg.std()), 6),
            "psnr_region_rgb_mean": round(float(np.mean(acc["psnr_region_rgb"])), 6),
            "ssim_global_chan_mean": round(float(np.mean(acc["ssim_global_chan"])), 6),
            "mse_global_rgb_mean": round(float(np.mean(acc["mse_global_rgb"])), 6),
            "changed_frac_mean": round(float(np.mean(acc["changed_frac"])), 6),
        })
        print(f"  {method} r{rate}: PSNRg={rows[-1]['psnr_global_rgb_mean']:.2f} "
              f"changed={rows[-1]['changed_frac_mean']:.3f} bpc={payload.bpc(rate):.4f}", flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--stego", default="data/alaska/stego")
    ap.add_argument("--out", default="results/imperceptibility_reference.csv")
    ap.add_argument("--octave", default=os.environ.get("OCTAVE_BIN"))
    ap.add_argument("--methods", default=",".join(METHODS))
    args = ap.parse_args()

    rows = []
    for m in [x.strip() for x in args.methods.split(",")]:
        rows += measure_method(m, args.covers, args.stego, args.octave)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
