"""Generate reference stego sets (LSB-R, LSB-M) payload-aligned to our algorithm.

Same 500 covers, seed 42, same embedding rates. For each (image, rate) we draw ONE
set of random positions + payload bits and feed it to BOTH LSB-R and LSB-M, so the
only difference between the two sets is replacement vs matching (a clean control).
The absolute payload equals what our algorithm embeds at that rate (payload.py).

HILL (adaptive) is NOT generated here: its Octave simulator (HILL_COLOR.m) is not
installed in the local Aletheia cache. See README / handoff for the pending decision.

Disk-aware: pass a single --rate so a driver can generate -> extract -> delete.

Run (from the repo root):
    python -m scripts.make_reference_sets --method lsbr --rate 0.05
    python -m scripts.make_reference_sets --method lsbm          # all rates
    python -m scripts.make_reference_sets --mapping-only          # write the r->bits CSV
"""
import argparse
import csv
import glob
import os
import subprocess

import numpy as np
from PIL import Image

from lib.rates import EMBEDDING_RATES
from reference import lsb_replacement, lsb_matching, payload

METHODS = ("lsbr", "lsbm", "hill")
BASE_SEED = 42
HILL_CACHE = os.path.abspath(os.path.join("aletheia", "aletheia-cache", "octave"))


def _payload(idx, rate, n_samples, width, height):
    """(positions, bits) drawn deterministically per (image, rate); shared by both methods."""
    nbits = payload.bits_for_rate(rate, width, height)
    rng = np.random.default_rng([BASE_SEED, idx, int(round(rate * 100))])
    positions = rng.permutation(n_samples)[:nbits]
    bits = rng.integers(0, 2, size=nbits, dtype=np.uint8)
    return positions, bits


def _embed(method, cover, positions, bits, idx, rate):
    if method == "lsbr":
        return lsb_replacement.embed(cover, bits, positions)
    # lsbm: extra seed only for the +/-1 direction, distinct per (image, rate)
    return lsb_matching.embed(cover, bits, positions,
                              seed=[BASE_SEED, idx, int(round(rate * 100)), 1])


def generate(method, covers_dir, out_root, rate, limit, octave=None):
    out_dir = os.path.join(out_root, method, f"r{rate}")
    os.makedirs(out_dir, exist_ok=True)
    if method == "hill":
        return _generate_hill(covers_dir, out_dir, rate, limit, octave)

    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))
    if limit:
        paths = paths[:limit]
    changed_total, bits_total = 0, 0
    for idx, path in enumerate(paths):
        dest = os.path.join(out_dir, os.path.basename(path))
        if os.path.exists(dest):
            continue
        cover = np.array(Image.open(path).convert("RGB"), dtype=np.uint8)
        h, w = cover.shape[:2]
        positions, bits = _payload(idx, rate, w * h * 3, w, h)
        stego = _embed(method, cover, positions, bits, idx, rate)
        changed_total += int(np.count_nonzero(cover != stego))
        bits_total += len(bits)
        Image.fromarray(stego, "RGB").save(dest)

    nbits = payload.bits_for_rate(rate)
    print(f"{method} r{rate}: {len(paths)} covers, {nbits} bits/img "
          f"(bpc {payload.bpc(rate):.4f}) -> {out_dir}  "
          f"[changed/embedded ~{changed_total / max(bits_total, 1):.2f}]")


def _generate_hill(covers_dir, out_dir, rate, limit, octave):
    """HILL (adaptive) via the original HILL_COLOR.m simulator, one Octave call per
    rate looping over all covers. payload = bpc so the absolute bits match our
    algorithm. Deterministic (seeded RNG); resumable (skips existing dests)."""
    if not octave:
        raise SystemExit("hill needs --octave <octave-cli>")
    p = payload.bpc(rate)
    cov = os.path.abspath(covers_dir).replace("\\", "/")
    out = os.path.abspath(out_dir).replace("\\", "/")
    cache = HILL_CACHE.replace("\\", "/")
    m = (
        f"addpath('{cache}');warning('off');pkg load image;pkg load signal;pkg load nan;"
        f"rand('twister',{BASE_SEED});randn('twister',{BASE_SEED});"
        f"files=glob('{cov}/*.png');"
        f"lim={int(limit)};if lim>0;files=files(1:min(lim,numel(files)));end;"
        "for i=1:numel(files);"
        "  [~,nm,ext]=fileparts(files{i});"
        f"  dst=fullfile('{out}',[nm ext]);"
        "  if exist(dst,'file');continue;end;"
        f"  X=HILL_COLOR(files{{i}},{p});"
        "  imwrite(uint8(X),dst);"
        "end;exit"
    )
    r = subprocess.run([octave, "-q", "--no-gui", "--eval", m],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[:800])
        raise SystemExit(f"hill r{rate}: octave failed (rc {r.returncode})")
    n = len(glob.glob(os.path.join(out_dir, "*.png")))
    print(f"hill r{rate}: {n} covers, {payload.bits_for_rate(rate)} bits/img "
          f"(bpc {p:.4f}) -> {out_dir}")


def write_mapping(out_csv):
    rows = payload.mapping_rows()
    os.makedirs(os.path.dirname(os.path.abspath(out_csv)), exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rate", "chars", "bits", "bpc", "bpp_pixel"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out_csv}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=METHODS, default=None)
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--out", default="data/alaska/stego")
    ap.add_argument("--rate", type=float, default=None, help="single rate; omit for all")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--octave", default=os.environ.get("OCTAVE_BIN"),
                    help="octave-cli path (required for --method hill)")
    ap.add_argument("--mapping-only", action="store_true",
                    help="only (re)write results/reference_payload_mapping.csv")
    args = ap.parse_args()

    write_mapping("results/reference_payload_mapping.csv")
    if args.mapping_only:
        return
    if not args.method:
        ap.error("--method is required unless --mapping-only")
    rates = [args.rate] if args.rate is not None else list(EMBEDDING_RATES)
    for rate in rates:
        generate(args.method, args.covers, args.out, rate, args.limit, args.octave)


if __name__ == "__main__":
    main()
