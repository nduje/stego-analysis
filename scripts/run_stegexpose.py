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
    python -m scripts.run_stegexpose --java <path/java.exe> --jar StegExpose.jar
"""
import argparse
import csv
import os
import subprocess

from lib.rates import EMBEDDING_RATES
from analysis.detection import evaluate


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


def run(java, jar, covers_dir, stego_root, manifest, out):
    test = load_test(manifest)
    print("scoring covers ...", flush=True)
    cover = stegexpose_scores(java, jar, covers_dir, "results/_se_cover.csv")

    rows = []
    for rate in EMBEDDING_RATES:
        folder = os.path.join(stego_root, f"r{rate}")
        stego = stegexpose_scores(java, jar, folder, f"results/_se_stego_{rate}.csv")
        c = [cover[n] for n in cover if n in test]
        s = [stego[n] for n in stego if n in test]
        res = evaluate(c, s)
        rows.append({"rate": rate, "eval_set": "test250",
                     "n_cover": res["n_cover"], "n_stego": res["n_stego"],
                     "auc": round(res["auc"], 6), "pe": round(res["pe"], 6)})
        print(f"  rate {rate:<5} AUC {res['auc']:.3f}  P_E {res['pe']:.3f}", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rate", "eval_set", "n_cover", "n_stego", "auc", "pe"])
        w.writeheader()
        w.writerows(rows)
    for r in EMBEDDING_RATES:
        _rm(f"results/_se_stego_{r}.csv")
    _rm("results/_se_cover.csv")
    print(f"wrote {out}")


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
    ap.add_argument("--out", default="results/stegexpose_summary.csv")
    args = ap.parse_args()
    run(args.java, args.jar, args.covers, args.stego, args.manifest, args.out)


if __name__ == "__main__":
    main()
