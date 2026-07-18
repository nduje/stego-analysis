"""Tab 3 -- Raspored (P1): raster order leaves a positional edge, PRNG order does not."""
import numpy as np
import streamlit as st

from app.common import load_cover, embed


def _touched(cover, stego):
    return (np.abs(cover.astype(int) - stego.astype(int)).sum(axis=2) > 0)


def render(ctx):
    cover = load_cover(ctx["cover_path"])
    seq, _ = embed(ctx["cover_path"], ctx["message"], ctx["passphrase"], ctx["rate"],
                   False, ctx["p2"], ctx["p3"])
    rnd, _ = embed(ctx["cover_path"], ctx["message"], ctx["passphrase"], ctx["rate"],
                   True, ctx["p2"], ctx["p3"])

    st.subheader("Gdje algoritam dira piksele")
    st.caption("Isti nositelj, ista poruka, ista stopa — mijenja se samo redoslijed obilaska.")
    c1, c2 = st.columns(2)
    for col, arr, title in ((c1, seq, "sekvencijalno (P1 isključen)"),
                            (c2, rnd, "PRNG redoslijed (P1 uključen)")):
        t = _touched(cover, arr)
        heat = np.zeros((*t.shape, 3), dtype=np.uint8)
        heat[..., 0] = t * 255
        col.image(heat, caption=title, width='stretch')
        col.caption(f"dirano {100 * t.mean():.1f} % piksela")

    st.info(
        "Sekvencijalno se ugradnja skuplja na vrhu slike i ostavlja **oštar rub** ondje gdje "
        "poruka stane — pozicijski trag koji odaje i duljinu poruke. PRNG redoslijed "
        "(ključem sijan) raspršuje iste izmjene po cijeloj slici, pa ruba nema. "
        "P1 mijenja **gdje** se piše, ne **koliko** se piše."
    )
