"""Tests for Improvement 2: edge-safe +/-1 matching (pm_one).

Only the data-channel matching and the flag's edge-safety change. We check pm_one's
own round-trip (incl. the now-fixed saturated case), that decode is direction-agnostic
(parity only), that imperceptibility is unchanged (<=1 change/channel), determinism,
and that it differs from the baseline -- while sequential+plus_one parity stays green.

Run:
    python -m pytest tests/test_pm_one.py
    python tests/test_pm_one.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import StegAlgorithm, StegoConfig
from lib.algorithm import load_image
from lib.crypto import generate_key
from lib.embedding import _match_pm_one

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERS = os.path.join(ROOT, "data", "covers")
OUT = os.path.join(ROOT, "results", "_test_pm_one.png")
PM = StegoConfig(matching_mode="pm_one")


def _roundtrip(cover, msg, key, cfg=PM):
    alg = StegAlgorithm(cfg)
    hidden = alg.hide(message=msg, key=key, cover_path=os.path.join(COVERS, cover), out_path=OUT)
    assert hidden is not False, "message too large"
    return alg.expose(stego_image=load_image(OUT), key=key)


def test_pm_one_roundtrip_various():
    key = generate_key()
    for msg in ["Hi", "Hello!", "pm_one 2026 - test 123!", "z" * 50]:
        assert _roundtrip("cover_noise.png", msg, key) == msg


def test_pm_one_roundtrip_saturated():
    # the baseline FAILS here (255-skip loses data); pm_one FIXES it (255-bug gone)
    assert _roundtrip("cover_saturated.png", "Hi", generate_key()) == "Hi"


def test_pm_one_direction_agnostic_parity():
    # both +1 and -1 yield the target parity -> decode (parity only) ignores direction
    for v in range(1, 255):
        for bit in (0, 1):
            if v % 2 != bit:
                assert _match_pm_one(v, bit, +1) % 2 == bit
                assert _match_pm_one(v, bit, -1) % 2 == bit


def test_pm_one_edges():
    assert _match_pm_one(0, 1, -1) == 1        # 0 can't go -1
    assert _match_pm_one(255, 0, +1) == 254    # 255 can't go +1


def test_pm_one_at_most_one_change_per_channel():
    # imperceptibility unchanged: still +/-1 per channel -> |stego-cover| <= 1
    key = generate_key()
    cover = os.path.join(COVERS, "cover_noise.png")
    StegAlgorithm(PM).hide(message="imperceptibility check 123", key=key, cover_path=cover, out_path=OUT)
    c = np.asarray(load_image(cover), dtype=int)
    s = np.asarray(load_image(OUT), dtype=int)
    assert np.abs(s - c).max() <= 1


def test_pm_one_deterministic_and_differs_from_baseline():
    key, msg = generate_key(), "determinism check"
    cover = os.path.join(COVERS, "cover_noise.png")
    StegAlgorithm(PM).hide(message=msg, key=key, cover_path=cover, out_path=OUT)
    with open(OUT, "rb") as f:
        a = f.read()
    StegAlgorithm(PM).hide(message=msg, key=key, cover_path=cover, out_path=OUT)
    with open(OUT, "rb") as f:
        b = f.read()
    assert a == b                                      # same key -> same stego
    StegAlgorithm(StegoConfig()).hide(message=msg, key=key, cover_path=cover, out_path=OUT)
    with open(OUT, "rb") as f:
        base = f.read()
    assert a != base                                   # pm_one != baseline (plus_one)


def test_prng_plus_pm_one_roundtrip():
    cfg = StegoConfig(pixel_order="prng", matching_mode="pm_one")
    assert _roundtrip("cover_noise.png", "combined prng + pm_one!", generate_key(), cfg) == "combined prng + pm_one!"


if __name__ == "__main__":
    tests = [
        ("pm_one round-trip (various)", test_pm_one_roundtrip_various),
        ("pm_one round-trip on saturated (255-fix)", test_pm_one_roundtrip_saturated),
        ("decode direction-agnostic (parity)", test_pm_one_direction_agnostic_parity),
        ("edge values 0/255", test_pm_one_edges),
        ("<=1 change per channel (imperceptibility)", test_pm_one_at_most_one_change_per_channel),
        ("deterministic + differs from baseline", test_pm_one_deterministic_and_differs_from_baseline),
        ("prng + pm_one round-trip", test_prng_plus_pm_one_roundtrip),
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
