from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceFixtureRecord:
    record_id: int
    source_row: int
    source_folder: str | None
    source_file_type: str | None
    file_type: str
    request_file_type: str
    gcs_uri: str
    source_basename: str
    file_type_status: str
    workflow_status: str
    assignee: str
    verification_status: str
    include_in_batch: bool
    skip_reason: str | None = None
    batch_expected_warning: str | None = None
    batch_expected_error_type: str | None = None
    batch_expected_error: str | None = None

    def as_batch_fixture(self) -> dict[str, Any]:
        return {
            "name": self.source_basename,
            "file_type": self.file_type,
            "gcs_uri": self.gcs_uri,
            "source_row": self.source_row,
            "verification_status": self.verification_status,
            "batch_expected_warning": self.batch_expected_warning,
            "batch_expected_error_type": self.batch_expected_error_type,
            "batch_expected_error": self.batch_expected_error,
        }


@dataclass(frozen=True)
class ExcludedSourceRow:
    source_row: int
    raw_file_type: str
    gcs_uri: str | None
    reason: str


@dataclass(frozen=True)
class SourceRegistryParseResult:
    source_registry: Path | None
    source_workbook: Path | None
    schema_version: int
    fixtures: tuple[SourceFixtureRecord, ...]
    excluded_rows: tuple[ExcludedSourceRow, ...]


@dataclass(frozen=True)
class TemplateLayout:
    reference_workbook: Path
    reference_sheet_name: str
    headers: tuple[str, ...]
    freeze_panes: str | None
    header_font: Any
    header_fill: Any
    header_border: Any
    header_alignment: Any
    header_number_format: str
    header_protection: Any
    body_font: Any
    body_fill: Any
    body_border: Any
    body_alignment: Any
    body_number_format: str
    body_protection: Any
    width_by_header: dict[str, float | None]


@dataclass(frozen=True)
class FileTypePlan:
    file_type: str
    total_rows: int
    executable_rows: int
    skipped_rows: int
    chunk_count: int


@dataclass
class ExportRow:
    metadata: dict[str, Any]
    template_values: dict[str, Any] = field(default_factory=dict)
    extra_values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FileTypeExportResult:
    file_type: str
    workbook_path: Path
    total_rows: int
    executable_rows: int
    success_rows: int
    failed_rows: int
    skipped_rows: int
    chunk_count: int
    clean_workbook_path: Path | None = None
    clean_rows: int = 0
    triaged_rows: int = 0


@dataclass(frozen=True)
class BatchGroundTruthRunResult:
    output_dir: Path
    manifest_path: Path
    batch_artifact_run_dir: Path
    selected_file_types: tuple[str, ...]
    file_type_results: tuple[FileTypeExportResult, ...]
    clean_manifest_path: Path | None = None
    recovery_triage_json_path: Path | None = None
    recovery_triage_csv_path: Path | None = None
