"""Round-trip tests for the baseline algorithm (Day 1).

Run:
    python -m pytest tests/            # if pytest is installed
    python tests/test_baseline_roundtrip.py   # without pytest (standalone)

The KNOWN limitations of the baseline are recorded as passing tests so they
stay visible until we address them in the improvement phase.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baseline.stego import hide_message, expose_message
from baseline.image_utils import load_image
from baseline.crypto import generate_key

COVERS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "covers")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "_test_stego.png")


def _roundtrip(cover_name, message):
    key = generate_key()
    cover = os.path.join(COVERS, cover_name)
    hidden = hide_message(message=message, key=key, cover_path=cover, out_path=OUT)
    assert hidden is not False, "message too large for cover"
    stego = load_image(OUT)
    return expose_message(hidden_message=stego, key=key)


def test_roundtrip_ascii_gradient():
    msg = "Hello!"
    assert _roundtrip("cover_gradient.png", msg) == msg


def test_roundtrip_ascii_noise():
    msg = "Master's thesis 2026 - test 123!"
    assert _roundtrip("cover_noise.png", msg) == msg


def test_known_limitation_non_ascii():
    """KNOWN: characters with ord>255 (accented letters, em-dash, ...) break the
    8-bit/char assumption. Stays a documented limitation until Improvement 3
    (length header + correctness)."""
    msg = "č"  # 'c with caron' (ord 269 > 255)
    assert _roundtrip("cover_gradient.png", msg) != msg  # baseline does NOT survive non-ASCII


def test_known_limitation_saturated_255():
    """KNOWN: a fully saturated (255) cover -> the algorithm skips channels, so
    nothing is embedded. Stays a documented limitation until Improvement 3
    (255 edge-case fix)."""
    msg = "Hi"
    assert _roundtrip("cover_saturated.png", msg) != msg


if __name__ == "__main__":
    tests = [
        ("ascii/gradient round-trip", test_roundtrip_ascii_gradient),
        ("ascii/noise round-trip", test_roundtrip_ascii_noise),
        ("known-limit: non-ASCII dropped", test_known_limitation_non_ascii),
        ("known-limit: 255 saturation dropped", test_known_limitation_saturated_255),
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
