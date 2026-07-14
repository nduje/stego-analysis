"""Fidelity (imperceptibility) metrics: MSE, PSNR, SSIM.

All functions take numpy arrays (uint8 HxWx3 for images, float HxW for luminance)
and are pure/testable. Every metric is meant to be reported two ways (see
scripts/measure_imperceptibility.py):

  * GLOBAL  -- over the whole image.
  * REGION  -- over only the pixels the algorithm actually touched.

Why both: at low embedding rates the global number is dominated by the huge
untouched area, so it mostly measures COVERAGE, not distortion intensity. The
region number isolates the distortion where it actually happens.

Region definition
-----------------
Embedding is sequential (raster order, 3 pixels per character). The region for an
L-character payload is the set of pixels visited by the algorithm for the first L
blocks. We obtain the mask by REPLAYING the algorithm's own block iterator
(`region_mask`), not by a hand-derived formula, so it matches the real path --
including the skipped column when x+2 >= width.

  * MSE / PSNR region: computed on the exact touched-pixel mask.
  * SSIM region: SSIM is windowed, so it is computed on the bounding-box row band
    that contains the region (`region_row_span`) -- a documented approximation.

Luminance uses BT.601: Y = 0.299 R + 0.587 G + 0.114 B (the classic SDTV weights,
matching how legacy JPEG-era tooling and much of the steganalysis literature
define luma). PSNR peak = 255; SSIM data_range = 255, win_size = 7.
"""
import numpy as np
from skimage.metrics import structural_similarity

from lib.config import StegoConfig
from lib.embedding import _iter_blocks, _ordered_blocks

BT601 = (0.299, 0.587, 0.114)


def to_luminance(arr):
    """uint8 HxWx3 -> float HxW luminance Y (BT.601)."""
    a = arr.astype(np.float64)
    return a[..., 0] * BT601[0] + a[..., 1] * BT601[1] + a[..., 2] * BT601[2]


def mse(cover, stego, mask=None):
    """Mean squared error over all pixels, or only where mask is True.

    Works for 3D (HxWxC -> averaged over pixels and channels) and 2D arrays.
    """
    d = (cover.astype(np.float64) - stego.astype(np.float64)) ** 2
    if mask is not None:
        d = d[mask]                       # 3D -> (Npix, C); 2D -> (Npix,)
    return float(d.mean())


def psnr_from_mse(mse_value, peak=255.0):
    """PSNR in dB from an MSE; identical images (mse 0) -> +inf."""
    if mse_value == 0:
        return float("inf")
    return float(10.0 * np.log10((peak ** 2) / mse_value))


def ssim(cover, stego, data_range=255, win_size=7):
    """SSIM. 3D -> per-channel average (channel_axis=2); 2D (Y) -> plain."""
    if cover.ndim == 3:
        return float(structural_similarity(
            cover, stego, data_range=data_range, win_size=win_size, channel_axis=2))
    return float(structural_similarity(
        cover, stego, data_range=data_range, win_size=win_size))


def region_mask(width, height, char_count, config=None, seed=None):
    """Boolean HxW mask of pixels the algorithm touches for `char_count` chars.

    Replays the algorithm's ACTUAL visiting order (`_ordered_blocks`), marking the
    3 pixels of each visited block. For prng the touched pixels are scattered (not a
    top band); for sequential it matches the raster region exactly (seed unused).
    Note: the 9th channel (pixel-2 blue) is inside the mask but, under length_header,
    it is left unchanged -- so its distortion is 0 within the region.
    """
    config = config or StegoConfig()
    mask = np.zeros((height, width), dtype=bool)
    for x, y in _ordered_blocks(width, height, config, seed)[:char_count]:
        mask[y, x:x + 3] = True
    return mask


def region_row_span(mask):
    """(top, bottom) row range containing the region, for the SSIM bbox crop."""
    rows = np.where(mask.any(axis=1))[0]
    return int(rows.min()), int(rows.max()) + 1
