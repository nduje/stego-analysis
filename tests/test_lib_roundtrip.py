"""Round-trip tests for lib (default config).

Mirrors the baseline round-trip suite: with the default config, lib must behave
exactly like the baseline -- ASCII survives, and the two known limitations
(non-ASCII, saturated-255) are still limitations, recorded here as passing tests.

Run:
    python -m pytest tests/test_lib_roundtrip.py
    python tests/test_lib_roundtrip.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.algorithm import StegAlgorithm, load_image
from lib.crypto import generate_key

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERS = os.path.join(ROOT, "data", "covers")
OUT = os.path.join(ROOT, "results", "_test_lib_stego.png")


def _roundtrip(cover_name, message):
    alg = StegAlgorithm()
    key = generate_key()
    cover = os.path.join(COVERS, cover_name)
    hidden = alg.hide(message=message, key=key, cover_path=cover, out_path=OUT)
    assert hidden is not False, "message too large for cover"
    stego = load_image(OUT)
    return alg.expose(stego_image=stego, key=key)


def _roundtrip_passphrase(cover_name, message, passphrase):
    alg = StegAlgorithm()
    cover = os.path.join(COVERS, cover_name)
    hidden = alg.hide(message=message, cover_path=cover, out_path=OUT, passphrase=passphrase)
    assert hidden is not False, "message too large for cover"
    stego = load_image(OUT)
    return alg.expose(stego_image=stego, passphrase=passphrase)


def test_roundtrip_ascii_gradient():
    msg = "Hello!"
    assert _roundtrip("cover_gradient.png", msg) == msg


def test_roundtrip_ascii_noise():
    msg = "Master's thesis 2026 - test 123!"
    assert _roundtrip("cover_noise.png", msg) == msg


def test_known_limitation_non_ascii():
    """Same limitation as baseline: ord>255 breaks the 8-bit/char assumption."""
    msg = "č"
    assert _roundtrip("cover_gradient.png", msg) != msg


def test_known_limitation_saturated_255():
    """Same limitation as baseline: a fully saturated cover embeds nothing."""
    msg = "Hi"
    assert _roundtrip("cover_saturated.png", msg) != msg


def test_roundtrip_passphrase():
    """End-to-end via the passphrase path (scrypt -> HKDF -> k_enc)."""
    msg = "Passphrase path 2026!"
    assert _roundtrip_passphrase("cover_noise.png", msg, "correct horse battery") == msg


def test_dual_input_requires_exactly_one():
    """Providing both or neither of passphrase/key must raise ValueError."""
    alg = StegAlgorithm()
    cover = os.path.join(COVERS, "cover_noise.png")
    for kwargs in ({}, {"passphrase": "x", "key": generate_key()}):
        try:
            alg.hide(message="hi", cover_path=cover, out_path=OUT, **kwargs)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for hide(**{kwargs})")


if __name__ == "__main__":
    tests = [
        ("ascii/gradient round-trip", test_roundtrip_ascii_gradient),
        ("ascii/noise round-trip", test_roundtrip_ascii_noise),
        ("known-limit: non-ASCII dropped", test_known_limitation_non_ascii),
        ("known-limit: 255 saturation dropped", test_known_limitation_saturated_255),
        ("passphrase round-trip", test_roundtrip_passphrase),
        ("dual input requires exactly one", test_dual_input_requires_exactly_one),
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
