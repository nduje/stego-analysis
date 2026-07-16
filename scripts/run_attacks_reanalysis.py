"""Run the existing classical attacks (chi2 / RS / SPA) on the improved configs.

The attack LOGIC is untouched -- this only regenerates each config's stego on the
fly (in memory) and scores it with the existing analysis functions, then evaluates
through the same harness (test-250 headline + all-500). Cover scores are computed
once (rate-independent). Stego is embedded once per (config, rate, image) and all
three attacks share it.

Outputs (config x rate x eval_set), directly comparable to the Day 6-8 baseline:
  results/chisquare_reanalysis.csv, rs_reanalysis.csv, spa_reanalysis.csv
  results/chisquare_positional_reanalysis.csv  (baseline vs p1 vs all, a few images)

Run (from the repo root):
    python -m scripts.run_attacks_reanalysis
    python -m scripts.run_attacks_reanalysis --limit 20   # smoke
"""
import argparse
import csv
import glob
import os

import numpy as np

from lib import StegAlgorithm
from lib.algorithm import load_image
from lib.rates import EMBEDDING_RATES, capacity_chars, chars_for_rate
from analysis.chi_square import global_chisquare, positional_chisquare
from analysis.rs_analysis import analyze_image as rs_analyze
from analysis.spa import analyze_image as spa_analyze
from analysis.detection import evaluate
from scripts.make_stego_sets import CONFIGS, KEY, make_payload

CHAN = ("comb", "r", "g", "b")
ATTACKS = {"chi": global_chisquare, "rs": rs_analyze, "spa": spa_analyze}
CONFIGS_TO_RUN = ("p1", "p2", "p3", "all")


def _r6(x):
    return round(float(x), 6)


def _score(img):
    return {a: fn(img) for a, fn in ATTACKS.items()}


def _blank(paths):
    return {a: {c: [] for c in CHAN} for a in ATTACKS}


def _load_split(covers_dir):
    manifest = os.path.join(os.path.dirname(covers_dir.rstrip("/\\")), "manifest.csv")
    with open(manifest, newline="") as f:
        return {r["filename"]: r["split"] for r in csv.DictReader(f)}


def _header(config):
    return 2 if CONFIGS[config].termination == "length_header" else 0


def _existing(out_dir, name):
    path = os.path.join(out_dir, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def run(covers_dir, out_dir, limit, configs=CONFIGS_TO_RUN, append=False):
    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))
    if limit:
        paths = paths[:limit]
    names = [os.path.basename(p) for p in paths]
    split = _load_split(covers_dir)

    if append:
        chi_rows = _existing(out_dir, "chisquare_reanalysis.csv")
        rs_rows = _existing(out_dir, "rs_reanalysis.csv")
        spa_rows = _existing(out_dir, "spa_reanalysis.csv")
        present = {r["config"] for r in chi_rows}
        configs = [c for c in configs if c not in present]
        print(f"append: existing {sorted(present)}; computing {list(configs)}", flush=True)
    else:
        chi_rows, rs_rows, spa_rows = [], [], []

    print("scoring covers (once) ...", flush=True)
    cover = _blank(paths)
    for p in paths:
        s = _score(load_image(p))
        for a in ATTACKS:
            for c in CHAN:
                cover[a][c].append(s[a][c])

    for config in configs:
        alg = StegAlgorithm(CONFIGS[config])
        hdr = _header(config)
        for rate in EMBEDDING_RATES:
            stego = _blank(paths)
            for idx, p in enumerate(paths):
                length = chars_for_rate(capacity_chars(*load_image(p).size), rate) - hdr
                st = alg.hide(message=make_payload(idx, rate, length), key=KEY,
                              cover_path=p, out_path=None)
                s = _score(st)
                for a in ATTACKS:
                    for c in CHAN:
                        stego[a][c].append(s[a][c])

            for eval_set, want in (("test250", "test"), ("all500", None)):
                idxs = [i for i, n in enumerate(names) if want is None or split.get(n) == want]

                def sub(d, c):
                    return [d[c][i] for i in idxs]

                _append_chi(chi_rows, config, rate, eval_set, cover["chi"], stego["chi"], sub)
                _append_est(rs_rows, config, rate, eval_set, cover["rs"], stego["rs"], sub)
                _append_est(spa_rows, config, rate, eval_set, cover["spa"], stego["spa"], sub)
            print(f"  {config} r{rate} done", flush=True)

    _write(os.path.join(out_dir, "chisquare_reanalysis.csv"), chi_rows,
           ["config", "rate", "eval_set", "n_cover", "n_stego", "auc", "pe",
            "auc_r", "auc_g", "auc_b", "pe_r", "pe_g", "pe_b"])
    est_fields = ["config", "rate", "eval_set", "n_cover", "n_stego", "auc", "pe",
                  "auc_r", "auc_g", "auc_b", "mean_phat_stego", "std_phat_stego",
                  "bias", "mae", "mean_phat_cover"]
    _write(os.path.join(out_dir, "rs_reanalysis.csv"), rs_rows, est_fields)
    _write(os.path.join(out_dir, "spa_reanalysis.csv"), spa_rows, est_fields)

    if not append:
        _positional(paths, out_dir)
    print("done")


