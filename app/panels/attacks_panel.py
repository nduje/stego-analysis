"""Tab 5 -- Napadi uzivo: run the attacks on this image, against the measured distributions.

A single image gives a SCORE, not a P_E -- P_E is a statistic over 500 images. So every
score is drawn on top of the measured cover/stego distributions for the same switches and
rate, with a marker for where this image falls. Without that context a single score would
be misleading.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from PIL import Image

from analysis.chi_square import global_chisquare
from analysis.rs_analysis import analyze_image as rs_analyze
from analysis.spa import analyze_image as spa_analyze
from app.common import load_cover, embed, score_distribution, switches_tag

ATTACKS = [
    ("chi", "χ²", global_chisquare,
     "Mjeri izjednačavanje parova vrijednosti. Kod ovog algoritma ocjena je *invertirana*: "
     "stego pada NIŽE od nositelja, pa napadač koji to zna svejedno detektira."),
    ("rs", "RS", rs_analyze,
     "Procjenjuje udio ugrađenih bitova iz regularnih/singularnih grupa. Građen je za "
     "LSB *replacement*; na '+1' i ±1 daje procjenu blizu nule."),
    ("spa", "SPA", spa_analyze,
     "Analiza parova uzoraka — isti cilj kao RS, drugi model. Također cilja replacement."),
]


def _dist_plot(cov, ste, value, title):
    fig, ax = plt.subplots(figsize=(6, 2.6))
    bins = 40
    if cov is not None and len(cov):
        ax.hist(cov, bins=bins, alpha=0.55, label="nositelji (500)", color="tab:blue", density=True)
    if ste is not None and len(ste):
        ax.hist(ste, bins=bins, alpha=0.55, label="stego (500)", color="tab:red", density=True)
    ax.axvline(value, color="black", lw=2, label="ova slika")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("ocjena")
    ax.set_yticks([])
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def render(ctx):
    cover = load_cover(ctx["cover_path"])
    stego, _ = embed(ctx["cover_path"], ctx["message"], ctx["passphrase"], ctx["rate"],
                     ctx["p1"], ctx["p2"], ctx["p3"])
    tag = switches_tag(ctx["p1"], ctx["p2"], ctx["p3"])

    st.caption("Napad na **jednoj** slici daje ocjenu, ne P_E. Zato je uz svaku ocjenu "
               "nacrtana izmjerena raspodjela nositelja i stego slika (250 test slika, "
               "iste postavke), s markerom gdje ova slika pada.")

    for key, name, fn, explain in ATTACKS:
        st.subheader(name)
        s_cover = fn(Image.fromarray(cover, "RGB"))["comb"]
        s_stego = fn(Image.fromarray(stego, "RGB"))["comb"]
        c1, c2 = st.columns(2)
        c1.metric(f"{name} — nositelj", f"{s_cover:.4f}")
        c2.metric(f"{name} — stego", f"{s_stego:.4f}", delta=f"{s_stego - s_cover:+.4f}")

        cov, ste = score_distribution(key, tag, ctx["rate"])
        if cov is None and ste is None:
            st.warning("Izmjerene raspodjele nisu dostupne "
                       "(results/csv/score_distributions.csv nedostaje).")
        else:
            fig = _dist_plot(cov, ste, s_stego, f"{name}: gdje pada ova stego slika")
            st.pyplot(fig)
            plt.close(fig)
            if cov is not None and ste is not None and len(cov) and len(ste):
                overlap = float(np.mean(ste > np.median(cov)))
                st.caption(f"Preklapanje raspodjela je ono što napad čini (ne)uspješnim: "
                           f"{100 * overlap:.0f} % stego slika ima ocjenu iznad medijana "
                           f"nositelja pri ovim postavkama.")
        st.info(explain)
