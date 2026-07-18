"""Run RS analysis over the dataset: detection AND rate estimation.

For each embedding rate: embed the covers with the baseline (fixed key, payload
L = round(rate*21760)), get the RS rate estimate p_hat for every cover and stego
image (per channel + combined), then
  * DETECTION -- p_hat as score -> harness AUC/P_E/ROC (test-250 + all-500),
  * ESTIMATION -- p_hat vs the true rate (mean, std, bias, MAE), plus p_hat on
    covers (should be ~0).

Single-threaded on purpose (tiny memory; this machine has little free disk).

Run (from the repo root):
    python -m scripts.measure.run_rs
    python -m scripts.measure.run_rs --limit 20      # quick smoke
"""
import argparse
import base64
import csv
import glob
import os
import random

import numpy as np

from lib.algorithm import load_image
from lib.rates import EMBEDDING_RATES, capacity_chars, chars_for_rate
from baseline.stego import hide_message
from analysis.rs_analysis import analyze_image
from analysis.detection import evaluate

KEY = base64.b64encode(bytes(range(32))).decode()
CAPACITY = capacity_chars(256, 256)
CHAN = ("comb", "r", "g", "b")


def make_payload(image_idx, rate, length):
    rng = random.Random(f"{image_idx}:{rate}")
    return "".join(chr(c) for c in rng.choices(range(32, 127), k=length))


def _load_split(covers_dir):
    manifest = os.path.join(os.path.dirname(covers_dir.rstrip("/\\")), "manifest.csv")
    with open(manifest, newline="") as f:
        return {r["filename"]: r["split"] for r in csv.DictReader(f)}


def run(covers_dir, out_scores, out_summary, limit):
    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))
    if limit:
        paths = paths[:limit]
    split = _load_split(covers_dir)

    rows = []
    for idx, path in enumerate(paths):
        name = os.path.basename(path)
        sp = split.get(name, "?")
        cover = load_image(path)
        cp = analyze_image(cover)
        rows.append({"image": name, "split": sp, "label": "cover", "rate": "",
                     **{f"phat_{k}": cp[k] for k in CHAN}})
        for rate in EMBEDDING_RATES:
            L = chars_for_rate(CAPACITY, rate)
            stego = hide_message(make_payload(idx, rate, L), KEY, path, None)
            spi = analyze_image(stego)
            rows.append({"image": name, "split": sp, "label": "stego", "rate": rate,
                         **{f"phat_{k}": spi[k] for k in CHAN}})

    _write_scores(out_scores, rows)
    _write_summary(out_summary, rows)
    print(f"wrote {len(rows)} score rows -> {out_scores}")
    print(f"wrote per-rate summary -> {out_summary}")


def _write_scores(path, rows):
    fields = ["image", "split", "label", "rate"] + [f"phat_{k}" for k in CHAN]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _subset(rows, label, rate, key, want_split):
    def keep(r):
        return want_split is None or r["split"] == want_split
    return [r[f"phat_{key}"] for r in rows
            if r["label"] == label and (label == "cover" or r["rate"] == rate) and keep(r)]


def _write_summary(path, rows):
    fields = ["rate", "eval_set", "n_cover", "n_stego",
              "auc", "pe", "auc_r", "auc_g", "auc_b",
              "mean_phat_stego", "std_phat_stego", "bias", "mae", "mean_phat_cover"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for rate in EMBEDDING_RATES:
            for eval_set, want in (("test250", "test"), ("all500", None)):
                cov = _subset(rows, "cover", rate, "comb", want)
                ste = _subset(rows, "stego", rate, "comb", want)
                det = evaluate(cov, ste)
                out = [rate, eval_set, det["n_cover"], det["n_stego"],
                       round(det["auc"], 6), round(det["pe"], 6)]
                for ch in ("r", "g", "b"):
                    out.append(round(evaluate(_subset(rows, "cover", rate, ch, want),
                                               _subset(rows, "stego", rate, ch, want))["auc"], 6))
                ste_arr = np.array(ste, dtype=float)
                out += [round(float(ste_arr.mean()), 6), round(float(ste_arr.std()), 6),
                        round(float(ste_arr.mean() - rate), 6),
                        round(float(np.mean(np.abs(ste_arr - rate))), 6),
                        round(float(np.mean(cov)), 6)]
                w.writerow(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--scores", default="results/csv/rs_scores.csv")
    ap.add_argument("--summary", default="results/csv/rs_summary.csv")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    os.makedirs("results/csv", exist_ok=True)
    run(args.covers, args.scores, args.summary, args.limit)


if __name__ == "__main__":
    main()
