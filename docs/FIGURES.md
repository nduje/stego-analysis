# Figures

The print-ready figures are in `results/figures/final/` as vector **SVG**
(`final/svg/`, text as paths so the diacritics survive anywhere) and 1200-DPI **PNG**
(`final/png/`). All are generated from `results/csv/master_matrix.csv` by
`scripts/report/make_final_figures.py`, styled by `scripts/report/style.py`. The figures
themselves are labelled in Croatian (they go into a Croatian thesis); filenames, columns
and code stay English. Two figures also read a source CSV the matrix does not carry:
`chisquare_positional` (positional p-values) and the ML `*_group_*` figures (spatial/color
breakdown).

The `results/figures/working/` folder holds the earlier ad-hoc figures (the working
record); `results/figures/_archive/` holds superseded or incomplete ones.

| file | chapter | what it shows |
|------|---------|---------------|
| psnr_vs_rate | imperceptibility | HILL's adaptivity gives higher PSNR for the same payload (it changes fewer pixels) |
| psnr_beforeafter | imperceptibility | region PSNR is essentially unchanged by the improvements (the change is +/-1 either way) |
| ssim_beforeafter | imperceptibility | SSIM stays near 1 across all improved configurations |
| chisquare_auc_vs_rate | classical steganalysis | the baseline's chi-square is inverted (AUC -> 0.03), not blind |
| chisquare_positional | classical steganalysis | sequential embedding leaves a positional cliff; PRNG order scatters it |
| rs_vs_spa_estimate | classical steganalysis | RS badly under-estimates our "+1" embedding, i.e. it is blind to it |
| ml_pe_vs_rate | machine learning | the learned detector separates every version; HILL is the hardest |
| ml_group_pe | machine learning | the baseline's ML signal sits slightly more in the colour (cross-channel) submodels |
| chisquare_aucB_beforeafter | improvements | **single-number proof of P3**: removing the flag takes AUC_B from 0.03 to ~0.58 |
| chisquare_pe_beforeafter | improvements | P3 and `all` become chi-square-blind (the flag was the trace) |
| rs_pe_beforeafter | improvements | only P2 (the flag x pm_one interaction) is RS-visible; flag-free configurations are blind |
| ml_pe_beforeafter | improvements | P3 helps ML most, P2 slightly hurts; `all` reaches P_E ~0.086 |
| ml_group_beforeafter | improvements | P3 lifts the spatial group most (the flag was a spatial periodicity) |
| reference_chisquare_rs_spa | reference methods | **positive control**: LSB-R is caught (AUC -> 1) while LSB-M and HILL evade |
| all_attacks_comparison_multi | central figure | the full spectrum: P_E vs rate, our configurations against the references |
| all_attacks_comparison_single | central figure | the same comparison as a single r=1.0 profile -- the visual twin of the main table |

The corresponding tables are in `results/tables/` (`main_table`, `imperceptibility`,
`detectability_by_rate`, `reference_payload`), as CSV and Word-pasteable HTML.

## Data-derived illustrations

Four extra figures generated from one real ALASKA II cover (`00054.png`, fixed passphrase,
rate 0.25) and the measured score distributions, in the same style
(`scripts/report/make_illustration_figures.py`). The measured numbers are printed to stdout
for the prose; none are drawn on the figures.

| file | chapter | kind | what it shows |
|------|---------|------|---------------|
| illus_triptych_cover_stego_diff | 5.1 | data-derived illustration (single image) | cover, stego, and the difference amplified x50 -- invisible to the eye, the +/-1 noise in the embedded region |
| illus_changemap_seq_vs_prng | 5.2 | data-derived illustration (single image) | the touched-pixel map: raster embedding fills a top band, PRNG scatters the same block count across the image |
| illus_blue_odd_flag | 5.4 | data-derived illustration (single image) | the odd-value share per blue-channel value: with the flag it separates above 0.5 across the mid range, P3 brings it back to ~0.5 |
| illus_chi_inversion_ecdf | 5.2 | data-derived (population distribution, 250 images) | ECDFs of the chi-square scores of covers vs stego (250-image test split): the stego curve lies above the covers' -> stego scores are lower (the inversion). A population distribution, not one image. |
