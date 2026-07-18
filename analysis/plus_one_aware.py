"""Candidate "+1-aware" detectors -- and the (honest) negative result.

Motivation: the baseline embeds by ALWAYS adding 1 (never subtracting). We asked
whether an adversary who knows this can build a simple structural detector that fires
on the directional "+1" and stays blind on symmetric +/-1 (LSB matching / pm_one) and
on LSB replacement -- which would show the baseline's evasion of classical attacks is
"accidental" (direction-specific) rather than principled.

Result (validated on synthetic stego, see scripts/plus_one_aware_probe.py): **none of
the candidate statistics below isolates "+1" from symmetric embedding.** The ones that
respond at all respond to *any* embedding or specifically to LSB replacement, not to the
"+1" direction. The directional "+1" signature -- separated from the continuation-flag --
is a very weak second-order histogram effect that a simple cover-less statistic cannot
robustly exploit. (Consistent with the flag analysis: the classical-attack vulnerability
of our stego was the FLAG, not the matching direction.)

So these are kept as *documented candidate attacks with a negative outcome*, not as a
working detector. Each returns {comb, r, g, b}; higher = (intended) more "+1".
"""
import numpy as np

from analysis.spa import sample_pairs, _trace_counts

_CH = ("r", "g", "b")


def _hist(ch):
    return np.bincount(np.asarray(ch).ravel(), minlength=256).astype(np.float64)


def _laplace_residual(channel):
    x = np.asarray(channel, dtype=np.float64)
    pred = (x[:-2, 1:-1] + x[2:, 1:-1] + x[1:-1, :-2] + x[1:-1, 2:]) / 4.0
    return x[1:-1, 1:-1] - pred


def residual_sign_asymmetry(channel):
    """(#r>0 - #r<0)/(#r>0 + #r<0) of the Laplacian residual. Washes out when dense."""
    r = _laplace_residual(channel)
    pos = int(np.count_nonzero(r > 0)); neg = int(np.count_nonzero(r < 0))
    tot = pos + neg
    return (pos - neg) / tot if tot else 0.0


def hist_updown(channel):
    """Weighted directional histogram flow (positive if mass pushed up). Detects any
    embedding, not '+1' specifically."""
    h = _hist(channel)
    return float(((h[:-2] - h[2:]) * h[1:-1]).sum() / (h.sum() ** 2)) * 1e3


def odd_even_step(channel):
    """Net directional parity of adjacent pairs differing by 1. Fires on LSB-R."""
    a = channel[:, :-1].astype(np.int64).ravel(); b = channel[:, 1:].astype(np.int64).ravel()
    up = (b == a + 1); dn = (b == a - 1)
    eo = int(np.sum(up & (a % 2 == 0))); oe = int(np.sum(up & (a % 2 == 1)))
    eo2 = int(np.sum(dn & (a % 2 == 0))); oe2 = int(np.sum(dn & (a % 2 == 1)))
    t = eo + oe + eo2 + oe2
    return ((eo + oe2) - (oe + eo2)) / t if t else 0.0


def spa_trace_imbalance(channel):
    """SPA (X-Y)/(X+Y) trace imbalance. Fires on LSB replacement, not '+1'."""
    u, v = sample_pairs(channel)
    X, Y, W, Z, P = _trace_counts(u, v)
    denom = X + Y
    return (X - Y) / denom if denom else 0.0


_PER_CHANNEL = {
    "residual_sign_asymmetry": residual_sign_asymmetry,
    "hist_updown": hist_updown,
    "odd_even_step": odd_even_step,
    "spa_trace_imbalance": spa_trace_imbalance,
}


def _combify(fn):
    def wrapped(image):
        arr = np.asarray(image)
        out = {name: fn(arr[..., ci]) for ci, name in enumerate(_CH)}
        out["comb"] = (out["r"] + out["g"] + out["b"]) / 3.0
        return out
    return wrapped


CANDIDATES = {name: _combify(fn) for name, fn in _PER_CHANNEL.items()}
