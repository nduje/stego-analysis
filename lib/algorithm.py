"""Public API: the StegAlgorithm class.

Ties together message preparation, encryption, and the parameterized embed/extract
core under a single StegoConfig. With the default config this reproduces
baseline.stego.hide_message / expose_message exactly.

Both hide() and expose() take a DUAL key input -- exactly one of:
    passphrase=...   -> scrypt+HKDF derive k_enc (CLI/demo path)
    key=...          -> a raw 32-byte key or its base64 string, used directly
                        (parity tests + reproducible experiments)
Providing both or neither raises ValueError.

    alg = StegAlgorithm()                              # default config == baseline
    alg.hide(message, cover_path, out_path, passphrase="...")
    alg.expose(stego_image, passphrase="...")
"""
from PIL import Image

from lib.config import StegoConfig
from lib import message as msg
from lib import crypto
from lib import embedding


def load_image(path):
    """Open an image as an RGB copy (matches baseline.image_utils.load_image)."""
    return Image.open(path).copy().convert('RGB')


def _resolve_k_enc(passphrase, key):
    """Return the AES-CTR key from exactly one of passphrase / key."""
    if (passphrase is None) == (key is None):
        raise ValueError("provide exactly one of passphrase= or key=")
    if passphrase is not None:
        k_enc, _seed = crypto.derive_keys(passphrase)  # seed derived, unused (sequential order)
        return k_enc
    return key


class StegAlgorithm:
    def __init__(self, config=None):
        self.config = config or StegoConfig()
        self.config.validate()

    def hide(self, message, cover_path, out_path=None, *, passphrase=None, key=None):
        """Encrypt `message` and embed it into the cover at `cover_path`.

        Returns the stego image, or False if the message does not fit.
        """
        k_enc = _resolve_k_enc(passphrase, key)
        bitstring = msg.text_to_bitstring(message)
        ciphertext = crypto.encrypt_message(message=bitstring, key=k_enc)
        char_matrix, char_count = msg.split_into_chars(ciphertext)

        carrier = load_image(cover_path)
        stego = embedding.embed(char_matrix, carrier, char_count, self.config)
        if stego is False:
            return False
        if out_path is not None:
            stego.save(out_path)
        return stego

    def expose(self, stego_image, *, passphrase=None, key=None):
        """Recover the plaintext message from a stego image."""
        k_enc = _resolve_k_enc(passphrase, key)
        char_count, bits = embedding.extract(stego_image, self.config)
        ciphertext = msg.bits_to_bitstring(bits)
        plaintext_bits = crypto.decrypt_message(ciphertext=ciphertext, key=k_enc)
        return msg.bits_to_text(char_count, plaintext_bits)
