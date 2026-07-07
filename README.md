# Steganography algorithm detectability analysis

Companion code for the master's thesis *"Detectability analysis of a custom
steganography algorithm in a forensic setting"*. An extension of a seminar
project from the Computer Forensics course
([nduje/Steganography](https://github.com/nduje/Steganography)).

## Status

**Day 4 -- dataset pipeline.** Real color carriers: a reproducible random subset
(500 images, seed 42) of **ALASKA v2 TIFF 256 COLOR**, converted TIFF->PNG with
**no resampling** (native 256x256 RGB, so no resize/crop -- preserves natural
LSBs). On real covers the documented 255-saturation behavior is quantified:
round-trip corruption occurs exactly on images with a 255 channel in the used
embedding region (see `scripts/verify_dataset.py`).

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
  rates.py         # embedding-rate constants (fraction of capacity) for Day 5+
scripts/
  run_baseline.py      # baseline control-group demo
  run_stego.py         # lib demo, key from --passphrase
  download_alaska.py   # fetch a seeded ALASKA v2 TIFF-256-COLOR subset (http)
  prepare_dataset.py   # TIFF -> lossless PNG covers + manifest (no resampling)
  verify_dataset.py    # read-only report: round-trip + 255-saturation finding
tests/
  test_baseline_roundtrip.py   # baseline round-trip
  test_lib_parity.py           # lib default == baseline, byte-for-byte
  test_lib_roundtrip.py        # lib round-trip (raw key + passphrase, dual-input guard)
  test_lib_hooks.py            # non-default switches raise NotImplementedError
  test_lib_crypto_keyderiv.py  # passphrase -> (k_enc, seed) derivation
data/covers/  # synthetic test PNGs (gradient/noise/saturated)
data/alaska/  # ALASKA v2 covers: raw_tif/ + covers/ (git-ignored), manifest.csv (committed)
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

## Dataset (Day 4)

Real carriers are a reproducible random subset of **ALASKA v2 TIFF 256 COLOR**
(the algorithm is RGB, so native color covers avoid the R=G=B artifact a
grayscale->RGB set would introduce).

```bash
# 1. download a seeded subset of 500 native-256x256 TIFFs
python scripts/download_alaska.py          # -> data/alaska/raw_tif/  (N=500, seed 42)

# 2. TIFF -> lossless PNG (NO resize/crop) + manifest with a 50/50 train/test split
python -m scripts.prepare_dataset --src data/alaska/raw_tif --out data/alaska/covers --seed 42

# 3. read-only verification report (round-trip + 255-saturation finding)
python -m scripts.verify_dataset --covers data/alaska/covers --n 100 --seed 42
```

Notes:
- Images are served over `http://`; the server's **expired HTTPS certificate**
  only affects browser viewing, not the http downloads (the script tolerates an
  http->https redirect via `ssl.CERT_NONE`).
- No resampling: the TIFFs are already 256x256 RGB, so PNG conversion preserves
  the natural LSBs. Any image not exactly 256x256x3 is skipped and reported.
- Capacity is `(256 // 3) * 256 = 21760` characters per cover.
- Only `manifest.csv` is committed; `raw_tif/` and `covers/` are git-ignored.

## Imperceptibility analysis (Day 5)

Fidelity of the **baseline** across embedding rates (improvements are measured
later, for a before/after). Methodology:

- **(A) Global vs region.** Every metric is reported both over the whole image
  (**global**) and over only the pixels the algorithm touched (**region**). At
  low rates the global number is dominated by the untouched area, so it mostly
  reflects *coverage*; the region number isolates *distortion intensity*. The
  region mask is taken by replaying the algorithm's own raster block iterator for
  the payload length (not a formula), so it matches the real path including the
  skipped `x+2 >= width` column. SSIM (windowed) uses the region's bounding-box
  row band -- a documented approximation. Sanity: at rate 1.0 region ~= global.
- **(B) Channels.** MSE/PSNR: combined RGB + per-channel R,G,B + luminance Y.
  SSIM: per-channel average + Y. `Y = 0.299R + 0.587G + 0.114B` (BT.601).
  PSNR peak = 255; SSIM `data_range=255`, `win_size=7`.
- **(C) Payload.** Reproducible printable-ASCII of length `L = round(rate*21760)`;
  content is statistically irrelevant (AES whitening), only `L` matters. Fixed
  raw key (fast, reproducible; not scrypt per image). Payload seed = `f(image, rate)`.
- **(D) Aggregation.** mean +/- std over the 500 covers per rate, plus the
  round-trip failure fraction per rate.

```bash
python -m scripts.measure_imperceptibility --covers data/alaska/covers --workers 16
python -m scripts.plot_imperceptibility        # -> results/figures/*.png
```

Outputs: `results/imperceptibility.csv` (per image x rate; git-ignored),
`results/imperceptibility_summary.csv` (per rate; committed), and four figures in
`results/figures/` (committed).

Result (baseline, n=500 covers per rate):

| rate | PSNR global RGB | PSNR region RGB | SSIM global | SSIM region | round-trip fail |
|------|-----------------|-----------------|-------------|-------------|-----------------|
| 0.05 | 64.18 dB | 51.15 dB | 0.9999 | 0.9982 | 10.6% |
| 0.10 | 61.17 dB | 51.15 dB | 0.9998 | 0.9982 | 12.4% |
| 0.25 | 57.19 dB | 51.15 dB | 0.9996 | 0.9983 | 16.6% |
| 0.50 | 54.18 dB | 51.15 dB | 0.9992 | 0.9983 | 21.0% |
| 1.00 | 51.17 dB | 51.15 dB | 0.9983 | 0.9983 | 25.6% |

The **global** metric changes with rate (it tracks *coverage*), while the
**region** metric is essentially flat (~51.15 dB / ~0.998) -- the per-pixel
distortion intensity is the same regardless of payload size. They converge at
rate 1.0 (sanity check). Round-trip failures rise monotonically with rate,
confirming the 255-saturation bug scales with coverage.

## Detectability: chi-square (Day 6)

First forensic detector, plus a **reusable evaluation harness**
(`analysis/detection.py`: AUC, P_E, ROC) that every later detector (RS/SPA/ML,
Days 7-10) reuses. Convention: a detector maps each image to a score, **higher =
more likely stego**; the harness only compares cover-scores vs stego-scores.

`analysis/chi_square.py` implements the Westfeld Pairs-of-Values attack:

- **Global** -- one score per image. Per channel: PoV statistic on pairs
  {2i, 2i+1}; score = `chi2.sf(stat, df)` (the "probability of embedding").
  Channels combined by pooling statistics (sum of stats, sum of df), per decision D.
- **Positional** -- the p-value along a growing raster prefix; the "cliff" where
  the equalized region ends localizes the sequential payload.

Evaluation on the canonical **test-250** (comparable with later ML) and,
additionally, on **all 500** (robustness). P_E is orientation-agnostic (the
statistic's true detection power, optimal threshold in either direction); AUC is
kept orientation-sensitive so the *sign* of the effect stays visible.

```bash
python -m scripts.run_chisquare --covers data/alaska/covers
python -m scripts.plot_chisquare        # -> results/figures/chisquare_*.png
```

Result (baseline, combined score; test-250):

| rate | AUC | P_E | AUC_R | AUC_G | AUC_B |
|------|-----|-----|-------|-------|-------|
| 0.05 | 0.487 | 0.464 | 0.502 | 0.504 | 0.464 |
| 0.10 | 0.456 | 0.420 | 0.507 | 0.504 | 0.392 |
| 0.25 | 0.352 | 0.308 | 0.514 | 0.513 | 0.224 |
| 0.50 | 0.229 | 0.162 | 0.531 | 0.519 | 0.109 |
| 1.00 | 0.092 | 0.092 | 0.573 | 0.559 | 0.032 |

Findings (reported, not "fixed"):

- **The baseline's "+1" matching does not equalize PoV pairs** the way textbook
  LSB replacement does, so classic chi-square is not merely weak -- its p-value is
  *anti-correlated* with embedding (AUC falls below 0.5, down to 0.09 at full rate).
  The statistic is still discriminative; its textbook orientation is inverted.
- **Weak at low rates, strong at high** (P_E 0.46 -> 0.09): a small sequential
  region barely shifts the whole-image histogram. The **positional** mode exposes
  embedding even at low rates via the cliff (see `chisquare_positional_example.png`).
- **The signal is concentrated in the blue channel** (AUC_B 0.03 vs AUC_R/G ~0.5-0.57
  at full rate): the continuation flag rides the 9th channel (pixel-2 blue), leaving
  a systematic per-pair artifact there. This motivates RS/SPA/ML next.

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
