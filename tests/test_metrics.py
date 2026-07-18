"""Tests for the fidelity metrics.

Run:
    python -m pytest tests/test_metrics.py
    python tests/test_metrics.py
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.metrics import (
    mse, psnr_from_mse, ssim, to_luminance, region_mask, region_row_span,
)

_RNG = np.random.default_rng(0)
_IMG = _RNG.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)


def test_identical_images():
    assert mse(_IMG, _IMG) == 0.0
    assert psnr_from_mse(mse(_IMG, _IMG)) == float("inf")
    assert ssim(_IMG, _IMG) == 1.0
    assert ssim(to_luminance(_IMG), to_luminance(_IMG)) == 1.0


def test_uniform_plus_one():
    cover = np.full((32, 32, 3), 100, dtype=np.uint8)
    stego = np.full((32, 32, 3), 101, dtype=np.uint8)
    m = mse(cover, stego)
    assert m == 1.0
    assert abs(psnr_from_mse(m) - 48.1308) < 1e-3     # 10*log10(255^2)


def test_mask_full_equals_global():
    stego = _IMG.copy()
    stego[0, 0, 0] = (int(_IMG[0, 0, 0]) + 7) % 256
    full = np.ones(_IMG.shape[:2], dtype=bool)
    assert mse(_IMG, stego, mask=full) == mse(_IMG, stego)


def test_region_mask_full_capacity():
    # 256x256, capacity 21760 chars -> touches every valid pixel except the
    # never-visited last column (x+2 >= width): 255 * 256 = 65280.
    mask = region_mask(256, 256, 21760)
    assert mask.sum() == 255 * 256
    top, bottom = region_row_span(mask)
    assert (top, bottom) == (0, 256)          # full row span at r=1.0


def test_region_mask_low_rate_is_top_band():
    mask = region_mask(256, 256, 1088)        # r=0.05
    top, bottom = region_row_span(mask)
    assert top == 0
    assert bottom - top >= 7                  # tall enough for SSIM win_size


if __name__ == "__main__":
    tests = [
        ("identical images", test_identical_images),
        ("uniform +1 -> mse 1, psnr 48.13", test_uniform_plus_one),
        ("mask full == global", test_mask_full_equals_global),
        ("region mask at full capacity", test_region_mask_full_capacity),
        ("region mask low rate is top band", test_region_mask_low_rate_is_top_band),
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
