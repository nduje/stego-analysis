"""Westfeld chi-square (Pairs-of-Values) detector.

Classic PoV attack: LSB replacement drives each pair {2i, 2i+1} toward equal
counts, so the chi-square statistic testing "the two members of each pair are
equal" becomes small -> its survival-function p-value (the "probability of
embedding") becomes large. We report that p-value as the stego SCORE
(higher = more likely stego), which also normalizes across images with different
degrees of freedom.

Note on this algorithm: the baseline embeds with "+1" matching, not textbook LSB
replacement -- half of the changes stay inside a pair (2i -> 2i+1) but half spill
into the next pair (2i+1 -> 2i+2). So plain chi-square is expected to be WEAKER
here than on LSB-R; we implement the standard test and characterize how it fares
(that contrast is a finding, not a bug).

Two modes:
  * global_chisquare   -- one score per image (per channel + combined).
  * positional_chisquare -- p-value along a growing raster prefix; the "cliff"
    where the equalized region ends localizes the payload (sequential embedding).

Per decision D the channels are combined by POOLING statistics:
combined stat = sum of per-channel stats, combined df = sum of per-channel df,
then one p-value from the chi-square survival function.
"""
import numpy as np
from scipy.stats import chi2

from lib.config import StegoConfig
from lib.embedding import _iter_blocks

_CHANNELS = ("r", "g", "b")


def _channel_stat(hist):
    """PoV chi-square statistic and df for one channel's 256-bin histogram."""
    even = hist[0::2].astype(float)          # h[2i]
    odd = hist[1::2].astype(float)           # h[2i+1]
    expected = (even + odd) / 2.0
    valid = expected > 0
    stat = float(np.sum((even[valid] - expected[valid]) ** 2 / expected[valid]))
    df = max(int(valid.sum()) - 1, 1)
    return stat, df


def _combined_pvalue(hists):
    """Pool per-channel (stat, df) -> single p-value; also return per-channel p."""
    stat_comb, df_comb = 0.0, 0
    per = {}
    for name, hist in zip(_CHANNELS, hists):
        stat, df = _channel_stat(hist)
        per[name] = float(chi2.sf(stat, df))
        stat_comb += stat
        df_comb += df
    per["comb"] = float(chi2.sf(stat_comb, df_comb))
    return per


def global_chisquare(image):
    """{comb, r, g, b} p-values (probability of embedding) for the whole image."""
    arr = np.asarray(image)
    hists = [np.bincount(arr[..., ci].ravel(), minlength=256) for ci in range(3)]
    return _combined_pvalue(hists)


def positional_chisquare(image, n_points=100, config=None):
    """[(position_fraction, combined_p), ...] over a growing raster block prefix.

    Accumulates pixels in the algorithm's own block order, so for sequential
    embedding the p-value stays high inside the payload and drops at the "cliff"
    where the untouched cover begins.
    """
    arr = np.asarray(image)
    H, W = arr.shape[:2]
    blocks = list(_iter_blocks(W, H, config or StegoConfig()))
    total = len(blocks)
    # ordered pixel values in raster block order: (total*3, 3 channels)
    pix = np.stack([arr[y, x:x + 3] for (x, y) in blocks]).reshape(-1, 3)

    curve = []
    for k in np.linspace(max(total // n_points, 1), total, n_points, dtype=int):
        prefix = pix[: k * 3]
        hists = [np.bincount(prefix[:, ci], minlength=256) for ci in range(3)]
        curve.append((float(k / total), _combined_pvalue(hists)["comb"]))
    return curve
