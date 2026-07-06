"""Convert the downloaded ALASKA v2 TIFF 256 COLOR carriers into lossless PNGs.

The source images are already native 256x256 RGB, so there is NO resize and NO
crop -- resampling would disturb the natural LSBs we care about. Each TIFF is
just re-encoded as a lossless PNG. Images that are not exactly 256x256x3 are
skipped and reported.

A manifest with a fixed 50/50 train/test split (seeded) is written for the later
ML steganalysis phase.

Run (from the repo root):
    python -m scripts.prepare_dataset --src data/alaska/raw_tif --out data/alaska/covers --seed 42
"""
import argparse
import csv
import glob
import os
import random

from PIL import Image

EXPECTED_SIZE = (256, 256)


def _iter_tifs(src):
    return sorted(glob.glob(os.path.join(src, "*.tif")))


def prepare(src, out, seed):
    os.makedirs(out, exist_ok=True)
    tifs = _iter_tifs(src)
    if not tifs:
        print(f"[error] no .tif files in {src}")
        return []

    kept, skipped = [], []
    for path in tifs:
        stem = os.path.splitext(os.path.basename(path))[0]
        dest = os.path.join(out, stem + ".png")

        with Image.open(path) as im:
            if im.mode != "RGB":
                im = im.convert("RGB")
            if im.size != EXPECTED_SIZE:
                skipped.append((stem, f"size {im.size} != {EXPECTED_SIZE}"))
                continue
            im.save(dest)                      # PNG = lossless, no resampling
        kept.append(stem + ".png")

    _write_manifest(out, kept, seed)

    print(f"found {len(tifs)} tif | converted {len(kept)} png | skipped {len(skipped)}")
    for stem, why in skipped:
        print(f"  [skip] {stem}: {why}")
    return kept


def _write_manifest(out, filenames, seed):
    """filename,split with a fixed, seeded 50/50 train/test split."""
    rng = random.Random(seed)
    ordered = sorted(filenames)
    rng.shuffle(ordered)
    half = len(ordered) // 2
    split = {name: ("train" if i < half else "test") for i, name in enumerate(ordered)}

    manifest = os.path.join(os.path.dirname(out.rstrip("/\\")), "manifest.csv")
    with open(manifest, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["filename", "split"])
        for name in sorted(filenames):
            w.writerow([name, split[name]])
    print(f"manifest: {manifest} ({half} train / {len(ordered) - half} test)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/alaska/raw_tif")
    ap.add_argument("--out", default="data/alaska/covers")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    prepare(args.src, args.out, args.seed)


if __name__ == "__main__":
    main()
