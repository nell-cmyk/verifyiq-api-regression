from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
RENDER_SCRIPT = SCRIPT_DIR / "render_regression_summary.py"
DEFAULT_TERMINAL_OUTPUT = REPO_ROOT / "reports" / "parse" / "matrix" / "latest-terminal.txt"
DEFAULT_SUMMARY_OUTPUT = REPO_ROOT / "reports" / "parse" / "matrix" / "latest-summary.md"
DEFAULT_PROMOTION_CANDIDATES = (
    REPO_ROOT / "docs" / "knowledge-base" / "parse" / "promotion-candidates.md"
)
CANONICAL_WRAPPER = REPO_ROOT / "tools" / "reporting" / "run_parse_matrix_with_summary.py"


def _default_pytest_command() -> list[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        "tests/endpoints/parse/test_parse_matrix.py",
        "-v",
    ]


def _normalize_remainder(remainder: list[str]) -> list[str]:
    if remainder and remainder[0] == "--":
        return remainder[1:]
    return remainder


def _command_display(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def _reported_command(*, mode: str, custom_command: list[str]) -> str:
    if custom_command:
        return _command_display(custom_command)

    wrapper_command = [sys.executable, str(CANONICAL_WRAPPER)]
    if mode == "apply":
        wrapper_command.extend(["--mode", "apply"])
    return _command_display(wrapper_command)


def run_matrix_and_capture(command: list[str], terminal_output: Path) -> int:
    terminal_output.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["RUN_PARSE_MATRIX"] = "1"

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
            log_file.write(chunk)

    return process.wait()


def render_summary(
    *,
    terminal_output: Path,
    summary_output: Path,
    promotion_candidates_path: Path,
    mode: str,
    command_display: str,
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
        command_display,
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT)
    return completed.returncode


def main() -> int:
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
        "pytest_cmd",
        nargs=argparse.REMAINDER,
        help="Optional custom command to run instead of the default pytest matrix command.",
    )
    args = parser.parse_args()

    custom_command = _normalize_remainder(args.pytest_cmd)
    command = custom_command or _default_pytest_command()
    terminal_output = Path(args.terminal_output).resolve()
    summary_output = Path(args.summary_output).resolve()
    promotion_candidates_path = Path(args.promotion_candidates_path).resolve()
    command_display = _reported_command(mode=args.mode, custom_command=custom_command)

    print(f"Running matrix command: {_command_display(command)}")
    pytest_rc = run_matrix_and_capture(command, terminal_output)

    summary_rc = render_summary(
        terminal_output=terminal_output,
        summary_output=summary_output,
        promotion_candidates_path=promotion_candidates_path,
        mode=args.mode,
        command_display=command_display,
    )

    if pytest_rc != 0:
        return pytest_rc
    return summary_rc


if __name__ == "__main__":
    raise SystemExit(main())
