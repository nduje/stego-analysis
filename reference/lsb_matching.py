"""LSB matching (LSB-M) -- the symmetric +/-1 method (same idea as our P2).

If a selected sample's LSB already matches the message bit, it is left alone;
otherwise the value is moved by +/-1 (random direction), which flips the LSB
without the asymmetric Pairs-of-Values structure of LSB replacement. Edges are
forced inward (0 -> +1, 255 -> -1) so no value leaves [0, 255]. |delta| <= 1.

Because the change is symmetric, chi-square/RS/SPA (built for LSB-R) are largely
blind to it -- which is exactly why our baseline "+1" evaded them, and why P2's
+/-1 became visible to RS/SPA only through the residual statistics (Day 16).
"""
import numpy as np


def select_positions(n_samples, n_bits, seed):
    rng = np.random.default_rng(seed)
    return rng.permutation(n_samples)[:n_bits]


def embed(cover, payload_bits, positions, seed):
    """cover: HxWx3 uint8. payload_bits: 0/1 array. positions: flat sample indices.
    Returns a stego copy with LSB matching at `positions`."""
    stego = cover.copy().reshape(-1)
    v = stego[positions].astype(np.int16)
    bits = payload_bits.astype(np.int16)
    mismatch = (v & 1) != bits

    rng = np.random.default_rng(seed)
    step = rng.choice(np.array([-1, 1], dtype=np.int16), size=v.shape[0])
    step[v == 0] = 1        # edge: 0 can only go up
    step[v == 255] = -1     # edge: 255 can only go down

    v[mismatch] += step[mismatch]
    stego[positions] = v.astype(stego.dtype)
    return stego.reshape(cover.shape)
