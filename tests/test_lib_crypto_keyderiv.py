"""Key-derivation tests: passphrase -> scrypt -> HKDF -> (k_enc, seed).

Checks determinism, that different passphrases diverge, the 32-byte lengths, and
that domain separation actually makes k_enc and seed differ.

Run:
    python -m pytest tests/test_lib_crypto_keyderiv.py
    python tests/test_lib_crypto_keyderiv.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.crypto import derive_keys, derive_master


def test_same_passphrase_is_deterministic():
    a_enc, a_seed = derive_keys("hunter2")
    b_enc, b_seed = derive_keys("hunter2")
    assert a_enc == b_enc
    assert a_seed == b_seed


def test_different_passphrase_diverges():
    enc1, _ = derive_keys("hunter2")
    enc2, _ = derive_keys("hunter3")
    assert enc1 != enc2


def test_key_lengths_are_32_bytes():
    k_enc, seed = derive_keys("hunter2")
    assert len(derive_master("hunter2")) == 32
    assert len(k_enc) == 32
    assert len(seed) == 32


def test_domain_separation_enc_differs_from_seed():
    k_enc, seed = derive_keys("hunter2")
    assert k_enc != seed


if __name__ == "__main__":
    tests = [
        ("same passphrase deterministic", test_same_passphrase_is_deterministic),
        ("different passphrase diverges", test_different_passphrase_diverges),
        ("keys are 32 bytes", test_key_lengths_are_32_bytes),
        ("domain separation: k_enc != seed", test_domain_separation_enc_differs_from_seed),
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
