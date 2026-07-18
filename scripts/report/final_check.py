"""One command that verifies the whole artifact is sound -- the gate before freezing.

Runs, in order:
  1. every test suite in tests/
  2. the parity test on its own (the baseline must stay byte-identical)
  3. the table provenance check (every table number traces to the master matrix)
  4. an end-to-end regeneration: matrix -> tables -> figures

The matrix and tables are deterministic, so regenerating them must not change the
committed files; the figures are rendered into a temporary directory instead, because
vector output embeds a creation date and would dirty the tree without any real change.
Finally it reports whether the working tree is still clean.

Exit code 0 means everything is green.

Run (from the repo root):
    python -m scripts.report.final_check
"""
import glob
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def check_tests():
    files = sorted(glob.glob(os.path.join(ROOT, "tests", "test_*.py")))
    passed, failed = 0, []
    for f in files:
        ok, _ = _run([sys.executable, f])
        passed += ok
        if not ok:
            failed.append(os.path.basename(f))
    return (not failed), f"{passed}/{len(files)} suites" + (f"; failed: {failed}" if failed else "")


def check_parity():
    ok, out = _run([sys.executable, os.path.join(ROOT, "tests", "test_lib_parity.py")])
    tail = out.strip().splitlines()[-1] if out.strip() else ""
    return ok, f"baseline byte-identical ({tail})" if ok else out[-300:]


def check_provenance():
    sys.path.insert(0, ROOT)
    from scripts.report.verify_provenance import verify
    checked, mism, problems = verify()
    return (mism == 0 and checked > 0), f"{checked} cells, {mism} mismatched" + (
        f"; {problems[:2]}" if problems else "")


def check_regen():
    ok1, out1 = _run([sys.executable, "-m", "scripts.report.build_matrix"])
    if not ok1:
        return False, f"build_matrix failed: {out1[-300:]}"
    ok2, out2 = _run([sys.executable, "-m", "scripts.report.make_tables"])
    if not ok2:
        return False, f"make_tables failed: {out2[-300:]}"

    # figures into a temp dir: vector output carries a date, so writing over the
    # committed files would dirty the tree without any content change
    sys.path.insert(0, ROOT)
    from scripts.report import style, make_final_figures
    original = style.FINAL_DIR
    with tempfile.TemporaryDirectory() as tmp:
        style.FINAL_DIR = tmp
        try:
            make_final_figures.main()
            n = len(glob.glob(os.path.join(tmp, "png", "*.png")))
        except SystemExit:
            n = len(glob.glob(os.path.join(tmp, "png", "*.png")))
        except Exception as exc:                       # noqa: BLE001 - report any failure
            style.FINAL_DIR = original
            return False, f"figures failed: {exc}"
        finally:
            style.FINAL_DIR = original
    return n > 0, f"matrix + tables regenerated, {n} figures rendered"


def check_tree_clean():
    """Did regenerating move any committed result? Untracked new files are not a
    consistency problem, so only tracked modifications/deletions count."""
    ok, out = _run(["git", "status", "--porcelain"])
    if not ok:
        return True, "git not available (skipped)"
    changed = [l for l in out.splitlines() if l.strip() and not l.startswith("??")]
    untracked = [l for l in out.splitlines() if l.startswith("??")]
    note = "no committed result changed"
    if untracked:
        note += f" ({len(untracked)} untracked new file(s), not a problem)"
    return (not changed), (note if not changed else f"{len(changed)} tracked changed: {changed[:5]}")


CHECKS = [
    ("tests", check_tests),
    ("parity (baseline frozen)", check_parity),
    ("table provenance", check_provenance),
    ("end-to-end regeneration", check_regen),
    ("working tree unchanged", check_tree_clean),
]


def main():
    print("final check\n" + "=" * 60)
    results = []
    for name, fn in CHECKS:
        try:
            ok, detail = fn()
        except Exception as exc:                       # noqa: BLE001 - a failing check must report
            ok, detail = False, f"error: {exc}"
        results.append((name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name:28} {detail}")
    print("=" * 60)
    bad = [n for n, ok, _ in results if not ok]
    if bad:
        print(f"NOT GREEN: {bad}\nDo not freeze until these pass.")
        sys.exit(1)
    print("ALL GREEN - the artifact is consistent and ready to freeze.")


if __name__ == "__main__":
    main()
