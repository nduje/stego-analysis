"""'Where is the signal?' -- train the ensemble on SCRM feature SUBGROUPS.

Decision 4 asked for a per-channel (R/G/B) split. SCRM does not decompose that
way: its submodels are either SPATIAL or 3D cross-channel "color" cooccurrences
(submodel names ending in 'c'; see SCRMQ1.m header). A clean R/G/B split would
need separate per-channel SRMQ1 re-extraction. So here we do the honest, feasible
analysis: spatial-only vs color-only vs all features, ensemble P_E per rate. This
tells us whether the learned signal sits in the spatial statistics or the
cross-channel color statistics (where a blue-channel flag artifact would show up).

Requires Octave once (to read the SCRM submodel layout). Output: results/ml_group.csv.

Run (from the repo root):
    python -m scripts.run_ml_groups --octave <octave-cli>
"""
import argparse
import csv
import os
import shutil
import subprocess
import tempfile

import numpy as np
from scipy.io import loadmat

from lib.rates import EMBEDDING_RATES
from analysis.ml_features import load_feature_set, random_paired_split, assemble
from analysis.ml_classifier import ensemble_detector, stego_scores
from analysis.detection import evaluate

SCRM_DIR = os.path.abspath(os.path.join("aletheia", "aletheia-cache", "octave"))
N_SPLITS = 10


def submodel_layout(octave, img_path):
    """[(submodel_name, size), ...] in the flatten order used by extract_scrm."""
    tmp = tempfile.mkdtemp()
    try:
        out = os.path.abspath(os.path.join(tmp, "s.mat")).replace("\\", "/")
        m = (
            f"addpath('{SCRM_DIR.replace(chr(92), '/')}');warning('off');"
            "pkg load image;pkg load signal;pkg load nan;"
            f"data=SCRMQ1('{os.path.abspath(img_path).replace(chr(92), '/')}');"
            f"save('-mat7-binary','{out}','data');exit"
        )
        subprocess.run([octave, "-q", "--no-gui", "--eval", m], capture_output=True, text=True)
        rec = loadmat(out)["data"][0][0]
        return [(n, int(rec[n].reshape(1, -1).shape[1])) for n in rec.dtype.names]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _is_color(name):
    # SCRM color (cross-channel) submodels carry a 'c' on the residual-type token,
    # just before the '_q1' quantization suffix, e.g. s1_minmax22c_q1, s35_spam11c_q1.
    # Spatial submodels end in h/v/hv or a digit there, e.g. s1_minmax22h_q1, s1_minmax24_q1.
    return name.split("_q1")[0].endswith("c")


def group_columns(layout):
    spatial, color, off = [], [], 0
    for name, size in layout:
        (color if _is_color(name) else spatial).extend(range(off, off + size))
        off += size
    return {"all": np.arange(off), "spatial": np.array(spatial), "color": np.array(color)}, off


def evaluate_group(Xcg, Xsg, n_splits):
    aucs, pes = [], []
    for seed in range(n_splits):
        tr, te = random_paired_split(len(Xcg), seed)
        Xtr, ytr = assemble(Xcg, Xsg, tr)
        Xte, yte = assemble(Xcg, Xsg, te)
        model = ensemble_detector(seed=seed)
        model.fit(Xtr, ytr)
        s = stego_scores(model, Xte)
        res = evaluate(s[yte == 0], s[yte == 1])
        aucs.append(res["auc"])
        pes.append(res["pe"])
    return np.array(aucs), np.array(pes)


FIELDS = ["config", "rate", "group", "model", "auc_mean", "auc_std", "pe_mean", "pe_std"]


def stego_stem(features_dir, config, rate):
    if config == "baseline":
        return os.path.join(features_dir, f"stego_r{rate}")
    return os.path.join(features_dir, config, f"stego_r{rate}")


def _baseline_rows(path):
    """Day-10 ml_group.csv rows, tagged config=baseline (deterministic 'before')."""
    if not path or not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["config"] = "baseline"
    return rows


def run(octave, features_dir, out, n_splits, configs, baseline_from):
    Xc, fc = load_feature_set(os.path.join(features_dir, "covers"))
    layout = submodel_layout(octave, "data/alaska/covers/" + fc[0])
    cols, total = group_columns(layout)
    assert total == Xc.shape[1], f"layout {total} != feature dim {Xc.shape[1]}"
    print(f"SCRM layout: {len(layout)} submodels, {total} dims | "
          f"spatial {len(cols['spatial'])}, color {len(cols['color'])}", flush=True)

    rows = list(_baseline_rows(baseline_from)) if "baseline" in configs else []
    for config in [c for c in configs if c != "baseline"]:
        for rate in EMBEDDING_RATES:
            Xs, fs = load_feature_set(stego_stem(features_dir, config, rate))
            for group, idx in cols.items():
                aucs, pes = evaluate_group(Xc[:, idx], Xs[:, idx], n_splits)
                rows.append({"config": config, "rate": rate, "group": group, "model": "ensemble",
                             "auc_mean": round(float(aucs.mean()), 6), "auc_std": round(float(aucs.std()), 6),
                             "pe_mean": round(float(pes.mean()), 6), "pe_std": round(float(pes.std()), 6)})
                print(f"  {config:<8} rate {rate:<5} {group:<8} "
                      f"AUC {aucs.mean():.3f}  P_E {pes.mean():.3f}", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--octave", default=os.environ.get("OCTAVE_BIN", "octave-cli"))
    ap.add_argument("--features", default="data/alaska/features")
    ap.add_argument("--out", default="results/ml_group_reanalysis.csv")
    ap.add_argument("--splits", type=int, default=N_SPLITS)
    ap.add_argument("--config", default="baseline,p1,p2,p3,all",
                    help="comma-sep: baseline (copied from --baseline-from), p1,p2,p3,all (computed)")
    ap.add_argument("--baseline-from", default="results/ml_group.csv",
                    help="Day-10 group summary to copy the baseline 'before' rows from")
    args = ap.parse_args()
    run(args.octave, args.features, args.out, args.splits,
        [c.strip() for c in args.config.split(",")], args.baseline_from)


if __name__ == "__main__":
    main()
