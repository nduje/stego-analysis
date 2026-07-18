"""Generate the thesis tables from the master matrix -- no number is typed by hand.

Reads results/csv/master_matrix.csv and writes, into results/tables/{csv,html}/:
  * main_table          -- per version: PSNR region, round-trip, and P_E of every attack @ r=1.0
  * imperceptibility    -- PSNR/SSIM (global + region) per version @ r=1.0
  * detectability_by_rate -- P_E per version x attack x rate (appendix)
  * reference_payload   -- r -> bits -> bpc (payload alignment; source: reference_payload_mapping.csv)

CSV is the machine source; HTML pastes into Word keeping the table structure. Version and
attack labels are Croatian (reused from scripts.report.style); column keys stay English.
`build_tables` returns every table as (header, body) so provenance can re-derive and check.

Run (from the repo root):
    python -m scripts.report.make_tables
"""
import csv
import os

from scripts.report import style

MATRIX = "results/csv/master_matrix.csv"
PAYLOAD = "results/csv/reference_payload_mapping.csv"
CSV_DIR = "results/tables/csv"
HTML_DIR = "results/tables/html"
RATES = [0.05, 0.1, 0.25, 0.5, 1.0]
ATTACKS = ["chi2", "rs", "spa", "stegexpose", "ml"]
BOLD_MIN = {"main_table": (3, 4, 5, 6, 7)}   # columns where lowest = best detectability


def load_matrix():
    rows = {}
    with open(MATRIX, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[(r["version"], r["attack"], r["metric"], float(r["rate"]))] = float(r["value"])
    return rows


def _v(rows, version, attack, metric, rate=1.0):
    return rows.get((version, attack, metric, rate))


def _main_table(rows):
    header = ["verzija", "PSNR global (dB)", "round-trip (%)",
              "χ²", "RS", "SPA", "StegExpose", "ML"]
    body = []
    for v in style.ORDER:
        rt = _v(rows, v, "imperceptibility", "roundtrip_fail")
        row = [style.DISPLAY[v], _v(rows, v, "imperceptibility", "psnr_global"),
               "N/A" if rt is None else round(rt * 100, 1)]
        row += [_v(rows, v, atk, "pe") for atk in ATTACKS]
        body.append(row)
    return header, body


def _imperceptibility(rows):
    header = ["verzija", "PSNR global", "PSNR regija", "SSIM global"]
    body = [[style.DISPLAY[v], _v(rows, v, "imperceptibility", "psnr_global"),
             _v(rows, v, "imperceptibility", "psnr_region"),
             _v(rows, v, "imperceptibility", "ssim_global")] for v in style.ORDER]
    return header, body


def _detectability_by_rate(rows):
    header = ["verzija", "napad"] + [f"r={r:g}" for r in RATES]
    body = []
    for v in style.ORDER:
        for atk in ATTACKS:
            body.append([style.DISPLAY[v], style.ATTACK[atk]]
                        + [_v(rows, v, atk, "pe", r) for r in RATES])
    return header, body


def _reference_payload(rows):
    with open(PAYLOAD, newline="", encoding="utf-8") as f:
        src = list(csv.DictReader(f))
    header = ["stopa", "znakova", "bitova", "bpc"]
    body = [[float(r["rate"]), int(r["chars"]), int(r["bits"]), float(r["bpc"])] for r in src]
    return header, body


def build_tables(rows):
    """{name: (header, body)} -- the single definition used for both writing and provenance."""
    return {
        "main_table": _main_table(rows),
        "imperceptibility": _imperceptibility(rows),
        "detectability_by_rate": _detectability_by_rate(rows),
        "reference_payload": _reference_payload(rows),
    }


TITLES = {
    "main_table": "Profil detektabilnosti pri punoj ugradnji (stopa 1.0)",
    "imperceptibility": "Neprimjetnost pri stopi 1.0",
    "detectability_by_rate": "Detektabilnost (P_E) po verziji, napadu i stopi",
    "reference_payload": "Poravnanje payloada: stopa → bitovi → bpc",
}
NOTES = {
    "main_table": ("χ² na osnovnom/p1/p2 je invertiran (AUC ≈ 0.03); P_E ga broji kao "
                   "detekciju. N/A round-trip: reference se ne dekodiraju. P_E ≈ 0.5 = slijep napad."),
}


def _write_csv(name, header, body):
    os.makedirs(CSV_DIR, exist_ok=True)
    with open(f"{CSV_DIR}/{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(body)


def _write_html(name, header, body):
    os.makedirs(HTML_DIR, exist_ok=True)
    mins = {}
    for c in BOLD_MIN.get(name, ()):
        vals = [r[c] for r in body if isinstance(r[c], (int, float))]
        if vals:
            mins[c] = min(vals)
    css = "border:1px solid #999;padding:4px 8px;text-align:center;"
    html = ["<table style='border-collapse:collapse;font-family:sans-serif;font-size:13px;'>",
            f"<caption style='font-weight:bold;margin-bottom:6px;'>{TITLES[name]}</caption>",
            "<tr>" + "".join(f"<th style='{css}background:#eee;'>{h}</th>" for h in header) + "</tr>"]
    for r in body:
        cells = []
        for c, val in enumerate(r):
            txt = f"{val:.3f}" if isinstance(val, float) else str(val)
            b = c in mins and isinstance(val, (int, float)) and abs(val - mins[c]) < 1e-9
            cells.append(f"<td style='{css}{'font-weight:bold;' if b else ''}'>{txt}</td>")
        html.append("<tr>" + "".join(cells) + "</tr>")
    html.append("</table>")
    if name in NOTES:
        html.append(f"<p style='font-size:11px;color:#555;'>{NOTES[name]}</p>")
    with open(f"{HTML_DIR}/{name}.html", "w", encoding="utf-8") as f:
        f.write("\n".join(html))


def main():
    tables = build_tables(load_matrix())
    for name, (header, body) in tables.items():
        _write_csv(name, header, body)
        _write_html(name, header, body)
    print(f"wrote {len(tables)} tables -> {CSV_DIR} + {HTML_DIR}")


if __name__ == "__main__":
    main()
