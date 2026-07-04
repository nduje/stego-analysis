"""Custom steganography algorithm (RGB pixel parity).

BASELINE (Day 1): the encoding/decoding logic is IDENTICAL to the seminar
repo. The only change from the original: I/O paths are arguments (instead
of hardcoded "images/original.png" / "images/copy_server.png"), so the
algorithm can run standalone, without sockets. All known behaviors
(including the 255 edge case and the continuation flag in the 9th channel)
are intentionally preserved -- this is what we will later measure and fix.
"""
from PIL import Image


def load_image(path):
    original = Image.open(path)
    copy = original.copy()
    copy = copy.convert('RGB')
    return copy


def encode_message(message, image, counter, out_path=None):
    width, height = image.size

    binary_counter = 0
    capacity = (width // 3) * height

    if capacity < counter:
        print("The message is too large.")
        return False

    for y in range(height):
        for x in range(0, width, 3):
            if (x + 2 >= width) or counter == 0:
                continue

            index = 0
            binary = message[binary_counter]

            for i in range(3):
                current_x = x + i
                pixel_value = image.getpixel((current_x, y))
                colors = list(pixel_value)
                new_colors = list(colors)

                for j in range(3):
                    if index < len(binary) and colors[j] < 255:
                        if binary[index] == 0 and colors[j] % 2 == 0:
                            new_colors[j] = colors[j]
                        elif binary[index] == 1 and colors[j] % 2 == 0:
                            new_colors[j] = colors[j] + 1
                        elif binary[index] == 0 and colors[j] % 2 == 1:
                            new_colors[j] = colors[j] + 1
                        elif binary[index] == 1 and colors[j] % 2 == 1:
                            new_colors[j] = colors[j]

                    if index < 8:
                        index += 1

                    if index + 1 == 9:
                        if counter > 1:
                            if new_colors[2] % 2 == 0:
                                new_colors[2] += 1
                        else:
                            if new_colors[2] % 2 == 1:
                                new_colors[2] += 1

                image.putpixel((current_x, y), tuple(new_colors))

            counter -= 1
            binary_counter += 1

    if out_path is not None:
        image.save(out_path)

    return image


def decode_message(image):
    width, height = image.size

    binary_counter = 0
    break_all = False
    binary = []

    for y in range(height):
        for x in range(0, width, 3):
            if (x + 2 >= width):
                continue

            index = 0

            for i in range(3):
                current_x = x + i
                pixel_value = image.getpixel((current_x, y))
                colors = list(pixel_value)

                for color in colors:
                    if color % 2 == 0:
                        binary.append(0)
                    else:
                        binary.append(1)

                    index += 1

                    if index == 9:
                        if colors[2] % 2 == 1:
                            binary.pop()
                            continue
                        else:
                            if colors[2] % 2 == 0:
                                break_all = True
                                break

                if break_all:
                    break

            binary_counter += 1

            if break_all:
                break

        if break_all:
            break

    binary.pop()
    return binary_counter, binary
