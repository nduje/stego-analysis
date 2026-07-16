"""LSB replacement (LSB-R) -- the classic method chi-square/RS/SPA were designed for.

The least-significant bit of a selected channel-sample is REPLACED by a message
bit: v -> (v & 0xFE) | bit. The value stays within its LSB pair {2k, 2k+1}, so
|delta| <= 1 and no value leaves [0, 255]. This asymmetric, structure-creating
change is exactly the Pairs-of-Values signature RS/SPA/chi-square exploit -- so
LSB-R is our POSITIVE CONTROL: our attacks should light up on it.

Positions are a seeded random subset of all channel-samples (spread embedding).
"""
import numpy as np


def select_positions(n_samples, n_bits, seed):
    """Random distinct sample indices (0..n_samples-1) to carry the payload."""
    rng = np.random.default_rng(seed)
    return rng.permutation(n_samples)[:n_bits]


def embed(cover, payload_bits, positions):
    """cover: HxWx3 uint8. payload_bits: 0/1 array. positions: flat sample indices.
    Returns a stego copy with LSB replacement at `positions`."""
    stego = cover.copy().reshape(-1)
    v = stego[positions]
    stego[positions] = (v & 0xFE) | payload_bits.astype(stego.dtype)
    return stego.reshape(cover.shape)
