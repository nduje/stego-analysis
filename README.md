# stego-analysis

Forensic detectability analysis of an authored spatial steganography algorithm. The
algorithm hides a message in the RGB pixel parities of a cover image; this project measures
how detectable it is across the full spectrum of steganalysis (chi-square, RS, SPA, machine
learning, StegExpose), builds three improvements, and re-measures — placing the result next
to classic LSB methods and a modern adaptive one. It extends a prior seminar project
([nduje/Steganography](https://github.com/nduje/Steganography)) and is the software artifact
of a master's thesis.

## Key results

At full embedding (rate 1.0), P_E is the detection error (0.5 = a blind attacker, 0 = a
perfect one); PSNR is over the whole image (total distortion at equal payload).

| version | PSNR (dB) | round-trip | χ² | RS | SPA | StegExpose | ML |
|---------|-----------|-----------|----|----|-----|-----------|----|
| **baseline** | 51.2 | 74% ok | 0.09\* | 0.47 | 0.44 | 0.44 | **0.02** |
| **all** (baseline + P1+P2+P3) | 51.7 | 100% ok | 0.40 | 0.47 | 0.45 | 0.44 | 0.09 |
| LSB-R (replacement) | 51.7 | n/a | 0.11 | **0.02** | **0.00** | **0.02** | 0.08 |
| LSB-M (matching) | 51.7 | n/a | 0.38 | 0.47 | 0.46 | 0.46 | 0.09 |
| HILL (adaptive) | **54.9** | n/a | 0.47 | 0.47 | 0.46 | 0.47 | **0.20** |

\* the baseline's chi-square is *inverted* (AUC ≈ 0.03): an attacker who knows the method
detects it. Full table: `results/tables/`; central figures:
`results/figures/final/{png,svg}/all_attacks_comparison_{single,multi}.*`.

**In one sentence:** the three improvements take the algorithm from *trivially and
invertibly detectable* to *blind to every structural attack and at LSB-matching level
against the learned detector* — a large, honestly-bounded gain that still stops short of
the adaptive state of the art (HILL is ~2.3× harder for the ML detector *and* higher
quality, because it changes far fewer pixels for the same payload).

## The algorithm

The cover is an RGB image. A group of **3 pixels encodes one character**: 8 data bits are
written into the parities (odd/even) of 8 of the channels, and a 9th channel carries a
**continuation flag** that marks where the message ends. The message is encrypted
(AES-CTR) before embedding, so the payload is indistinguishable from random. A parity is
set by nudging a channel value by +1 when needed ("+1" matching), skipping value 255.

`lib/` is a parameterized re-implementation whose **defaults reproduce the baseline
byte-for-byte** (guaranteed by a parity test). Three improvements are exposed as switches
in `StegoConfig`; each changes one thing:

- **P1 — `pixel_order="prng"`**: the 3-pixel blocks are visited in a key-seeded random
  order instead of raster order, so the embedding has no positional structure.
- **P2 — `matching_mode="pm_one"`**: parities are set by a *symmetric* ±1 (edge-safe:
  0→+1, 255→−1) instead of the asymmetric "+1"; this also removes the 255-saturation bug,
  so round-trip succeeds on every cover.
- **P3 — `termination="length_header"`**: a 16-bit length is prepended to the plaintext
  before encryption, so the message end is known without the continuation flag — the flag
  (a fixed per-block modification of one channel) is no longer written.

`all` is P1+P2+P3; `p13` is P1+P3 (no P2). AES-CTR and key derivation (scrypt + HKDF from a
passphrase) live in `lib/crypto.py`.

## Methodology

- **Dataset:** a reproducible 500-image subset (seed 42) of ALASKA II, native 256×256 RGB,
  split 250/250 train/test.
- **Evaluation:** every attack produces a per-image score; detectability is reported as
  **AUC** and the orientation-agnostic **P_E** (minimum decision error), so one number
  compares across attacks. Headline numbers are on the 250-image test set.
- **Attacks:** chi-square (Pairs-of-Values), RS and SPA (LSB estimators), a learned
  detector (SCRM 18157-dim colour features via Octave + an FLD ensemble and a linear-SVM
  control, over 10 leakage-free 250/250 splits), and StegExpose as a practitioner baseline.
- **Reference methods:** LSB-R and LSB-M (written here) and HILL (adaptive, the original
  authors' Octave simulator), all **payload-aligned** to our algorithm — every reference
  embeds the same absolute number of bits our algorithm embeds at a given rate.
- Embedding rates are fractions of capacity: 0.05, 0.10, 0.25, 0.50, 1.00.

All measurements are collected into one source of truth,
`results/csv/master_matrix.csv`, from which every table and figure is generated.

## Repository layout

```
baseline/     the original seminar algorithm, frozen as a control group (do not edit)
lib/          the parameterized algorithm + StegoConfig switches + crypto
reference/    LSB-R, LSB-M, and payload alignment (HILL is an external Octave simulator)
analysis/     the attacks (chi_square, rs, spa, ml_*) + the shared detection harness
scripts/
  data/       download/prepare the dataset, generate stego and reference sets
  extract/    SCRM feature extraction (disk-safe: generate -> extract -> delete)
  measure/    run the attacks + imperceptibility measurements
  report/     build the matrix, tables, and final figures (style is the single source)
results/
  csv/        the committed measurement CSVs + master_matrix.csv
  tables/     thesis tables (CSV + Word-pasteable HTML)
  figures/    final/ (print SVG+PNG), working/ (day-to-day), _archive/ (superseded)
tests/        algorithm/analysis suites + a table-provenance check
docs/         REPRODUCIBILITY.md, FIGURES.md
```

## Running

Minimal demo (needs a cover image):

```bash
python -m scripts.data.run_stego --cover <cover.png> --message "Hello!"
```

Regenerate the matrix, tables, and figures from the committed CSVs (seconds, no heavy
recomputation):

```bash
python -m scripts.report.build_matrix       # results/csv/master_matrix.csv + main_table.csv
python -m scripts.report.make_tables        # results/tables/{csv,html}/
python -m scripts.report.make_final_figures # results/figures/final/{svg,png}/
python -m scripts.report.verify_provenance  # every table number traces to the matrix
```

Run the tests:

```bash
for t in tests/test_*.py; do python "$t"; done
```

## Reproducibility

A full regeneration (dataset → stego → SCRM extraction → attacks → matrix) is ~10 hours,
dominated by SCRM feature extraction. The committed CSVs let anyone reproduce every table
and figure in seconds without that cost. Environment, exact pipeline, seeds, and known
pitfalls are in **[docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)**.

## Results and figures

The print-ready figures and what each one shows are indexed in
**[docs/FIGURES.md](docs/FIGURES.md)**; the tables are in `results/tables/`.

## Literature and licenses

- HILL simulator: `HILL_COLOR.m` from Aletheia's resource repository; original code
  © 2014 Shenzhen University (Ming Wang), from B. Li, M. Wang, J. Huang, X. Li,
  *"A New Cost Function for Spatial Image Steganography"*, IEEE ICIP 2014. Licensed for
  educational/research use.
- SCRM features (`SCRMQ1.m`) and the ALASKA II dataset are used via their respective
  sources (see docs/REPRODUCIBILITY.md).
- Attacks implemented from their original papers: Westfeld & Pfitzmann (chi-square),
  Fridrich et al. (RS), Dumitrescu, Wu & Wang (SPA).
