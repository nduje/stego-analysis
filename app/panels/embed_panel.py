"""Tab 1 -- Ugradnja: what the embedding actually does to the pixels."""
import numpy as np
import streamlit as st

from lib.metrics import mse, psnr_from_mse, ssim
from app.common import load_cover, embed, capacity_info


def render(ctx):
    cover = load_cover(ctx["cover_path"])
    stego, payload = embed(ctx["cover_path"], ctx["message"], ctx["passphrase"],
                           ctx["rate"], ctx["p1"], ctx["p2"], ctx["p3"])

    st.subheader("Nositelj i stego — okom se ne razlikuju")
    c1, c2 = st.columns(2)
    c1.image(cover, caption="nositelj (cover)", width='stretch')
    c2.image(stego, caption="stego (s porukom)", width='stretch')

    diff = np.abs(cover.astype(int) - stego.astype(int))
    st.subheader("Razlika, pojačana ×50")
    st.caption("Promjena je doslovno ±1 po kanalu; bez pojačanja se ne vidi ništa.")
    d1, d2 = st.columns(2)
    d1.image(np.clip(diff * 50, 0, 255).astype(np.uint8),
             caption="|nositelj − stego| × 50", width='stretch')

    touched = (diff.sum(axis=2) > 0)
    heat = np.zeros((*touched.shape, 3), dtype=np.uint8)
    heat[..., 0] = touched * 255                      # red where a pixel changed
    d2.image(heat, caption="dirani pikseli (crveno)", width='stretch')

    cap, used = capacity_info(ctx["rate"])
    m = mse(cover, stego)
    st.subheader("Brojke")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("PSNR", f"{psnr_from_mse(m):.2f} dB" if m else "∞")
    k2.metric("SSIM", f"{ssim(cover, stego):.5f}")
    k3.metric("MSE", f"{m:.4f}")
    k4.metric("Promijenjeni kanali", f"{int((diff > 0).sum()):,}")
    k5, k6, k7 = st.columns(3)
    k5.metric("Kapacitet", f"{cap:,} znakova")
    k6.metric("Iskorišteno", f"{len(payload):,} znakova")
    k7.metric("Udio kapaciteta", f"{100 * len(payload) / cap:.0f} %")
    st.caption(f"Promijenjeni pikseli: {int(touched.sum()):,} od {touched.size:,} "
               f"({100 * touched.mean():.1f} %). Maksimalna promjena po kanalu: "
               f"{int(diff.max())}.")
