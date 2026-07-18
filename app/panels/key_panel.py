"""Tab 2 -- Ključ: the passphrase carries both the content (AES) and the layout (PRNG seed)."""
import streamlit as st

from app.common import embed, extract


def render(ctx):
    stego, payload = embed(ctx["cover_path"], ctx["message"], ctx["passphrase"],
                           ctx["rate"], ctx["p1"], ctx["p2"], ctx["p3"])

    st.subheader("Ispravna zaporka")
    ok = extract(stego, ctx["passphrase"], ctx["p1"], ctx["p2"], ctx["p3"])
    if ok:
        st.success("Poruka je izvučena.")
        st.code((ok[:300] + " …") if len(ok) > 300 else ok)
    else:
        st.error("Izvlačenje nije uspjelo (očekivano samo ako je nositelj zasićen — v. 255-bug).")

    st.subheader("Kriva zaporka")
    wrong = st.text_input("probaj krivu zaporku", value=ctx["passphrase"] + "x",
                          key="wrong_pass")
    bad = extract(stego, wrong, ctx["p1"], ctx["p2"], ctx["p3"])
    if not bad:
        st.success("Ništa ne izlazi — dekodiranje pada.")
    else:
        shown = (bad[:300] + " …") if len(bad) > 300 else bad
        st.warning("Izlazi samo smeće (dešifriranje daje nasumične bajtove):")
        st.code(repr(shown))

    st.info(
        "Zaporka se rasteže (scrypt) i dijeli (HKDF) na dva dijela: **ključ za AES-CTR** "
        "(sadržaj poruke) i **sjeme za PRNG** (redoslijed blokova kad je P1 uključen). "
        "Bez zaporke napadač ne zna ni što piše ni gdje piše."
    )
