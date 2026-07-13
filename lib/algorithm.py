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


_HEADER_BITS = 16               # length header = 16-bit char count (max 65535)
_HEADER_BLOCKS = _HEADER_BITS // 8   # 8 data bits per block -> 2 header blocks


def load_image(path):
    """Open an image as an RGB copy (matches baseline.image_utils.load_image)."""
    return Image.open(path).copy().convert('RGB')


def _resolve(passphrase, key):
    """Return (k_enc, seed) from exactly one of passphrase / key.

    seed drives the PRNG embed order (Improvement 1): from HKDF on the passphrase
    path, or deterministically from the raw key otherwise.
    """
    if (passphrase is None) == (key is None):
        raise ValueError("provide exactly one of passphrase= or key=")
    if passphrase is not None:
        return crypto.derive_keys(passphrase)          # (k_enc, seed)
    return key, crypto.seed_from_key(key)


class StegAlgorithm:
    def __init__(self, config=None):
        self.config = config or StegoConfig()
        self.config.validate()

    def hide(self, message, cover_path, out_path=None, *, passphrase=None, key=None):
        """Encrypt `message` and embed it into the cover at `cover_path`.

        Returns the stego image, or False if the message does not fit.
        """
        k_enc, seed = _resolve(passphrase, key)
        bitstring = msg.text_to_bitstring(message)
        if self.config.termination == "length_header":
            # prepend a 16-bit char count BEFORE AES so the header is whitened too
            bitstring = format(len(message), "016b") + bitstring
        ciphertext = crypto.encrypt_message(message=bitstring, key=k_enc)
        char_matrix, char_count = msg.split_into_chars(ciphertext)

        carrier = load_image(cover_path)
        stego = embedding.embed(char_matrix, carrier, char_count, self.config, seed)
        if stego is False:
            return False
        if out_path is not None:
            stego.save(out_path)
        return stego

    def expose(self, stego_image, *, passphrase=None, key=None):
        """Recover the plaintext message from a stego image."""
        k_enc, seed = _resolve(passphrase, key)
        if self.config.termination == "length_header":
            return self._expose_length_header(stego_image, k_enc, seed)
        char_count, bits = embedding.extract(stego_image, self.config, seed)
        ciphertext = msg.bits_to_bitstring(bits)
        plaintext_bits = crypto.decrypt_message(ciphertext=ciphertext, key=k_enc)
        return msg.bits_to_text(char_count, plaintext_bits)

    def _expose_length_header(self, stego_image, k_enc, seed):
        """read -> decrypt -> length -> read rest -> decrypt -> message.

        AES-CTR is a stream cipher, so decrypting the first 2 blocks (16 bits) of
        ciphertext yields the 16-bit plaintext header; then read 2 + N blocks.
        """
        hdr = embedding.read_bits(stego_image, self.config, seed, _HEADER_BLOCKS)
        n = int(crypto.decrypt_message(msg.bits_to_bitstring(hdr), k_enc)[:_HEADER_BITS], 2)
        # robustness: a corrupt/undecodable stego can yield a garbage length -> clamp to
        # what the image can hold so decode degrades to a wrong answer, not a crash.
        w, h = stego_image.size
        n = min(n, embedding.capacity_blocks(w, h) - _HEADER_BLOCKS)
        cbits = embedding.read_bits(stego_image, self.config, seed, _HEADER_BLOCKS + n)
        plaintext = crypto.decrypt_message(msg.bits_to_bitstring(cbits), k_enc)
        return msg.bits_to_text(n, plaintext[_HEADER_BITS:])
