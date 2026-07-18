"""Sanity for the candidate '+1-aware' detectors and the documented negative result.

We do NOT assert that any candidate detects '+1' -- the finding is that none
does. We assert the detectors run and return a well-formed score, and we lock the two
things that ARE true: the probe's internal validity (a replacement detector catches
synthetic LSB-R) and the negative result (no candidate separates '+1' from LSB-M).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.plus_one_aware import CANDIDATES
from scripts.measure.plus_one_aware_probe import synth, auc


def _cover(seed=0):
    """Smooth low-frequency image (local correlation, like a natural cover)."""
    rng = np.random.default_rng(seed)
    small = rng.integers(40, 216, size=(16, 16, 3)).astype(np.float64)
    img = np.repeat(np.repeat(small, 8, axis=0), 8, axis=1)          # 128x128 blocky
    img += rng.normal(0, 3, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def test_candidates_wellformed():
    img = _cover()
    for name, fn in CANDIDATES.items():
        out = fn(img)
        assert set(out) == {"comb", "r", "g", "b"}
        assert all(np.isfinite(v) for v in out.values()), name
    print("candidates well-formed OK")


def test_probe_internal_validity_lsbr():
    # a replacement detector must catch synthetic LSB-R (proves the probe machinery works)
    rng = np.random.default_rng(1)
    covers = [_cover(i) for i in range(40)]
    caught = []
    for stat in ("odd_even_step", "spa_trace_imbalance"):
        cov = [CANDIDATES[stat](c)["comb"] for c in covers]
        ste = [CANDIDATES[stat](synth(c, "lsbr", rng, 1.0))["comb"] for c in covers]
        caught.append(max((a := auc(cov, ste)), 1 - a))
    assert max(caught) > 0.7, f"no replacement detector caught LSB-R: {caught}"
    print("probe internal validity (LSB-R) OK")


def test_negative_result_plus1_not_isolated():
    # no candidate separates '+1' from cover much better than it separates LSB-M
    rng = np.random.default_rng(2)
    covers = [_cover(i + 100) for i in range(40)]
    for stat, fn in CANDIDATES.items():
        cov = [fn(c)["comb"] for c in covers]
        a_p1 = max(lambda_ := auc(cov, [fn(synth(c, "plus1", rng, 1.0))["comb"] for c in covers]),
                   1 - lambda_)
        a_lm = max(lambda_ := auc(cov, [fn(synth(c, "lsbm", rng, 1.0))["comb"] for c in covers]),
                   1 - lambda_)
        # '+1' specificity would require a_p1 high AND a_lm ~0.5; assert it does NOT hold
        assert not (a_p1 > 0.8 and a_lm < 0.6), f"{stat} unexpectedly '+1'-specific ({a_p1},{a_lm})"
    print("negative result (no +1 isolation) OK")


if __name__ == "__main__":
    test_candidates_wellformed()
    test_probe_internal_validity_lsbr()
    test_negative_result_plus1_not_isolated()
    print("all plus_one_aware tests passed")
