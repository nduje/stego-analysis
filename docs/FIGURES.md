# Figures

The print-ready figures are in `results/figures/final/` as vector **SVG**
(`final/svg/`, text as paths so the Croatian diacritics survive anywhere) and 1200-DPI
**PNG** (`final/png/`). All are generated from `results/csv/master_matrix.csv` by
`scripts/report/make_final_figures.py`, styled by `scripts/report/style.py`. Croatian
labels are in the figures; filenames stay English. Two figures also read a source CSV the
matrix does not carry: `chisquare_positional` (positional p-values) and the ML `*_group_*`
figures (spatial/color breakdown).

The `results/figures/working/` folder holds the earlier ad-hoc figures (the day-by-day
record); `results/figures/_archive/` holds superseded/incomplete ones.

| file | naslov | poglavlje | tvrdnja |
|------|--------|-----------|---------|
| psnr_vs_rate | PSNR (globalni) po stopi | neprimjetnost | HILL's adaptivity gives higher PSNR for the same payload (fewer pixels changed) |
| psnr_beforeafter | PSNR (regija): prije i poslije | neprimjetnost | region PSNR is essentially unchanged by the improvements (+/-1 magnitude) |
| ssim_beforeafter | SSIM: prije i poslije | neprimjetnost | SSIM stays near 1 across all improved configs |
| chisquare_auc_vs_rate | χ²: AUC i inverzija na osnovnom | klasična steganaliza | baseline chi-square is inverted (AUC -> 0.03), not blind |
| chisquare_positional | Pozicijski χ² profil | klasična steganaliza | sequential embedding shows a positional cliff; PRNG order scatters it |
| rs_vs_spa_estimate | RS: procijenjena stopa | klasična steganaliza | RS badly under-estimates our "+1" embedding (blind) |
| ml_pe_vs_rate | ML: detektabilnost svih verzija | strojno učenje | the learned detector separates everything; HILL is hardest |
| ml_group_pe | ML značajke: osnovni algoritam | strojno učenje | baseline's ML signal sits slightly more in the color (cross-channel) submodels |
| chisquare_aucB_beforeafter | χ² u plavom kanalu (AUC_B) | poboljšanja | **single-number proof of P3**: removing the flag takes AUC_B 0.03 -> ~0.58 |
| chisquare_pe_beforeafter | χ²: prije i poslije | poboljšanja | P3/all become chi-square-blind (the flag was the trace) |
| rs_pe_beforeafter | RS: prije i poslije | poboljšanja | only P2 (flag x pm_one interaction) is RS-visible; flag-free configs are blind |
| ml_pe_beforeafter | ML: prije i poslije | poboljšanja | P3 helps ML most; P2 slightly hurts; `all` reaches ~0.086 |
| ml_group_beforeafter | ML značajke prije i poslije | poboljšanja | P3 lifts the spatial group most (flag was a spatial periodicity) |
| reference_chisquare_rs_spa | Napadi na referentne metode | reference | **positive control**: LSB-R is caught (AUC -> 1); LSB-M/HILL evade |
| all_attacks_comparison_multi | Usporedba svih metoda i napada (po stopi) | središnja slika | full spectrum, P_E vs rate, our configs vs references |
| all_attacks_comparison_single | Profil pri punoj ugradnji (r=1.0) | središnja slika | the r=1.0 profile -- visual twin of the main table |

The corresponding tables are in `results/tables/` (`main_table`, `imperceptibility`,
`detectability_by_rate`, `reference_payload`), as CSV and Word-pasteable HTML.
