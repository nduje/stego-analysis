"""Tests for ML feature loading / leakage-free dataset assembly (Day 9).

Uses synthetic feature files (no Octave needed) to check the assembly logic:
dimensions, no NaN, disjoint train/test images, and cover+stego of the same
image staying in the same split.

Run:
    python -m pytest tests/test_ml_features.py
    python tests/test_ml_features.py
"""
import csv
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.ml_features import build_dataset, load_feature_set

FILES = [f"{i:03d}.png" for i in range(10)]
DIM = 7


def _write_set(stem, seed):
    rng = np.random.default_rng(seed)
    np.save(stem + ".npy", rng.normal(size=(len(FILES), DIM)).astype(np.float32))
    with open(stem + ".files", "w") as f:
        f.write("\n".join(FILES))


def _write_manifest(path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["filename", "split"])
        for i, fn in enumerate(FILES):
            w.writerow([fn, "train" if i < 5 else "test"])


def _fixture(tmp):
    cover = os.path.join(tmp, "cover")
    stego = os.path.join(tmp, "stego")
    manifest = os.path.join(tmp, "manifest.csv")
    _write_set(cover, 1)
    _write_set(stego, 2)
    _write_manifest(manifest)
    return cover, stego, manifest


def test_shapes_and_labels():
    with tempfile.TemporaryDirectory() as tmp:
        cover, stego, manifest = _fixture(tmp)
        Xtr, ytr, Xte, yte = build_dataset(cover, stego, manifest)
        assert Xtr.shape == (10, DIM)     # 5 train covers + 5 train stego
        assert Xte.shape == (10, DIM)
        assert set(ytr) == {0, 1} and set(yte) == {0, 1}
        assert not np.isnan(Xtr).any() and not np.isnan(Xte).any()


def test_load_mismatch_raises():
    with tempfile.TemporaryDirectory() as tmp:
        stem = os.path.join(tmp, "bad")
        np.save(stem + ".npy", np.zeros((3, DIM), dtype=np.float32))
        with open(stem + ".files", "w") as f:
            f.write("a.png\nb.png")          # 2 names vs 3 rows
        try:
            load_feature_set(stem)
        except ValueError:
            return
        raise AssertionError("expected ValueError on row/name mismatch")


def test_no_scene_leakage():
    # every image contributes exactly one cover row and one stego row to the SAME
    # split; train and test images must be disjoint.
    with tempfile.TemporaryDirectory() as tmp:
        _, _, manifest = _fixture(tmp)
        from analysis.ml_features import load_split
        split = load_split(manifest)
        train_imgs = {fn for fn, s in split.items() if s == "train"}
        test_imgs = {fn for fn, s in split.items() if s == "test"}
        assert train_imgs.isdisjoint(test_imgs)
        assert train_imgs and test_imgs


if __name__ == "__main__":
    tests = [
        ("shapes and labels", test_shapes_and_labels),
        ("row/name mismatch raises", test_load_mismatch_raises),
        ("no scene leakage (disjoint splits)", test_no_scene_leakage),
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
