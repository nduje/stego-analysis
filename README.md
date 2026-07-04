# Steganography algorithm detectability analysis

Companion code for the master's thesis *"Detectability analysis of a custom
steganography algorithm in a forensic setting"*. An extension of a seminar
project from the Computer Forensics course
([nduje/Steganography](https://github.com/nduje/Steganography)).

## Status

**Day 1 -- foundations.** Environment set up + the starting ("baseline")
algorithm works end-to-end, without sockets, as a reproducible **control
group**. The algorithmic logic is intentionally *identical* to the seminar
repo; the refactor into a parameterized library follows on Day 2.

## Structure

```
baseline/     # the old algorithm, decoupled from sockets (control group)
  image_utils.py   # encoding/decoding (RGB parity, logic as in the original)
  message_utils.py # message <-> bits
  crypto.py        # AES-CTR (+ stand-in key until DH arrives on Day 3)
  stego.py         # hide_message / expose_message
scripts/
  run_baseline.py  # end-to-end round-trip demo
tests/
  test_baseline_roundtrip.py
data/covers/  # synthetic test PNGs (BOSSBase pipeline = Day 4)
results/      # output stego PNGs (git-ignored)
```

## Running

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m scripts.run_baseline
python -m scripts.run_baseline --cover data/covers/cover_noise.png --message "Hello!"
python tests/test_baseline_roundtrip.py
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
