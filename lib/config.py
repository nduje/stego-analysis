"""Configuration for the parameterized steganography algorithm.

`StegoConfig` is the single object that turns the baseline's hard-coded choices
into explicit switches. Every DEFAULT value reproduces the frozen baseline
exactly; every non-default value is a HOOK reserved for the improvement phase
and raises NotImplementedError until it is actually built.

Switches
--------
bits_per_channel : int   (default 1)
    LSB/parity payload per channel. Only 1 is implemented (the baseline rate).
matching_mode    : str   "plus_one" (default) | "pm_one"
    How a channel is nudged to carry a bit. Baseline only ever +1 or keeps.
    "pm_one" (Improvement 2) uses edge-safe +/-1 matching (direction key-seeded),
    removing the upward drift AND the 255-skip -- so the 255-bug disappears too.
pixel_order      : str   "sequential" (default) | "prng"
    Order in which 3-pixel blocks are visited. Baseline is raster/sequential.
    "prng" (Improvement 1) permutes the blocks with a key-seeded PRNG, scattering
    the payload so the sequential "cliff" (positional chi-square) disappears.
termination      : str   "continuation_flag" (default) | "length_header"
    How the decoder knows where the payload ends. Baseline uses the 9th-channel
    continuation flag. "length_header" is a future improvement (also fixes the
    non-ASCII / length-correctness limitation).
saturation_255   : str   "skip" (default) | "fix"
    What to do with a channel already at 255. Baseline skips it (payload lost).
    "fix" is a future improvement.
prng_seed        : int | None
    Reserved for pixel_order="prng"; unused while order is sequential.
"""
from dataclasses import dataclass

# value -> is it implemented on Day 2?  (False == inert hook)
_SWITCHES = {
    "matching_mode":  {"plus_one": True,          "pm_one": True},
    "pixel_order":    {"sequential": True,        "prng": True},
    "termination":    {"continuation_flag": True, "length_header": False},
    "saturation_255": {"skip": True,              "fix": False},
}


@dataclass(frozen=True)
class StegoConfig:
    bits_per_channel: int = 1
    matching_mode: str = "plus_one"
    pixel_order: str = "sequential"
    termination: str = "continuation_flag"
    saturation_255: str = "skip"
    prng_seed: int | None = None

    def __post_init__(self):
        self.validate()

    def validate(self):
        """Reject unknown values (ValueError) and inert hooks (NotImplementedError)."""
        for field, options in _SWITCHES.items():
            value = getattr(self, field)
            if value not in options:
                raise ValueError(
                    f"{field}={value!r} is not a known option "
                    f"(choose from {sorted(options)})"
                )
            if not options[value]:
                raise NotImplementedError(
                    f"{field}={value!r} is a hook reserved for the improvement "
                    f"phase and is not implemented on Day 2; the only Day 2 value "
                    f"is the baseline default."
                )
        if self.bits_per_channel != 1:
            raise NotImplementedError(
                f"bits_per_channel={self.bits_per_channel} is not implemented on "
                f"Day 2; the baseline rate is 1."
            )
