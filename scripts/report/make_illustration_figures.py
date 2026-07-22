"""Four data-derived illustration figures, in the same visual style as the final ones.

Everything is generated from a real ALASKA II cover and the measured score distributions,
reusing the demo/lib code (no re-implementation):
  A) triptych  cover | stego | |cover - stego| x50
  B) change map  raster (baseline) vs PRNG (P1), coverage-matched
  C) blue-channel odd-value histogram: cover, stego with flag, stego without flag
  D) chi-square score distribution: covers vs stego (population, 250 test images)

Determinism: one fixed cover, one fixed passphrase, rate 0.25 (D uses the rate where the
inversion is clearest). All measured numbers are printed to stdout for the prose -- none
are drawn on the figures.

Run (from the repo root):
    python -m scripts.report.make_illustration_figures
"""
import csv
import os

import matplotlib.pyplot as plt
import numpy as np

from app.common import load_cover, test_covers, config_from_switches, embed
from lib.crypto import derive_keys
from lib.metrics import region_mask, mse, psnr_from_mse, ssim
from lib.rates import capacity_chars, chars_for_rate
from scripts.report import style

COVER = os.path.join("data", "alaska", "covers", "00054.png")
PASSPHRASE = "lozinka123"
MESSAGE = "Tajna poruka."
RATE = 0.25
FLAG_RATE = 1.0                     # flag writes one channel per block: more blocks = clearer
CHI_RATE = 1.0                      # rate where the chi-square inversion is clearest
MIN_PAIR = 200                      # drop value pairs with too few pixels (noisy edges)
SCORE_DIST = os.path.join("results", "csv", "score_distributions.csv")


def _cover_path():
    return COVER if os.path.exists(COVER) else test_covers(1)[0]


