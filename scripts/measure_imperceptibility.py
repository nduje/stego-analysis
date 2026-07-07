"""Measure baseline fidelity (imperceptibility) across embedding rates.

For every cover x every embedding rate:
  * build a reproducible printable-ASCII payload of length L = round(rate*capacity),
  * embed it with the BASELINE algorithm using a FIXED raw key (fast + reproducible;
    payload content is statistically irrelevant thanks to AES whitening -- only L
    matters),
  * compute all fidelity metrics GLOBAL and REGION (MSE/PSNR: rgb+r+g+b+Y,
    SSIM: per-channel avg + Y),
  * record whether the payload still round-trips.

Stego images are computed in memory and discarded -- no PNGs are written. Two CSVs
are produced: a per-(image,rate) table (git-ignored, large) and a per-rate
mean+/-std summary (committed).

Run (from the repo root):
    python -m scripts.measure_imperceptibility --covers data/alaska/covers --workers 16
    python -m scripts.measure_imperceptibility --limit 20        # quick smoke
"""
import argparse
import base64
import csv
import glob
import os
import random
from multiprocessing import Pool

import numpy as np

from baseline.stego import hide_message, expose_message
from lib.algorithm import load_image
from lib.rates import EMBEDDING_RATES, capacity_chars, chars_for_rate
from lib.metrics import (
    mse, psnr_from_mse, ssim, to_luminance, region_mask, region_row_span,
)

# Fixed raw key (base64 of bytes 0..31): deterministic ciphertext -> reproducible.
KEY = base64.b64encode(bytes(range(32))).decode()
CAPACITY = capacity_chars(256, 256)          # 21760

COLUMNS = [
    "image", "rate", "L", "region_px", "roundtrip_ok",
    "mse_global_rgb", "mse_global_r", "mse_global_g", "mse_global_b", "mse_global_y",
    "mse_region_rgb", "mse_region_r", "mse_region_g", "mse_region_b", "mse_region_y",
    "psnr_global_rgb", "psnr_global_r", "psnr_global_g", "psnr_global_b", "psnr_global_y",
    "psnr_region_rgb", "psnr_region_r", "psnr_region_g", "psnr_region_b", "psnr_region_y",
    "ssim_global_chan", "ssim_global_y", "ssim_region_chan", "ssim_region_y",
]
METRIC_COLUMNS = COLUMNS[5:]                  # the 24 numeric metrics


def make_payload(image_idx, rate, length):
    """Reproducible printable-ASCII payload (seed depends on image and rate)."""
    rng = random.Random(f"{image_idx}:{rate}")
    return "".join(chr(c) for c in rng.choices(range(32, 127), k=length))


def _compute_row(image_name, rate, cover, cover_y, stego, length):
    W, H = cover.shape[1], cover.shape[0]
    stego_y = to_luminance(stego)
    mask = region_mask(W, H, length)
    top, bottom = region_row_span(mask)

    def per(kind_mask):
        return {
            "rgb": mse(cover, stego, kind_mask),
            "r": mse(cover[..., 0], stego[..., 0], kind_mask),
            "g": mse(cover[..., 1], stego[..., 1], kind_mask),
            "b": mse(cover[..., 2], stego[..., 2], kind_mask),
            "y": mse(cover_y, stego_y, kind_mask),
        }

    mse_g, mse_r = per(None), per(mask)
    row = {"image": image_name, "rate": rate, "L": length, "region_px": int(mask.sum())}
    for k in ("rgb", "r", "g", "b", "y"):
        row[f"mse_global_{k}"] = mse_g[k]
        row[f"mse_region_{k}"] = mse_r[k]
        row[f"psnr_global_{k}"] = psnr_from_mse(mse_g[k])
        row[f"psnr_region_{k}"] = psnr_from_mse(mse_r[k])
    row["ssim_global_chan"] = ssim(cover, stego)
    row["ssim_global_y"] = ssim(cover_y, stego_y)
    row["ssim_region_chan"] = ssim(cover[top:bottom], stego[top:bottom])
    row["ssim_region_y"] = ssim(cover_y[top:bottom], stego_y[top:bottom])
    return row


def process_image(task):
    """Return one row per rate for a single cover. Top-level for multiprocessing."""
    image_idx, path = task
    name = os.path.basename(path)
    cover = np.asarray(load_image(path))
    cover_y = to_luminance(cover)

    rows = []
    for rate in EMBEDDING_RATES:
        L = chars_for_rate(CAPACITY, rate)
        payload = make_payload(image_idx, rate, L)
        stego_pil = hide_message(payload, KEY, path, None)     # in memory, no save
        if stego_pil is False:
            continue
        recovered = expose_message(stego_pil, KEY)
        row = _compute_row(name, rate, cover, cover_y, np.asarray(stego_pil), L)
        row["roundtrip_ok"] = (recovered == payload)
        rows.append(row)
    return rows


def write_summary(rows, path):
    fields = ["rate", "n", "roundtrip_fail_frac"]
    for c in METRIC_COLUMNS:
        fields += [f"{c}_mean", f"{c}_std"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for rate in EMBEDDING_RATES:
            sub = [r for r in rows if r["rate"] == rate]
            if not sub:
                continue
            n = len(sub)
            fail = 1.0 - sum(r["roundtrip_ok"] for r in sub) / n
            out = [rate, n, round(fail, 6)]
            for c in METRIC_COLUMNS:
                vals = np.array([r[c] for r in sub], dtype=np.float64)
                out += [float(vals.mean()), float(vals.std())]
            w.writerow(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--out", default="results/imperceptibility.csv")
    ap.add_argument("--summary", default="results/imperceptibility_summary.csv")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="only first N covers (smoke test)")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.covers, "*.png")))
    if args.limit:
        paths = paths[:args.limit]
    if not paths:
        print(f"[error] no covers in {args.covers}")
        raise SystemExit(1)
    tasks = list(enumerate(paths))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    print(f"measuring {len(paths)} covers x {len(EMBEDDING_RATES)} rates "
          f"= {len(paths) * len(EMBEDDING_RATES)} rows, workers={args.workers}")

    if args.workers > 1:
        with Pool(args.workers) as pool:
            results = pool.map(process_image, tasks)
    else:
        results = [process_image(t) for t in tasks]
    rows = [r for group in results for r in group]

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    write_summary(rows, args.summary)

    fails = sum(not r["roundtrip_ok"] for r in rows)
    print(f"wrote {len(rows)} rows -> {args.out}")
    print(f"wrote per-rate summary -> {args.summary}")
    print(f"round-trip failures: {fails}/{len(rows)}")


if __name__ == "__main__":
    main()
