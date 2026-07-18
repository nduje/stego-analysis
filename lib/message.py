"""Message <-> bits conversion.

A cleaned copy of `baseline/message_utils.py`; the logic (and therefore the bit
stream) is identical, which is what keeps the default configuration byte-for-byte
compatible with the baseline. The 8-bit/char assumption is intentionally kept --
lifting it is a separate improvement (length header).
"""


def text_to_bitstring(text):
    """Each character -> its 8-bit ASCII code, concatenated."""
    return ''.join(bin(ord(char))[2:].zfill(8) for char in text)


def bitstring_to_int_list(bitstring):
    return [int(bit) for bit in bitstring]


def bits_to_bitstring(bit_list):
    return ''.join(str(bit) for bit in bit_list)


def split_into_chars(bitstring):
    """Group a bitstring into 8-bit character chunks -> list of int-lists.

    Returns (char_matrix, char_count): the payload to embed, one 8-bit list per
    character, and how many characters there are (the baseline's `counter`).
    """
    char_matrix = [
        bitstring_to_int_list(bitstring[i:i + 8])
        for i in range(0, len(bitstring), 8)
    ]
    return char_matrix, len(char_matrix)


def bits_to_text(char_count, bitstring):
    """Inverse of split_into_chars: first `char_count` 8-bit groups -> text."""
    bits = bitstring_to_int_list(bitstring)
    message = ""
    for i in range(char_count):
        chunk = bits[i * 8:min((i + 1) * 8, len(bits))]
        message += chr(int(''.join(str(bit) for bit in chunk), 2))
    return message