def _fill(message, n):
    if n <= 0 or not message:
        return ""
    return (message * (-(-n // len(message))))[:n]


def triptych(cover_path):
    cover = load_cover(cover_path)
    stego, payload = embed(cover_path, MESSAGE, PASSPHRASE, RATE, False, False, False)
    diff = np.abs(cover.astype(int) - stego.astype(int))
    amp = np.clip(diff * 50, 0, 255).astype(np.uint8)

    style.apply_style("full")
    fig, axes = plt.subplots(1, 3, figsize=(9.5, 3.4))
    for ax, img, title in ((axes[0], cover, "nositelj"),
                           (axes[1], stego, "stego"),
                           (axes[2], amp, "|nositelj − stego| × 50")):
        ax.imshow(img)
        ax.set_title(title)
        ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout()
    style.save_figure(fig, "illus_triptych_cover_stego_diff")

    m = mse(cover, stego)
    return {"cover": os.path.basename(cover_path), "rate": RATE, "chars": len(payload),
            "PSNR": round(psnr_from_mse(m), 3), "SSIM": round(ssim(cover, stego), 6),
            "MSE": round(m, 6), "touched_%": round(100 * (diff.sum(2) > 0).mean(), 2)}


def change_map(cover_path):
    cover = load_cover(cover_path)
    h, w = cover.shape[:2]
    _, seed = derive_keys(PASSPHRASE)
    char_count = chars_for_rate(capacity_chars(w, h), RATE)
    seq = region_mask(w, h, char_count, config_from_switches(False, False, False), None)
    rnd = region_mask(w, h, char_count, config_from_switches(True, False, False), seed)

    style.apply_style("full")
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 4.1))
    for ax, mask, title in ((axes[0], seq, "rasterski (osnovni)"),
                            (axes[1], rnd, "PRNG redoslijed (P1)")):
        ax.imshow(mask, cmap="Reds", vmin=0, vmax=1, interpolation="nearest")
        ax.set_title(title)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("isti broj blokova, drukčiji raspored")
    fig.tight_layout()
    style.save_figure(fig, "illus_changemap_seq_vs_prng")

    return {"char_count": char_count, "seq_touched_%": round(100 * seq.mean(), 2),
            "prng_touched_%": round(100 * rnd.mean(), 2)}


def blue_odd(cover_path):
    """Odd-value share per {2k, 2k+1} pair -- the flag pushes even values up to odd, so
    the shift shows up as a rise above 0.5, invisible in a raw value histogram."""
    cover = load_cover(cover_path)
    with_flag, _ = embed(cover_path, MESSAGE, PASSPHRASE, FLAG_RATE, False, False, False)
    no_flag, _ = embed(cover_path, MESSAGE, PASSPHRASE, FLAG_RATE, False, False, True)

    def odd_share_per_pair(channel):
        counts = np.bincount(channel.ravel(), minlength=256).astype(float)
        even, odd = counts[0::2], counts[1::2]            # pairs (2k, 2k+1)
        total = even + odd
        centers = np.arange(0, 256, 2) + 0.5
        keep = total >= MIN_PAIR                          # drop noisy sparse edges
        with np.errstate(invalid="ignore", divide="ignore"):
            share = np.where(keep, odd / total, np.nan)
        return centers, share

    style.apply_style("full")
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    series = ((cover, "nositelj", "black"),
              (with_flag, "stego SA zastavicom", "tab:red"),
              (no_flag, "stego BEZ zastavice", "tab:green"))
    fracs = {}
    for arr, lab, col in series:
        b = arr[..., 2]
        x, share = odd_share_per_pair(b)
        ax.plot(x, share, color=col, label=lab, linewidth=1.6)
        fracs[lab] = round(float((b & 1).mean()), 6)
    ax.axhline(0.5, color="lightgray", ls=":", lw=1)
    ax.set_xlabel("vrijednost plavog kanala")
    ax.set_ylabel("udio neparnih u paru")
    ax.set_ylim(0.4, 0.85)
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    style.save_figure(fig, "illus_blue_odd_flag")
    return fracs


def chi_distribution():
    if not os.path.exists(SCORE_DIST):
        print("  ! score_distributions.csv missing -- skipping figure D")
        return None
    cover, stego = [], []
    with open(SCORE_DIST, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["attack"] != "chi":
                continue
            if r["label"] == "cover":
                cover.append(float(r["score"]))
            elif r["switches"] == "000" and float(r["rate"] or 0) == CHI_RATE:
                stego.append(float(r["score"]))
    cover, stego = np.sort(np.array(cover)), np.sort(np.array(stego))

    def _ecdf(v):
        return v, np.arange(1, len(v) + 1) / len(v)

    style.apply_style("full")
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    xc, yc = _ecdf(cover)
    xs, ys = _ecdf(stego)
    ax.plot(xc, yc, color="tab:blue", label="nositelji", linewidth=1.8)
    ax.plot(xs, ys, color="tab:red", label="stego (osnovni)", linewidth=1.8)
    ax.set_xlabel("χ² ocjena")
    ax.set_ylabel("kumulativni udio")
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    style.save_figure(fig, "illus_chi_inversion_ecdf")
    return {"rate": CHI_RATE, "n_cover": len(cover), "n_stego": len(stego),
            "cover_median": round(float(np.median(cover)), 4),
            "stego_median": round(float(np.median(stego)), 4)}


def main():
    cover_path = _cover_path()
    print(f"cover: {cover_path}\npassphrase: {PASSPHRASE!r}  message: {MESSAGE!r}\n")

    a = triptych(cover_path)
    b = change_map(cover_path)
    c = blue_odd(cover_path)
    d = chi_distribution()

    print("=" * 60)
    print("A) triptych (baseline, rate 0.25):")
    for k, v in a.items():
        print(f"     {k:12} {v}")
    print("B) change map (coverage-matched, rate 0.25):")
    for k, v in b.items():
        print(f"     {k:16} {v}")
    print("C) blue-channel odd fraction:")
    for k, v in c.items():
        print(f"     {k:24} {v}")
    if d:
        print("D) chi-square distribution (population, 250 images):")
        for k, v in d.items():
            print(f"     {k:14} {v}")
    print("=" * 60)
    created = ["illus_triptych_cover_stego_diff", "illus_changemap_seq_vs_prng",
               "illus_blue_odd_flag"] + (["illus_chi_inversion_ecdf"] if d else [])
    print("created (svg + png in results/figures/final/{svg,png}/):")
    for n in created:
        print(f"  {n}.svg / {n}.png")


if __name__ == "__main__":
    main()
