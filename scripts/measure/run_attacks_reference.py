"""Run the existing chi-square / RS / SPA attacks on the reference methods.

Same attack logic and harness as the config re-analysis -- only the target changes. For
each (method, rate) the reference stego is regenerated on the fly into a folder
(byte-identical to the SCRM sets; HILL via its Octave simulator), scored, evaluated
against the cover scores, then the folder is deleted (disk-safe). LSB-R runs first:
it is the POSITIVE CONTROL -- chi-square/RS/SPA were designed for LSB replacement, so
they must light up (chi-square AUC -> 1 normally oriented, RS/SPA phat ~ true rate,
bias ~ 0). The key test-250 numbers are printed live so the control can be read early.

Outputs (method x rate x eval_set):
  results/{chisquare,rs,spa}_reference.csv

Run (from the repo root):
    python -m scripts.measure.run_attacks_reference --octave <octave-cli>
    python -m scripts.measure.run_attacks_reference --methods lsbr --octave <octave-cli>  # control first
"""
import argparse
import glob
import os
import shutil

import numpy as np

from lib.algorithm import load_image
from lib.rates import EMBEDDING_RATES, capacity_chars, chars_for_rate
from analysis.detection import evaluate
from scripts.measure.run_attacks_reanalysis import CHAN, ATTACKS, _score, _blank, _load_split, _r6, _write
from scripts.data.make_reference_sets import generate
from reference import payload

METHODS = ("lsbr", "hill", "lsbm")   # lsbr first: positive control


def _append_chi(rows, method, rate, eval_set, cov, ste, sub):
    comb = evaluate(sub(cov, "comb"), sub(ste, "comb"))
    row = {"method": method, "rate": rate, "eval_set": eval_set,
           "n_cover": comb["n_cover"], "n_stego": comb["n_stego"],
           "auc": _r6(comb["auc"]), "pe": _r6(comb["pe"])}
    for c in ("r", "g", "b"):
        e = evaluate(sub(cov, c), sub(ste, c))
        row[f"auc_{c}"] = _r6(e["auc"])
        row[f"pe_{c}"] = _r6(e["pe"])
    rows.append(row)
    return row


def _append_est(rows, method, rate, eval_set, cov, ste, sub, true_rate):
    comb = evaluate(sub(cov, "comb"), sub(ste, "comb"))
    row = {"method": method, "rate": rate, "eval_set": eval_set,
           "n_cover": comb["n_cover"], "n_stego": comb["n_stego"],
           "auc": _r6(comb["auc"]), "pe": _r6(comb["pe"])}
    for c in ("r", "g", "b"):
        row[f"auc_{c}"] = _r6(evaluate(sub(cov, c), sub(ste, c))["auc"])
    ph = np.array(sub(ste, "comb"), dtype=float)
    row["mean_phat_stego"] = _r6(ph.mean())
    row["std_phat_stego"] = _r6(ph.std())
    row["bias"] = _r6(ph.mean() - true_rate)
    row["mae"] = _r6(np.mean(np.abs(ph - true_rate)))
    row["mean_phat_cover"] = _r6(np.mean(sub(cov, "comb")))
    rows.append(row)
    return row


def _true_bpc(rate):
    """The reference embedding rate in bits/channel-sample (what RS/SPA estimate)."""
    return payload.bpc(rate)


CHI_FIELDS = ["method", "rate", "eval_set", "n_cover", "n_stego", "auc", "pe",
              "auc_r", "auc_g", "auc_b", "pe_r", "pe_g", "pe_b"]
EST_FIELDS = ["method", "rate", "eval_set", "n_cover", "n_stego", "auc", "pe",
              "auc_r", "auc_g", "auc_b", "mean_phat_stego", "std_phat_stego",
              "bias", "mae", "mean_phat_cover"]


def _load_existing(path):
    if not os.path.exists(path):
        return []
    import csv as _csv
    with open(path, newline="") as f:
        return list(_csv.DictReader(f))


