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

## Detectability: RS analysis (Day 7)

`analysis/rs_analysis.py` implements the Fridrich-Goljan-Du RS (Regular/Singular)
method: groups of 4 pixels in a row, mask `[0,1,1,0]`, smoothness
`f=Σ|xᵢ₊₁−xᵢ|`, flips `F1(x)=x⊕1` / `F₋₁(x)=((x+1)⊕1)−1`. It both **detects**
(p̂ as score → harness) and **estimates the rate** (p̂ via the RS quadratic).
Standard RS (flip = XOR 1); channels combined by mean p̂ (decision C).

```bash
python -m scripts.run_rs --covers data/alaska/covers
python -m scripts.plot_rs        # -> results/figures/rs_*.png
```

Result (baseline, combined; test-250):

| rate | AUC | P_E | mean p̂ | bias | MAE | AUC_R | AUC_G | AUC_B |
|------|-----|-----|--------|------|-----|-------|-------|-------|
| 0.05 | 0.492 | 0.484 | 0.079 | +0.029 | 0.109 | 0.495 | 0.509 | 0.497 |
| 0.10 | 0.495 | 0.484 | 0.074 | −0.026 | 0.137 | 0.494 | 0.505 | 0.497 |
| 0.25 | 0.509 | 0.472 | 0.069 | −0.181 | 0.241 | 0.511 | 0.506 | 0.493 |
| 0.50 | 0.496 | 0.470 | 0.058 | −0.442 | 0.465 | 0.468 | 0.525 | 0.500 |
| 1.00 | 0.496 | 0.466 | 0.032 | −0.968 | 0.968 | 0.464 | 0.496 | 0.503 |

(cover mean p̂ ≈ 0.083.) Findings (reported, not "fixed"):

- **Standard RS fails on "+1".** Detection AUC ≈ 0.5 (chance) at every rate and
  every channel; unlike LSB replacement, "+1" does not create the RS
  regular/singular imbalance. This is **weaker than chi-square** here (which at
  least caught the blue-channel flag artifact) -- contradicting the usual "RS beats
  chi-square at low rates" expectation *for this algorithm*.
- **The rate estimate collapses:** p̂ stays ≈ the cover value (~0.08) regardless of
  the true rate, so the bias grows to −0.97 at full rate. RS effectively always
  reports "no message" (see `rs_estimated_vs_true_rate.png`).
- The estimator is validated on textbook LSB replacement (test: p̂ → 1), so the
  failure is genuinely "+1" evading RS, not an implementation error.

Two classic, LSB-replacement-tuned attacks (chi-square, RS) thus miss (or invert)
on the "+1" design -- direct motivation for the learned detectors on Days 9-10.

## Detectability: SPA (Day 8)

`analysis/spa.py` implements Dumitrescu-Wu-Wang Sample Pair Analysis over
horizontally adjacent pairs (u,v): trace sets X, Y, W (LSB-differ, ⊂ Y), Z (equal)
→ quadratic `0.5(W+Z)p² + (2X−P)p + (Y−X) = 0`, smaller-magnitude root → p̂.
Standard SPA (flip = LSB); channels combined by mean p̂. Same detection +
estimation protocol as RS, for direct comparison.

```bash
python -m scripts.run_spa --covers data/alaska/covers
python -m scripts.plot_spa        # -> results/figures/spa_*.png + rs_vs_spa_estimate.png
```

Result (baseline, combined; test-250):

| rate | AUC | P_E | mean p̂ | bias | AUC_B |
|------|-----|-----|--------|------|-------|
| 0.05 | 0.497 | 0.484 | 0.041 | −0.009 | 0.494 |
| 0.25 | 0.509 | 0.472 | 0.038 | −0.212 | 0.493 |
| 0.50 | 0.502 | 0.460 | 0.035 | −0.465 | 0.484 |
| 1.00 | 0.485 | 0.438 | 0.031 | −0.969 | 0.481 |

(cover p̂ ≈ 0.042.) Findings (confirmatory):

- **SPA behaves like RS on "+1":** detection AUC ≈ 0.5 (chance) at every rate and
  channel; the rate estimate stays ≈ the cover level regardless of the true rate
  (bias → −0.97). SPA's finite-state model assumes a symmetric LSB flip, which
  "+1" is not.
- **RS and SPA agree** (`rs_vs_spa_estimate.png`): two independent rate estimators
  both collapse to ~cover on "+1" -- an internal-consistency check that the miss
  is a property of "+1", not of one estimator.

