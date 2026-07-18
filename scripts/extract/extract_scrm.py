"""Extract SCRMQ1 (Spatial Color Rich Model, q=1) features via Octave.

Self-contained: it drives the DDE `SCRMQ1.m` (fetched into
aletheia/aletheia-cache/octave/) directly through Octave -- it does NOT import
Aletheia's Python (which would pull pandas/TensorFlow). One Octave process per
image; SCRM is slow, so this runs in the background, optionally with a few
parallel workers.

RESUMABLE + FAULT-TOLERANT: each image's features are cached to
<out>_cache/<stem>.npy as soon as they are computed, so a crash or transient
Octave glitch never loses completed work -- just re-run and it continues. A
failed image is retried a few times; if it still fails it is reported (not fatal),
and re-running fills the gap. The final <out>.npy + <out>.files are assembled
from the cache in filename order.

Octave binary: set --octave or the OCTAVE_BIN env var to the portable
octave-cli.exe (this machine has no Octave on PATH).

Run (from the repo root):
    python -m scripts.extract.extract_scrm --images data/alaska/covers --out data/alaska/features/covers \
        --octave "C:/.../octave-cli.exe" --workers 4
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np
from scipy.io import loadmat

SCRM_DIR = os.path.abspath(os.path.join("aletheia", "aletheia-cache", "octave"))
RETRIES = 3


def _octave_bin(arg):
    return arg or os.environ.get("OCTAVE_BIN", "octave-cli")


def _fwd(p):
    return os.path.abspath(p).replace("\\", "/")


def extract_one(octave, img_path):
    """Extract one image's SCRM vector, retrying transient Octave failures."""
    last_err = ""
    for _ in range(RETRIES):
        tmp = tempfile.mkdtemp()
        try:
            out = _fwd(os.path.join(tmp, "data.mat"))
            m = (
                f"addpath('{SCRM_DIR.replace(chr(92), '/')}');warning('off');"
                "pkg load image;pkg load signal;pkg load nan;"
                f"data=SCRMQ1('{_fwd(img_path)}');"
                f"save('-mat7-binary','{out}','data');exit"
            )
            r = subprocess.run([octave, "-q", "--no-gui", "--eval", m],
                               capture_output=True, text=True)
            if os.path.exists(out):
                data = loadmat(out)
                X = np.array([], dtype=np.float64)
                for submodel in data["data"][0][0]:
                    X = np.hstack((X, submodel.reshape(submodel.shape[1])))
                return X.astype(np.float32)
            last_err = (r.stderr or "")[-400:]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    raise RuntimeError(f"octave failed after {RETRIES} tries: {last_err}")


def _worker(args):
    """Return (basename, ok, err). Caches on success; never raises."""
    octave, img_path, cache_path = args
    if os.path.exists(cache_path):
        return os.path.basename(img_path), True, ""
    try:
        np.save(cache_path, extract_one(octave, img_path))
        return os.path.basename(img_path), True, ""
    except Exception as e:                       # noqa: BLE001 -- report, don't crash the pool
        return os.path.basename(img_path), False, str(e)[:200]


def run(octave, images_dir, out, limit, workers):
    paths = sorted(glob.glob(os.path.join(images_dir, "*.png")))
    if limit:
        paths = paths[:limit]
    if not paths:
        print(f"[error] no PNGs in {images_dir}")
        sys.exit(1)

    out = os.path.abspath(out)
    cache_dir = out + "_cache"
    os.makedirs(cache_dir, exist_ok=True)
    tasks = [
        (octave, p, os.path.join(cache_dir, os.path.splitext(os.path.basename(p))[0] + ".npy"))
        for p in paths
    ]

    ok = 0
    failed = []

    def note(i, name, good, err):
        nonlocal ok
        ok += good
        if not good:
            failed.append((name, err))
        if i == 1 or i % 25 == 0 or i == len(paths):
            print(f"  {i}/{len(paths)}  ok={ok} failed={len(failed)}", flush=True)

    if workers > 1:
        with Pool(workers) as pool:
            for i, (name, good, err) in enumerate(pool.imap(_worker, tasks), 1):
                note(i, name, good, err)
    else:
        for i, t in enumerate(tasks, 1):
            note(i, *_worker(t))

    # assemble from cache in filename order (only images that succeeded)
    feats, used = [], []
    for _, p, cache_path in tasks:
        if os.path.exists(cache_path):
            feats.append(np.load(cache_path))
            used.append(os.path.basename(p))
    matrix = np.vstack(feats)
    np.save(out + ".npy", matrix)
    with open(out + ".files", "w") as f:
        f.write("\n".join(used))
    print(f"saved {matrix.shape} -> {out}.npy  ({len(used)}/{len(paths)} images)")
    if failed:
        print(f"[warn] {len(failed)} failed (re-run to retry): {[n for n, _ in failed][:10]}")
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True, help="output stem (no extension)")
    ap.add_argument("--octave", default=None, help="octave-cli path (or OCTAVE_BIN env)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1, help="parallel Octave processes")
    args = ap.parse_args()
    run(_octave_bin(args.octave), args.images, args.out, args.limit, args.workers)


if __name__ == "__main__":
    main()
