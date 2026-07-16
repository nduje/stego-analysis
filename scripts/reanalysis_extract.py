"""Drive the disk-safe SCRM extraction for one improved-algorithm configuration.

For each rate: generate the stego PNGs, extract SCRM features, and (only if the
extraction fully succeeded) delete the PNGs to reclaim disk -- features are what we
keep. Resumable: a feature set that already exists is skipped, and stego PNGs are
kept for retry if any image failed.

Run (from the repo root), one config at a time:
    python -m scripts.reanalysis_extract --config all --octave <octave-cli> --workers 4
"""
import argparse
import os
import shutil
import subprocess
import sys

from lib.rates import EMBEDDING_RATES


def run(config, octave, workers):
    for rate in EMBEDDING_RATES:
        stego_dir = os.path.join("data", "alaska", "stego", config, f"r{rate}")
        feat_out = os.path.join("data", "alaska", "features", config, f"stego_r{rate}")

        if os.path.exists(feat_out + ".npy"):
            print(f"[skip] {config} r{rate}: features already exist")
        else:
            subprocess.run([sys.executable, "-m", "scripts.make_stego_sets",
                            "--config", config, "--rate", str(rate)], check=True)
            r = subprocess.run([sys.executable, "-m", "scripts.extract_scrm",
                                "--images", stego_dir, "--out", feat_out,
                                "--octave", octave, "--workers", str(workers)])
            if r.returncode != 0:
                print(f"[warn] {config} r{rate}: extraction incomplete (exit {r.returncode}); "
                      f"keeping stego PNGs for retry. Re-run to continue.")
                return
        if os.path.isdir(stego_dir):
            shutil.rmtree(stego_dir)           # reclaim disk; features kept
        print(f"[done] {config} r{rate}", flush=True)
    print(f"=== config '{config}' complete ===")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, choices=["p1", "p2", "p3", "all", "p13"])
    ap.add_argument("--octave", default=os.environ.get("OCTAVE_BIN", "octave-cli"))
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    run(args.config, args.octave, args.workers)


if __name__ == "__main__":
    main()
