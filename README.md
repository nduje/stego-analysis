# Steganography algorithm detectability analysis

Companion code for the master's thesis *"Detectability analysis of a custom
steganography algorithm in a forensic setting"*. An extension of a seminar
project from the Computer Forensics course
([nduje/Steganography](https://github.com/nduje/Steganography)).

## Status

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
  crypto.py        # AES-CTR (copy for now; real RSA/DH on Day 3)
  embedding.py     # parameterized embed/extract core
  algorithm.py     # StegAlgorithm: hide() / expose()
scripts/
  run_baseline.py  # end-to-end round-trip demo
tests/
  test_baseline_roundtrip.py   # baseline round-trip
  test_lib_parity.py           # lib default == baseline, byte-for-byte
  test_lib_roundtrip.py        # lib round-trip
  test_lib_hooks.py            # non-default switches raise NotImplementedError
data/covers/  # synthetic test PNGs (BOSSBase pipeline = Day 4)
results/      # output stego PNGs (git-ignored)
```

## Using the library

```python
from lib import StegAlgorithm, StegoConfig
from lib.algorithm import load_image

alg = StegAlgorithm()                       # default config == frozen baseline
alg.hide("secret", key, "data/covers/cover_noise.png", "results/out.png")
alg.expose(load_image("results/out.png"), key)
```

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
python -m scripts.run_baseline --cover data/covers/cover_noise.png --message "Hello!"

# tests (standalone; or `python -m pytest tests/`)
python tests/test_baseline_roundtrip.py
python tests/test_lib_parity.py
python tests/test_lib_roundtrip.py
python tests/test_lib_hooks.py
```

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
