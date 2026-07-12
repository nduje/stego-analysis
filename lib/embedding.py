"""Core embed / extract, parameterized by StegoConfig.

This is a clean re-implementation of the baseline's algorithm, NOT an import of
it. The frozen baseline packs one character (8 bits) into a block of 3 RGB
pixels: the first 8 channels carry the data bits (via parity matching, skipping
any channel already at 255), and the 9th channel (the 3rd pixel's blue) carries
a continuation flag -- odd means "more characters follow", even means "this was
the last one".

The four decision points are factored out so the improvement phase can replace
them; with the default StegoConfig the behavior -- and the saved PNG bytes --
are identical to the baseline.

Channel layout of a 3-pixel block (indices 0..8):
    0,1,2 = pixel0 R,G,B    3,4,5 = pixel1 R,G,B    6,7 = pixel2 R,G    8 = pixel2 B (flag)
"""
import hashlib

import numpy as np

from lib.config import StegoConfig

_DATA_CHANNELS = 8   # channels 0..7 carry data; channel 8 is the continuation flag


def capacity_blocks(width, height):
    """Number of usable 3-pixel blocks (== baseline capacity)."""
    return (width // 3) * height


def _iter_blocks(width, height, config):
    """Yield (x, y) top-left of each usable block, in the configured order.

    Default 'sequential' == raster order over blocks whose 3 pixels fit in-row,
    matching the baseline exactly.
    """
    for y in range(height):
        for x in range(0, width, 3):
            if x + 2 < width:
                yield x, y


def _ordered_blocks(width, height, config, seed):
    """The usable blocks in the configured visiting order.

    'sequential' returns raster order (identical to _iter_blocks, so the baseline
    stays byte-for-byte). 'prng' (Improvement 1) permutes that list with a PRNG
    seeded by the 32-byte `seed` -- scattering the payload so the sequential
    "cliff" vanishes. Only the ORDER changes; the "+1" matching, the continuation
    flag and the 255-skip are untouched, so any effect is due to ordering alone.
    """
    raster = list(_iter_blocks(width, height, config))
    if config.pixel_order == "sequential":
        return raster
    if config.pixel_order == "prng":
        if seed is None:
            raise ValueError("pixel_order='prng' requires a seed")
        rng = np.random.default_rng(int.from_bytes(seed, "big"))
        return [raster[i] for i in rng.permutation(len(raster))]
    raise ValueError(f"unknown pixel_order {config.pixel_order!r}")


def _match_plus_one(value, bit):
    """Baseline matching: keep if parity already matches, otherwise +1 (never -1).

    The caller skips channels at 255 (saturation_255 == "skip").
    """
    if value % 2 == bit:
        return value
    return value + 1


def _match_pm_one(value, bit, direction):
    """Edge-safe +/-1 matching (Improvement 2): no drift, no 255-skip.

    On a parity mismatch: 0 -> +1 and 255 -> -1 (staying in range), otherwise
    value + `direction` (a key-seeded +/-1). Every channel is usable, so the
    255-bug disappears.
    """
    if value % 2 == bit:
        return value
    if value == 0:
        return 1
    if value == 255:
        return 254
    return value + direction


def _direction_stream(seed):
    """Infinite +/-1 stream for pm_one, seeded SEPARATELY from the permutation PRNG.

    Decode never uses it (parity is corrected either way); it only makes the stego
    image reproducible for a given key.
    """
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(seed + b"pm1").digest(), "big"))
    while True:
        for d in rng.integers(0, 2, size=4096):
            yield 1 if d else -1


def _apply_continuation_flag(blue_value, more_follows, config):
    """Baseline flag: odd if more characters follow, else even, via +1.

    Applied regardless of saturation, so a blue channel at 255 on the final
    character becomes 256 -- exactly as the baseline leaves it.
    """
    if more_follows:
        if blue_value % 2 == 0:
            return blue_value + 1
    else:
        if blue_value % 2 == 1:
            return blue_value + 1
    return blue_value


