"""Train + evaluate the learned detectors on the baseline, per embedding rate.

For each rate: load the cover and stego SCRM feature sets (aligned, 500 each), do
10 random 250/250 image splits (leakage-free -- an image's cover and stego rows
stay on the same side), train the FLD ensemble and the SVM control, score the test
set, and push scores through OUR harness (AUC, P_E). Report mean +/- std over the
10 splits.

Output: results/csv/ml_summary.csv (per rate x model).

Run (from the repo root):
    python -m scripts.measure.run_ml_detection
"""
import argparse
import csv
import os

import numpy as np

from lib.rates import EMBEDDING_RATES
from analysis.ml_features import load_feature_set, random_paired_split, assemble
from analysis.ml_classifier import ensemble_detector, svm_detector, stego_scores
from analysis.detection import evaluate

FEATURES = "data/alaska/features"
N_SPLITS = 10
MODELS = {"ensemble": ensemble_detector, "svm": svm_detector}


def stego_stem(features_dir, config, rate):
    """Baseline features are flat (features/stego_r*); config features are nested
    (features/{config}/stego_r*). Covers are shared at features/covers."""
    if config == "baseline":
        return os.path.join(features_dir, f"stego_r{rate}")
    return os.path.join(features_dir, config, f"stego_r{rate}")


def evaluate_rate(Xc, Xs, make_model, n_splits):
    aucs, pes = [], []
    for seed in range(n_splits):
        tr, te = random_paired_split(len(Xc), seed)
        Xtr, ytr = assemble(Xc, Xs, tr)
        Xte, yte = assemble(Xc, Xs, te)
        model = make_model(seed=seed)
        model.fit(Xtr, ytr)
        s = stego_scores(model, Xte)
        res = evaluate(s[yte == 0], s[yte == 1])
        aucs.append(res["auc"])
        pes.append(res["pe"])
    return np.array(aucs), np.array(pes)


FIELDS = ["config", "rate", "model", "n_splits", "auc_mean", "auc_std", "pe_mean", "pe_std"]


def _baseline_rows(path):
    """Baseline ML-summary rows, tagged config=baseline (deterministic 'before')."""
    if not path or not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r.setdefault("config", "baseline")
        r["config"] = "baseline"
    return rows


def _existing(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def run(features_dir, out, n_splits, models, configs, baseline_from, append=False):
    Xc, fc = load_feature_set(os.path.join(features_dir, "covers"))
    if append:
        rows = _existing(out)                       # keep existing configs, add the new ones
        present = {r["config"] for r in rows}
        configs = [c for c in configs if c not in present]
        print(f"append: existing {sorted(present)}; computing {configs}", flush=True)
    else:
        rows = list(_baseline_rows(baseline_from)) if "baseline" in configs else []
    for config in [c for c in configs if c != "baseline"]:
        for rate in EMBEDDING_RATES:
            Xs, fs = load_feature_set(stego_stem(features_dir, config, rate))
            assert fc == fs, f"cover/stego filename mismatch at {config} rate {rate}"
            for name in models:
                make = MODELS[name]
                aucs, pes = evaluate_rate(Xc, Xs, make, n_splits)
                rows.append({
                    "config": config, "rate": rate, "model": name, "n_splits": n_splits,
                    "auc_mean": round(float(aucs.mean()), 6), "auc_std": round(float(aucs.std()), 6),
                    "pe_mean": round(float(pes.mean()), 6), "pe_std": round(float(pes.std()), 6),
                })
                print(f"  {config:<8} rate {rate:<5} {name:<9} "
                      f"AUC {aucs.mean():.3f}+/-{aucs.std():.3f}  "
                      f"P_E {pes.mean():.3f}+/-{pes.std():.3f}", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default=FEATURES)
    ap.add_argument("--out", default="results/csv/ml_reanalysis.csv")
    ap.add_argument("--splits", type=int, default=N_SPLITS)
    ap.add_argument("--models", default="ensemble,svm", help="comma-sep: ensemble,svm")
    ap.add_argument("--config", default="baseline,p1,p2,p3,all",
                    help="comma-sep: baseline (copied from --baseline-from), p1,p2,p3,all (computed)")
    ap.add_argument("--baseline-from", default="results/csv/ml_summary.csv",
                    help="summary to copy the baseline 'before' rows from")
    ap.add_argument("--append", action="store_true",
                    help="add the given configs to an existing --out, keeping present ones")
    args = ap.parse_args()
    run(args.features, args.out, args.splits,
        [m.strip() for m in args.models.split(",")],
        [c.strip() for c in args.config.split(",")],
        args.baseline_from, args.append)


if __name__ == "__main__":
    main()
