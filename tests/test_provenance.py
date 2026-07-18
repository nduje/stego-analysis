"""Keep the tables honest: every number must still trace to the master matrix.

Runs the provenance re-derivation and asserts no cell in results/tables/ disagrees with
the value re-computed from results/csv/master_matrix.csv. Also checks that the guard would
actually fire on a tampered value (so the check is not vacuous).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.report.verify_provenance import verify, _cell_matches


def test_all_table_numbers_trace_to_matrix():
    checked, mism, problems = verify()
    assert checked > 0, "no cells were checked"
    assert mism == 0, f"{mism} table cells do not match the matrix: {problems[:5]}"
    print(f"provenance OK: {checked} cells, 0 mismatches")


def test_guard_catches_a_tampered_value():
    # a value that differs beyond tolerance must be flagged (guard is not vacuous)
    assert _cell_matches(0.086, "0.086")
    assert _cell_matches(0.086, "0.0860004")        # within rounding tolerance
    assert not _cell_matches(0.086, "0.200")        # tampered -> caught
    assert not _cell_matches("N/A", "0.5")
    print("guard catches tampering OK")


if __name__ == "__main__":
    test_all_table_numbers_trace_to_matrix()
    test_guard_catches_a_tampered_value()
    print("all provenance tests passed")