def _append_chi(rows, config, rate, eval_set, cov, ste, sub):
    comb = evaluate(sub(cov, "comb"), sub(ste, "comb"))
    row = {"config": config, "rate": rate, "eval_set": eval_set,
           "n_cover": comb["n_cover"], "n_stego": comb["n_stego"],
           "auc": _r6(comb["auc"]), "pe": _r6(comb["pe"])}
    for c in ("r", "g", "b"):
        e = evaluate(sub(cov, c), sub(ste, c))
        row[f"auc_{c}"] = _r6(e["auc"])
        row[f"pe_{c}"] = _r6(e["pe"])
    rows.append(row)


def _append_est(rows, config, rate, eval_set, cov, ste, sub):
    comb = evaluate(sub(cov, "comb"), sub(ste, "comb"))
    row = {"config": config, "rate": rate, "eval_set": eval_set,
           "n_cover": comb["n_cover"], "n_stego": comb["n_stego"],
           "auc": _r6(comb["auc"]), "pe": _r6(comb["pe"])}
    for c in ("r", "g", "b"):
        row[f"auc_{c}"] = _r6(evaluate(sub(cov, c), sub(ste, c))["auc"])
    ph = np.array(sub(ste, "comb"), dtype=float)
    row["mean_phat_stego"] = _r6(ph.mean())
    row["std_phat_stego"] = _r6(ph.std())
    row["bias"] = _r6(ph.mean() - rate)
    row["mae"] = _r6(np.mean(np.abs(ph - rate)))
    row["mean_phat_cover"] = _r6(np.mean(sub(cov, "comb")))
    rows.append(row)


def _positional(paths, out_dir):
    subset = paths[:5]
    rows = []
    for config in ("baseline", "p1", "all"):
        alg = StegAlgorithm(CONFIGS[config])
        hdr = _header(config)
        for rate in (0.25, 0.5):
            for idx, p in enumerate(subset):
                length = chars_for_rate(capacity_chars(*load_image(p).size), rate) - hdr
                st = alg.hide(message=make_payload(idx, rate, length), key=KEY,
                              cover_path=p, out_path=None)
                for pos, pv in positional_chisquare(st):
                    rows.append({"config": config, "image": os.path.basename(p),
                                 "rate": rate, "position": _r6(pos), "p_embed": _r6(pv)})
    _write(os.path.join(out_dir, "chisquare_positional_reanalysis.csv"), rows,
           ["config", "image", "rate", "position", "p_embed"])


def _write(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--out", default="results")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--configs", default=",".join(CONFIGS_TO_RUN),
                    help="comma-sep configs to run (e.g. p13)")
    ap.add_argument("--append", action="store_true",
                    help="add the given configs to existing *_reanalysis.csv, keeping present ones")
    args = ap.parse_args()
    run(args.covers, args.out, args.limit,
        [c.strip() for c in args.configs.split(",")], args.append)


if __name__ == "__main__":
    main()
