"""Tests for the ML detectors + leakage-free split helper.

Synthetic sanity: clearly separable classes -> P_E ~ 0; identically distributed
classes -> P_E ~ 0.5. Both the ensemble and the SVM. Plus the random paired split
is disjoint and correctly sized.

Run:
    python -m pytest tests/test_ml_classifier.py
    python tests/test_ml_classifier.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.ml_classifier import ensemble_detector, svm_detector, stego_scores
from analysis.detection import p_error
from analysis.ml_features import random_paired_split

N, D = 200, 300           # samples per class, features


def _dataset(separable, seed=0):
    rng = np.random.default_rng(seed)
    c0 = rng.normal(0.0, 1.0, (N, D))
    c1 = rng.normal(3.0 if separable else 0.0, 1.0, (N, D))
    half = N // 2
    Xtr = np.vstack([c0[:half], c1[:half]])
    ytr = np.r_[np.zeros(half), np.ones(half)].astype(int)
    Xte = np.vstack([c0[half:], c1[half:]])
    yte = np.r_[np.zeros(N - half), np.ones(N - half)].astype(int)
    return Xtr, ytr, Xte, yte


def _pe(make_model, separable):
    Xtr, ytr, Xte, yte = _dataset(separable)
    model = make_model(seed=0)
    model.fit(Xtr, ytr)
    s = stego_scores(model, Xte)
    pe, _ = p_error(s[yte == 0], s[yte == 1])
    return pe


def test_ensemble_separable():
    assert _pe(ensemble_detector, separable=True) < 0.05


def test_ensemble_random():
    assert _pe(ensemble_detector, separable=False) > 0.35


def test_svm_separable():
    assert _pe(svm_detector, separable=True) < 0.05


def test_svm_random():
    assert _pe(svm_detector, separable=False) > 0.35


def test_paired_split_disjoint():
    tr, te = random_paired_split(500, seed=1, test_frac=0.5)
    assert len(tr) == 250 and len(te) == 250
    assert set(tr.tolist()).isdisjoint(te.tolist())
    assert sorted(tr.tolist() + te.tolist()) == list(range(500))


if __name__ == "__main__":
    tests = [
        ("ensemble separable -> P_E~0", test_ensemble_separable),
        ("ensemble random -> P_E~0.5", test_ensemble_random),
        ("svm separable -> P_E~0", test_svm_separable),
        ("svm random -> P_E~0.5", test_svm_random),
        ("paired split disjoint", test_paired_split_disjoint),
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
