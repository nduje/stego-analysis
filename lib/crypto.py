"""AES-CTR encryption + passphrase-based key derivation.

The AES-CTR core (encrypt_message / decrypt_message / generate_iv and the bit
helpers) is copied byte-for-byte from `baseline/crypto.py`, which is what keeps
the parity guarantee intact -- it is intentionally NOT modified.

Day 3 adds a real key origin: a passphrase is stretched with scrypt (fixed app
salt) into a 32-byte master secret, then split with HKDF into two independent
keys via domain separation:
    k_enc  (info="stego:aes-ctr:enc")   -> the AES-CTR key
    seed   (info="stego:embed-order")   -> reserved for pixel_order="prng" (unused today)

Documented, intentionally-kept properties (NOT bugs to fix on Day 3):
  * IV = SHA256(key)[:16] is deterministic  -> nonce reuse across messages with
    the same key.
  * APP_SALT is fixed  -> the same passphrase always yields the same master
    secret (reproducible, but no per-run randomness).

The socket-based RSA/DH handshake from the seminar lives in `lib/keyexchange.py`
as a DEPRECATED in-process simulation and is not part of this flow.
"""
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import hashlib
import base64
import os

# --- key derivation (Day 3) ---
DEFAULT_PASSPHRASE = "diplomski-stego-2026"
APP_SALT = b"stego-analysis/v1/app-salt"     # fixed on purpose (documented above)
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2 ** 14, 8, 1
_INFO_ENC = b"stego:aes-ctr:enc"             # domain separation: encryption key
_INFO_ORDER = b"stego:embed-order"           # domain separation: embed-order seed


def generate_key():
    """Raw/test key helper: 32 random bytes, base64-encoded.

    NOT the passphrase path -- this is used by the parity/round-trip suites and
    reproducible experiments that need a fixed or random raw key. The real key
    origin for the CLI/demo is derive_keys() below.
    """
    return base64.b64encode(os.urandom(32)).decode()


def derive_master(passphrase):
    """passphrase -> 32-byte master secret via scrypt with the fixed APP_SALT."""
    if isinstance(passphrase, str):
        passphrase = passphrase.encode("utf-8")
    kdf = Scrypt(salt=APP_SALT, length=32, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return kdf.derive(passphrase)


def _hkdf(master, info):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(master)


def derive_keys(passphrase):
    """passphrase -> (k_enc, seed): two independent 32-byte keys.

    Domain separation (distinct HKDF `info`) guarantees k_enc != seed despite the
    shared master secret. `seed` is derived but unused today (pixel_order stays
    sequential; PRNG order is a future improvement).
    """
    master = derive_master(passphrase)
    k_enc = _hkdf(master, _INFO_ENC)
    seed = _hkdf(master, _INFO_ORDER)
    return k_enc, seed


def bitstring_to_bytes(bitstring):
    bitstring = bitstring.zfill(8 * ((len(bitstring) + 7) // 8))
    return int(bitstring, 2).to_bytes((len(bitstring) + 7) // 8, byteorder='big')


def bytes_to_bitstring(byte_array):
    return ''.join(format(byte, '08b') for byte in byte_array)


def generate_iv(key):
    if isinstance(key, str):
        key = key.encode('utf-8')
    iv = hashlib.sha256(key).digest()[:16]
    return iv


def encrypt_message(message, key):
    if isinstance(key, str):
        key = base64.b64decode(key)
    message = bitstring_to_bytes(message)
    iv = generate_iv(key=key)
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=backend)
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(message) + encryptor.finalize()
    ciphertext = bytes_to_bitstring(ciphertext)
    return ciphertext


def decrypt_message(ciphertext, key):
    if isinstance(key, str):
        key = base64.b64decode(key)
    ciphertext = bitstring_to_bytes(ciphertext)
    iv = generate_iv(key=key)
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=backend)
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    plaintext = bytes_to_bitstring(plaintext)
    return plaintext
