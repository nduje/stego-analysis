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


def _match_channel(value, bit, config):
    """Nudge a channel so its parity equals `bit`, per matching_mode.

    Default 'plus_one': keep if parity already matches, otherwise +1 (never -1).
    Reproduces the baseline's four-branch parity rule exactly.
    """
    if value % 2 == bit:
        return value
    return value + 1


def _apply_continuation_flag(blue_value, more_follows, config):
    """Set the 9th-channel flag: odd if more characters follow, else even.

    Applied regardless of saturation (matching the baseline), so a blue channel
    at 255 on the final character becomes 256 -- exactly as the baseline leaves it.
    """
    if more_follows:
        if blue_value % 2 == 0:
            return blue_value + 1
    else:
        if blue_value % 2 == 1:
            return blue_value + 1
    return blue_value


def embed(char_matrix, image, char_count, config=None):
    """Embed `char_count` characters (8-bit int lists) into `image` in place.

    Returns the mutated image, or False if the message does not fit -- same
    contract as baseline.image_utils.encode_message.
    """
    config = config or StegoConfig()
    config.validate()

    width, height = image.size
    if capacity_blocks(width, height) < char_count:
        print("The message is too large.")
        return False

    blocks = _iter_blocks(width, height, config)
    for block_index in range(char_count):
        x, y = next(blocks)
        bits = char_matrix[block_index]
        more_follows = block_index < char_count - 1

        pixels = [list(image.getpixel((x + i, y))) for i in range(3)]

        # channels 0..7 -> data bits (skip channels already at 255)
        for ch in range(_DATA_CHANNELS):
            pi, ci = divmod(ch, 3)
            if pixels[pi][ci] < 255:                       # saturation_255 == "skip"
                pixels[pi][ci] = _match_channel(pixels[pi][ci], bits[ch], config)

        # channel 8 (pixel2 blue) -> continuation flag  (termination == "continuation_flag")
        pixels[2][2] = _apply_continuation_flag(pixels[2][2], more_follows, config)

        for i in range(3):
            image.putpixel((x + i, y), tuple(pixels[i]))

    return image


def extract(image, config=None):
    """Read the hidden payload back.

    Returns (char_count, bit_list) with 8 bits per character -- same contract as
    baseline.image_utils.decode_message.
    """
    config = config or StegoConfig()
    config.validate()

    width, height = image.size
    bits = []
    char_count = 0

    for x, y in _iter_blocks(width, height, config):
        pixels = [image.getpixel((x + i, y)) for i in range(3)]

        for ch in range(_DATA_CHANNELS):
            pi, ci = divmod(ch, 3)
            bits.append(pixels[pi][ci] % 2)
        char_count += 1

        # even flag on the 9th channel = terminator
        if pixels[2][2] % 2 == 0:
            break

    return char_count, bits
