"""Provenance check: every number in results/tables/ must come from the master matrix.

The tables are built only from results/csv/master_matrix.csv (and, for the payload table,
results/csv/reference_payload_mapping.csv). This re-derives each table straight from those
sources via make_tables.build_tables and compares it, cell by cell, to the CSV on disk. A
hand-edited or stale number in a table would not match its re-derived value and is reported
as a mismatch. Floats are compared with a small tolerance (rounding is allowed).

Run (from the repo root):
    python -m scripts.report.verify_provenance
"""
import csv
import os
import sys

from scripts.report.make_tables import CSV_DIR, build_tables, load_matrix

TOL = 1e-6


def _cell_matches(expected, got):
    if isinstance(expected, float):
        try:
            return abs(float(got) - expected) <= TOL
        except ValueError:
            return False
    if isinstance(expected, int):
        try:
            return int(got) == expected
        except ValueError:
            return False
    return str(expected) == got


def verify():
    tables = build_tables(load_matrix())
    checked = mism = 0
    problems = []
    for name, (header, body) in tables.items():
        path = os.path.join(CSV_DIR, f"{name}.csv")
        if not os.path.exists(path):
            problems.append(f"{name}: table CSV missing ({path})")
            continue
        with open(path, newline="", encoding="utf-8") as f:
            disk = list(csv.reader(f))
        if disk[0] != header:
            problems.append(f"{name}: header mismatch")
        for i, exp_row in enumerate(body, start=1):
            for j, exp in enumerate(exp_row):
                checked += 1
                got = disk[i][j] if i < len(disk) and j < len(disk[i]) else "<missing>"
                if not _cell_matches(exp, got):
                    mism += 1
                    problems.append(f"{name}[row {i}, col {j}]: table={got!r} matrix={exp!r}")
    return checked, mism, problems


def main():
    checked, mism, problems = verify()
    print(f"provenance: {checked} cells checked, {mism} mismatched")
    for p in problems[:20]:
        print("  " + p)
    if mism or any("missing" in p or "header" in p for p in problems):
        sys.exit(1)
    print("all table numbers trace to the master matrix (payload table: reference_payload_mapping.csv)")


if __name__ == "__main__":
    main()
