"""Reference steganography methods for the comparison (Day 18).

- LSB-R (lsb_replacement): classic replacement, our positive control.
- LSB-M (lsb_matching): symmetric +/-1, same idea as our P2.
- HILL (adaptive): provided externally (Aletheia embedding simulator), not here.

All are payload-aligned to our algorithm via `payload.bits_for_rate` so the
before/after comparison is at equal absolute payload.
"""
from . import lsb_replacement, lsb_matching, payload

__all__ = ["lsb_replacement", "lsb_matching", "payload"]
