# Reproducibility

Everything in `results/` is regenerated from code and a fixed seed/key. The committed
CSVs (`results/csv/`) and figures (`results/figures/`) are the artifacts, so the numbers
can be inspected without re-running the ~10 h pipeline (see "Cost" below).

## Environment

- **Python 3.10.11**
- Libraries: `numpy 1.26.4`, `scipy 1.15.3`, `scikit-learn 1.7.2`, `scikit-image 0.25.2`,
  `matplotlib 3.10.9`, `Pillow 12.3.0`, `cryptography 42.0.6`
- **Octave 10.1.0** (SCRM feature extraction + the HILL simulator) — GNU Octave, run as
  `octave-cli`. The SCRM code (`SCRMQ1.m`) and HILL simulator (`HILL_COLOR.m`) are fetched
  from Aletheia's resource repo (see Sources at the bottom).
- **Temurin JRE 21** + `StegExpose.jar` (the StegExpose practitioner baseline).

External tools (Octave, JRE, StegExpose.jar, the Aletheia cache) are **not** in the repo
(`.gitignore`); install/fetch them separately.

## Dataset

ALASKA II (`TIFF-256-COLOR`). A reproducible random subset of **500 images (seed 42)** is
selected and converted TIFF->PNG with no resampling (native 256x256 RGB). The train/test
split (250/250) is `data/alaska/manifest.csv` (committed; the images themselves are not).

```
python -m scripts.data.download_alaska        # fetch + subset (seed 42)
python -m scripts.data.prepare_dataset        # TIFF -> PNG, manifest
python -m scripts.data.verify_dataset         # sanity + 255-saturation quantification
```

## Pipeline (in order)

| step | command | ~time |
|------|---------|-------|
| 1. stego sets (our configs) | `python -m scripts.data.make_stego_sets --config <cfg> --rate <r>` | fast |
| 2. reference sets (LSB-R/M, HILL) | `python -m scripts.data.make_reference_sets --method <m> [--octave <cli>]` | fast / HILL slow |
| 3. SCRM features (disk-safe: gen->extract->delete) | `python -m scripts.extract.reanalysis_extract --config <cfg> --octave <cli> --workers 4` | **~25 min / rate** |
|   reference features | `python -m scripts.extract.reference_extract --method <m> --octave <cli> --workers 4` | ~25 min / rate |
| 4. classical attacks | `python -m scripts.measure.run_attacks_reanalysis` / `...run_attacks_reference` | ~30-45 min |
| 5. ML detection + groups | `python -m scripts.measure.run_ml_detection --config ...` / `...run_ml_groups` | **~1 h / config (SVM)** |
| 6. StegExpose | `python -m scripts.measure.run_stegexpose --java <java> --jar StegExpose.jar --config ...` | ~15 min |
| 7. imperceptibility | `python -m scripts.measure.measure_imperceptibility_reanalysis` / `...reference` | ~30 min |
| 8. matrix | `python -m scripts.report.build_matrix` | seconds |
| 9. tables + figures | `python -m scripts.report.make_tables` / `...make_final_figures` | ~2 min |

`--config` values: `baseline, p1, p2, p3, p13, all`; `--method`: `lsbr, lsbm, hill`.
Rates: `0.05, 0.10, 0.25, 0.50, 1.00`.

## Seeds and key

- Dataset subset + split: **seed 42**.
- Stego generation uses a **fixed key** `base64(bytes(range(32)))` and per-(image,rate)
  deterministic payloads, so every config/method embeds at matched coverage on the same
  covers (`scripts/data/make_stego_sets.py`, `make_reference_sets.py`).
- ML uses 10 leakage-free 250/250 splits (an image's cover and stego stay on the same
  side), seeds `0..9`.

## Cost

A full regeneration is **~10 hours**, dominated by SCRM feature extraction (Octave, the
bottleneck). Because of that the extracted-feature-derived CSVs live in `results/csv/` in
the repo: anyone can re-run `build_matrix` + `make_tables` + `make_final_figures` (seconds)
and reproduce every table/figure without the 10 h of extraction. `verify_provenance`
confirms every table number traces to `master_matrix.csv`.

## Known pitfalls

- **Windows console (cp1252)** can't print Croatian/`χ`; keep program output ASCII and open
  files with `encoding="utf-8"`.
- **Octave / Java need `C:/...` paths**, not MSYS `/c/...`, when passed from Python.
- **LinearSVC** on 18157-dim features (p >> n): `C=0.01, dual=True, tol=1e-3, max_iter=20000`
  (otherwise it does not converge).
- **StegExpose CSV** has a leading blank line; filter it before parsing; score column is
  "Fusion (mean)".
- **SCRM color marker** is the `c` just before `_q1` (e.g. `s1_minmax22c_q1`), used to split
  spatial (12753) vs color (5404) submodels.
- Do **not** run `run_ml_groups` and `run_ml_detection` at the same time (both use an
  ensemble with `n_jobs=4` -> CPU oversubscription).
- The machine's disk can shrink under RAM pressure (Windows pagefile growth), independent
  of our files; extraction uses `--workers 4` and deletes stego PNGs per rate to stay
  disk-safe.

## Sources

- SCRM features: `SCRMQ1.m` from Aletheia's `aletheia-external-resources` repo.
- HILL simulator: `HILL_COLOR.m`, same repo; original code (c) 2014 Shenzhen University
  (Ming Wang); method from B. Li, M. Wang, J. Huang, X. Li, "A New Cost Function for
  Spatial Image Steganography", IEEE ICIP 2014.
- Dataset: ALASKA II steganalysis challenge.
