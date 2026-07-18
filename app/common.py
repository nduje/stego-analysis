"""Shared helpers for the demo: cover loading, config from switches, embedding, caching.

The demo drives the *same* code the measurements use -- `lib.StegAlgorithm` with a
`StegoConfig` built from the three switches, and the attacks from `analysis/`. Nothing is
re-implemented here, so what the demo shows is what was measured.
"""
import glob
import os

import numpy as np
import streamlit as st
from PIL import Image

from lib import StegAlgorithm, StegoConfig
from lib.algorithm import load_image
from lib.rates import EMBEDDING_RATES, capacity_chars, chars_for_rate

COVERS_DIR = os.path.join("data", "alaska", "covers")
MANIFEST = os.path.join("data", "alaska", "manifest.csv")
SCORE_DIST = os.path.join("results", "csv", "score_distributions.csv")
RATES = list(EMBEDDING_RATES)


# ---- covers ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def test_covers(n=6):
    """A few predefined real ALASKA covers from the test split (same set we measured on)."""
    import csv
    split = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, newline="") as f:
            split = {r["filename"]: r["split"] for r in csv.DictReader(f)}
    paths = sorted(glob.glob(os.path.join(COVERS_DIR, "*.png")))
    test = [p for p in paths if split.get(os.path.basename(p)) == "test"] or paths
    return test[:n]


@st.cache_data(show_spinner=False)
def load_cover(path):
    return np.array(Image.open(path).convert("RGB"), dtype=np.uint8)


# ---- config / embedding ---------------------------------------------------------
def config_from_switches(p1, p2, p3):
    """The same StegoConfig switches that were measured."""
    return StegoConfig(
        pixel_order="prng" if p1 else "sequential",
        matching_mode="pm_one" if p2 else "plus_one",
        termination="length_header" if p3 else "continuation_flag",
    )


def switches_tag(p1, p2, p3):
    return f"{int(p1)}{int(p2)}{int(p3)}"


def payload_for_rate(message, rate, width=256, height=256, header=0):
    """Repeat the user's message to fill the chosen rate, so coverage matches the
    measured runs and the live score is comparable to the measured distribution."""
    n = chars_for_rate(capacity_chars(width, height), rate) - header
    if n <= 0 or not message:
        return ""
    reps = -(-n // len(message))
    return (message * reps)[:n]


@st.cache_data(show_spinner=False)
def embed(cover_path, message, passphrase, rate, p1, p2, p3):
    """(stego array, payload, config) -- cached on every input that changes the result."""
    cfg = config_from_switches(p1, p2, p3)
    alg = StegAlgorithm(cfg)
    header = 2 if cfg.termination == "length_header" else 0
    cover_im = load_image(cover_path)
    w, h = cover_im.size
    payload = payload_for_rate(message, rate, w, h, header)
    stego_im = alg.hide(message=payload, cover_path=cover_path, passphrase=passphrase)
    return np.array(stego_im, dtype=np.uint8), payload


def extract(stego_arr, passphrase, p1, p2, p3):
    """Try to recover the message; returns None when the passphrase is wrong."""
    alg = StegAlgorithm(config_from_switches(p1, p2, p3))
    try:
        return alg.expose(Image.fromarray(stego_arr, "RGB"), passphrase=passphrase)
    except Exception:
        return None


# ---- measured score distributions ------------------------------------------------
@st.cache_data(show_spinner=False)
def score_distribution(attack, switches, rate):
    """(cover_scores, stego_scores) measured over the 250-image test split."""
    import csv
    if not os.path.exists(SCORE_DIST):
        return None, None
    cov, ste = [], []
    with open(SCORE_DIST, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["attack"] != attack:
                continue
            if r["label"] == "cover":
                cov.append(float(r["score"]))
            elif r["switches"] == switches and float(r["rate"] or 0) == rate:
                ste.append(float(r["score"]))
    return (np.array(cov) if cov else None), (np.array(ste) if ste else None)


def capacity_info(rate, width=256, height=256):
    cap = capacity_chars(width, height)
    return cap, chars_for_rate(cap, rate)
