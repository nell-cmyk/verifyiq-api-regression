#!/usr/bin/env python3
"""Plan targeted batch ground-truth recovery reruns from recovery triage."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import shlex
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.reporting.batch_ground_truth.recovery import (
    INVALID_JSON_5XX_REVIEW_CLASS,
    RecoveryTriageError,
    read_recovery_triage_rows,
    summarize_retryable_recovery_rows,
)

EXPORTER_COMMAND = (
    "./.venv/bin/python",
    "tools/reporting/export_batch_ground_truth.py",
)


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def _non_negative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a non-negative number") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative number")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    triage_source = parser.add_mutually_exclusive_group(required=True)
    triage_source.add_argument(
        "--triage-csv",
        help="Path to a recovery_triage.csv file from a previous batch GT run.",
    )
    triage_source.add_argument(
        "--run-dir",
        help=(
            "Path to a previous reports/batch_ground_truth/batch_ground_truth_<timestamp>/ "
            "directory. The planner reads recovery_triage.csv inside it."
        ),
    )
    parser.add_argument(
        "--reference-workbook",
        required=True,
        help="Absolute path to the reference workbook to pass to the generated exporter command.",
    )
    parser.add_argument(
        "--row-level",
        action="store_true",
        help=(
            "Generate exporter commands that restrict execution to exact retryable rows "
            "from the triage CSV via --recovery-triage-csv. Defaults to fileType-level commands."
        ),
    )
    parser.add_argument(
        "--max-concurrent-file-types",
        type=_positive_int,
        default=1,
        help="Maximum fileTypes for the generated rerun command. Defaults to 1.",
    )
    parser.add_argument(
        "--max-concurrent-chunks",
        type=_positive_int,
        default=1,
        help="Maximum chunks per fileType for the generated rerun command. Defaults to 1.",
    )
    parser.add_argument(
        "--token-expiry-retries",
        type=_non_negative_int,
        default=1,
        help="Token-expiry retries for the generated rerun command. Defaults to 1.",
    )
    parser.add_argument(
        "--transient-chunk-retries",
        type=_non_negative_int,
        default=1,
        help="Transient chunk retries for the generated rerun command. Defaults to 1.",
    )
    parser.add_argument(
        "--rate-limit-retries",
        type=_non_negative_int,
        default=1,
        help="HTTP 429 retries for the generated rerun command. Defaults to 1.",
    )
    parser.add_argument(
        "--rate-limit-backoff-secs",
        type=_non_negative_float,
        default=2.0,
        help="HTTP 429 fallback backoff seconds for the generated rerun command. Defaults to 2.",
    )
    return parser


def _resolve_triage_csv(args: argparse.Namespace) -> Path:
    if args.triage_csv:
        triage_csv = Path(args.triage_csv).expanduser()
    else:
        triage_csv = Path(args.run_dir).expanduser() / "recovery_triage.csv"
    triage_csv = triage_csv.resolve()
    if not triage_csv.is_file():
        raise RecoveryTriageError(f"triage CSV does not exist: {triage_csv}")
    return triage_csv


def _resolve_reference_workbook(value: str) -> Path:
    reference_workbook = Path(value).expanduser()
    if not reference_workbook.is_absolute():
        raise RecoveryTriageError("--reference-workbook must be an absolute path")
    reference_workbook = reference_workbook.resolve()
    if not reference_workbook.is_file():
        raise RecoveryTriageError(f"reference workbook does not exist: {reference_workbook}")
    return reference_workbook


def _shell_command(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def _format_float(value: float) -> str:
    return f"{value:g}"


def _build_export_command(
    *,
    reference_workbook: Path,
    recovery_triage_csv: Path | None,
    file_types: list[str],
    max_concurrent_file_types: int,
    max_concurrent_chunks: int,
    token_expiry_retries: int,
    transient_chunk_retries: int,
    rate_limit_retries: int,
    rate_limit_backoff_secs: float,
    plan: bool,
) -> str:
    parts = [
        *EXPORTER_COMMAND,
        "--reference-workbook",
        str(reference_workbook),
    ]
    if recovery_triage_csv is not None:
        parts.extend(["--recovery-triage-csv", str(recovery_triage_csv)])
    for file_type in file_types:
        parts.extend(["--file-type", file_type])
    parts.extend(
        [
            "--max-concurrent-file-types",
            str(max_concurrent_file_types),
            "--max-concurrent-chunks",
            str(max_concurrent_chunks),
            "--token-expiry-retries",
            str(token_expiry_retries),
            "--transient-chunk-retries",
            str(transient_chunk_retries),
            "--rate-limit-retries",
            str(rate_limit_retries),
            "--rate-limit-backoff-secs",
            _format_float(rate_limit_backoff_secs),
        ]
    )
    if plan:
        parts.append("--plan")
    return _shell_command(parts)


def _print_counter(title: str, counts: Counter[str]) -> None:
    print(f"{title}:")
    if not counts:
        print("- none")
        return
    for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"- {key}: {count}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        triage_csv = _resolve_triage_csv(args)
        reference_workbook = _resolve_reference_workbook(args.reference_workbook)
        rows = read_recovery_triage_rows(
            triage_csv,
            require_row_identity=args.row_level,
        )
        selection = summarize_retryable_recovery_rows(
            rows,
            include_row_keys=args.row_level,
        )
    except RecoveryTriageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if "<none>" in selection.retryable_by_file_type:
        print(
            "ERROR: retryable triage row(s) are missing fileType values.",
            file=sys.stderr,
        )
        return 2

    approx_in_flight = args.max_concurrent_file_types * args.max_concurrent_chunks
    file_types = sorted(selection.retryable_by_file_type)
    retryable_by_class = Counter(selection.retryable_by_class)
    retryable_by_file_type = Counter(selection.retryable_by_file_type)
    excluded_by_class = Counter(selection.excluded_by_class)

    print("Batch GT recovery planner")
    print(f"Triage CSV: {triage_csv}")
    print(f"Reference workbook: {reference_workbook}")
    print(f"Recovery command mode: {'row-level' if args.row_level else 'fileType-level'}")
    print(f"Total triage rows: {selection.total_rows}")
    print(f"Retryable recovery rows: {selection.retryable_rows}")
    print(f"Excluded/non-retryable rows: {selection.excluded_rows}")
    print(f"Invalid JSON 5xx review-only rows: {selection.invalid_json_5xx_review_rows}")
    if args.row_level:
        print(f"Row-level recovery filter rows: {len(selection.row_keys)}")
    print(f"Approx max in-flight batch requests for generated commands: {approx_in_flight}")
    _print_counter("Retryable rows by recovery_class", retryable_by_class)
    _print_counter("Retryable rows by fileType", retryable_by_file_type)
    _print_counter("Excluded rows by recovery_class", excluded_by_class)

    if selection.invalid_json_5xx_review_rows:
        print(
            "Note: invalid_json_response rows with HTTP status >=500 are review-only, "
            "not retryable transient/auth recovery candidates."
        )

    if not file_types:
        print("No retryable recovery candidates found. No targeted rerun command was generated.")
        return 0

    print("Plan command (no live calls):")
    print(
        _build_export_command(
            reference_workbook=reference_workbook,
            recovery_triage_csv=triage_csv if args.row_level else None,
            file_types=file_types,
            max_concurrent_file_types=args.max_concurrent_file_types,
            max_concurrent_chunks=args.max_concurrent_chunks,
            token_expiry_retries=args.token_expiry_retries,
            transient_chunk_retries=args.transient_chunk_retries,
            rate_limit_retries=args.rate_limit_retries,
            rate_limit_backoff_secs=args.rate_limit_backoff_secs,
            plan=True,
        )
    )
    print("Live command (operator-run only):")
    print(
        _build_export_command(
            reference_workbook=reference_workbook,
            recovery_triage_csv=triage_csv if args.row_level else None,
            file_types=file_types,
            max_concurrent_file_types=args.max_concurrent_file_types,
            max_concurrent_chunks=args.max_concurrent_chunks,
            token_expiry_retries=args.token_expiry_retries,
            transient_chunk_retries=args.transient_chunk_retries,
            rate_limit_retries=args.rate_limit_retries,
            rate_limit_backoff_secs=args.rate_limit_backoff_secs,
            plan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
