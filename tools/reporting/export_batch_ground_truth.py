#!/usr/bin/env python3
"""Export /documents/batch results to one ground-truth workbook per fileType."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.fixtures.registry import REGISTRY_PATH as SHARED_REGISTRY_PATH
from tools.reporting.batch_ground_truth.schema import load_reference_template
from tools.reporting.batch_ground_truth.workflow import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_RATE_LIMIT_BACKOFF_SECS,
    DEFAULT_RATE_LIMIT_RETRIES,
    DEFAULT_TOKEN_EXPIRY_RETRIES,
    DEFAULT_TRANSIENT_CHUNK_RETRIES,
    plan_file_types,
    run_batch_ground_truth_export,
)


def _parse_file_types(values: list[str]) -> set[str]:
    file_types: set[str] = set()
    for value in values:
        for part in value.split(","):
            cleaned = part.strip()
            if cleaned:
                file_types.add(cleaned)
    return file_types


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
    parser = argparse.ArgumentParser(
        description=__doc__,
    )
    parser.add_argument(
        "--fixture-registry",
        default=str(SHARED_REGISTRY_PATH),
        help="Generated fixture registry YAML to read. Defaults to tests/fixtures/fixture_registry.yaml.",
    )
    parser.add_argument(
        "--source-workbook",
        default="",
        help=(
            "Deprecated migration guard. The exporter now reads the generated YAML registry; "
            "edit the workbook, run tools/generate_fixture_registry.py, then use --fixture-registry if needed."
        ),
    )
    parser.add_argument(
        "--reference-workbook",
        required=True,
        help="Reference workbook whose flat layout/style should be mirrored and adapted.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help=(
            "Output directory for this run. Defaults to "
            f"{DEFAULT_OUTPUT_ROOT.as_posix()}/batch_ground_truth_<timestamp>/"
        ),
    )
    parser.add_argument(
        "--file-type",
        dest="file_types",
        action="append",
        default=[],
        help="Repeat or comma-separate to export selected split fileTypes only.",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Inspect registry coverage and planned chunking without calling the live endpoint.",
    )
    parser.add_argument(
        "--max-concurrent-chunks",
        type=_positive_int,
        default=1,
        help=(
            "Maximum number of in-flight batch chunks within one fileType. "
            "Defaults to 1 for the current sequential behavior."
        ),
    )
    parser.add_argument(
        "--max-concurrent-file-types",
        type=_positive_int,
        default=1,
        help=(
            "Maximum number of fileTypes to export at once. Defaults to 1 "
            "to preserve fileType-sequential execution."
        ),
    )
    parser.add_argument(
        "--token-expiry-retries",
        type=_non_negative_int,
        default=DEFAULT_TOKEN_EXPIRY_RETRIES,
        help=(
            "Number of same-chunk retries after a confirmed IAP/OIDC/JWT token expiry. "
            f"Defaults to {DEFAULT_TOKEN_EXPIRY_RETRIES}."
        ),
    )
    parser.add_argument(
        "--transient-chunk-retries",
        type=_non_negative_int,
        default=DEFAULT_TRANSIENT_CHUNK_RETRIES,
        help=(
            "Number of same-chunk retries for transient ReadTimeout or "
            "RemoteProtocolError failures. "
            f"Defaults to {DEFAULT_TRANSIENT_CHUNK_RETRIES}."
        ),
    )
    parser.add_argument(
        "--rate-limit-retries",
        type=_non_negative_int,
        default=DEFAULT_RATE_LIMIT_RETRIES,
        help=(
            "Number of same-chunk retries after HTTP 429 rate limiting. "
            f"Defaults to {DEFAULT_RATE_LIMIT_RETRIES}."
        ),
    )
    parser.add_argument(
        "--rate-limit-backoff-secs",
        type=_non_negative_float,
        default=DEFAULT_RATE_LIMIT_BACKOFF_SECS,
        help=(
            "Fallback seconds for HTTP 429 retry backoff when Retry-After is absent. "
            f"Defaults to {DEFAULT_RATE_LIMIT_BACKOFF_SECS}."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.source_workbook:
        print(
            "ERROR: --source-workbook no longer drives normal batch export execution. "
            "Regenerate the shared fixture registry, then use --fixture-registry.",
            file=sys.stderr,
        )
        return 2

    selected_file_types = _parse_file_types(args.file_types)
    selected = selected_file_types or None
    try:
        parsed, _grouped, plans = plan_file_types(
            fixture_registry=args.fixture_registry,
            selected_file_types=selected,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not plans:
        print("ERROR: No matching fileTypes were found in the fixture registry.", file=sys.stderr)
        return 2

    print(f"Fixture registry: {Path(args.fixture_registry).expanduser().resolve()}")
    if parsed.source_workbook is not None:
        print(f"Curated source workbook: {parsed.source_workbook}")
    print(f"Reference workbook: {Path(args.reference_workbook).expanduser().resolve()}")
    print(f"Selected fileTypes: {len(plans)}")
    print(f"Max concurrent fileTypes: {args.max_concurrent_file_types}")
    print(f"Max concurrent chunks per fileType: {args.max_concurrent_chunks}")
    print(f"Token-expiry retries per chunk: {args.token_expiry_retries}")
    print(f"Transient transport retries per chunk: {args.transient_chunk_retries}")
    print(f"Rate-limit retries per chunk: {args.rate_limit_retries}")
    print(f"Rate-limit fallback backoff seconds: {args.rate_limit_backoff_secs:g}")
    print(
        "Approx max in-flight batch requests: "
        f"{args.max_concurrent_file_types * args.max_concurrent_chunks}"
    )
    for plan in plans:
        print(
            f"- {plan.file_type}: total_rows={plan.total_rows}, executable_rows={plan.executable_rows}, "
            f"skipped_rows={plan.skipped_rows}, chunk_count={plan.chunk_count}"
        )

    if args.plan:
        return 0

    try:
        layout = load_reference_template(args.reference_workbook)
        result = run_batch_ground_truth_export(
            fixture_registry=args.fixture_registry,
            reference_workbook=args.reference_workbook,
            output_dir=args.output_dir or None,
            selected_file_types=selected,
            template_layout=layout,
            max_concurrent_chunks=args.max_concurrent_chunks,
            max_concurrent_file_types=args.max_concurrent_file_types,
            token_expiry_retries=args.token_expiry_retries,
            transient_chunk_retries=args.transient_chunk_retries,
            rate_limit_retries=args.rate_limit_retries,
            rate_limit_backoff_secs=args.rate_limit_backoff_secs,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Output dir: {result.output_dir}")
    print(f"Manifest: {result.manifest_path}")
    clean_manifest_path = getattr(result, "clean_manifest_path", None)
    recovery_triage_json_path = getattr(result, "recovery_triage_json_path", None)
    recovery_triage_csv_path = getattr(result, "recovery_triage_csv_path", None)
    if clean_manifest_path is not None:
        print(f"Clean manifest: {clean_manifest_path}")
    if recovery_triage_json_path is not None:
        print(f"Recovery triage JSON: {recovery_triage_json_path}")
    if recovery_triage_csv_path is not None:
        print(f"Recovery triage CSV: {recovery_triage_csv_path}")
    print(f"Batch artifact dir: {result.batch_artifact_run_dir}")
    for file_type_result in result.file_type_results:
        print(
            f"- {file_type_result.file_type}: "
            f"success_rows={file_type_result.success_rows}, "
            f"failed_rows={file_type_result.failed_rows}, "
            f"skipped_rows={file_type_result.skipped_rows}, "
            f"clean_rows={getattr(file_type_result, 'clean_rows', 0)}, "
            f"triaged_rows={getattr(file_type_result, 'triaged_rows', 0)}, "
            f"workbook={file_type_result.workbook_path}"
        )
        clean_workbook_path = getattr(file_type_result, "clean_workbook_path", None)
        if clean_workbook_path is not None:
            print(f"  clean_workbook={clean_workbook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
