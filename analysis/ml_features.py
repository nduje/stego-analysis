"""Load SCRM feature sets and assemble leakage-free train/test datasets.

A feature set is a `<stem>.npy` matrix (one row per image) plus a `<stem>.files`
list of basenames in the same order (produced by scripts/extract_scrm.py).

For one embedding rate we pair the cover feature set with the stego feature set
(same 500 images). Labels: cover=0, stego=1. The train/test split comes from the
manifest and is keyed by FILENAME, so an image's cover row and its stego row
always land in the SAME split -- the classifier cannot learn the scene and cheat.
"""
import csv

import numpy as np


def load_feature_set(stem):
    """(matrix, filenames) from <stem>.npy and <stem>.files."""
    X = np.load(stem + ".npy")
    with open(stem + ".files") as f:
        files = f.read().splitlines()
    if X.shape[0] != len(files):
        raise ValueError(f"{stem}: {X.shape[0]} rows but {len(files)} filenames")
    return X, files


def load_split(manifest_path):
    with open(manifest_path, newline="") as f:
        return {r["filename"]: r["split"] for r in csv.DictReader(f)}


def _split_rows(X, files, label, split):
    train = [i for i, fn in enumerate(files) if split.get(fn) == "train"]
    test = [i for i, fn in enumerate(files) if split.get(fn) == "test"]
    y = lambda idx: np.full(len(idx), label, dtype=np.int64)
    return (X[train], y(train)), (X[test], y(test))


def build_dataset(cover_stem, stego_stem, manifest_path):
    """(X_train, y_train, X_test, y_test) for one rate (cover=0, stego=1)."""
    split = load_split(manifest_path)
    Xc, fc = load_feature_set(cover_stem)
    Xs, fs = load_feature_set(stego_stem)

    (Xc_tr, yc_tr), (Xc_te, yc_te) = _split_rows(Xc, fc, 0, split)
    (Xs_tr, ys_tr), (Xs_te, ys_te) = _split_rows(Xs, fs, 1, split)

    X_train = np.vstack([Xc_tr, Xs_tr])
    y_train = np.concatenate([yc_tr, ys_tr])
    X_test = np.vstack([Xc_te, Xs_te])
    y_test = np.concatenate([yc_te, ys_te])
    return X_train, y_train, X_test, y_test


def random_paired_split(n_images, seed, test_frac=0.5):
    """Random split of image INDICES into (train, test).

    Splitting by image index (not by row) keeps an image's cover and stego rows on
    the SAME side -> no scene leakage. Used for the 10-repeat ML protocol.
    """
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n_images)
    n_test = int(round(n_images * test_frac))
    return idx[n_test:], idx[:n_test]


def assemble(Xc, Xs, image_idx):
    """Stack cover+stego rows for the given image indices -> (X, y) with cover=0, stego=1."""
    X = np.vstack([Xc[image_idx], Xs[image_idx]])
    y = np.concatenate([np.zeros(len(image_idx), dtype=np.int64),
                        np.ones(len(image_idx), dtype=np.int64)])
    return X, y
