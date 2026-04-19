#!/usr/bin/env python3
"""Run the protected /parse baseline, then the opt-in matrix wrapper."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MATRIX_WRAPPER = (
    REPO_ROOT
    / ".codex"
    / "skills"
    / "regression-run-summary"
    / "scripts"
    / "run_parse_matrix_with_summary.py"
)

BASELINE_COMMAND = [
    sys.executable,
    "-m",
    "pytest",
    "tests/endpoints/parse/",
    "-v",
]
MATRIX_COMMAND = [sys.executable, str(MATRIX_WRAPPER)]


def _run_step(label: str, command: list[str]) -> int:
    print(f"== {label} ==")
    print(subprocess.list2cmdline(command))
    completed = subprocess.run(command, cwd=REPO_ROOT)
    return completed.returncode


def main() -> int:
    baseline_rc = _run_step("Protected baseline", BASELINE_COMMAND)
    if baseline_rc != 0:
        print(f"Stopped after protected baseline failed with exit code {baseline_rc}.")
        return baseline_rc

    matrix_rc = _run_step("Parse matrix", MATRIX_COMMAND)
    if matrix_rc != 0:
        print(f"Full regression failed in matrix step with exit code {matrix_rc}.")
    return matrix_rc


if __name__ == "__main__":
    raise SystemExit(main())
