#!/usr/bin/env python3
"""Run the opt-in /parse matrix, capture terminal output, and render a summary."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.endpoints.parse.fixture_json import normalize_fixture_json_entries
from tests.endpoints.artifact_runs import ensure_run_folder_name
from tests.endpoints.parse.artifacts import PARSE_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR

RENDER_SCRIPT = Path(__file__).resolve().with_name("render_regression_summary.py")
DEFAULT_TERMINAL_OUTPUT = REPO_ROOT / "reports" / "parse" / "matrix" / "latest-terminal.txt"
DEFAULT_SUMMARY_OUTPUT = REPO_ROOT / "reports" / "parse" / "matrix" / "latest-summary.md"
DEFAULT_PROMOTION_CANDIDATES = (
    REPO_ROOT / "docs" / "knowledge-base" / "parse" / "promotion-candidates.md"
)
CANONICAL_WRAPPER = REPO_ROOT / "tools" / "reporting" / "run_parse_matrix_with_summary.py"


def default_pytest_command(
    *,
    k_expr: str | None = None,
    file_types: list[str] | None = None,
    extra: list[str] | None = None,
) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/endpoints/parse/test_parse_matrix.py",
        "-v",
    ]
    k_parts: list[str] = []
    if file_types:
        k_parts.append(" or ".join(ft.strip() for ft in file_types if ft.strip()))
    if k_expr:
        k_parts.append(f"({k_expr})")
    combined_k = " and ".join(part for part in k_parts if part)
    if combined_k:
        cmd.extend(["-k", combined_k])
    if extra:
        cmd.extend(extra)
    return cmd


def normalize_remainder(remainder: list[str]) -> list[str]:
    if remainder and remainder[0] == "--":
        return remainder[1:]
    return remainder


def command_display(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def print_skipped_fixture_entries(*, fixtures_json: Path, skipped) -> None:
    print(f"Skipped unsupported entries: {len(skipped)}")
    for item in skipped:
        print(f"  - {item.gcs_uri}: {item.reason}")
    print(f"Filtered JSON input: {fixtures_json}")


def reported_command(
    *,
    mode: str,
    custom_command: list[str],
    fixtures_json: Path | None = None,
) -> str:
    if custom_command:
        return command_display(custom_command)

    wrapper_command = [sys.executable, str(CANONICAL_WRAPPER)]
    if mode == "apply":
        wrapper_command.extend(["--mode", "apply"])
    if fixtures_json is not None:
        wrapper_command.extend(["--fixtures-json", str(fixtures_json)])
    return command_display(wrapper_command)


def run_matrix_and_capture(
    command: list[str],
    terminal_output: Path,
    *,
    report: bool = False,
    fixtures_json: Path | None = None,
) -> int:
    terminal_output.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["RUN_PARSE_MATRIX"] = "1"
    ensure_run_folder_name(
        env,
        prefix="parse",
        env_var=PARSE_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR,
    )
    if report:
        env["REGRESSION_REPORT"] = "1"
        env.setdefault("REGRESSION_REPORT_TIER", "matrix")
    if fixtures_json is not None:
        env["PARSE_MATRIX_FIXTURES_JSON"] = str(fixtures_json)
    else:
        env.pop("PARSE_MATRIX_FIXTURES_JSON", None)

    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    assert process.stdout is not None
    with terminal_output.open("w", encoding="utf-8", newline="\n") as log_file:
        for chunk in process.stdout:
            sys.stdout.write(chunk)
            sys.stdout.flush()
            log_file.write(chunk)
            log_file.flush()

    return process.wait()


def render_summary(
    *,
    terminal_output: Path,
    summary_output: Path,
    promotion_candidates_path: Path,
    mode: str,
    command_to_report: str,
    fixtures_json: Path | None = None,
) -> int:
    cmd = [
        sys.executable,
        str(RENDER_SCRIPT),
        "--endpoint",
        "parse",
        "--input",
        str(terminal_output),
        "--output",
        str(summary_output),
        "--promotion-candidates-path",
        str(promotion_candidates_path),
        "--mode",
        mode,
        "--command",
        command_to_report,
    ]
    if fixtures_json is not None:
        cmd.extend(["--fixtures-json", str(fixtures_json)])
    completed = subprocess.run(cmd, cwd=REPO_ROOT)
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the /parse matrix, save terminal output, and render a post-run summary.",
    )
    parser.add_argument("--mode", choices=["draft", "apply"], default="draft")
    parser.add_argument("--terminal-output", default=str(DEFAULT_TERMINAL_OUTPUT))
    parser.add_argument("--summary-output", default=str(DEFAULT_SUMMARY_OUTPUT))
    parser.add_argument(
        "--promotion-candidates-path",
        default=str(DEFAULT_PROMOTION_CANDIDATES),
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Also emit a structured per-case regression report under reports/regression/.",
    )
    parser.add_argument(
        "--file-types",
        default="",
        help="Comma-separated registry fileTypes to subset the matrix (e.g. 'Payslip,TIN').",
    )
    parser.add_argument(
        "--fixtures-json",
        default="",
        help="JSON file of gs:// paths to run through the matrix instead of canonical selection.",
    )
    parser.add_argument(
        "--k",
        dest="k_expr",
        default="",
        help="Extra pytest -k expression applied on top of --file-types.",
    )
    parser.add_argument(
        "pytest_cmd",
        nargs=argparse.REMAINDER,
        help="Optional custom command to run instead of the default pytest matrix command.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    custom_command = normalize_remainder(args.pytest_cmd)
    file_types = [ft for ft in (args.file_types or "").split(",") if ft.strip()]
    fixtures_json = Path(args.fixtures_json).resolve() if args.fixtures_json else None
    if fixtures_json is not None and not fixtures_json.exists():
        raise SystemExit(f"Fixture JSON not found: {fixtures_json}")
    if fixtures_json is not None and file_types:
        raise SystemExit("--fixtures-json and --file-types are mutually exclusive.")
    if fixtures_json is not None:
        try:
            normalization = normalize_fixture_json_entries(fixtures_json)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if normalization.skipped:
            print_skipped_fixture_entries(fixtures_json=fixtures_json, skipped=normalization.skipped)
        if not normalization.entries:
            raise SystemExit(
                "No supported fixture entries remained after filtering unsupported formats "
                f"from {fixtures_json}."
            )
    if custom_command:
        command = custom_command
    else:
        command = default_pytest_command(
            k_expr=args.k_expr or None,
            file_types=file_types or None,
        )

    terminal_output = Path(args.terminal_output).resolve()
    summary_output = Path(args.summary_output).resolve()
    promotion_candidates_path = Path(args.promotion_candidates_path).resolve()
    command_to_report = reported_command(
        mode=args.mode,
        custom_command=custom_command,
        fixtures_json=fixtures_json,
    )

    print(f"Running matrix command: {command_display(command)}")
    pytest_rc = run_matrix_and_capture(
        command,
        terminal_output,
        report=args.report,
        fixtures_json=fixtures_json,
    )

    summary_rc = render_summary(
        terminal_output=terminal_output,
        summary_output=summary_output,
        promotion_candidates_path=promotion_candidates_path,
        mode=args.mode,
        command_to_report=command_to_report,
        fixtures_json=fixtures_json,
    )

    if pytest_rc != 0:
        return pytest_rc
    return summary_rc


if __name__ == "__main__":
    raise SystemExit(main())
