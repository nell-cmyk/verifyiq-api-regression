#!/usr/bin/env python3
"""Advanced/internal helper for targeted /parse reporting runs.

Emits a structured per-case JSON + Markdown report under
`reports/regression/<timestamp>/`. This utility is for focused reporter
iteration and targeted inspection, not the default operator workflow.

Prefer these canonical commands for normal use:
- `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py`
- `./.venv/bin/python tools/run_parse_full_regression.py`

Examples:

  # one happy-path case
  ./.venv/bin/python tools/run_parse_with_report.py --tier baseline \
      --case tests/endpoints/parse/test_parse.py::TestParseHappyPath::test_returns_200

  # subset of the matrix by fileType
  ./.venv/bin/python tools/run_parse_with_report.py --tier matrix --file-types Payslip,TIN

  # full regression with report
  ./.venv/bin/python tools/run_parse_with_report.py --tier full
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MATRIX_WRAPPER = REPO_ROOT / "tools" / "reporting" / "run_parse_matrix_with_summary.py"
FULL_WRAPPER = REPO_ROOT / "tools" / "run_parse_full_regression.py"


def _baseline_cmd(args) -> list[str]:
    cmd = [sys.executable, "-m", "pytest", "-v"]
    if args.case:
        cmd.extend(args.case)
    else:
        cmd.append("tests/endpoints/parse/")
    if args.k_expr:
        cmd.extend(["-k", args.k_expr])
    return cmd


def _matrix_cmd(args) -> list[str]:
    cmd = [sys.executable, str(MATRIX_WRAPPER), "--report"]
    if args.file_types:
        cmd.extend(["--file-types", args.file_types])
    if args.k_expr:
        cmd.extend(["--k", args.k_expr])
    return cmd


def _full_cmd(args) -> list[str]:
    cmd = [sys.executable, str(FULL_WRAPPER), "--report"]
    if args.file_types:
        cmd.extend(["--file-types", args.file_types])
    if args.k_expr:
        cmd.extend(["--k", args.k_expr])
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=["baseline", "matrix", "full"], default="baseline")
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="Repeatable pytest nodeid (baseline tier only; ignored for matrix/full).",
    )
    parser.add_argument("--file-types", default="", help="Matrix/full: subset by registry fileType (comma-separated).")
    parser.add_argument("--k", dest="k_expr", default="", help="pytest -k expression passed through.")
    args = parser.parse_args()

    if args.tier == "baseline":
        env = os.environ.copy()
        env["REGRESSION_REPORT"] = "1"
        env.setdefault("REGRESSION_REPORT_TIER", "baseline")
        cmd = _baseline_cmd(args)
        print(subprocess.list2cmdline(cmd))
        return subprocess.run(cmd, cwd=REPO_ROOT, env=env).returncode

    if args.tier == "matrix":
        cmd = _matrix_cmd(args)
        print(subprocess.list2cmdline(cmd))
        return subprocess.run(cmd, cwd=REPO_ROOT).returncode

    cmd = _full_cmd(args)
    print(subprocess.list2cmdline(cmd))
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
