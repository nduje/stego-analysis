"""Imperceptibility of the improved configs (p1/p2/p3/all) -- the before/after axis.

The same imperceptibility metrics (MSE/PSNR/SSIM, GLOBAL + REGION, per-channel + Y), so the
numbers are directly comparable to the frozen baseline
(results/csv/imperceptibility_summary.csv). Stego is regenerated on the fly (in memory,
same key/seed/coverage as the feature sets) and discarded -- no PNGs, no SCRM. The REGION
comes from the algorithm's
actual visiting order (region_mask with config+seed): scattered for prng, and under
length_header the freed 9th channel contributes 0 distortion inside the region.

Also reports the per-config round-trip failure fraction on the 500 covers (the
correctness side of "after": p2/all fix the 255-bug, baseline/p1/p3 keep it).

Output: results/csv/imperceptibility_reanalysis.csv (config x rate) with deltas vs baseline.

Run (from the repo root):
    python -m scripts.measure.measure_imperceptibility_reanalysis
    python -m scripts.measure.measure_imperceptibility_reanalysis --limit 20   # smoke
"""
import argparse
import base64
import csv
import glob
import os
import random

import numpy as np

from lib import StegAlgorithm, StegoConfig
from lib.algorithm import load_image, _resolve
from lib.rates import EMBEDDING_RATES, capacity_chars, chars_for_rate
from lib.metrics import mse, psnr_from_mse, ssim, to_luminance, region_mask, region_row_span
from scripts.data.make_stego_sets import CONFIGS, KEY

CHANS = ("rgb", "r", "g", "b", "y")
METRIC_KEYS = (
    [f"mse_global_{c}" for c in CHANS] + [f"mse_region_{c}" for c in CHANS] +
    [f"psnr_global_{c}" for c in CHANS] + [f"psnr_region_{c}" for c in CHANS] +
    ["ssim_global_chan", "ssim_global_y", "ssim_region_chan", "ssim_region_y"]
)


def _payload(image_idx, rate, length):
    rng = random.Random(f"{image_idx}:{rate}")
    return "".join(chr(c) for c in rng.choices(range(32, 127), k=length))


def _row(cover, cover_y, stego, mask, span):
    top, bottom = span
    g = {c: None for c in CHANS}
    r = {c: None for c in CHANS}
    for c, ca, cb in (("rgb", cover, stego), ("r", cover[..., 0], stego[..., 0]),
                      ("g", cover[..., 1], stego[..., 1]), ("b", cover[..., 2], stego[..., 2]),
                      ("y", cover_y, to_luminance(stego))):
        g[c] = mse(ca, cb)
        r[c] = mse(ca, cb, mask)
    out = {}
    for c in CHANS:
        out[f"mse_global_{c}"] = g[c]
        out[f"mse_region_{c}"] = r[c]
        out[f"psnr_global_{c}"] = psnr_from_mse(g[c])
        out[f"psnr_region_{c}"] = psnr_from_mse(r[c])
    out["ssim_global_chan"] = ssim(cover, stego)
    out["ssim_global_y"] = ssim(cover_y, to_luminance(stego))
    out["ssim_region_chan"] = ssim(cover[top:bottom], stego[top:bottom])
    out["ssim_region_y"] = ssim(cover_y[top:bottom], to_luminance(stego)[top:bottom])
    return out


def measure_config(name, paths, seed):
    cfg = CONFIGS[name]
    alg = StegAlgorithm(cfg)
    header = 2 if cfg.termination == "length_header" else 0
    rows = {}
    for rate in EMBEDDING_RATES:
        acc = {k: [] for k in METRIC_KEYS}
        fails = 0
        for idx, path in enumerate(paths):
            cover_im = load_image(path)
            w, h = cover_im.size
            blocks = chars_for_rate(capacity_chars(w, h), rate)      # coverage-matched
            payload = _payload(idx, rate, blocks - header)
            stego_im = alg.hide(message=payload, key=KEY, cover_path=path, out_path=None)
            fails += int(alg.expose(stego_image=stego_im, key=KEY) != payload)

            cover = np.asarray(cover_im)
            stego = np.asarray(stego_im)
            mask = region_mask(w, h, blocks, cfg, seed)
            m = _row(cover, to_luminance(cover), stego, mask, region_row_span(mask))
            for k in METRIC_KEYS:
                acc[k].append(m[k])
        row = {"config": name, "rate": rate, "n": len(paths),
               "roundtrip_fail_frac": round(fails / len(paths), 6)}
        for k in METRIC_KEYS:
            a = np.array(acc[k], dtype=np.float64)
            row[f"{k}_mean"] = round(float(a.mean()), 6)
            row[f"{k}_std"] = round(float(a.std()), 6)
        rows[rate] = row
        print(f"  {name} r{rate}: PSNRg={row['psnr_global_rgb_mean']:.2f} "
              f"PSNRreg={row['psnr_region_rgb_mean']:.2f} SSIMg={row['ssim_global_chan_mean']:.4f} "
              f"fail={row['roundtrip_fail_frac']}", flush=True)
    return rows


def _baseline(path):
    if not os.path.exists(path):
        return {}
    return {r["rate"]: r for r in csv.DictReader(open(path))}


def _existing(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def run(covers_dir, out, baseline_csv, limit, configs, append):
    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))
    if limit:
        paths = paths[:limit]
    _, seed = _resolve(None, KEY)
    base = _baseline(baseline_csv)

    fields = (["config", "rate", "n", "roundtrip_fail_frac"] +
              [f"{k}_mean" for k in METRIC_KEYS] + [f"{k}_std" for k in METRIC_KEYS] +
              ["psnr_global_rgb_delta", "psnr_region_rgb_delta", "ssim_global_chan_delta"])

    rows = _existing(out) if append else []
    present = {r["config"] for r in rows}
    todo = [c for c in configs if c not in present]
    if append:
        print(f"append: existing {sorted(present)}; computing {todo}", flush=True)

    for name in todo:
        for rate, row in measure_config(name, paths, seed).items():
            b = base.get(str(rate))
            for hk in ("psnr_global_rgb", "psnr_region_rgb", "ssim_global_chan"):
                row[f"{hk}_delta"] = (round(row[f"{hk}_mean"] - float(b[f"{hk}_mean"]), 6)
                                      if b else "")
            rows.append(row)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--out", default="results/csv/imperceptibility_reanalysis.csv")
    ap.add_argument("--baseline", default="results/csv/imperceptibility_summary.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--config", default="p1,p2,p3,all")
    ap.add_argument("--append", action="store_true")
    args = ap.parse_args()
    run(args.covers, args.out, args.baseline, args.limit,
        [c.strip() for c in args.config.split(",")], args.append)


if __name__ == "__main__":
    main()
