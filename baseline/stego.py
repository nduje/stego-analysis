"""Orchestration: hide_message / expose_message.

BASELINE (Day 1): mirrors steganography.py from the seminar, without sockets.
`hide_message` takes the cover path and output path as arguments (instead of
hardcoded ones); otherwise the flow is identical.
"""
from baseline.image_utils import load_image, encode_message, decode_message
from baseline.message_utils import (
    message_to_ascii_binary_strings,
    prepare_message_for_hidding,
    binary_list_to_string,
    prepare_message_for_exposing,
)
from baseline.crypto import encrypt_message, decrypt_message


def hide_message(message, key, cover_path, out_path):
    binary_string = message_to_ascii_binary_strings(message=message)
    binary = encrypt_message(message=binary_string, key=key)
    binary, counter = prepare_message_for_hidding(binary_code=binary)

    carrier = load_image(cover_path)
    hidden_message = encode_message(message=binary, image=carrier, counter=counter, out_path=out_path)
    return hidden_message


def expose_message(hidden_message, key):
    characters_number, binary = decode_message(image=hidden_message)
    binary_string = binary_list_to_string(binary_list=binary)
    binary = decrypt_message(ciphertext=binary_string, key=key)
    exposed_message = prepare_message_for_exposing(number_of_lists=characters_number, binary_code=binary)
    return exposed_message