def _flush(out_dir, chi_rows, rs_rows, spa_rows):
    _write(os.path.join(out_dir, "chisquare_reference.csv"), chi_rows, CHI_FIELDS)
    _write(os.path.join(out_dir, "rs_reference.csv"), rs_rows, EST_FIELDS)
    _write(os.path.join(out_dir, "spa_reference.csv"), spa_rows, EST_FIELDS)


def run(covers_dir, stego_root, out_dir, octave, limit, methods):
    paths = sorted(glob.glob(os.path.join(covers_dir, "*.png")))
    if limit:
        paths = paths[:limit]
    names = [os.path.basename(p) for p in paths]
    split = _load_split(covers_dir)

    # resume: keep rows for methods already present, skip recomputing them
    chi_rows = _load_existing(os.path.join(out_dir, "chisquare_reference.csv"))
    rs_rows = _load_existing(os.path.join(out_dir, "rs_reference.csv"))
    spa_rows = _load_existing(os.path.join(out_dir, "spa_reference.csv"))
    done = {r["method"] for r in chi_rows}
    todo = [m for m in methods if m not in done]
    if done:
        print(f"resume: already have {sorted(done)}; computing {todo}", flush=True)
    if not todo:
        print("all requested methods already present; nothing to do")
        return

    print("scoring covers (once) ...", flush=True)
    cover = _blank(paths)
    for p in paths:
        s = _score(load_image(p))
        for a in ATTACKS:
            for c in CHAN:
                cover[a][c].append(s[a][c])

    for method in todo:
        for rate in EMBEDDING_RATES:
            folder = os.path.join(stego_root, method, f"r{rate}")
            generate(method, covers_dir, stego_root, rate, limit, octave)
            stego = _blank(paths)
            for p in paths:
                sp = os.path.join(folder, os.path.basename(p))
                s = _score(load_image(sp))
                for a in ATTACKS:
                    for c in CHAN:
                        stego[a][c].append(s[a][c])

            true_rate = _true_bpc(rate)
            printed = {}
            for eval_set, want in (("test250", "test"), ("all500", None)):
                idxs = [i for i, n in enumerate(names) if want is None or split.get(n) == want]

                def sub(d, c):
                    return [d[c][i] for i in idxs]

                chi = _append_chi(chi_rows, method, rate, eval_set, cover["chi"], stego["chi"], sub)
                rs = _append_est(rs_rows, method, rate, eval_set, cover["rs"], stego["rs"], sub, true_rate)
                spa = _append_est(spa_rows, method, rate, eval_set, cover["spa"], stego["spa"], sub, true_rate)
                if eval_set == "test250":
                    printed = (chi, rs, spa)
            shutil.rmtree(folder, ignore_errors=True)
            c, r, s = printed
            print(f"  {method} r{rate} test250 | chi AUC {c['auc']:.3f} P_E {c['pe']:.3f} "
                  f"AUC_B {c['auc_b']:.3f} | RS AUC {r['auc']:.3f} phat {r['mean_phat_stego']:.3f} "
                  f"bias {r['bias']:+.3f} | SPA AUC {s['auc']:.3f} phat {s['mean_phat_stego']:.3f} "
                  f"(true {true_rate:.3f})", flush=True)

        _flush(out_dir, chi_rows, rs_rows, spa_rows)   # persist after each method (resume-safe)
        print(f"=== {method} written ===", flush=True)
    print("done")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="data/alaska/covers")
    ap.add_argument("--stego", default="data/alaska/stego")
    ap.add_argument("--out", default="results/csv")
    ap.add_argument("--octave", default=os.environ.get("OCTAVE_BIN"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--methods", default=",".join(METHODS),
                    help="comma-sep subset of lsbr,hill,lsbm (lsbr = positive control)")
    args = ap.parse_args()
    run(args.covers, args.stego, args.out, args.octave, args.limit,
        [m.strip() for m in args.methods.split(",")])


if __name__ == "__main__":
    main()
