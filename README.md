# Steganography algorithm detectability analysis

Companion code for the master's thesis *"Detectability analysis of a custom
steganography algorithm in a forensic setting"*. An extension of a seminar
project from the Computer Forensics course
([nduje/Steganography](https://github.com/nduje/Steganography)).

## Status

**Day 3 -- real key origin.** The stego key now comes from a passphrase:
`scrypt` (fixed app salt) stretches it into a 32-byte master secret, then `HKDF`
splits it into `k_enc` (AES-CTR key) and `seed` (reserved for future PRNG
embed-order) via domain separation. `hide()`/`expose()` take a dual input --
`passphrase=` (CLI/demo) or `key=` (raw key, used by the parity tests). The
AES-CTR core is **unchanged**, so parity stays byte-identical. The seminar's
socket RSA/DH handshake is ported to `lib/keyexchange.py` as a **deprecated,
in-process simulation that is called nowhere**.

**Day 2 -- parameterized library.** The baseline is refactored into a clean,
parameterized package `lib/`. Its behavior is exposed as explicit "switches"
(`StegoConfig`) whose **default values reproduce the baseline 1:1** -- proven
byte-for-byte by a parity test on all three covers. No behavior was changed;
non-default switches are inert hooks (`NotImplementedError`) reserved for the
improvement phase. `baseline/` stays **frozen** as the control group.

**Day 1 -- foundations.** Environment + the starting ("baseline") algorithm
working end-to-end without sockets, as a reproducible control group, with logic
intentionally identical to the seminar repo.

## Structure

```
baseline/     # frozen control group -- the old algorithm, decoupled from sockets
  image_utils.py   # encoding/decoding (RGB parity, logic as in the original)
  message_utils.py # message <-> bits
  crypto.py        # AES-CTR (+ stand-in key until DH arrives on Day 3)
  stego.py         # hide_message / expose_message
lib/          # clean, parameterized library (default config == baseline)
  config.py        # StegoConfig -- the switches (bpp, matching, order, ...)
  message.py       # message <-> bits (clean copy, identical behavior)
  crypto.py        # AES-CTR (unchanged) + passphrase key derivation (scrypt/HKDF)
  embedding.py     # parameterized embed/extract core
  algorithm.py     # StegAlgorithm: hide() / expose() (passphrase= or key=)
  keyexchange.py   # DEPRECATED in-process RSA/DH simulation (called nowhere)
scripts/
  run_baseline.py  # baseline control-group demo
  run_stego.py     # lib demo, key from --passphrase
tests/
  test_baseline_roundtrip.py   # baseline round-trip
  test_lib_parity.py           # lib default == baseline, byte-for-byte
  test_lib_roundtrip.py        # lib round-trip (raw key + passphrase, dual-input guard)
  test_lib_hooks.py            # non-default switches raise NotImplementedError
  test_lib_crypto_keyderiv.py  # passphrase -> (k_enc, seed) derivation
data/covers/  # synthetic test PNGs (BOSSBase pipeline = Day 4)
results/      # output stego PNGs (git-ignored)
```

## Using the library

```python
from lib import StegAlgorithm, StegoConfig
from lib.algorithm import load_image

alg = StegAlgorithm()                       # default config == frozen baseline

# key from a passphrase (scrypt -> HKDF); the CLI/demo path
alg.hide("secret", "data/covers/cover_noise.png", "results/out.png", passphrase="my pass")
alg.expose(load_image("results/out.png"), passphrase="my pass")

# or a raw 32-byte key / base64 string, used directly (reproducible experiments)
alg.hide("secret", "data/covers/cover_noise.png", "results/out.png", key=raw_key)
```

Exactly one of `passphrase=` / `key=` must be given (else `ValueError`).

`StegoConfig` switches (Day 2: only the defaults are implemented):

| switch             | default (baseline)     | hook (future improvement) |
|--------------------|------------------------|---------------------------|
| `bits_per_channel` | `1`                    | other rates               |
| `matching_mode`    | `"plus_one"`           | `"pm_one"` (+/-1)         |
| `pixel_order`      | `"sequential"`         | `"prng"`                  |
| `termination`      | `"continuation_flag"`  | `"length_header"`         |
| `saturation_255`   | `"skip"`               | `"fix"`                   |

## Running

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m scripts.run_baseline
python -m scripts.run_stego --message "Hi" --passphrase "correct horse"

# tests (standalone; or `python -m pytest tests/`)
python tests/test_baseline_roundtrip.py
python tests/test_lib_parity.py
python tests/test_lib_roundtrip.py
python tests/test_lib_hooks.py
python tests/test_lib_crypto_keyderiv.py
```

## Cryptography (Day 3)

Key origin -- **no sockets**:

```
passphrase --scrypt(APP_SALT)--> master (32B) --HKDF--> k_enc  (info "stego:aes-ctr:enc")
                                               \-HKDF--> seed   (info "stego:embed-order")
```

- **AES-CTR is untouched** from the baseline (parity-safe); `k_enc` feeds it.
- `seed` is derived but **unused** today (embed order stays sequential; PRNG
  order is a future improvement).
- `lib/keyexchange.py` faithfully ports the seminar's RSA/DH + RSA-PSS handshake
  as an in-process simulation. It is **deprecated and imported nowhere** in the
  live pipeline; importing it emits a `DeprecationWarning`.

Intentionally-kept properties (documented, **not** fixed here):

- **Deterministic IV** = `SHA256(key)[:16]` -> nonce reuse across messages under
  the same key.
- **Fixed scrypt salt** -> the same passphrase always yields the same master
  secret (reproducible, no per-run randomness).

## Known baseline behaviors (confirmed Day 1)

Recorded as a starting point for the improvement phase -- we *measure*, we
do not criticize:

1. **Non-ASCII characters** (e.g. `č`, `—`): `bin(ord(char)).zfill(8)` yields
   >8 bits for ord>255 -> shifts the whole bit stream -> wrong reconstruction.
   Tied to Improvement 3 (length header + correctness).
2. **Saturated (255) cover/channels**: the algorithm skips channels at 255 ->
   embedding is dropped, decoding reads garbage. Tied to Improvement 3
   (255 edge-case fix).
3. Plain ASCII on a non-saturated cover: **round-trip OK**.
