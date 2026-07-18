"""PARITY: lib (default config) must reproduce the frozen baseline byte-for-byte.

This is the central proof that the parameterization refactor changed no behavior:
  1. embedding-layer parity  -- same char matrix, no crypto, compare stego PNGs
  2. full-pipeline parity     -- same fixed key + message, compare stego PNGs
on all three covers. If either differs by a single byte, the refactor broke.

Run:
    python -m pytest tests/test_lib_parity.py
    python tests/test_lib_parity.py
"""
import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baseline import image_utils as base_img
from baseline import stego as base_stego
from lib import embedding as lib_embed
from lib.algorithm import StegAlgorithm, load_image
from lib import message as msg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERS = os.path.join(ROOT, "data", "covers")
OUTDIR = os.path.join(ROOT, "results", "_scratch")
os.makedirs(OUTDIR, exist_ok=True)
COVER_NAMES = ["cover_gradient.png", "cover_noise.png", "cover_saturated.png"]

# Deterministic key so the AES-CTR ciphertext (and thus the embedding) is fixed.
FIXED_KEY = base64.b64encode(bytes(range(32))).decode()


def _read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def _parity_embedding(cover_name):
    """Same char matrix through both encoders; compare saved PNG bytes."""
    matrix, count = msg.split_into_chars(msg.text_to_bitstring("Parity check 42!"))
    cover = os.path.join(COVERS, cover_name)

    base_out = os.path.join(OUTDIR, "_parity_base.png")
    lib_out = os.path.join(OUTDIR, "_parity_lib.png")

    base_img.encode_message(matrix, base_img.load_image(cover), count, out_path=base_out)
    stego = lib_embed.embed(matrix, load_image(cover), count)
    stego.save(lib_out)

    return _read_bytes(base_out) == _read_bytes(lib_out)


def _parity_pipeline(cover_name):
    """Full hide() with a fixed key; compare saved PNG bytes."""
    message = "Byte-identical?"
    cover = os.path.join(COVERS, cover_name)

    base_out = os.path.join(OUTDIR, "_pipe_base.png")
    lib_out = os.path.join(OUTDIR, "_pipe_lib.png")

    base_stego.hide_message(message=message, key=FIXED_KEY, cover_path=cover, out_path=base_out)
    StegAlgorithm().hide(message=message, key=FIXED_KEY, cover_path=cover, out_path=lib_out)

    return _read_bytes(base_out) == _read_bytes(lib_out)


def test_embedding_parity_all_covers():
    for name in COVER_NAMES:
        assert _parity_embedding(name), f"embedding parity broke on {name}"


def test_pipeline_parity_all_covers():
    for name in COVER_NAMES:
        assert _parity_pipeline(name), f"pipeline parity broke on {name}"


if __name__ == "__main__":
    tests = []
    for name in COVER_NAMES:
        tests.append((f"embedding parity: {name}", lambda n=name: _parity_embedding(n)))
    for name in COVER_NAMES:
        tests.append((f"pipeline  parity: {name}", lambda n=name: _parity_pipeline(n)))

    failed = 0
    for label, fn in tests:
        ok = fn()
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        failed += 0 if ok else 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
