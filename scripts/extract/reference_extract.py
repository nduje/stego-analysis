"""Drive the disk-safe SCRM extraction for one reference method (LSB-R / LSB-M).

Mirror of reanalysis_extract.py but for the reference sets: for each rate, generate
the stego PNGs, extract SCRM features, and (only on full success) delete the PNGs.
Resumable: an existing feature set is skipped; PNGs are kept for retry on failure.

Run (from the repo root), one method at a time:
    python -m scripts.extract.reference_extract --method lsbr --octave <octave-cli> --workers 4
"""
import argparse
import os
import shutil
import subprocess
import sys

from lib.rates import EMBEDDING_RATES


def run(method, octave, workers):
    for rate in EMBEDDING_RATES:
        stego_dir = os.path.join("data", "alaska", "stego", method, f"r{rate}")
        feat_out = os.path.join("data", "alaska", "features", method, f"stego_r{rate}")

        if os.path.exists(feat_out + ".npy"):
            print(f"[skip] {method} r{rate}: features already exist")
        else:
            gen = [sys.executable, "-m", "scripts.data.make_reference_sets",
                   "--method", method, "--rate", str(rate)]
            if method == "hill":
                gen += ["--octave", octave]
            subprocess.run(gen, check=True)
            r = subprocess.run([sys.executable, "-m", "scripts.extract.extract_scrm",
                                "--images", stego_dir, "--out", feat_out,
                                "--octave", octave, "--workers", str(workers)])
            if r.returncode != 0:
                print(f"[warn] {method} r{rate}: extraction incomplete (exit {r.returncode}); "
                      f"keeping stego PNGs for retry. Re-run to continue.")
                return
        if os.path.isdir(stego_dir):
            shutil.rmtree(stego_dir)           # reclaim disk; features kept
        print(f"[done] {method} r{rate}", flush=True)
    print(f"=== method '{method}' complete ===")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=["lsbr", "lsbm", "hill"])
    ap.add_argument("--octave", default=os.environ.get("OCTAVE_BIN", "octave-cli"))
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    run(args.method, args.octave, args.workers)


if __name__ == "__main__":
    main()
