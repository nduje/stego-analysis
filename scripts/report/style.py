"""Single source of visual style for the final (print) figures.

Defines the version -> (colour, marker, line) map, the legend order, Croatian display
names for versions/attacks/axes, and one full-page print preset applied as matplotlib
rcParams. Figures are drawn at their final size, so fonts stay in points.

save_figure writes both a vector SVG (text as paths, so Croatian diacritics survive on
any machine) into results/figures/final/svg/ and a 1200-DPI white-background PNG into
results/figures/final/png/.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# version -> (colour, marker, linestyle). Distinct but plain markers (circle, square,
# triangles, diamond, plus, x -- no stars/hexagons); ours solid, references dashed.
STYLE = {
    "baseline": ("black", "o", "-"),
    "p1": ("tab:blue", "s", "-"),
    "p2": ("tab:orange", "^", "-"),
    "p3": ("tab:green", "D", "-"),
    "p13": ("tab:brown", "v", "-"),
    "all": ("tab:red", "P", "-"),
    "lsbr": ("tab:purple", "X", "--"),
    "lsbm": ("tab:pink", ">", "--"),
    "hill": ("tab:cyan", "<", "--"),
}
ORDER = ["baseline", "p1", "p2", "p3", "p13", "all", "lsbr", "lsbm", "hill"]
OURS = ORDER[:6]

DISPLAY = {                       # legend labels (Croatian where it reads naturally)
    "baseline": "osnovni", "p1": "p1", "p2": "p2", "p3": "p3", "p13": "p1+p3",
    "all": "poboljšani", "lsbr": "LSB-R", "lsbm": "LSB-M", "hill": "HILL",
}
ATTACK = {                        # Croatian attack names
    "chi2": "χ²", "rs": "RS", "spa": "SPA", "stegexpose": "StegExpose",
    "ml": "strojno učenje (ML)", "imperceptibility": "neprimjetnost",
}
AXIS = {                          # Croatian axis labels
    "rate": "stopa ugradnje", "pe": "P_E", "auc": "AUC detekcije",
    "psnr": "PSNR (dB)", "ssim": "SSIM", "phat": "procijenjena stopa",
}

# One print spec (full page). Figures are drawn at final size; fonts stay in points.
PRESETS = {
    "full": dict(figsize=(7.0, 4.5), title=12, label=10, legend=9, tick=9, lw=1.8, ms=6),
}

RATES = [0.05, 0.1, 0.25, 0.5, 1.0]
FINAL_DIR = os.path.join("results", "figures", "final")


def apply_style(preset="full"):
    """Set global rcParams for the print spec; returns the dict for figsize/markers."""
    p = PRESETS[preset]
    plt.rcParams.update({
        "figure.figsize": p["figsize"],
        "axes.titlesize": p["title"], "axes.labelsize": p["label"],
        "legend.fontsize": p["legend"], "xtick.labelsize": p["tick"],
        "ytick.labelsize": p["tick"], "lines.linewidth": p["lw"],
        "lines.markersize": p["ms"], "font.family": "DejaVu Sans",
        "svg.fonttype": "path", "axes.grid": True, "grid.alpha": 0.3,
        "grid.linewidth": 0.5, "figure.autolayout": True,
    })
    return p


def plot_version(ax, version, xs, ys, preset):
    col, marker, ls = STYLE[version]
    ax.plot(xs, ys, color=col, marker=marker, ls=ls, label=DISPLAY[version],
            markersize=preset["ms"], linewidth=preset["lw"])


def ordered_handles(ax):
    """(handles, labels) for whatever this axis plotted, in the fixed version order."""
    handles, labels = ax.get_legend_handles_labels()
    lut = {lab: h for lab, h in zip(labels, handles)}
    labs = [DISPLAY[v] for v in ORDER if DISPLAY[v] in lut]
    extra = [l for l in labels if l not in lut.values() and l not in labs and l not in
             [DISPLAY[v] for v in ORDER]]           # non-version entries (e.g. "prava stopa")
    return [lut[l] for l in labs] + [lut[e] for e in extra], labs + extra


def legend_in_order(ax, **kw):
    """Per-axis legend with the fixed version order."""
    hs, labs = ordered_handles(ax)
    if hs:
        ax.legend(hs, labs, **kw)


def side_legend(fig, ax, **kw):
    """One shared legend to the right of a multi-panel figure (never over data)."""
    hs, labs = ordered_handles(ax)
    if hs:
        fig.legend(hs, labs, loc="center left", bbox_to_anchor=(1.0, 0.5), **kw)


def rate_ticks(ax):
    """Rate x-axis ticks, rotated so the close 0.05/0.10 labels never collide."""
    ax.set_xticks(RATES)
    ax.set_xticklabels([f"{r:g}" for r in RATES], rotation=30, ha="right")


def save_figure(fig, name):
    """Write the vector SVG (final/svg/) and the 1200-DPI PNG (final/png/)."""
    svg_dir = os.path.join(FINAL_DIR, "svg")
    png_dir = os.path.join(FINAL_DIR, "png")
    os.makedirs(svg_dir, exist_ok=True)
    os.makedirs(png_dir, exist_ok=True)
    fig.savefig(os.path.join(svg_dir, name + ".svg"), bbox_inches="tight", facecolor="white")
    fig.savefig(os.path.join(png_dir, name + ".png"), dpi=1200, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    return name
