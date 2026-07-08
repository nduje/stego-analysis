"""RS (Regular/Singular) steganalysis -- Fridrich, Goljan & Du.

Reference: J. Fridrich, M. Goljan, R. Du, "Reliable detection of LSB
steganography in color and grayscale images" (2001).

Groups of 4 pixels in a row, mask M = [0,1,1,0]. Smoothness (discrimination)
function f(G) = sum |x_{i+1} - x_i|. Flip functions:
    F1(x)  = x XOR 1            (LSB flip: 0<->1, 2<->3, ...)
    F-1(x) = ((x+1) XOR 1) - 1  (dual/shifted flip)
Applying F_M to a group and comparing f gives Regular (f grows), Singular
(f shrinks) or Unusable groups. Counting R_M, S_M and R_-M, S_-M on the image and
on the all-LSB-flipped image yields a quadratic whose root estimates the embedded
rate p.

Important: RS is built for LSB REPLACEMENT (flip = XOR 1). The baseline is "+1"
matching -- for even values it coincides with the LSB flip (2->3) but for odd
values it carries up (3->4). So standard RS is expected to give a BIASED rate
estimate on "+1"; we implement the STANDARD method and characterize the miss
(that is the finding, not a bug).
"""
import math

import numpy as np

MASK = (0, 1, 1, 0)


def _flip1(v):
    """LSB flip, F1(x) = x XOR 1 (stays within 0..255)."""
    return v ^ 1


def _flip_minus1(v):
    """Dual flip, F-1(x) = ((x+1) XOR 1) - 1 (may yield -1 or 256; fine for f())."""
    return ((v + 1) ^ 1) - 1


def _row_groups(channel):
    """Tile each row into disjoint groups of 4 (dropping the remainder)."""
    h, w = channel.shape
    ng = w // 4
    return channel[:, :ng * 4].reshape(h, ng, 4).reshape(-1, 4)


def _smoothness(groups):
    return np.abs(np.diff(groups, axis=1)).sum(axis=1)


def _apply_mask(groups, mask):
    out = groups.copy()
    for i, m in enumerate(mask):
        if m == 1:
            out[:, i] = _flip1(out[:, i])
        elif m == -1:
            out[:, i] = _flip_minus1(out[:, i])
    return out


def rs_counts(channel, mask=MASK):
    """(R_M, S_M, R_negM, S_negM) as fractions of groups for one channel."""
    g = _row_groups(np.asarray(channel, dtype=np.int64))
    f0 = _smoothness(g)
    fM = _smoothness(_apply_mask(g, mask))
    fNeg = _smoothness(_apply_mask(g, tuple(-m for m in mask)))
    return (
        float(np.mean(fM > f0)), float(np.mean(fM < f0)),
        float(np.mean(fNeg > f0)), float(np.mean(fNeg < f0)),
    )


def estimate_rate(channel, mask=MASK):
    """RS estimate of the embedded rate p_hat for one channel (raw, unclamped)."""
    ch = np.asarray(channel, dtype=np.int64)
    RM, SM, RmM, SmM = rs_counts(ch, mask)
    RM1, SM1, RmM1, SmM1 = rs_counts(_flip1(ch), mask)   # all LSBs flipped

    d0, d1 = RM - SM, RM1 - SM1
    dm0, dm1 = RmM - SmM, RmM1 - SmM1

    a = 2.0 * (d1 + d0)
    b = dm0 - dm1 - d1 - 3.0 * d0
    c = d0 - dm0

    if abs(a) < 1e-12:
        x = c / b if abs(b) > 1e-12 else 0.0
    else:
        disc = max(b * b - 4.0 * a * c, 0.0)
        r1 = (-b + math.sqrt(disc)) / (2.0 * a)
        r2 = (-b - math.sqrt(disc)) / (2.0 * a)
        x = r1 if abs(r1) <= abs(r2) else r2

    return float(x / (x - 0.5)) if abs(x - 0.5) > 1e-12 else 0.0


def analyze_image(image):
    """{comb, r, g, b} RS rate estimates; comb = mean of the three channels."""
    arr = np.asarray(image)
    per = {name: estimate_rate(arr[..., ci]) for ci, name in enumerate(("r", "g", "b"))}
    per["comb"] = (per["r"] + per["g"] + per["b"]) / 3.0
    return per
