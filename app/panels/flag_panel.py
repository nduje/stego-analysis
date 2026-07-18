"""Tab 4 -- Zastavica (P3): the continuation flag as an odd-bias in the blue channel."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from app.common import load_cover, embed


def _odd_fraction(channel):
    return float((channel & 1).mean())


def render(ctx):
    cover = load_cover(ctx["cover_path"])
    with_flag, _ = embed(ctx["cover_path"], ctx["message"], ctx["passphrase"], ctx["rate"],
                         ctx["p1"], ctx["p2"], False)     # continuation flag written
    no_flag, _ = embed(ctx["cover_path"], ctx["message"], ctx["passphrase"], ctx["rate"],
                       ctx["p1"], ctx["p2"], True)        # length header instead

    st.subheader("Plavi kanal: sa zastavicom i bez nje")
    st.caption("Zastavica se piše u plavi kanal svakog 3. piksela — uvijek na isto mjesto, "
               "uvijek isti smjer. To ostavlja višak neparnih vrijednosti.")

    fig, ax = plt.subplots(figsize=(7, 3.2))
    bins = np.arange(0, 257, 2)
    for arr, lab, col in ((cover, "nositelj", "black"),
                          (with_flag, "stego SA zastavicom (P3 isključen)", "tab:red"),
                          (no_flag, "stego BEZ zastavice (P3 uključen)", "tab:green")):
        odd = (arr[..., 2] & 1).astype(float)
        ax.hist(arr[..., 2][odd == 1], bins=bins, histtype="step", label=lab, color=col,
                density=True, linewidth=1.4)
    ax.set_xlabel("vrijednost plavog kanala (neparne)")
    ax.set_ylabel("gustoća")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    o_c, o_f, o_n = (_odd_fraction(a[..., 2]) for a in (cover, with_flag, no_flag))
    k1, k2, k3 = st.columns(3)
    k1.metric("udio neparnih — nositelj", f"{o_c:.4f}")
    k2.metric("sa zastavicom", f"{o_f:.4f}", delta=f"{o_f - o_c:+.4f}")
    k3.metric("bez zastavice", f"{o_n:.4f}", delta=f"{o_n - o_c:+.4f}")

    st.info(
        "Zastavica pomiče udio neparnih plavih vrijednosti od nositelja; kad je P3 uključen "
        "(duljina se nosi u zaglavlju, unutar šifrata) zastavica se **uopće ne piše** i pomak "
        "nestaje. To je isti trag koji χ² u plavom kanalu mjeri kao AUC_B ≈ 0.03 → ≈ 0.58."
    )
