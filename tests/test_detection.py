"""Tests for the detection harness and the chi-square detector (Day 6).

Run:
    python -m pytest tests/test_detection.py
    python tests/test_detection.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.detection import auc, p_error, evaluate, roc_points
from analysis.chi_square import global_chisquare, positional_chisquare


# ---- harness ----

def test_perfect_separation():
    cover = [0.1, 0.2, 0.3, 0.15]
    stego = [0.7, 0.8, 0.9, 0.75]
    assert auc(cover, stego) == 1.0
    pe, _ = p_error(cover, stego)
    assert pe == 0.0


def test_reversed_separation():
    cover = [0.7, 0.8, 0.9]
    stego = [0.1, 0.2, 0.3]
    assert auc(cover, stego) == 0.0            # AUC stays orientation-sensitive
    pe, _ = p_error(cover, stego)              # P_E is orientation-agnostic
    assert pe == 0.0                           # perfectly separable, just inverted


def test_identical_distributions():
    vals = [0.2, 0.4, 0.6, 0.8]
    assert auc(vals, vals) == 0.5              # tie-averaged
    pe, _ = p_error(vals, vals)
    assert abs(pe - 0.5) < 1e-9


def test_roc_monotone_and_bounds():
    fpr, tpr = roc_points([0.1, 0.2, 0.3], [0.6, 0.7, 0.8])
    assert fpr[0] == 0.0 and tpr[0] == 0.0
    assert abs(fpr[-1] - 1.0) < 1e-9 and abs(tpr[-1] - 1.0) < 1e-9
    assert np.all(np.diff(fpr) >= -1e-12) and np.all(np.diff(tpr) >= -1e-12)


# ---- chi-square ----

def _rgb(gray2d):
    return np.stack([gray2d] * 3, axis=2).astype(np.uint8)


def test_chi2_cover_like_low_score():
    # every used value is even -> each pair maximally unequal -> low p_embed
    arr = _rgb(np.full((64, 64), 40, dtype=np.uint8))
    assert global_chisquare(arr)["comb"] < 0.01


def test_chi2_equalized_pairs_high_score():
    # half the pixels value 40, half value 41 -> the pair {40,41} is equal
    flat = np.array([40, 41] * (64 * 32), dtype=np.uint8).reshape(64, 64)
    assert global_chisquare(_rgb(flat))["comb"] > 0.99


def test_positional_cliff_direction():
    # top half: equalized pair {40,41}; bottom half: all-even 40 (unequal)
    top = np.array([40, 41] * (128 * 128), dtype=np.uint8).reshape(128, 256)
    bottom = np.full((128, 256), 40, dtype=np.uint8)
    img = _rgb(np.vstack([top, bottom]))
    curve = positional_chisquare(img, n_points=50)
    early = curve[len(curve) // 4][1]          # ~25% in, still in equalized top
    late = curve[-1][1]                        # whole image, dragged down
    assert early > late


if __name__ == "__main__":
    tests = [
        ("perfect separation -> AUC 1, PE 0", test_perfect_separation),
        ("reversed -> AUC 0", test_reversed_separation),
        ("identical -> AUC 0.5", test_identical_distributions),
        ("ROC monotone + bounds", test_roc_monotone_and_bounds),
        ("chi2 cover-like -> low score", test_chi2_cover_like_low_score),
        ("chi2 equalized pairs -> high score", test_chi2_equalized_pairs_high_score),
        ("positional cliff direction", test_positional_cliff_direction),
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
