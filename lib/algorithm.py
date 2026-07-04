"""Public API: the StegAlgorithm class.

Ties together message preparation, encryption, and the parameterized embed/extract
core under a single StegoConfig. With the default config this reproduces
baseline.stego.hide_message / expose_message exactly.

    alg = StegAlgorithm()                       # default config == baseline
    alg.hide(message, key, cover_path, out_path)
    alg.expose(stego_image, key)
"""
from PIL import Image

from lib.config import StegoConfig
from lib import message as msg
from lib import crypto
from lib import embedding


def load_image(path):
    """Open an image as an RGB copy (matches baseline.image_utils.load_image)."""
    return Image.open(path).copy().convert('RGB')


class StegAlgorithm:
    def __init__(self, config=None):
        self.config = config or StegoConfig()
        self.config.validate()

    def hide(self, message, key, cover_path, out_path=None):
        """Encrypt `message` and embed it into the cover at `cover_path`.

        Returns the stego image, or False if the message does not fit.
        """
        bitstring = msg.text_to_bitstring(message)
        ciphertext = crypto.encrypt_message(message=bitstring, key=key)
        char_matrix, char_count = msg.split_into_chars(ciphertext)

        carrier = load_image(cover_path)
        stego = embedding.embed(char_matrix, carrier, char_count, self.config)
        if stego is False:
            return False
        if out_path is not None:
            stego.save(out_path)
        return stego

    def expose(self, stego_image, key):
        """Recover the plaintext message from a stego image."""
        char_count, bits = embedding.extract(stego_image, self.config)
        ciphertext = msg.bits_to_bitstring(bits)
        plaintext_bits = crypto.decrypt_message(ciphertext=ciphertext, key=key)
        return msg.bits_to_text(char_count, plaintext_bits)
