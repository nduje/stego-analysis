"""Round-trip sanity for every configuration before the re-analysis measures anything.

For each config (baseline, p1, p2, p3, all) x a few rates x a sample of covers
(including a fully saturated one), embed a coverage-matched payload and check the
message comes back exactly. Reports the success rate, separating natural covers
from the saturated edge.

Expectation (documented): p2/p3/all -> ~100% including saturated (pm_one fixes 255);
baseline/p1 keep the 255-bug (no pm_one), so they can fail on the saturated cover --
that is expected, not a regression.

Run (from the repo root):
    python -m scripts.measure.verify_roundtrip
"""
import argparse
import base64
import glob
import os
import random

from lib import StegAlgorithm
from lib.algorithm import load_image
from lib.rates import capacity_chars, chars_for_rate
from scripts.data.make_stego_sets import CONFIGS, KEY

RATES = (0.05, 0.25, 1.0)


def _payload(seed_tag, length):
    rng = random.Random(seed_tag)
    return "".join(chr(c) for c in rng.choices(range(32, 127), k=length))


def _roundtrip_ok(alg, header, cover_path, rate):
    im = load_image(cover_path)
    cap = capacity_chars(*im.size)
    length = chars_for_rate(cap, rate) - header
    if length <= 0:
        return True
    msg = _payload(f"{cover_path}:{rate}", length)
    try:
        stego = alg.hide(message=msg, key=KEY, cover_path=cover_path, out_path=None)
        if stego is False:
            return False
        return alg.expose(stego_image=stego, key=KEY) == msg
    except Exception:            # garbage decode on an unembeddable cover -> not a round-trip
        return False


def run(covers_dir, n_natural):
    natural = sorted(glob.glob(os.path.join(covers_dir, "*.png")))[:n_natural]
    saturated = os.path.join("data", "covers", "cover_saturated.png")

    print(f"{'config':<9} {'natural (n=%d x %d rates)' % (n_natural, len(RATES)):<26} saturated")
    for name, cfg in CONFIGS.items():
        alg = StegAlgorithm(cfg)
        header = 2 if cfg.termination == "length_header" else 0
        ok = total = 0
        for cover in natural:
            for rate in RATES:
                total += 1
                ok += _roundtrip_ok(alg, header, cover, rate)
        sat = all(_roundtrip_ok(alg, header, saturated, r) for r in RATES)
        print(f"{name:<9} {f'{ok}/{total}':<26} {'OK' if sat else 'FAIL (255-bug, expected w/o pm_one)'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--n", type=int, default=3)
    args = ap.parse_args()
    run(args.covers, args.n)


if __name__ == "__main__":
    main()
