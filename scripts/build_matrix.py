"""Assemble every measurement into one source-of-truth matrix + the main table.

Reads all the per-attack CSVs (reanalysis for our configs, *_summary for the baseline
chi2/RS/SPA rows, *_reference for LSB-R/LSB-M/HILL) and the three imperceptibility CSVs,
normalises the version column (config / method -> version), and writes:

  results/master_matrix.csv  -- tidy: version, family, rate, attack, metric, value, eval_set
  results/main_table.csv     -- wide pivot at rate=1.0 (9 versions x the headline columns)

Then runs sanity checks (known values, no dupes/NaN). If a check fails it raises, so a
bad CSV is caught before it reaches the thesis. Attacks use P_E (orientation-agnostic)
as the headline metric; imperceptibility uses global PSNR (comparable across methods).

Run (from the repo root):
    python -m scripts.build_matrix
"""
import csv
import os

RES = "results"
OURS = ["baseline", "p1", "p2", "p3", "p13", "all"]
REFS = ["lsbr", "lsbm", "hill"]
ORDER = OURS + REFS

CLASSIC = {
    "chi2": [("pe", "pe"), ("auc", "auc"), ("auc_b", "auc_b")],
    "rs": [("pe", "pe"), ("auc", "auc"), ("phat", "mean_phat_stego"), ("bias", "bias")],
    "spa": [("pe", "pe"), ("auc", "auc"), ("phat", "mean_phat_stego"), ("bias", "bias")],
}
CLASSIC_BASE = {"chi2": "chisquare", "rs": "rs", "spa": "spa"}


def _rows(name):
    p = os.path.join(RES, name)
    return list(csv.DictReader(open(p, newline=""))) if os.path.exists(p) else []


def _fam(v):
    return "ours" if v in OURS else "reference"


def _add(out, version, rate, attack, metric, value, eval_set):
    if value in (None, ""):
        return
    out.append({"version": version, "family": _fam(version), "rate": round(float(rate), 2),
                "attack": attack, "metric": metric, "value": round(float(value), 6),
                "eval_set": eval_set})


def build():
    out = []
    # classic chi2/RS/SPA: reanalysis(config) + summary(baseline) + reference(method), test250
    for atk, mets in CLASSIC.items():
        base = CLASSIC_BASE[atk]
        for name, vcol in ((f"{base}_reanalysis.csv", "config"),
                           (f"{base}_summary.csv", None),
                           (f"{base}_reference.csv", "method")):
            for r in _rows(name):
                if r.get("eval_set", "test250") != "test250":
                    continue
                v = r[vcol] if vcol else "baseline"
                for mn, col in mets:
                    _add(out, v, r["rate"], atk, mn, r.get(col), "test250")

    # ML (ensemble headline): reanalysis has baseline, reference has lsbr/lsbm/hill
    for name in ("ml_reanalysis.csv", "ml_reference.csv"):
        for r in _rows(name):
            if r.get("model") != "ensemble":
                continue
            _add(out, r["config"], r["rate"], "ml", "pe", r["pe_mean"], "cv10")
            _add(out, r["config"], r["rate"], "ml", "auc", r["auc_mean"], "cv10")

    # StegExpose: reanalysis has baseline, reference has lsbr/lsbm/hill
    for name in ("stegexpose_reanalysis.csv", "stegexpose_reference.csv"):
        for r in _rows(name):
            _add(out, r["config"], r["rate"], "stegexpose", "pe", r["pe"], "test250")
            _add(out, r["config"], r["rate"], "stegexpose", "auc", r["auc"], "test250")

    # Imperceptibility: summary(baseline) + reanalysis(ours) + reference
    for name in ("imperceptibility_summary.csv", "imperceptibility_reanalysis.csv",
                 "imperceptibility_reference.csv"):
        for r in _rows(name):
            v = r.get("config") or "baseline"
            for mn, col in (("psnr_global", "psnr_global_rgb_mean"),
                            ("psnr_region", "psnr_region_rgb_mean"),
                            ("ssim_global", "ssim_global_chan_mean"),
                            ("mse_global", "mse_global_rgb_mean")):
                _add(out, v, r["rate"], "imperceptibility", mn, r.get(col), "")
            rt = r.get("roundtrip_fail_frac")
            if rt not in (None, ""):
                _add(out, v, r["rate"], "imperceptibility", "roundtrip_fail", rt, "")
    return out


def write_master(rows, out):
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["version", "family", "rate", "attack",
                                          "metric", "value", "eval_set"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (ORDER.index(r["version"]) if r["version"] in ORDER else 99,
                                                r["attack"], r["rate"], r["metric"])))
    print(f"wrote {out} ({len(rows)} rows)")


def _val(rows, version, attack, metric, rate=1.0):
    for r in rows:
        if (r["version"] == version and r["attack"] == attack and r["metric"] == metric
                and r["rate"] == rate):
            return r["value"]
    return None


def write_main_table(rows, out, rate=1.0):
    cols = [("PSNR_global_dB", "imperceptibility", "psnr_global"),
            ("roundtrip_fail", "imperceptibility", "roundtrip_fail"),
            ("chi2_PE", "chi2", "pe"), ("RS_PE", "rs", "pe"), ("SPA_PE", "spa", "pe"),
            ("StegExpose_PE", "stegexpose", "pe"), ("ML_PE", "ml", "pe")]
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["version", "family"] + [c[0] for c in cols])
        for v in ORDER:
            row = [v, _fam(v)]
            for _, atk, met in cols:
                val = _val(rows, v, atk, met, rate)
                row.append("" if val is None else val)
            w.writerow(row)
    print(f"wrote {out} (rate {rate})")


def sanity(rows):
    checks = [("baseline", "ml", "pe", 0.02), ("all", "ml", "pe", 0.086),
              ("p3", "ml", "pe", 0.124), ("p13", "ml", "pe", 0.125),
              ("hill", "ml", "pe", 0.199), ("lsbr", "chi2", "auc", 0.955)]
    print("-- sanity: known values --")
    bad = []
    for v, atk, met, want in checks:
        got = _val(rows, v, atk, met)
        ok = got is not None and abs(got - want) < 0.01
        print(f"  {v:8} {atk:10} {met:4} = {got} (want ~{want}) {'OK' if ok else 'MISMATCH'}")
        if not ok:
            bad.append((v, atk, met, got, want))
    # duplicates
    seen = set()
    dupes = 0
    for r in rows:
        k = (r["version"], r["attack"], r["metric"], r["rate"], r["eval_set"])
        if k in seen:
            dupes += 1
        seen.add(k)
    print(f"-- duplicates: {dupes}")
    # coverage: every version has a ml pe at r=1.0
    missing = [v for v in ORDER if _val(rows, v, "ml", "pe") is None]
    print(f"-- versions missing ML P_E @r=1.0: {missing}")
    if bad or dupes or missing:
        raise SystemExit(f"SANITY FAILED: mismatches={bad} dupes={dupes} missing={missing}")
    print("-- sanity OK --")


def main():
    rows = build()
    sanity(rows)
    write_master(rows, os.path.join(RES, "master_matrix.csv"))
    write_main_table(rows, os.path.join(RES, "main_table.csv"))


if __name__ == "__main__":
    main()
