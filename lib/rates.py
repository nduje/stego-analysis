"""Embedding-rate constants for the experiments (defined Day 4, used Day 5+).

For this algorithm the embedding rate is the payload as a fraction of capacity.
Embedding is sequential (raster order over 3-pixel blocks), so a rate of r means
the top r-fraction of the image's blocks are fully embedded and the rest is
untouched cover -- a property worth remembering when interpreting steganalysis.

Capacity (in characters) for a WxH image is (W // 3) * H; each 3-pixel block
carries exactly one 8-bit character.
"""

EMBEDDING_RATES = (0.05, 0.10, 0.25, 0.50, 1.00)   # fraction of capacity


def capacity_chars(width, height):
    """Characters that fit in a WxH cover (one per usable 3-pixel block)."""
    return (width // 3) * height


def chars_for_rate(capacity, rate):
    """Number of characters to embed for a given capacity and rate fraction."""
    return int(round(capacity * rate))
