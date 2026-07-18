"""Interactive demo: what the steganography algorithm does, and how detectable it is.

Six tabs walk from the mechanics (what changes in the pixels, what the key does, what each
switch changes) to the attacks run live on the chosen image, and finally to the measured
results. The demo drives the same `lib`/`analysis` code the measurements use, so what is
shown here is what was measured.

Run (from the repo root):
    pip install -r requirements-demo.txt
    python -m streamlit run app/demo.py
"""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.common import test_covers, RATES
from app.panels import (embed_panel, key_panel, order_panel, flag_panel,
                        attacks_panel, results_panel)

st.set_page_config(page_title="Steganografija — analiza detektabilnosti",
                   layout="wide", initial_sidebar_state="expanded")


def sidebar():
    st.sidebar.title("Postavke")
    covers = test_covers()
    if not covers:
        st.sidebar.error("Nema nositelja u data/alaska/covers/.")
        st.stop()
    names = [os.path.basename(p) for p in covers]
    choice = st.sidebar.selectbox("Nositelj (ALASKA II)", names, index=0)
    cover_path = covers[names.index(choice)]

    message = st.sidebar.text_input("Poruka", value="Tajna poruka.")
    passphrase = st.sidebar.text_input("Zaporka", value="lozinka123", type="password")
    rate = st.sidebar.select_slider("Stopa ugradnje", options=RATES, value=RATES[2])

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Poboljšanja (prekidači)**")
    p1 = st.sidebar.checkbox("P1 — PRNG redoslijed blokova", value=False)
    p2 = st.sidebar.checkbox("P2 — simetrični ±1 (pm_one)", value=False)
    p3 = st.sidebar.checkbox("P3 — duljina u zaglavlju (bez zastavice)", value=False)
    st.sidebar.caption("Isti `StegoConfig` prekidači kojima su rađena sva mjerenja. "
                       "Sva tri isključena = osnovni algoritam; sva tri uključena = poboljšani.")
    if not message.strip():
        st.sidebar.error("Poruka ne smije biti prazna.")
        st.stop()
    return {"cover_path": cover_path, "message": message, "passphrase": passphrase,
            "rate": rate, "p1": p1, "p2": p2, "p3": p3}


def main():
    st.title("Analiza detektabilnosti steganografskog algoritma")
    ctx = sidebar()
    active = [n for n, on in (("P1", ctx["p1"]), ("P2", ctx["p2"]), ("P3", ctx["p3"])) if on]
    st.caption(f"Nositelj **{os.path.basename(ctx['cover_path'])}** · stopa "
               f"**{ctx['rate']:g}** · poboljšanja: **{', '.join(active) if active else 'nijedno (osnovni)'}**")

    tabs = st.tabs(["1 · Ugradnja", "2 · Ključ", "3 · Raspored (P1)",
                    "4 · Zastavica (P3)", "5 · Napadi uživo", "6 · Rezultati"])
    for tab, panel in zip(tabs, (embed_panel, key_panel, order_panel,
                                 flag_panel, attacks_panel, results_panel)):
        with tab:
            panel.render(ctx)


if __name__ == "__main__":
    main()
