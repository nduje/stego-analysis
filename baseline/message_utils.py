"""Message preparation for encoding / decoding.

BASELINE: copied almost verbatim from the seminar repo
(github.com/nduje/Steganography). We intentionally do NOT touch the logic --
this is the control group. Refactoring and parameterization live in lib/.
"""


def message_to_ascii_binary_strings(message):
    binary_string = ''.join([bin(ord(char))[2:].zfill(8) for char in message])
    return binary_string


def group_binary_strings(binary_string):
    result = []
    for i in range(0, len(binary_string), 8):
        result.append(binary_string[i:i + 8])
    return result


def binary_strings_to_matrix(binary_strings):
    int_lists = [binary_string_to_int_list(binary_string) for binary_string in binary_strings]
    return int_lists


def binary_list_to_string(binary_list):
    binary_string = ''.join(str(bit) for bit in binary_list)
    return binary_string


def binary_string_to_int_list(binary_string):
    return [int(bit) for bit in binary_string]


def get_binary_strings_length(binary_strings):
    return len(binary_strings)


def group_binary_in_list(number_of_lists, binary_code):
    matrix = []
    for i in range(number_of_lists):
        start_index = i * 8
        end_index = min((i + 1) * 8, len(binary_code))
        character = binary_code[start_index:end_index]
        matrix.append(character)
    return matrix


def ascii_binary_strings_to_message(matrix):
    message = ""
    for char_list in matrix:
        binary_string = ''.join(str(bit) for bit in char_list)
        ascii_value = int(binary_string, 2)
        message += chr(ascii_value)
    return message


def prepare_message_for_hidding(binary_code):
    binary = group_binary_strings(binary_string=binary_code)
    counter = get_binary_strings_length(binary_strings=binary)
    binary = binary_strings_to_matrix(binary_strings=binary)
    return binary, counter


def prepare_message_for_exposing(number_of_lists, binary_code):
    binary_code = binary_string_to_int_list(binary_string=binary_code)
    character_matrix = group_binary_in_list(number_of_lists=number_of_lists, binary_code=binary_code)
    message = ascii_binary_strings_to_message(matrix=character_matrix)
    return message
