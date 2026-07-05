"""DEPRECATED -- in-process simulation of the seminar's RSA/DH handshake.

This is a faithful port of `modules/exchange/key_exchange.py` from the seminar
repo (github.com/nduje/Steganography): the RSA/DH key generation, RSA-PSS/SHA256
signatures, and the DH->HKDF shared-key derivation are preserved exactly. The
only changes are cleanup: the socket transport is removed (everything runs
in-process via `simulate_handshake()`) and the debug prints are dropped.

It is kept purely as a reference for the thesis narrative and is **called
nowhere** in the active pipeline -- the real key origin is the passphrase ->
scrypt -> HKDF derivation in `lib/crypto.py`. Importing this module emits a
DeprecationWarning by design.
"""
import base64
import warnings

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dh, padding, rsa
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

warnings.warn(
    "lib.keyexchange is a DEPRECATED in-process simulation of the seminar "
    "RSA/DH handshake; it is not part of the active pipeline. The live key "
    "origin is lib.crypto.derive_keys (passphrase -> scrypt -> HKDF).",
    DeprecationWarning,
    stacklevel=2,
)


def generate_RSA_private_key():
    RSA_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return RSA_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def generate_RSA_public_key(RSA_private_key):
    RSA_private_key = serialization.load_pem_private_key(RSA_private_key, password=None)
    return RSA_private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def generate_DH_parameters():
    DH_parameters = dh.generate_parameters(generator=2, key_size=2048)
    return DH_parameters.parameter_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.ParameterFormat.PKCS3,
    )


def generate_DH_private_key(DH_parameters):
    """`DH_parameters` is a parameters OBJECT (as in the seminar's local use)."""
    return DH_parameters.generate_private_key()


def generate_DH_public_key(DH_private_key):
    return DH_private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def sign_key_client_to_server(RSA_private_key, DH_public_key):
    RSA_private_key = serialization.load_pem_private_key(RSA_private_key, password=None)
    signature = RSA_private_key.sign(
        DH_public_key,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(signature)


def sign_key_server_to_client(RSA_private_key, DH_parameters, server_DH_public_key, client_DH_public_key):
    RSA_private_key = serialization.load_pem_private_key(RSA_private_key, password=None)
    client_DH_public_key = client_DH_public_key.encode()
    message = DH_parameters + server_DH_public_key + client_DH_public_key
    signature = RSA_private_key.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(signature)


def get_key(private_key, public_key):
    public_key = serialization.load_pem_public_key(public_key.encode())
    DH_shared_key = private_key.exchange(public_key)
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"handshake data",
    ).derive(DH_shared_key)
    return base64.b64encode(derived_key).decode()


def simulate_handshake():
    """Run both sides in-process; return the base64 shared key both parties derive.

    Exercises the ported RSA/DH/signature/HKDF path end-to-end without sockets,
    and asserts client and server arrive at the same key.
    """
    # Shared DH parameters (distributed by the server in the original protocol).
    params_bytes = generate_DH_parameters()
    params_obj = serialization.load_pem_parameters(params_bytes)

    # Server and client each hold an RSA identity key and a DH ephemeral key.
    server_rsa = generate_RSA_private_key()
    client_rsa = generate_RSA_private_key()

    server_dh_priv = generate_DH_private_key(params_obj)
    client_dh_priv = generate_DH_private_key(params_obj)
    server_dh_pub = generate_DH_public_key(server_dh_priv)
    client_dh_pub = generate_DH_public_key(client_dh_priv)

    # Authenticate the DH public keys with the RSA identity keys (RSA-PSS/SHA256).
    client_sig = sign_key_client_to_server(client_rsa, client_dh_pub)
    server_sig = sign_key_server_to_client(server_rsa, params_bytes, server_dh_pub, client_dh_pub.decode())
    _verify(generate_RSA_public_key(client_rsa), client_dh_pub, client_sig)
    _verify(
        generate_RSA_public_key(server_rsa),
        params_bytes + server_dh_pub + client_dh_pub,
        server_sig,
    )

    # Both sides derive the same shared key.
    server_key = get_key(server_dh_priv, client_dh_pub.decode())
    client_key = get_key(client_dh_priv, server_dh_pub.decode())
    assert server_key == client_key, "in-process DH handshake did not agree on a key"
    return server_key


def _verify(rsa_public_pem, message, signature_b64):
    public_key = serialization.load_pem_public_key(rsa_public_pem)
    public_key.verify(
        base64.b64decode(signature_b64),
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
