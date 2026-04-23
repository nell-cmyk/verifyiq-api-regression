from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from tests.endpoints.parse.file_types import request_file_type_for
from tests.endpoints.parse.fixture_json import unsupported_fixture_reason
from tools.generate_fixture_registry import (
    COMPOSITE_DELIMITER,
    EXCLUDED_FILE_TYPES,
    HEADER_ROW,
    SHEET_NAME,
    SOURCE_XLSX,
    classify,
    fixture_metadata_overrides_for,
)

from .models import ExcludedSourceRow, SourceFixtureRecord, SourceWorkbookParseResult

EXPECTED_HEADERS = (
    "Folder",
    "fileType",
    "gsutil Path",
    "fileType Status",
    "Assignee",
    "Status",
)


def _clean_string(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _base_name_from_uri(uri: str) -> str:
    base = uri.rsplit("/", 1)[-1]
    stem = base.rsplit(".", 1)[0] if "." in base else base
    return stem.strip() or "fixture"


def parse_source_workbook(source_workbook: Path | str = SOURCE_XLSX) -> SourceWorkbookParseResult:
    workbook_path = Path(source_workbook).expanduser().resolve()
    if not workbook_path.exists():
        raise RuntimeError(f"Source fixture workbook not found: {workbook_path}")

    workbook = load_workbook(workbook_path, data_only=True)
    if SHEET_NAME not in workbook.sheetnames:
        raise RuntimeError(f"Sheet {SHEET_NAME!r} not found in {workbook_path}; got {workbook.sheetnames}")
    sheet = workbook[SHEET_NAME]

    headers = tuple(sheet.cell(HEADER_ROW, column).value for column in range(1, sheet.max_column + 1))
    if headers[: len(EXPECTED_HEADERS)] != EXPECTED_HEADERS:
        raise RuntimeError(
            f"Unexpected headers in {workbook_path} row {HEADER_ROW}: "
            f"expected {EXPECTED_HEADERS!r}, got {headers[:len(EXPECTED_HEADERS)]!r}"
        )

    fixtures: list[SourceFixtureRecord] = []
    excluded_rows: list[ExcludedSourceRow] = []
    record_id = 0

    for row_idx in range(HEADER_ROW + 1, sheet.max_row + 1):
        folder = _clean_string(sheet.cell(row_idx, 1).value) or None
        raw_file_type = _clean_string(sheet.cell(row_idx, 2).value)
        gcs_uri = _clean_string(sheet.cell(row_idx, 3).value)
        file_type_status = _clean_string(sheet.cell(row_idx, 4).value)
        assignee = _clean_string(sheet.cell(row_idx, 5).value)
        workflow_status = _clean_string(sheet.cell(row_idx, 6).value)

        if raw_file_type:
            split_types = [part.strip() for part in raw_file_type.split(COMPOSITE_DELIMITER) if part.strip()]
        else:
            split_types = []

        if not split_types:
            excluded_rows.append(
                ExcludedSourceRow(
                    source_row=row_idx,
                    raw_file_type=raw_file_type or "<blank>",
                    gcs_uri=gcs_uri or None,
                    reason="missing_file_type",
                )
            )
            continue

        for split_file_type in split_types:
            verification_status, _enabled = classify(split_file_type, file_type_status)
            if split_file_type in EXCLUDED_FILE_TYPES:
                excluded_rows.append(
                    ExcludedSourceRow(
                        source_row=row_idx,
                        raw_file_type=split_file_type,
                        gcs_uri=gcs_uri or None,
                        reason="excluded_file_type",
                    )
                )
                continue

            if not gcs_uri:
                skip_reason = "missing_gcs_uri"
                request_file_type = request_file_type_for(split_file_type)
                source_basename = f"source-row-{row_idx}"
            elif not gcs_uri.startswith("gs://"):
                skip_reason = "invalid_gcs_uri"
                request_file_type = request_file_type_for(split_file_type)
                source_basename = _base_name_from_uri(gcs_uri)
            else:
                skip_reason = unsupported_fixture_reason(gcs_uri)
                request_file_type = request_file_type_for(split_file_type)
                source_basename = _base_name_from_uri(gcs_uri)

            overrides = fixture_metadata_overrides_for(gcs_uri=gcs_uri, file_type=split_file_type)
            record_id += 1
            fixtures.append(
                SourceFixtureRecord(
                    record_id=record_id,
                    source_row=row_idx,
                    source_folder=folder,
                    source_file_type=raw_file_type or None,
                    file_type=split_file_type,
                    request_file_type=request_file_type,
                    gcs_uri=gcs_uri,
                    source_basename=source_basename,
                    file_type_status=file_type_status,
                    workflow_status=workflow_status,
                    assignee=assignee,
                    verification_status=verification_status,
                    include_in_batch=skip_reason is None,
                    skip_reason=skip_reason,
                    batch_expected_warning=overrides.get("batch_expected_warning"),
                    batch_expected_error_type=overrides.get("batch_expected_error_type"),
                    batch_expected_error=overrides.get("batch_expected_error"),
                )
            )

    return SourceWorkbookParseResult(
        source_workbook=workbook_path,
        sheet_name=SHEET_NAME,
        headers=headers,
        fixtures=tuple(fixtures),
        excluded_rows=tuple(excluded_rows),
    )


def grouped_fixtures_by_file_type(
    parsed: SourceWorkbookParseResult,
    *,
    selected_file_types: set[str] | None = None,
) -> dict[str, list[SourceFixtureRecord]]:
    grouped: dict[str, list[SourceFixtureRecord]] = {}
    for fixture in parsed.fixtures:
        if selected_file_types is not None and fixture.file_type not in selected_file_types:
            continue
        grouped.setdefault(fixture.file_type, []).append(fixture)
    return grouped

