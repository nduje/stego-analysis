"""Verify the prepared ALASKA covers and report the known 255-saturation finding.

Read-only: this script never modifies the dataset. It samples prepared PNG covers
and reports
  * capacity (asserted 21760 chars for 256x256),
  * ASCII round-trip pass rate through the lib pipeline (passphrase key),
  * how 255-saturated channels in the used embedding region correlate with
    round-trip corruption (the documented "255 bug").

Run (from the repo root):
    python -m scripts.data.verify_dataset --covers data/alaska/covers --n 20 --seed 42
"""
import argparse
import glob
import os
import random

import numpy as np

from lib.algorithm import StegAlgorithm, load_image
from lib.config import StegoConfig
from lib.embedding import _iter_blocks, _DATA_CHANNELS, capacity_blocks

TEST_MESSAGE = "Steganalysis test 2026 - the quick brown fox jumps."
PASSPHRASE = "verify-pass"


def _region_has_255(img, char_count):
    """True if any data channel in the first `char_count` blocks equals 255."""
    w, h = img.size
    blocks = _iter_blocks(w, h, StegoConfig())
    for _ in range(char_count):
        x, y = next(blocks)
        pixels = [img.getpixel((x + i, y)) for i in range(3)]
        for ch in range(_DATA_CHANNELS):
            pi, ci = divmod(ch, 3)
            if pixels[pi][ci] == 255:
                return True
    return False


def verify(covers_dir, n, seed):
    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))
    if not paths:
        print(f"[error] no PNG covers in {covers_dir} -- run prepare_dataset first")
        return
    sample = random.Random(seed).sample(paths, min(n, len(paths)))

    alg = StegAlgorithm()
    char_count = len(TEST_MESSAGE)

    # capacity check on the first cover
    w, h = load_image(sample[0]).size
    cap = capacity_blocks(w, h)
    assert cap == (256 // 3) * 256 == 21760, f"unexpected capacity {cap} for {w}x{h}"

    ok = fail = 0
    any255 = region255 = fail_with_region255 = 0

    os.makedirs("results/_scratch", exist_ok=True)
    for path in sample:
        img = load_image(path)
        any255 += int((np.array(img) == 255).any())
        has_region = _region_has_255(img, char_count)
        region255 += int(has_region)

        alg.hide(TEST_MESSAGE, path, "results/_scratch/_verify_stego.png", passphrase=PASSPHRASE)
        recovered = alg.expose(load_image("results/_scratch/_verify_stego.png"), passphrase=PASSPHRASE)
        passed = (recovered == TEST_MESSAGE)
        ok += int(passed)
        fail += int(not passed)
        if not passed and has_region:
            fail_with_region255 += 1

    n = len(sample)
    print(f"covers dir     : {covers_dir}")
    print(f"sampled        : {n} (seed {seed})")
    print(f"image size     : {w}x{h}  ->  capacity {cap} chars  [OK]")
    print(f"test message   : {char_count} ASCII chars")
    print("-" * 52)
    print(f"round-trip OK  : {ok}/{n}   ({100*ok/n:.0f}%)")
    print(f"round-trip FAIL: {fail}/{n}")
    print(f"any 255 pixel  : {any255}/{n} images")
    print(f"255 in region  : {region255}/{n} images (used by a {char_count}-char msg)")
    print(f"fails w/ 255-in-region: {fail_with_region255}/{fail if fail else '-'}"
          f"  <- confirms the saturation-skip mechanism")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    verify(args.covers, args.n, args.seed)


if __name__ == "__main__":
    main()
