"""Tests for Improvement 3: length header (replaces the continuation flag).

The 16-bit char count is prepended to the plaintext BEFORE AES (so it is whitened),
and the 9th channel (the old flag) is left untouched. This checks length_header's
round-trip, the full P1+P2+P3 "after" algorithm, the freed 9th channel, and
capacity accept/reject -- while the baseline flag path stays green (parity).

Run:
    python -m pytest tests/test_length_header.py
    python tests/test_length_header.py
"""
import os
import sys
import tempfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import StegAlgorithm, StegoConfig
from lib.algorithm import load_image
from lib.crypto import generate_key
from lib.embedding import _ordered_blocks

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERS = os.path.join(ROOT, "data", "covers")
OUT = os.path.join(ROOT, "results", "_scratch", "_test_lh.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

LH = StegoConfig(termination="length_header")
AFTER = StegoConfig(pixel_order="prng", matching_mode="pm_one", termination="length_header")


def _roundtrip(cover, msg, key, cfg=LH):
    alg = StegAlgorithm(cfg)
    hidden = alg.hide(message=msg, key=key, cover_path=os.path.join(COVERS, cover), out_path=OUT)
    assert hidden is not False, "message too large"
    return alg.expose(stego_image=load_image(OUT), key=key)


def test_length_header_roundtrip_various():
    key = generate_key()
    for msg in ["A", "Hi", "length header 2026 - test!", "q" * 80]:
        assert _roundtrip("cover_noise.png", msg, key) == msg


def test_after_algorithm_p1_p2_p3():
    # the full "after" algorithm: prng order + pm_one matching + length header
    key = generate_key()
    for msg in ["x", "final after algorithm!", "m" * 60]:
        assert _roundtrip("cover_noise.png", msg, key, AFTER) == msg


def test_after_algorithm_saturated():
    # pm_one fixes 255; length header must also round-trip on a saturated cover
    assert _roundtrip("cover_saturated.png", "Hi", generate_key(), AFTER) == "Hi"


def test_ninth_channel_untouched():
    # length_header must NOT write the 9th channel (pixel-2 blue) -> flag trace gone
    key = generate_key()
    cover_path = os.path.join(COVERS, "cover_gradient.png")
    cover = load_image(cover_path)
    msg = "flag freed"
    StegAlgorithm(LH).hide(message=msg, key=key, cover_path=cover_path, out_path=OUT)
    stego = load_image(OUT)
    w, h = cover.size
    for x, y in _ordered_blocks(w, h, LH, None)[: 2 + len(msg)]:
        assert cover.getpixel((x + 2, y))[2] == stego.getpixel((x + 2, y))[2]


def test_capacity_accept_and_reject():
    key = generate_key()
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "tiny.png")
        Image.new("RGB", (12, 4), (100, 110, 120)).save(p)   # capacity = (12//3)*4 = 16 chars
        alg = StegAlgorithm(LH)
        assert alg.hide(message="x" * 14, cover_path=p, out_path=OUT, key=key) is not False   # 2+14=16
        assert alg.hide(message="x" * 15, cover_path=p, out_path=OUT, key=key) is False        # 2+15>16


if __name__ == "__main__":
    tests = [
        ("length_header round-trip (various)", test_length_header_roundtrip_various),
        ("P1+P2+P3 'after' algorithm round-trip", test_after_algorithm_p1_p2_p3),
        ("'after' round-trip on saturated", test_after_algorithm_saturated),
        ("9th channel untouched (flag gone)", test_ninth_channel_untouched),
        ("capacity accept / reject", test_capacity_accept_and_reject),
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
