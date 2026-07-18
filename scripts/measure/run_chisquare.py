"""Run the chi-square (PoV) detector over the dataset and evaluate detection.

For each embedding rate: embed the covers with the baseline (fixed key,
payload length L = round(rate*21760)), score every cover and stego image with the
global chi-square detector, then evaluate AUC / P_E / ROC via the reusable harness
on the canonical test-250 set and, additionally, on all 500 (robustness).

Also records the positional chi-square curve (p-value vs raster position) for a
subset, to show the "cliff" that localizes the sequential payload.

Single-threaded on purpose (keeps memory tiny; this machine has little free disk).

Run (from the repo root):
    python -m scripts.measure.run_chisquare
    python -m scripts.measure.run_chisquare --limit 20      # quick smoke
"""
import argparse
import base64
import csv
import glob
import os
import random

from lib.algorithm import load_image
from lib.rates import EMBEDDING_RATES, capacity_chars, chars_for_rate
from baseline.stego import hide_message
from analysis.chi_square import global_chisquare, positional_chisquare
from analysis.detection import evaluate

KEY = base64.b64encode(bytes(range(32))).decode()
CAPACITY = capacity_chars(256, 256)                  # 21760
CHAN = ("comb", "r", "g", "b")
POSITIONAL_SUBSET = 30                                # test covers used for positional


def make_payload(image_idx, rate, length):
    rng = random.Random(f"{image_idx}:{rate}")
    return "".join(chr(c) for c in rng.choices(range(32, 127), k=length))


def _load_split(covers_dir):
    manifest = os.path.join(os.path.dirname(covers_dir.rstrip("/\\")), "manifest.csv")
    with open(manifest, newline="") as f:
        return {r["filename"]: r["split"] for r in csv.DictReader(f)}


def run(covers_dir, out_scores, out_summary, out_positional, limit):
    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))
    if limit:
        paths = paths[:limit]
    split = _load_split(covers_dir)

    score_rows = []          # cover + stego scores
    positional_rows = []     # image, rate, position, p_embed
    test_names = [os.path.basename(p) for p in paths if split.get(os.path.basename(p)) == "test"]
    positional_names = set(test_names[:POSITIONAL_SUBSET])

    for idx, path in enumerate(paths):
        name = os.path.basename(path)
        sp = split.get(name, "?")
        cover = load_image(path)

        cs = global_chisquare(cover)
        score_rows.append({"image": name, "split": sp, "label": "cover", "rate": "",
                           **{f"score_{k}": cs[k] for k in CHAN}})

        for rate in EMBEDDING_RATES:
            L = chars_for_rate(CAPACITY, rate)
            stego = hide_message(make_payload(idx, rate, L), KEY, path, None)
            ss = global_chisquare(stego)
            score_rows.append({"image": name, "split": sp, "label": "stego", "rate": rate,
                               **{f"score_{k}": ss[k] for k in CHAN}})
            if name in positional_names:
                for pos, p in positional_chisquare(stego):
                    positional_rows.append({"image": name, "rate": rate,
                                            "position": pos, "p_embed": p})

    _write_scores(out_scores, score_rows)
    _write_positional(out_positional, positional_rows)
    _write_summary(out_summary, score_rows)
    print(f"wrote {len(score_rows)} score rows -> {out_scores}")
    print(f"wrote {len(positional_rows)} positional rows -> {out_positional}")
    print(f"wrote per-rate summary -> {out_summary}")


def _write_scores(path, rows):
    fields = ["image", "split", "label", "rate"] + [f"score_{k}" for k in CHAN]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _write_positional(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["image", "rate", "position", "p_embed"])
        w.writeheader()
        w.writerows(rows)


def _eval_set(rows, rate, key, want_split):
    def keep(r):
        return want_split is None or r["split"] == want_split
    cover = [r[f"score_{key}"] for r in rows if r["label"] == "cover" and keep(r)]
    stego = [r[f"score_{key}"] for r in rows if r["label"] == "stego" and r["rate"] == rate and keep(r)]
    return cover, stego


def _write_summary(path, rows):
    fields = ["rate", "eval_set", "n_cover", "n_stego",
              "auc", "pe", "auc_r", "auc_g", "auc_b", "pe_r", "pe_g", "pe_b"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for rate in EMBEDDING_RATES:
            for eval_set, want in (("test250", "test"), ("all500", None)):
                cov, ste = _eval_set(rows, rate, "comb", want)
                comb = evaluate(cov, ste)
                out = [rate, eval_set, comb["n_cover"], comb["n_stego"],
                       round(comb["auc"], 6), round(comb["pe"], 6)]
                for ch in ("r", "g", "b"):
                    c2, s2 = _eval_set(rows, rate, ch, want)
                    out.append(round(evaluate(c2, s2)["auc"], 6))
                for ch in ("r", "g", "b"):
                    c2, s2 = _eval_set(rows, rate, ch, want)
                    out.append(round(evaluate(c2, s2)["pe"], 6))
                w.writerow(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--scores", default="results/csv/chisquare_scores.csv")
    ap.add_argument("--summary", default="results/csv/chisquare_summary.csv")
    ap.add_argument("--positional", default="results/csv/chisquare_positional.csv")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    os.makedirs("results/csv", exist_ok=True)
    run(args.covers, args.scores, args.summary, args.positional, args.limit)


if __name__ == "__main__":
    main()
