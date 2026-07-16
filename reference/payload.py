"""Payload alignment between our algorithm and the reference methods.

Our embedding rate `r` is a fraction of OUR capacity (characters, 8 bits each).
The reference methods (LSB-R, LSB-M, HILL) are parameterized in bits. To compare
fairly we give every reference the SAME ABSOLUTE NUMBER OF BITS our algorithm
embeds at rate `r`, and document the conversion r -> bits -> bpc.

For a WxH RGB cover:
  capacity_chars = (W // 3) * H         (one 8-bit char per 3-pixel block)
  bits(r)        = round(capacity * r) * 8
  bpc(r)         = bits(r) / (W * H * 3)   bits per channel-sample (LSB fraction)
"""
from lib.rates import EMBEDDING_RATES, capacity_chars, chars_for_rate

BITS_PER_CHAR = 8


def bits_for_rate(rate, width=256, height=256):
    """Absolute payload bits our algorithm embeds at this rate (chars * 8)."""
    return chars_for_rate(capacity_chars(width, height), rate) * BITS_PER_CHAR


def n_samples(width=256, height=256, channels=3):
    """Number of channel-samples (independent LSB slots) in the cover."""
    return width * height * channels


def bpc(rate, width=256, height=256, channels=3):
    """Bits per channel-sample: LSB-capacity fraction and the HILL payload arg."""
    return bits_for_rate(rate, width, height) / n_samples(width, height, channels)


def mapping_rows(width=256, height=256, channels=3):
    """The documented r -> bits -> bpc table (for CSV/README)."""
    rows = []
    for r in EMBEDDING_RATES:
        b = bits_for_rate(r, width, height)
        rows.append({
            "rate": r,
            "chars": b // BITS_PER_CHAR,
            "bits": b,
            "bpc": round(bpc(r, width, height, channels), 6),
            "bpp_pixel": round(b / (width * height), 6),
        })
    return rows
