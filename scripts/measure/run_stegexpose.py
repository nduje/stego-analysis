"""Run StegExpose (a practitioner tool) as an illustrative baseline detector.

StegExpose fuses classic LSB-replacement attacks (Primary Sets, Chi-Square,
Sample Pairs, RS) into one continuous "Fusion" score. We feed that score through
OUR harness (AUC, P_E) on test-250, so it lands in the same table as
chi2/RS/SPA/ML.

Caveats (documented, per the plan): StegExpose is threshold-dependent and prone to
false alarms; it is an ILLUSTRATIVE practitioner baseline, not a strict yardstick.
Since it combines RS/Sample-Pairs logic, it is expected to miss "+1" like RS/SPA.

Requires Java + StegExpose.jar (both git-ignored). Reuses the stego PNG folders
already generated under data/alaska/stego/.

Run (from the repo root):
    python -m scripts.measure.run_stegexpose --java <path/java.exe> --jar StegExpose.jar
"""
import argparse
import csv
import os
import shutil
import subprocess

from lib.rates import EMBEDDING_RATES
from analysis.detection import evaluate
from scripts.data.make_stego_sets import generate
from scripts.data.make_reference_sets import generate as ref_generate

REFERENCE = {"lsbr", "lsbm", "hill"}   # generated via make_reference_sets (hill needs octave)


def stegexpose_scores(java, jar, folder, out_csv):
    """Run StegExpose on a folder -> {filename: fusion_score}."""
    subprocess.run([java, "-jar", jar, folder, "default", "default", out_csv],
                   capture_output=True, text=True, timeout=3600)
    scores = {}
    with open(out_csv, newline="") as f:
        lines = [ln for ln in f if ln.strip()]     # StegExpose writes a leading blank line
    for row in csv.DictReader(lines):
        scores[row["File name"]] = float(row["Fusion (mean)"])
    return scores


def load_test(manifest):
    with open(manifest, newline="") as f:
        return {r["filename"] for r in csv.DictReader(f) if r["split"] == "test"}


FIELDS = ["config", "rate", "eval_set", "n_cover", "n_stego", "auc", "pe"]


def _baseline_rows(path):
    """Baseline StegExpose-summary rows, tagged config=baseline (the 'before')."""
    if not path or not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["config"] = "baseline"
    return rows


def _existing(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def run(java, jar, covers_dir, stego_root, manifest, out, configs, baseline_from,
        octave=None, append=False):
    test = load_test(manifest)

    if append:
        rows = _existing(out)
        present = {r["config"] for r in rows}
        configs = [c for c in configs if c not in present]
        print(f"append: existing {sorted(present)}; computing {configs}", flush=True)
    else:
        rows = list(_baseline_rows(baseline_from)) if "baseline" in configs else []
    todo = [c for c in configs if c != "baseline"]
    if not todo:
        _flush_stegexpose(out, rows)
        print(f"wrote {out} (nothing new)")
        return

    print("scoring covers ...", flush=True)
    cover = stegexpose_scores(java, jar, covers_dir, "results/csv/_se_cover.csv")
    cov_test = [cover[n] for n in cover if n in test]

    for config in todo:
        for rate in EMBEDDING_RATES:
            folder = os.path.join(stego_root, config, f"r{rate}")
            if config in REFERENCE:
                ref_generate(config, covers_dir, stego_root, rate, 0, octave)
            else:
                generate(config, covers_dir, stego_root, rate, 0)   # on-the-fly, disk-safe
            stego = stegexpose_scores(java, jar, folder, f"results/_se_stego_{rate}.csv")
            s = [stego[n] for n in stego if n in test]
            res = evaluate(cov_test, s)
            rows.append({"config": config, "rate": rate, "eval_set": "test250",
                         "n_cover": res["n_cover"], "n_stego": res["n_stego"],
                         "auc": round(res["auc"], 6), "pe": round(res["pe"], 6)})
            print(f"  {config:<8} rate {rate:<5} AUC {res['auc']:.3f}  P_E {res['pe']:.3f}",
                  flush=True)
            shutil.rmtree(folder, ignore_errors=True)           # delete PNGs before next rate

    _flush_stegexpose(out, rows)
    for r in EMBEDDING_RATES:
        _rm(f"results/_se_stego_{r}.csv")
    _rm("results/csv/_se_cover.csv")
    print(f"wrote {out}")


def _flush_stegexpose(out, rows):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def _rm(p):
    try:
        os.remove(p)
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--java", required=True)
    ap.add_argument("--jar", default="StegExpose.jar")
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--stego", default="data/alaska/stego")
    ap.add_argument("--manifest", default="data/alaska/manifest.csv")
    ap.add_argument("--out", default="results/csv/stegexpose_reanalysis.csv")
    ap.add_argument("--config", default="baseline,p1,p2,p3,all",
                    help="comma-sep: baseline (copied from --baseline-from), p1,p2,p3,all (generated)")
    ap.add_argument("--baseline-from", default="results/csv/stegexpose_summary.csv",
                    help="summary to copy the baseline 'before' rows from")
    ap.add_argument("--octave", default=os.environ.get("OCTAVE_BIN"),
                    help="octave-cli path (required if --config includes hill)")
    ap.add_argument("--append", action="store_true",
                    help="add the given configs to an existing --out, keeping present ones")
    args = ap.parse_args()
    run(args.java, args.jar, args.covers, args.stego, args.manifest, args.out,
        [c.strip() for c in args.config.split(",")], args.baseline_from, args.octave, args.append)


if __name__ == "__main__":
    main()
