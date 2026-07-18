"""Tab 6 -- Rezultati: the measured outcome (static), straight from results/."""
import csv
import os

import streamlit as st

TABLE = os.path.join("results", "tables", "csv", "main_table.csv")
FIGDIR = os.path.join("results", "figures", "final", "png")
FIGS = [
    ("all_attacks_comparison_single.png", "Profil pri punoj ugradnji (stopa 1.0)"),
    ("all_attacks_comparison_multi.png", "Usporedba svih metoda i napada po stopi"),
    ("chisquare_aucB_beforeafter.png", "χ² u plavom kanalu — učinak P3"),
]


def render(ctx):
    st.subheader("Glavna tablica (stopa 1.0)")
    if os.path.exists(TABLE):
        with open(TABLE, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        st.dataframe({h: [r[i] for r in rows[1:]] for i, h in enumerate(rows[0])},
                     width='stretch', hide_index=True)
        st.caption("P_E je pogreška detekcije: 0.5 = napad je slijep, 0 = savršena detekcija. "
                   "χ² na osnovnom/p1/p2 je invertiran (AUC ≈ 0.03), pa ga P_E broji kao "
                   "detekciju. Round-trip N/A za reference — njih ne dekodiramo.")
    else:
        st.warning(f"Tablica nije pronađena: {TABLE}")

    st.subheader("Središnje slike")
    for fname, caption in FIGS:
        path = os.path.join(FIGDIR, fname)
        if os.path.exists(path):
            st.image(path, caption=caption, width='stretch')

    st.subheader("Zaključak")
    st.success(
        "Tri poboljšanja vode algoritam od **trivijalno (i invertirano) detektabilnog** do "
        "**slijepog na sve strukturne napade** i na razini **LSB-matchinga** protiv naučenog "
        "detektora (P_E 0.02 → 0.09 pri punoj ugradnji). Strukturno nadmašuje klasični "
        "LSB-replacement, koji svi napadi hvataju. Adaptivni **HILL ostaje izvan dosega**: "
        "~2,3× teži za ML *i* bolje kvalitete, jer za isti payload mijenja upola manje piksela."
    )
