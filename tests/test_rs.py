"""Tests for RS (Regular/Singular) analysis.

Validates the estimator on textbook LSB replacement (what RS is built for):
clean cover -> p_hat ~ 0; fully LSB-randomized -> p_hat ~ 1. The baseline's "+1"
bias is a measured finding, characterized in the sweep, not asserted here.

Run:
    python -m pytest tests/test_rs.py
    python tests/test_rs.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.rs_analysis import rs_counts, estimate_rate, analyze_image


def _natural_channel(h=256, w=256, seed=0):
    """Smooth base with mild noise -> natural-like LSBs (cover)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    base = (0.5 * xx + 0.5 * yy) * (200.0 / (h + w))      # smooth ramp ~0..100
    base = base + rng.normal(0, 3, size=(h, w))           # mild gaussian texture
    return np.clip(base, 0, 255).astype(np.uint8)


def _lsb_randomize(channel, seed=1):
    """Textbook LSB replacement over ALL pixels (rate ~1)."""
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=channel.shape).astype(np.uint8)
    return ((channel.astype(np.int64) & ~1) | bits).astype(np.uint8)


def test_clean_cover_low_estimate():
    ch = _natural_channel()
    assert abs(estimate_rate(ch)) < 0.15


def test_full_lsb_high_estimate():
    ch = _natural_channel()
    stego = _lsb_randomize(ch)
    assert estimate_rate(stego) > 0.8


def test_rs_counts_cover_symmetry():
    ch = _natural_channel()
    RM, SM, RmM, SmM = rs_counts(ch)
    assert RM > SM                       # regular dominates on a cover
    assert abs(RM - RmM) < 0.1           # RS null hypothesis: M and -M agree
    assert abs(SM - SmM) < 0.1


def test_analyze_image_keys():
    img = np.stack([_natural_channel(seed=s) for s in (1, 2, 3)], axis=2)
    out = analyze_image(img)
    assert set(out) == {"comb", "r", "g", "b"}
    assert abs(out["comb"] - (out["r"] + out["g"] + out["b"]) / 3.0) < 1e-9


if __name__ == "__main__":
    tests = [
        ("clean cover -> p_hat ~ 0", test_clean_cover_low_estimate),
        ("full LSB -> p_hat ~ 1", test_full_lsb_high_estimate),
        ("RS counts cover symmetry", test_rs_counts_cover_symmetry),
        ("analyze_image keys/combine", test_analyze_image_keys),
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
