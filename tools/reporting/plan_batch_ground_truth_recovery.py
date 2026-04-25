#!/usr/bin/env python3
"""Plan targeted batch ground-truth recovery reruns from recovery triage."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from pathlib import Path
import shlex
import sys
from typing import Any

RETRYABLE_RECOVERY_CLASSES = {
    "rate_limited",
    "transient_or_auth_failure",
}

INVALID_JSON_5XX_REVIEW_CLASS = "invalid_json_5xx_review"

REQUIRED_TRIAGE_COLUMNS = (
    "fileType",
    "recovery_class",
    "failure_tag",
    "batch_http_status",
)

EXPORTER_COMMAND = (
    "./.venv/bin/python",
    "tools/reporting/export_batch_ground_truth.py",
)


class PlannerError(RuntimeError):
    """Raised for clear operator-facing planner input errors."""


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
        raise PlannerError(f"triage CSV does not exist: {triage_csv}")
    return triage_csv


def _resolve_reference_workbook(value: str) -> Path:
    reference_workbook = Path(value).expanduser()
    if not reference_workbook.is_absolute():
        raise PlannerError("--reference-workbook must be an absolute path")
    reference_workbook = reference_workbook.resolve()
    if not reference_workbook.is_file():
        raise PlannerError(f"reference workbook does not exist: {reference_workbook}")
    return reference_workbook


def _read_triage_rows(triage_csv: Path) -> list[dict[str, str]]:
    with triage_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or ())
        missing_columns = [column for column in REQUIRED_TRIAGE_COLUMNS if column not in fieldnames]
        if missing_columns:
            raise PlannerError(
                "triage CSV is missing required columns: " + ", ".join(missing_columns)
            )
        return [
            row
            for row in reader
            if any(str(value or "").strip() for value in row.values())
        ]


def _parse_http_status(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _is_invalid_json_5xx_review(row: dict[str, str]) -> bool:
    failure_tag = str(row.get("failure_tag") or "").strip()
    return failure_tag == "invalid_json_response" and (
        (_parse_http_status(row.get("batch_http_status")) or 0) >= 500
    )


def _effective_recovery_class(row: dict[str, str]) -> str:
    if _is_invalid_json_5xx_review(row):
        return INVALID_JSON_5XX_REVIEW_CLASS
    return str(row.get("recovery_class") or "").strip() or "<none>"


def _shell_command(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def _format_float(value: float) -> str:
    return f"{value:g}"


def _build_export_command(
    *,
    reference_workbook: Path,
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
        rows = _read_triage_rows(triage_csv)
    except PlannerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    retryable_by_class: Counter[str] = Counter()
    retryable_by_file_type: Counter[str] = Counter()
    excluded_by_class: Counter[str] = Counter()
    missing_file_type_rows = 0

    for row in rows:
        recovery_class = _effective_recovery_class(row)
        if recovery_class in RETRYABLE_RECOVERY_CLASSES:
            file_type = str(row.get("fileType") or "").strip()
            if not file_type:
                missing_file_type_rows += 1
                continue
            retryable_by_class[recovery_class] += 1
            retryable_by_file_type[file_type] += 1
        else:
            excluded_by_class[recovery_class] += 1

    if missing_file_type_rows:
        print(
            f"ERROR: {missing_file_type_rows} retryable triage row(s) are missing fileType values.",
            file=sys.stderr,
        )
        return 2

    retryable_count = sum(retryable_by_class.values())
    excluded_count = len(rows) - retryable_count
    invalid_json_5xx_review_count = excluded_by_class.get(INVALID_JSON_5XX_REVIEW_CLASS, 0)
    approx_in_flight = args.max_concurrent_file_types * args.max_concurrent_chunks
    file_types = sorted(retryable_by_file_type)

    print("Batch GT recovery planner")
    print(f"Triage CSV: {triage_csv}")
    print(f"Reference workbook: {reference_workbook}")
    print(f"Total triage rows: {len(rows)}")
    print(f"Retryable recovery rows: {retryable_count}")
    print(f"Excluded/non-retryable rows: {excluded_count}")
    print(f"Invalid JSON 5xx review-only rows: {invalid_json_5xx_review_count}")
    print(f"Approx max in-flight batch requests for generated commands: {approx_in_flight}")
    _print_counter("Retryable rows by recovery_class", retryable_by_class)
    _print_counter("Retryable rows by fileType", retryable_by_file_type)
    _print_counter("Excluded rows by recovery_class", excluded_by_class)

    if invalid_json_5xx_review_count:
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
