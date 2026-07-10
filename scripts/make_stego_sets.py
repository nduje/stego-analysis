"""Generate baseline stego images for ML feature extraction.

For a given embedding rate (or all rates), embed every cover with the baseline
(fixed key, payload L = round(rate*21760)) and save the stego PNG under
data/alaska/stego/r<rate>/<name>.png. Everything here is git-ignored.

Disk-aware: pass a single --rate to generate one rate at a time so a driver can
generate -> extract features -> delete PNGs before the next rate (features are
what we keep, not the images). Prints the resulting size.

Run (from the repo root):
    python -m scripts.make_stego_sets --rate 1.0         # one rate
    python -m scripts.make_stego_sets                    # all rates
"""
import argparse
import base64
import glob
import os
import random

from lib.algorithm import load_image  # noqa: F401  (kept for symmetry / future use)
from lib.rates import EMBEDDING_RATES, capacity_chars, chars_for_rate
from baseline.stego import hide_message

KEY = base64.b64encode(bytes(range(32))).decode()
CAPACITY = capacity_chars(256, 256)


def make_payload(image_idx, rate, length):
    rng = random.Random(f"{image_idx}:{rate}")
    return "".join(chr(c) for c in rng.choices(range(32, 127), k=length))


def _dir_size_mb(path):
    total = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(path) for f in fs)
    return total / (1024 * 1024)


def generate_rate(covers_dir, out_root, rate, limit):
    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))
    if limit:
        paths = paths[:limit]
    out_dir = os.path.join(out_root, f"r{rate}")
    os.makedirs(out_dir, exist_ok=True)
    L = chars_for_rate(CAPACITY, rate)

    for idx, path in enumerate(paths):
        name = os.path.basename(path)
        dest = os.path.join(out_dir, name)
        if os.path.exists(dest):
            continue
        stego = hide_message(make_payload(idx, rate, L), KEY, path, dest)
        if stego is False:
            print(f"[warn] embed failed (too large?) for {name} @ r{rate}")
    print(f"rate {rate}: {len(paths)} stego -> {out_dir}  ({_dir_size_mb(out_dir):.0f} MB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--out", default="data/alaska/stego")
    ap.add_argument("--rate", type=float, default=None, help="single rate; omit for all")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rates = [args.rate] if args.rate is not None else list(EMBEDDING_RATES)
    for rate in rates:
        generate_rate(args.covers, args.out, rate, args.limit)


if __name__ == "__main__":
    main()
