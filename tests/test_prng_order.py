"""Tests for Improvement 1: PRNG (key-seeded) block order.

Only the visiting ORDER changes vs the baseline. We do NOT test prng against the
baseline (parity is intentionally lost -- that's the behavior change); instead we
check prng's own round-trip, determinism, seed-sensitivity, and that it really
differs from sequential -- while confirming sequential parity is untouched.

Run:
    python -m pytest tests/test_prng_order.py
    python tests/test_prng_order.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import StegAlgorithm, StegoConfig
from lib.algorithm import load_image
from lib.crypto import generate_key
from lib.embedding import _ordered_blocks, capacity_blocks
from lib.config import StegoConfig as Cfg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERS = os.path.join(ROOT, "data", "covers")
OUT = os.path.join(ROOT, "results", "_test_prng.png")

PRNG = StegoConfig(pixel_order="prng")


def _roundtrip(cover, message, key):
    alg = StegAlgorithm(PRNG)
    hidden = alg.hide(message=message, key=key, cover_path=os.path.join(COVERS, cover), out_path=OUT)
    assert hidden is not False, "message too large"
    return alg.expose(stego_image=load_image(OUT), key=key)


def test_prng_roundtrip_various():
    key = generate_key()
    for msg in ["Hi", "Hello!", "PRNG order 2026 - test 123!", "x" * 60]:
        assert _roundtrip("cover_noise.png", msg, key) == msg


def test_same_seed_same_permutation():
    seed = b"\x11" * 32
    a = _ordered_blocks(256, 256, PRNG, seed)
    b = _ordered_blocks(256, 256, PRNG, seed)
    assert a == b


def test_different_seed_different_permutation():
    a = _ordered_blocks(256, 256, PRNG, b"\x11" * 32)
    b = _ordered_blocks(256, 256, PRNG, b"\x22" * 32)
    assert a != b


def test_wrong_key_fails_to_decode():
    # different key -> different seed -> different permutation -> wrong plaintext
    msg = "secret message here"
    good = generate_key()
    bad = generate_key()
    alg = StegAlgorithm(PRNG)
    alg.hide(message=msg, key=good, cover_path=os.path.join(COVERS, "cover_noise.png"), out_path=OUT)
    recovered = alg.expose(stego_image=load_image(OUT), key=bad)
    assert recovered != msg


def test_prng_differs_from_sequential():
    seq = _ordered_blocks(256, 256, Cfg(), None)                 # sequential (raster)
    prng = _ordered_blocks(256, 256, PRNG, b"\x33" * 32)
    assert len(seq) == len(prng) == capacity_blocks(256, 256)
    assert set(seq) == set(prng)                                 # same blocks...
    assert seq != prng                                          # ...different order


def test_prng_requires_seed():
    try:
        _ordered_blocks(256, 256, PRNG, None)
    except ValueError:
        return
    raise AssertionError("prng order should require a seed")


if __name__ == "__main__":
    tests = [
        ("prng round-trip (various messages)", test_prng_roundtrip_various),
        ("same seed -> same permutation", test_same_seed_same_permutation),
        ("different seed -> different permutation", test_different_seed_different_permutation),
        ("wrong key fails to decode", test_wrong_key_fails_to_decode),
        ("prng differs from sequential", test_prng_differs_from_sequential),
        ("prng requires a seed", test_prng_requires_seed),
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
