"""Generate stego images for a given algorithm CONFIGURATION (baseline + P1/P2/P3/ALL).

For re-analysis we compare the baseline against the improved configurations on the
SAME covers, SAME key/seed, SAME per-(image,rate) payloads -- only the algorithm
(order / matching / termination) changes, so the before/after is clean.

Coverage is matched across configs: blocks touched = round(rate*21760) for every
config. length_header configs prepend a 2-char header, so their message is 2 chars
shorter (content is AES-whitened, so this does not affect the features -- only the
coverage matters, and coverage is identical).

Disk-aware: pass a single --rate to generate one rate at a time so a driver can
generate -> extract features -> delete PNGs before the next.

Run (from the repo root):
    python -m scripts.make_stego_sets --config all --rate 1.0
    python -m scripts.make_stego_sets --config p3           # all rates
"""
import argparse
import base64
import glob
import os
import random

from lib import StegAlgorithm, StegoConfig
from lib.rates import EMBEDDING_RATES, capacity_chars, chars_for_rate

KEY = base64.b64encode(bytes(range(32))).decode()      # same fixed key as the baseline sets
CAPACITY = capacity_chars(256, 256)                    # 21760

CONFIGS = {
    "baseline": StegoConfig(),
    "p1": StegoConfig(pixel_order="prng"),
    "p2": StegoConfig(matching_mode="pm_one"),
    "p3": StegoConfig(termination="length_header"),
    "all": StegoConfig(pixel_order="prng", matching_mode="pm_one", termination="length_header"),
    "p13": StegoConfig(pixel_order="prng", termination="length_header"),   # P1+P3, no P2
}


def make_payload(image_idx, rate, length):
    rng = random.Random(f"{image_idx}:{rate}")         # same seed scheme as the baseline sets
    return "".join(chr(c) for c in rng.choices(range(32, 127), k=length))


def _dir_size_mb(path):
    total = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(path) for f in fs)
    return total / (1024 * 1024)


def generate(config_name, covers_dir, out_root, rate, limit):
    cfg = CONFIGS[config_name]
    alg = StegAlgorithm(cfg)
    header = 2 if cfg.termination == "length_header" else 0   # coverage-matched

    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))
    if limit:
        paths = paths[:limit]
    out_dir = os.path.join(out_root, config_name, f"r{rate}")
    os.makedirs(out_dir, exist_ok=True)
    blocks = chars_for_rate(CAPACITY, rate)
    msg_len = blocks - header

    failed = 0
    for idx, path in enumerate(paths):
        dest = os.path.join(out_dir, os.path.basename(path))
        if os.path.exists(dest):
            continue
        payload = make_payload(idx, rate, msg_len)
        if alg.hide(message=payload, key=KEY, cover_path=path, out_path=dest) is False:
            failed += 1
    tag = f"{config_name} r{rate}"
    print(f"{tag}: {len(paths)} covers, {msg_len} chars (+{header} hdr) -> {out_dir}  "
          f"({_dir_size_mb(out_dir):.0f} MB){'  [%d failed]' % failed if failed else ''}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, choices=list(CONFIGS))
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--out", default="data/alaska/stego")
    ap.add_argument("--rate", type=float, default=None, help="single rate; omit for all")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rates = [args.rate] if args.rate is not None else list(EMBEDDING_RATES)
    for rate in rates:
        generate(args.config, args.covers, args.out, rate, args.limit)


if __name__ == "__main__":
    main()
