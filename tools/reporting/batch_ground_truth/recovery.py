from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import SourceFixtureRecord

RETRYABLE_RECOVERY_CLASSES = {
    "rate_limited",
    "transient_or_auth_failure",
}

INVALID_JSON_5XX_REVIEW_CLASS = "invalid_json_5xx_review"

TRIAGE_SUMMARY_COLUMNS = (
    "fileType",
    "recovery_class",
    "failure_tag",
    "batch_http_status",
)

TRIAGE_ROW_IDENTITY_COLUMNS = (
    "source_row",
    "source_gcs_uri",
    "request_file_type",
)


class RecoveryTriageError(RuntimeError):
    """Raised for clear operator-facing recovery triage input errors."""


@dataclass(frozen=True, order=True)
class RecoveryRowKey:
    file_type: str
    request_file_type: str
    source_row: int
    source_gcs_uri: str


@dataclass(frozen=True)
class RetryableRecoverySelection:
    row_keys: frozenset[RecoveryRowKey]
    total_rows: int
    retryable_rows: int
    excluded_rows: int
    invalid_json_5xx_review_rows: int
    retryable_by_class: dict[str, int]
    retryable_by_file_type: dict[str, int]
    excluded_by_class: dict[str, int]


def parse_http_status(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def is_invalid_json_5xx_review(row: dict[str, str]) -> bool:
    failure_tag = str(row.get("failure_tag") or "").strip()
    return failure_tag == "invalid_json_response" and (
        (parse_http_status(row.get("batch_http_status")) or 0) >= 500
    )


def effective_recovery_class(row: dict[str, str]) -> str:
    if is_invalid_json_5xx_review(row):
        return INVALID_JSON_5XX_REVIEW_CLASS
    return str(row.get("recovery_class") or "").strip() or "<none>"


def is_retryable_recovery_row(row: dict[str, str]) -> bool:
    return effective_recovery_class(row) in RETRYABLE_RECOVERY_CLASSES


def read_recovery_triage_rows(
    triage_csv: Path | str,
    *,
    require_row_identity: bool = False,
) -> list[dict[str, str]]:
    triage_path = Path(triage_csv).expanduser().resolve()
    if not triage_path.is_file():
        raise RecoveryTriageError(f"triage CSV does not exist: {triage_path}")

    required_columns = list(TRIAGE_SUMMARY_COLUMNS)
    if require_row_identity:
        required_columns.extend(TRIAGE_ROW_IDENTITY_COLUMNS)

    with triage_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or ())
        missing_columns = [column for column in required_columns if column not in fieldnames]
        if missing_columns:
            raise RecoveryTriageError(
                "triage CSV is missing required columns: " + ", ".join(missing_columns)
            )
        return [
            row
            for row in reader
            if any(str(value or "").strip() for value in row.values())
        ]


def recovery_row_key_from_fixture(fixture: SourceFixtureRecord) -> RecoveryRowKey:
    return RecoveryRowKey(
        file_type=fixture.file_type,
        request_file_type=fixture.request_file_type,
        source_row=fixture.source_row,
        source_gcs_uri=fixture.gcs_uri,
    )


def recovery_row_key_from_triage_row(row: dict[str, str]) -> RecoveryRowKey:
    raw_source_row = str(row.get("source_row") or "").strip()
    try:
        source_row = int(raw_source_row)
    except ValueError as exc:
        raise RecoveryTriageError(
            f"retryable triage row has invalid source_row: {raw_source_row!r}"
        ) from exc

    file_type = str(row.get("fileType") or "").strip()
    request_file_type = str(row.get("request_file_type") or "").strip()
    source_gcs_uri = str(row.get("source_gcs_uri") or "").strip()
    missing = []
    if not file_type:
        missing.append("fileType")
    if not request_file_type:
        missing.append("request_file_type")
    if not source_gcs_uri:
        missing.append("source_gcs_uri")
    if missing:
        raise RecoveryTriageError(
            "retryable triage row is missing required identity values: "
            + ", ".join(missing)
        )

    return RecoveryRowKey(
        file_type=file_type,
        request_file_type=request_file_type,
        source_row=source_row,
        source_gcs_uri=source_gcs_uri,
    )


def summarize_retryable_recovery_rows(
    rows: list[dict[str, str]],
    *,
    selected_file_types: set[str] | None = None,
    include_row_keys: bool = False,
) -> RetryableRecoverySelection:
    retryable_by_class: Counter[str] = Counter()
    retryable_by_file_type: Counter[str] = Counter()
    excluded_by_class: Counter[str] = Counter()
    row_keys: set[RecoveryRowKey] = set()

    for row in rows:
        file_type = str(row.get("fileType") or "").strip()
        if selected_file_types is not None and file_type not in selected_file_types:
            continue

        recovery_class = effective_recovery_class(row)
        if recovery_class in RETRYABLE_RECOVERY_CLASSES:
            retryable_by_class[recovery_class] += 1
            retryable_by_file_type[file_type or "<none>"] += 1
            if include_row_keys:
                row_keys.add(recovery_row_key_from_triage_row(row))
        else:
            excluded_by_class[recovery_class] += 1

    retryable_rows = sum(retryable_by_class.values())
    excluded_rows = sum(excluded_by_class.values())
    return RetryableRecoverySelection(
        row_keys=frozenset(row_keys),
        total_rows=retryable_rows + excluded_rows,
        retryable_rows=retryable_rows,
        excluded_rows=excluded_rows,
        invalid_json_5xx_review_rows=excluded_by_class.get(INVALID_JSON_5XX_REVIEW_CLASS, 0),
        retryable_by_class=dict(retryable_by_class),
        retryable_by_file_type=dict(retryable_by_file_type),
        excluded_by_class=dict(excluded_by_class),
    )


def load_retryable_recovery_selection(
    triage_csv: Path | str,
    *,
    selected_file_types: set[str] | None = None,
) -> RetryableRecoverySelection:
    rows = read_recovery_triage_rows(triage_csv, require_row_identity=True)
    return summarize_retryable_recovery_rows(
        rows,
        selected_file_types=selected_file_types,
        include_row_keys=True,
    )
