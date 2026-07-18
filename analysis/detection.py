"""Detector-agnostic evaluation harness: AUC, P_E, ROC.

A detector maps each image to a scalar SCORE with the convention
**higher score = more likely stego**. This module never looks at what a score
means -- it only compares a set of cover scores against a set of stego scores --
so it is reused unchanged for chi-square and RS/SPA/ML.

Definitions
-----------
- AUC: area under the ROC = P(stego score > cover score) + 0.5 P(equal),
  computed tie-aware from average ranks (Mann-Whitney U form). No sklearn.
- P_E: minimal average detection error over the decision threshold,
  P_E = min_tau 0.5 (P_FA(tau) + P_MD(tau)), deciding "stego" when score >= tau.
- ROC: (false-positive rate, true-positive rate) step curve for plotting.

Only numpy is used here; scipy is confined to the chi-square distribution.
"""
import numpy as np


def _arrays(cover_scores, stego_scores):
    return np.asarray(cover_scores, dtype=float), np.asarray(stego_scores, dtype=float)


def _avg_ranks(values):
    """1-based ranks with ties averaged (like scipy.stats.rankdata, custom)."""
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(1, len(values) + 1)
    sv = values[order]
    i, n = 0, len(sv)
    while i < n:
        j = i
        while j + 1 < n and sv[j + 1] == sv[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    return ranks


def auc(cover_scores, stego_scores):
    """Tie-aware AUC. nan if either set is empty."""
    c, s = _arrays(cover_scores, stego_scores)
    nc, ns = len(c), len(s)
    if nc == 0 or ns == 0:
        return float("nan")
    ranks = _avg_ranks(np.concatenate([c, s]))
    r_stego = ranks[nc:].sum()
    return float((r_stego - ns * (ns + 1) / 2.0) / (nc * ns))


def roc_points(cover_scores, stego_scores):
    """Step ROC as (fpr, tpr) arrays, starting at (0,0)."""
    c, s = _arrays(cover_scores, stego_scores)
    y = np.concatenate([np.zeros(len(c)), np.ones(len(s))])
    scores = np.concatenate([c, s])
    order = np.argsort(-scores, kind="mergesort")
    y = y[order]
    P, N = y.sum(), len(y) - y.sum()
    tp = np.concatenate([[0.0], np.cumsum(y)])
    fp = np.concatenate([[0.0], np.cumsum(1 - y)])
    tpr = tp / P if P else np.zeros_like(tp)
    fpr = fp / N if N else np.zeros_like(fp)
    return fpr, tpr


def _pe_one_direction(c, s):
    """min 0.5*(P_FA+P_MD) deciding stego if score >= tau (one orientation)."""
    uniq = np.unique(np.concatenate([c, s]))
    cands = np.concatenate([[uniq[0] - 1.0], uniq])   # below-all -> predict all stego
    best_pe, best_tau = 1.0, float(cands[0])
    for tau in cands:
        pe = 0.5 * (float(np.mean(c >= tau)) + float(np.mean(s < tau)))
        if pe < best_pe:
            best_pe, best_tau = pe, float(tau)
    return best_pe, best_tau


def p_error(cover_scores, stego_scores):
    """Orientation-agnostic (P_E, threshold): the minimal average error of this
    statistic as a detector, allowing the optimal threshold in EITHER direction.

    A correctly-oriented detector's answer is unchanged (the "higher=stego"
    direction wins); but a detector whose score is inverted for a given algorithm
    (e.g. classic chi-square vs the baseline's "+1" matching) still reports its
    true power instead of an artificial ~0.5. AUC stays orientation-sensitive, so
    the SIGN of the effect remains visible there.
    """
    c, s = _arrays(cover_scores, stego_scores)
    pe_hi, tau_hi = _pe_one_direction(c, s)           # stego if score >= tau
    pe_lo, tau_lo = _pe_one_direction(-c, -s)          # stego if score <= tau
    return (pe_hi, tau_hi) if pe_hi <= pe_lo else (pe_lo, -tau_lo)


def evaluate(cover_scores, stego_scores):
    """Convenience: {auc, pe, pe_threshold, n_cover, n_stego}."""
    pe, tau = p_error(cover_scores, stego_scores)
    return {
        "auc": auc(cover_scores, stego_scores),
        "pe": pe,
        "pe_threshold": tau,
        "n_cover": len(cover_scores),
        "n_stego": len(stego_scores),
    }
