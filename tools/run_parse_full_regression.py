#!/usr/bin/env python3
"""Run the protected /parse baseline, then the opt-in matrix wrapper.

Default behavior is unchanged. Pass `--report` to also emit a structured
per-case regression report under `reports/regression/<timestamp>/`.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.endpoints.artifact_runs import ensure_run_folder_name
from tests.endpoints.parse.artifacts import PARSE_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR

MATRIX_WRAPPER = (
    REPO_ROOT
    / "tools"
    / "reporting"
    / "run_parse_matrix_with_summary.py"
)

BASELINE_COMMAND = [
    sys.executable,
    "-m",
    "pytest",
    "tests/endpoints/parse/",
    "-v",
]


def _run_step(label: str, command: list[str], env: dict[str, str] | None = None) -> int:
    print(f"== {label} ==")
    print(subprocess.list2cmdline(command))
    completed = subprocess.run(command, cwd=REPO_ROOT, env=env)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        action="store_true",
        help="Emit structured per-case regression report for both baseline and matrix.",
    )
    parser.add_argument(
        "--file-types",
        default="",
        help="Forwarded to the matrix wrapper as --file-types.",
    )
    parser.add_argument(
        "--k",
        dest="k_expr",
        default="",
        help="Forwarded to the matrix wrapper as --k.",
    )
    args = parser.parse_args()

    shared_env = os.environ.copy()
    ensure_run_folder_name(
        shared_env,
        prefix="parse",
        env_var=PARSE_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR,
    )

    baseline_env = shared_env.copy()
    if args.report:
        baseline_env["REGRESSION_REPORT"] = "1"
        baseline_env.setdefault("REGRESSION_REPORT_TIER", "baseline")
    baseline_rc = _run_step("Protected baseline", BASELINE_COMMAND, env=baseline_env)
    if baseline_rc != 0:
        print(f"Stopped after protected baseline failed with exit code {baseline_rc}.")
        return baseline_rc

    matrix_cmd = [sys.executable, str(MATRIX_WRAPPER)]
    if args.report:
        matrix_cmd.append("--report")
    if args.file_types:
        matrix_cmd.extend(["--file-types", args.file_types])
    if args.k_expr:
        matrix_cmd.extend(["--k", args.k_expr])
    matrix_rc = _run_step("Parse matrix", matrix_cmd, env=shared_env.copy())
    if matrix_rc != 0:
        print(f"Full regression failed in matrix step with exit code {matrix_rc}.")
    return matrix_rc


if __name__ == "__main__":
    raise SystemExit(main())
