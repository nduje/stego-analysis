"""SPA (Sample Pair Analysis) -- Dumitrescu, Wu & Wang.

Reference: S. Dumitrescu, X. Wu, Z. Wang, "Detection of LSB steganography via
sample pair analysis", IEEE Trans. Signal Processing 51(7), 2003.

Over horizontally adjacent pixel pairs (u, v) each pair is assigned to a trace
set from the finite-state model of LSB flipping:
    X: v even and v > u, or v odd and v < u
    Y: v even and v < u, or v odd and v > u
    W: pairs differing only in the LSB (same {2i,2i+1} bin, u != v)  -- a subset of Y
    Z: equal pairs (u == v)
With P = total pairs and the cover assumption |X0| = |Y0|, the embedded rate p
solves the quadratic
    0.5 (W + Z) p^2 + (2 X - P) p + (Y - X) = 0,
and we take the root of smaller magnitude (p = 0 for a cover, where Y = X).

Like RS, SPA assumes a symmetric LSB flip. The baseline is "+1" (asymmetric:
even values behave like an LSB flip, odd values carry up), so standard SPA is
expected to be biased / blind on "+1" -- we implement the STANDARD method and
characterize the miss (finding, not bug).
"""
import math

import numpy as np


def sample_pairs(channel):
    """Horizontally adjacent pairs (u=left, v=right) as flat int arrays."""
    ch = np.asarray(channel, dtype=np.int64)
    return ch[:, :-1].ravel(), ch[:, 1:].ravel()


def _trace_counts(u, v):
    """(X, Y, W, Z, P) trace-set cardinalities for the pair arrays."""
    v_even = (v % 2 == 0)
    X = int(np.sum((v_even & (v > u)) | (~v_even & (v < u))))
    Y = int(np.sum((v_even & (v < u)) | (~v_even & (v > u))))
    same_bin = int(np.sum((u >> 1) == (v >> 1)))
    Z = int(np.sum(u == v))
    W = same_bin - Z                      # same bin but not equal == differ only in LSB
    return X, Y, W, Z, len(u)


def estimate_rate(channel):
    """SPA estimate of the embedded rate p_hat for one channel (raw, unclamped)."""
    u, v = sample_pairs(channel)
    X, Y, W, Z, P = _trace_counts(u, v)

    a = 0.5 * (W + Z)
    b = 2.0 * X - P
    c = float(Y - X)

    if abs(a) < 1e-12:
        return float(-c / b) if abs(b) > 1e-12 else 0.0
    disc = max(b * b - 4.0 * a * c, 0.0)
    r1 = (-b + math.sqrt(disc)) / (2.0 * a)
    r2 = (-b - math.sqrt(disc)) / (2.0 * a)
    return float(r1 if abs(r1) <= abs(r2) else r2)


def analyze_image(image):
    """{comb, r, g, b} SPA rate estimates; comb = mean of the three channels."""
    arr = np.asarray(image)
    per = {name: estimate_rate(arr[..., ci]) for ci, name in enumerate(("r", "g", "b"))}
    per["comb"] = (per["r"] + per["g"] + per["b"]) / 3.0
    return per
