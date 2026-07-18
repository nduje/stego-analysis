"""Validate (and document the failure of) the candidate "+1-aware" detectors.

For a sample of real covers we synthesize matched stego with three embedding styles
-- '+1' (baseline-like: always add 1 on LSB mismatch), 'lsbm' (symmetric +/-1) and
'lsbr' (LSB replacement) -- and, for each candidate statistic in
analysis.plus_one_aware, measure how well it separates cover from each style (AUC on
the per-image scores).

A genuine "+1-aware" detector would show: AUC(+1) high, AUC(lsbm) ~0.5, AUC(lsbr) ~0.5.
The output shows that NONE of the candidates achieves this (they respond to any
embedding or specifically to replacement), i.e. the "+1" direction is not isolable by a
simple structural statistic -- the honest negative result.

Output: results/csv/plus_one_aware_probe.csv (statistic x alpha x target x AUC).

Run (from the repo root):
    python -m scripts.measure.plus_one_aware_probe --limit 100
"""
import argparse
import csv
import glob
import os

import numpy as np
from PIL import Image

from analysis.plus_one_aware import CANDIDATES

TARGETS = ("plus1", "lsbm", "lsbr")


def synth(cover, kind, rng, alpha):
    c = cover.astype(np.int16).copy()
    flat = c.reshape(-1); n = flat.size
    sel = rng.random(n) < alpha
    bit = rng.integers(0, 2, n)
    if kind == "lsbr":
        s = flat.copy(); s[sel] = ((flat & ~1) | bit)[sel]
        return np.clip(s, 0, 255).reshape(cover.shape).astype(np.uint8)
    mism = sel & ((flat & 1) != bit)
    if kind == "plus1":
        step = np.ones(n, np.int16); step[flat == 255] = 0        # baseline 255-skip
    else:  # lsbm
        step = rng.choice([-1, 1], size=n).astype(np.int16)
        step[flat == 0] = 1; step[flat == 255] = -1
    return np.clip(flat + mism * step, 0, 255).reshape(cover.shape).astype(np.uint8)


def auc(cover_scores, stego_scores):
    a = np.sort(np.asarray(cover_scores, float))
    b = np.asarray(stego_scores, float)
    r = np.searchsorted(a, b, side="right")           # ties -> upper; symmetric enough here
    return float(r.sum() / (len(a) * len(b)))


def run(covers_dir, out, limit, alphas):
    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))[:limit]
    rng = np.random.default_rng(42)
    rows = []
    for alpha in alphas:
        scores = {stat: {k: [] for k in ("cover",) + TARGETS} for stat in CANDIDATES}
        for p in paths:
            c = np.array(Image.open(p).convert("RGB"))
            imgs = {"cover": c, **{k: synth(c, k, rng, alpha) for k in TARGETS}}
            for stat, fn in CANDIDATES.items():
                for k, im in imgs.items():
                    scores[stat][k].append(fn(im)["comb"])
        for stat in CANDIDATES:
            for tgt in TARGETS:
                a = auc(scores[stat]["cover"], scores[stat][tgt])
                rows.append({"statistic": stat, "alpha": alpha, "target": tgt,
                             "auc": round(a, 4), "auc_oriented": round(max(a, 1 - a), 4)})
                print(f"  a={alpha} {stat:24} vs {tgt:6} AUC {a:.3f} "
                      f"(oriented {max(a, 1 - a):.3f})", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["statistic", "alpha", "target", "auc", "auc_oriented"])
        w.writeheader(); w.writerows(rows)
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--out", default="results/csv/plus_one_aware_probe.csv")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--alphas", default="1.0,0.5")
    args = ap.parse_args()
    run(args.covers, args.out, args.limit, [float(a) for a in args.alphas.split(",")])


if __name__ == "__main__":
    main()
