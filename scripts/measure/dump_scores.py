"""Dump per-image chi-square / RS / SPA scores for every switch combination.

The aggregated CSVs answer "how detectable is this configuration"; the interactive demo
also needs the *distribution* behind a single-image score, so a score shown for one image
can be placed against the cover/stego populations. This writes those per-image scores for
all eight P1/P2/P3 combinations (the demo toggles the three switches independently) over
the 250-image test split.

Attack logic is untouched -- stego is regenerated in memory and scored with the same
functions the measurements use.

Output: results/csv/score_distributions.csv
    attack, switches (p1p2p3 as 3 flags), rate, image, label (cover|stego), score

Run (from the repo root):
    python -m scripts.measure.dump_scores
"""
import argparse
import csv
import glob
import os

from lib import StegAlgorithm, StegoConfig
from lib.algorithm import load_image
from lib.rates import EMBEDDING_RATES, capacity_chars, chars_for_rate
from scripts.measure.run_attacks_reanalysis import ATTACKS, _score, _load_split
from scripts.data.make_stego_sets import KEY, make_payload

OUT = "results/csv/score_distributions.csv"


def _config(p1, p2, p3):
    return StegoConfig(
        pixel_order="prng" if p1 else "sequential",
        matching_mode="pm_one" if p2 else "plus_one",
        termination="length_header" if p3 else "continuation_flag",
    )


def run(covers_dir, out, limit):
    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))
    split = _load_split(covers_dir)
    paths = [p for p in paths if split.get(os.path.basename(p)) == "test"]
    if limit:
        paths = paths[:limit]
    print(f"test covers: {len(paths)}", flush=True)

    rows = []
    for p in paths:                                     # covers: rate/config independent
        s = _score(load_image(p))
        for a in ATTACKS:
            rows.append({"attack": a, "switches": "", "rate": "",
                         "image": os.path.basename(p), "label": "cover",
                         "score": round(s[a]["comb"], 6)})

    combos = [(p1, p2, p3) for p1 in (0, 1) for p2 in (0, 1) for p3 in (0, 1)]
    for p1, p2, p3 in combos:
        cfg = _config(p1, p2, p3)
        alg = StegAlgorithm(cfg)
        hdr = 2 if cfg.termination == "length_header" else 0
        tag = f"{p1}{p2}{p3}"
        for rate in EMBEDDING_RATES:
            for idx, p in enumerate(paths):
                length = chars_for_rate(capacity_chars(*load_image(p).size), rate) - hdr
                st = alg.hide(message=make_payload(idx, rate, length), key=KEY,
                              cover_path=p, out_path=None)
                s = _score(st)
                for a in ATTACKS:
                    rows.append({"attack": a, "switches": tag, "rate": rate,
                                 "image": os.path.basename(p), "label": "stego",
                                 "score": round(s[a]["comb"], 6)})
            print(f"  switches {tag} r{rate} done", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["attack", "switches", "rate", "image", "label", "score"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    run(args.covers, args.out, args.limit)


if __name__ == "__main__":
    main()