**Summary of the classical structural attacks (Days 6-8):** all three are tuned
to LSB replacement and none works on the "+1" design -- chi-square is inverted
(signal only via the blue-channel flag artifact), RS and SPA are blind (chance
detection, collapsed rate estimates). This is the empirical case for the learned
detectors on Days 9-10.

## Detectability: machine learning setup (Day 9)

The classical attacks (Days 6-8) are model-based -- they assume LSB replacement
and miss "+1". A learned detector assumes no mechanism; it learns the traces from
data. This is the real test of the algorithm.

- **Features: SCRM** (Spatial Color Rich Model, q=1; DDE `SCRMQ1`). Color, **not**
  grayscale SRM -- the flag signal lives in the blue channel, and a grayscale
  model would flatten color and could dilute exactly that trace.
- **Extraction:** the DDE `SCRMQ1.m` is driven directly through Octave by
  `scripts/extract_scrm.py` (self-contained; it does not import Aletheia's Python
  stack, avoiding TensorFlow/pandas). Octave is installed as the portable build.
- **Classifier + evaluation are ours** (Day 10), through the same
  `analysis/detection.py` harness, so ML numbers land in the SAME AUC/P_E table as
  chi-square/RS/SPA.
- **Protocol:** one classifier per rate (5 curves), train on train-250, test on
  test-250 (from the manifest).
- **No leakage** (critical): a cover and its stego share the manifest split (keyed
  by filename), so the classifier cannot learn the scene instead of the embedding
  (`analysis/ml_features.py`, enforced in `tests/test_ml_features.py`).

```bash
# 1. stego sets (baseline, fixed key), git-ignored; one rate at a time if disk is tight
python -m scripts.make_stego_sets --rate 1.0

# 2. SCRM features via Octave (slow; single-threaded)
python -m scripts.extract_scrm --images data/alaska/covers      --out data/alaska/features/covers   --octave <octave-cli>
python -m scripts.extract_scrm --images data/alaska/stego/r1.0  --out data/alaska/features/stego_r1.0 --octave <octave-cli>
```

Everything heavy is git-ignored (`data/alaska/stego/`, `data/alaska/features/`,
`*.fea`, `aletheia/`, `octave/`); only the code is versioned. Training,
evaluation, and P_E/AUC-vs-rate curves are Day 10.

## Detectability: machine learning + whole-spectrum comparison (Day 10)

The learned detector closes the baseline assessment. Unlike chi2/RS/SPA it assumes
no embedding mechanism -- it learns the traces from the SCRM features.

- **Detectors** (`analysis/ml_classifier.py`): an FLD **ensemble** (sklearn
  equivalent of Kodovsky-Fridrich: bagged LDA on random 256-feature subspaces) and
  a linear **SVM** control (standardize + `LinearSVC`, C=0.01 for the p>>n regime).
  No PCA. Scores go through our harness, so ML sits in the same P_E/AUC table.
