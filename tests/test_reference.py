"""Sanity tests for the reference LSB methods (LSB-R, LSB-M).

Not a round-trip test (we never decode reference stego -- we only steganalyze it).
We check the embedding invariants: |delta| <= 1, no value leaves [0, 255], the
number of changed samples is about half the payload (a random bit matches the LSB
half the time), LSB-R keeps values inside their {2k, 2k+1} pair, and LSB-M flips
the LSB on every changed sample.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reference import lsb_replacement, lsb_matching, payload


def _cover(seed=0):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(256, 256, 3), dtype=np.uint8)


def _draw(cover, rate=0.5):
    h, w = cover.shape[:2]
    nbits = payload.bits_for_rate(rate, w, h)
    rng = np.random.default_rng(123)
    positions = rng.permutation(w * h * 3)[:nbits]
    bits = rng.integers(0, 2, size=nbits, dtype=np.uint8)
    return positions, bits


def test_lsbr_invariants():
    cover = _cover()
    positions, bits = _draw(cover)
    stego = lsb_replacement.embed(cover, bits, positions)
    d = stego.astype(int) - cover.astype(int)
    assert np.abs(d).max() <= 1
    assert stego.min() >= 0 and stego.max() <= 255
    # embedded LSBs must equal the payload bits
    flat = stego.reshape(-1)
    assert np.array_equal(flat[positions] & 1, bits)
    # value stays within its {2k, 2k+1} pair
    assert np.array_equal(cover.reshape(-1)[positions] >> 1, flat[positions] >> 1)
    # untouched samples are unchanged
    mask = np.ones(flat.size, dtype=bool)
    mask[positions] = False
    assert np.array_equal(flat[mask], cover.reshape(-1)[mask])
    print("lsbr invariants OK")


def test_lsbm_invariants():
    cover = _cover(1)
    positions, bits = _draw(cover)
    stego = lsb_matching.embed(cover, bits, positions, seed=7)
    d = stego.astype(int) - cover.astype(int)
    assert np.abs(d).max() <= 1
    assert stego.min() >= 0 and stego.max() <= 255
    flat = stego.reshape(-1)
    # every selected sample now carries the right LSB
    assert np.array_equal(flat[positions] & 1, bits)
    # changes only where the LSB had to flip; magnitude exactly 1 there
    cflat = cover.reshape(-1)
    changed = flat[positions] != cflat[positions]
    assert np.array_equal(changed, (cflat[positions] & 1) != bits)
    assert np.all(np.abs(flat[positions][changed].astype(int)
                         - cflat[positions][changed].astype(int)) == 1)
    print("lsbm invariants OK")


def test_change_rate_about_half():
    cover = _cover(2)
    positions, bits = _draw(cover, rate=1.0)
    for name, stego in (("lsbr", lsb_replacement.embed(cover, bits, positions)),
                        ("lsbm", lsb_matching.embed(cover, bits, positions, seed=3))):
        flat = stego.reshape(-1)
        cflat = cover.reshape(-1)
        frac = np.mean(flat[positions] != cflat[positions])
        assert 0.45 < frac < 0.55, f"{name} change fraction {frac}"
    print("change-rate ~0.5 OK")


def test_edges_stay_in_range():
    # a cover made only of 0 and 255 stresses the edge handling
    cover = np.zeros((6, 6, 3), dtype=np.uint8)
    cover[..., 0] = 255
    positions = np.arange(cover.size)
    bits = np.ones(cover.size, dtype=np.uint8)   # force a flip on every 0 and 255
    for stego in (lsb_replacement.embed(cover, bits, positions),
                  lsb_matching.embed(cover, bits, positions, seed=5)):
        assert stego.min() >= 0 and stego.max() <= 255
    print("edge range OK")


if __name__ == "__main__":
    test_lsbr_invariants()
    test_lsbm_invariants()
    test_change_rate_about_half()
    test_edges_stay_in_range()
    print("all reference tests passed")