def _flag_pm_one(blue_value, more_follows):
    """Edge-safe continuation flag for pm_one: same mechanism, no 255 overflow.

    Forces the target parity (odd = more follows, even = terminator) using 255 -> -1
    and 0 -> +1, so a 255 blue on the terminator does not overflow (fixes saturated
    round-trip). The flag MECHANISM is unchanged (still a continuation flag).
    """
    target = 1 if more_follows else 0
    if blue_value % 2 == target:
        return blue_value
    if blue_value == 255:
        return 254
    if blue_value == 0:
        return 1
    return blue_value + 1


def embed(char_matrix, image, char_count, config=None, seed=None):
    """Embed `char_count` characters (8-bit int lists) into `image` in place.

    Returns the mutated image, or False if the message does not fit -- same
    contract as baseline.image_utils.encode_message. `seed` is required only for
    pixel_order='prng'.
    """
    config = config or StegoConfig()
    config.validate()

    width, height = image.size
    if capacity_blocks(width, height) < char_count:
        print("The message is too large.")
        return False

    blocks = _ordered_blocks(width, height, config, seed)
    pm_one = config.matching_mode == "pm_one"
    directions = _direction_stream(seed) if pm_one else None

    for block_index in range(char_count):
        x, y = blocks[block_index]
        bits = char_matrix[block_index]
        more_follows = block_index < char_count - 1

        pixels = [list(image.getpixel((x + i, y))) for i in range(3)]

        # channels 0..7 -> data bits
        for ch in range(_DATA_CHANNELS):
            pi, ci = divmod(ch, 3)
            v = pixels[pi][ci]
            if pm_one:
                needs_dir = (v % 2 != bits[ch]) and (1 <= v <= 254)
                pixels[pi][ci] = _match_pm_one(v, bits[ch], next(directions) if needs_dir else 0)
            elif v < 255:                                  # plus_one: saturation_255 == "skip"
                pixels[pi][ci] = _match_plus_one(v, bits[ch])

        # channel 8 (pixel2 blue) -> continuation flag (termination == "continuation_flag").
        # For "length_header" (Improvement 3) the 9th channel is left as untouched cover.
        if config.termination == "continuation_flag":
            if pm_one:
                pixels[2][2] = _flag_pm_one(pixels[2][2], more_follows)
            else:
                pixels[2][2] = _apply_continuation_flag(pixels[2][2], more_follows, config)

        for i in range(3):
            image.putpixel((x + i, y), tuple(pixels[i]))

    return image


def read_bits(image, config, seed, n_blocks):
    """Read the 8 data-channel parities from the first `n_blocks` visited blocks.

    Used by the length-header decoder (which learns how many blocks to read only
    after decrypting the header); the 9th channel is never read.
    """
    width, height = image.size
    blocks = _ordered_blocks(width, height, config, seed)
    bits = []
    for x, y in blocks[:n_blocks]:
        pixels = [image.getpixel((x + i, y)) for i in range(3)]
        for ch in range(_DATA_CHANNELS):
            pi, ci = divmod(ch, 3)
            bits.append(pixels[pi][ci] % 2)
    return bits


def extract(image, config=None, seed=None):
    """Read the hidden payload back.

    Returns (char_count, bit_list) with 8 bits per character -- same contract as
    baseline.image_utils.decode_message. `seed` is required only for
    pixel_order='prng' (it must match the one used to embed).
    """
    config = config or StegoConfig()
    config.validate()

    width, height = image.size
    bits = []
    char_count = 0

    for x, y in _ordered_blocks(width, height, config, seed):
        pixels = [image.getpixel((x + i, y)) for i in range(3)]

        for ch in range(_DATA_CHANNELS):
            pi, ci = divmod(ch, 3)
            bits.append(pixels[pi][ci] % 2)
        char_count += 1

        # even flag on the 9th channel = terminator
        if pixels[2][2] % 2 == 0:
            break

    return char_count, bits