- **Protocol** (`scripts/run_ml_detection.py`): per rate, **10 random 250/250 image
  splits** (leakage-free -- an image's cover and stego stay on the same side),
  train both models, report mean +/- std.

ML detection (test protocol, 10 splits):

| rate | ensemble AUC / P_E | SVM AUC / P_E |
|------|--------------------|---------------|
| 0.05 | 0.578 / 0.431 | 0.619 / 0.397 |
| 0.10 | 0.668 / 0.368 | 0.746 / 0.303 |
| 0.25 | 0.855 / 0.217 | 0.923 / 0.132 |
| 0.50 | 0.964 / 0.090 | 0.979 / 0.051 |
| 1.00 | 0.997 / 0.020 | 0.996 / 0.012 |

Ensemble and SVM agree (robust); detection climbs from near-chance at the smallest
payload to near-perfect at full rate.

**Where is the signal?** (`scripts/run_ml_groups.py`) Decision 4 asked for an R/G/B
split, but **SCRM has no clean per-channel decomposition** -- its 69 submodels are
either spatial (12753 dims) or 3D cross-channel "color" cooccurrences (5404 dims,
submodel type ending in `c`). So we compare spatial vs color feature groups
instead (documented deviation). Finding: at low rates the **color/cross-channel
features carry slightly more signal** than the spatial ones (r=0.05 AUC 0.595 vs
0.567), despite being fewer -- consistent with the flag perturbing the blue channel
and creating cross-channel structure (not a direct R/G/B proof).

**StegExpose** (`scripts/run_stegexpose.py`), an illustrative practitioner baseline
(threshold-dependent, prone to false alarms; fuses Primary Sets / Chi-Square /
Sample Pairs / RS): near-chance at every rate (AUC 0.51-0.55, P_E 0.44-0.46) -- it
misses "+1" like RS/SPA, as expected.

### Whole-spectrum comparison (P_E vs rate, test-250; lower = better)

| rate | chi2 | RS | SPA | **ML (ens)** | StegExpose |
|------|------|-----|-----|----------|------------|
| 0.05 | 0.464 | 0.484 | 0.484 | **0.431** | 0.458 |
| 0.10 | 0.420 | 0.484 | 0.478 | **0.368** | 0.466 |
| 0.25 | 0.308 | 0.472 | 0.472 | **0.217** | 0.460 |
| 0.50 | 0.162 | 0.470 | 0.460 | **0.090** | 0.456 |
| 1.00 | 0.092 | 0.466 | 0.438 | **0.020** | 0.442 |

The learned detector is strongest at **every** rate and the only method that
detects meaningfully at low payloads; chi-square is second (via the blue-channel
flag artifact); RS, SPA and StegExpose sit near chance. This full spectrum --
hand-crafted -> learned -> off-the-shelf tool -- is the firm "before" baseline for
the before/after comparison against Improvements 1-3 (Days 11-13). See
`results/figures/all_attacks_comparison.png`.

```bash
python -m scripts.run_ml_detection          # ensemble + SVM -> ml_summary.csv
python -m scripts.run_ml_groups --octave <octave-cli>   # spatial vs color -> ml_group.csv
python -m scripts.run_stegexpose --java <java> --jar StegExpose.jar
python -m scripts.plot_ml                    # all figures incl. all_attacks_comparison.png
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

## References

Sources for the implemented formulas (for citation in the written thesis).

**Steganalysis methods** (`analysis/`):

- **Chi-square / Pairs-of-Values attack** (Day 6, `analysis/chi_square.py`) --
  A. Westfeld, A. Pfitzmann, "Attacks on Steganographic Systems," in *Information
  Hiding*, LNCS 1768, Springer, 2000, pp. 61-76.
- **RS analysis** (Day 7, `analysis/rs_analysis.py`) -- J. Fridrich, M. Goljan,
  R. Du, "Reliable Detection of LSB Steganography in Color and Grayscale Images,"
  in *Proc. ACM Workshop on Multimedia and Security*, 2001, pp. 27-30.
- **Sample Pair Analysis** (Day 8, `analysis/spa.py`) -- S. Dumitrescu, X. Wu,
  Z. Wang, "Detection of LSB Steganography via Sample Pair Analysis," *IEEE Trans.
  Signal Processing*, vol. 51, no. 7, 2003.
  Authors' copy (used for the equations):
  <https://www.ece.mcmaster.ca/~sorina/papers/LSBfinalTSP.pdf>.
  Trace-set / quadratic cross-check:
  <https://steveryan.net/steganalysis-sample-pairs-analysis-explained.html>.
  (Verify the exact page numbers against the source before citing -- indexed
  listings disagree, e.g. pp. 1995-2007 vs pp. 355-372.)

**Fidelity metrics** (Day 5, `lib/metrics.py`):

- **SSIM** -- Z. Wang, A. C. Bovik, H. R. Sheikh, E. P. Simoncelli, "Image Quality
  Assessment: From Error Visibility to Structural Similarity," *IEEE Trans. Image
  Processing*, vol. 13, no. 4, 2004, pp. 600-612 (via scikit-image
  `structural_similarity`).
- **PSNR** -- standard peak-signal-to-noise ratio (peak = 255).
- **Luminance (Y)** -- ITU-R Recommendation BT.601 (Y = 0.299R + 0.587G + 0.114B).

**Dataset** (Day 4):

- **ALASKA v2** -- R. Cogranne, Q. Giboulot, P. Bas, "ALASKA-2: Challenging
  Academic Research on Steganalysis with Realistic Images," in *IEEE Int. Workshop
  on Information Forensics and Security (WIFS)*, 2020. Dataset: <http://alaska.utt.fr>.

All citation details (especially page numbers) should be verified against the
primary sources before inclusion in the written work.
