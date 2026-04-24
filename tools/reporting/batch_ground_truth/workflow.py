from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from tests.client import make_client
from tests.diagnostics import diagnose, request_error_diagnostics, timeout_diagnostics
from tests.endpoints.artifact_runs import readable_utc_timestamp
from tests.endpoints.batch.artifacts import (
    BATCH_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR,
    batch_response_artifact_dir,
)
from tests.endpoints.batch.fixtures import BATCH_SAFE_ITEM_LIMIT, build_batch_request

from .excel import workbook_filename_for, write_workbook
from .models import (
    BatchGroundTruthRunResult,
    ExportRow,
    FileTypeExportResult,
    FileTypePlan,
    SourceFixtureRecord,
    SourceRegistryParseResult,
    TemplateLayout,
)
from .schema import build_failure_template_values, build_success_template_values
from .source import grouped_fixtures_by_file_type, parse_source_registry

BATCH_ENDPOINT = "/v1/documents/batch"
DEFAULT_OUTPUT_ROOT = Path("reports") / "batch_ground_truth"
BATCH_TIMEOUT_SECS = 300.0


@dataclass(frozen=True)
class _FileTypeExecution:
    plan: FileTypePlan
    fixtures: list[SourceFixtureRecord]
    export_rows: list[ExportRow]
    chunk_count: int


def _utc_iso_now() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


def _json_dumps(value: Any) -> str | None:
    if value in (None, "", [], {}):
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def _artifact_run_dir() -> Path:
    env_value = os.getenv(BATCH_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR, "").strip()
    if not env_value:
        env_value = f"batch_{readable_utc_timestamp()}"
        os.environ[BATCH_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR] = env_value
    run_dir = batch_response_artifact_dir() / env_value
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _ensure_output_dir(output_dir: str | Path | None) -> Path:
    if output_dir is not None:
        resolved = Path(output_dir).expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved
    run_label = f"batch_ground_truth_{readable_utc_timestamp()}"
    resolved = (DEFAULT_OUTPUT_ROOT / run_label).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _skip_failure_tag(reason: str | None) -> str:
    if not reason:
        return "skipped"
    if reason == "missing_gcs_uri":
        return "missing_gcs_uri"
    if reason == "invalid_gcs_uri":
        return "invalid_gcs_uri"
    if reason.startswith("unsupported file extension"):
        return "unsupported_fixture"
    return "skipped"


def _chunked(records: list[SourceFixtureRecord], chunk_size: int) -> list[list[SourceFixtureRecord]]:
    return [
        records[index : index + chunk_size]
        for index in range(0, len(records), chunk_size)
    ]


def _metadata_for_fixture(
    fixture: SourceFixtureRecord,
    *,
    output_generated_at: str,
    batch_chunk_number: int | None,
    batch_result_index: int | None,
    batch_http_status: int | None,
    batch_result_correlation_id: str | None,
    batch_elapsed_ms: float | int | None,
    ok: bool,
    failure_tag: str | None,
    error_type: str | None,
    error: str | None,
    warning: str | None,
    raw_result_json: str | None,
) -> dict[str, Any]:
    return {
        "source_row": fixture.source_row,
        "source_gcs_uri": fixture.gcs_uri,
        "source_file_type": fixture.source_file_type,
        "normalized_file_type": fixture.file_type,
        "request_file_type": fixture.request_file_type,
        "source_folder": fixture.source_folder,
        "source_assignee": fixture.assignee,
        "source_workflow_status": fixture.workflow_status,
        "fixture_status_from_source": fixture.file_type_status,
        "batch_chunk_number": batch_chunk_number,
        "batch_result_index": batch_result_index,
        "batch_http_status": batch_http_status,
        "batch_result_correlation_id": batch_result_correlation_id,
        "batch_elapsed_ms": batch_elapsed_ms,
        "ok": ok,
        "failure_tag": failure_tag,
        "error_type": error_type,
        "error": error,
        "warning": warning,
        "raw_result_json": raw_result_json,
        "output_generated_at": output_generated_at,
    }


def _skipped_export_row(fixture: SourceFixtureRecord, *, output_generated_at: str) -> ExportRow:
    return ExportRow(
        metadata=_metadata_for_fixture(
            fixture,
            output_generated_at=output_generated_at,
            batch_chunk_number=None,
            batch_result_index=None,
            batch_http_status=None,
            batch_result_correlation_id=None,
            batch_elapsed_ms=None,
            ok=False,
            failure_tag=_skip_failure_tag(fixture.skip_reason),
            error_type=None,
            error=fixture.skip_reason,
            warning=fixture.batch_expected_warning,
            raw_result_json=None,
        ),
        template_values=build_failure_template_values(
            source_basename=fixture.source_basename,
            error=fixture.skip_reason,
        ),
    )


def _request_failure_rows(
    fixtures: Iterable[SourceFixtureRecord],
    *,
    output_generated_at: str,
    batch_chunk_number: int,
    failure_tag: str,
    error_type: str | None,
    error: str,
) -> dict[int, ExportRow]:
    rows: dict[int, ExportRow] = {}
    for fixture in fixtures:
        rows[fixture.record_id] = ExportRow(
            metadata=_metadata_for_fixture(
                fixture,
                output_generated_at=output_generated_at,
                batch_chunk_number=batch_chunk_number,
                batch_result_index=None,
                batch_http_status=None,
                batch_result_correlation_id=None,
                batch_elapsed_ms=None,
                ok=False,
                failure_tag=failure_tag,
                error_type=error_type,
                error=error,
                warning=fixture.batch_expected_warning,
                raw_result_json=None,
            ),
            template_values=build_failure_template_values(
                source_basename=fixture.source_basename,
                error=error,
            ),
        )
    return rows


def _result_export_row(
    fixture: SourceFixtureRecord,
    *,
    result: dict[str, Any],
    batch_chunk_number: int,
    batch_http_status: int,
    output_generated_at: str,
) -> ExportRow:
    ok = bool(result.get("ok"))
    warning_value = result.get("warning")
    warning = str(warning_value) if warning_value not in (None, "") else fixture.batch_expected_warning
    raw_result_json = _json_dumps(result)
    correlation_id = result.get("correlation_id")
    elapsed_ms = result.get("elapsed_ms")

    if ok:
        try:
            template_values, extra_values = build_success_template_values(
                source_basename=fixture.source_basename,
                request_file_type=fixture.request_file_type,
                result=result,
            )
        except ValueError as exc:
            return ExportRow(
                metadata=_metadata_for_fixture(
                    fixture,
                    output_generated_at=output_generated_at,
                    batch_chunk_number=batch_chunk_number,
                    batch_result_index=result.get("index"),
                    batch_http_status=batch_http_status,
                    batch_result_correlation_id=correlation_id,
                    batch_elapsed_ms=elapsed_ms,
                    ok=False,
                    failure_tag="unusable_result",
                    error_type=type(exc).__name__,
                    error=str(exc),
                    warning=warning,
                    raw_result_json=raw_result_json,
                ),
                template_values=build_failure_template_values(
                    source_basename=fixture.source_basename,
                    error=str(exc),
                ),
            )

        return ExportRow(
            metadata=_metadata_for_fixture(
                fixture,
                output_generated_at=output_generated_at,
                batch_chunk_number=batch_chunk_number,
                batch_result_index=result.get("index"),
                batch_http_status=batch_http_status,
                batch_result_correlation_id=correlation_id,
                batch_elapsed_ms=elapsed_ms,
                ok=True,
                failure_tag=None,
                error_type=None,
                error=None,
                warning=warning,
                raw_result_json=raw_result_json,
            ),
            template_values=template_values,
            extra_values=extra_values,
        )

    error_type = result.get("error_type")
    failure_tag = "result_error"
    if fixture.batch_expected_error_type and error_type == fixture.batch_expected_error_type:
        failure_tag = "expected_warning_result"

    return ExportRow(
        metadata=_metadata_for_fixture(
            fixture,
            output_generated_at=output_generated_at,
            batch_chunk_number=batch_chunk_number,
            batch_result_index=result.get("index"),
            batch_http_status=batch_http_status,
            batch_result_correlation_id=correlation_id,
            batch_elapsed_ms=elapsed_ms,
            ok=False,
            failure_tag=failure_tag,
            error_type=str(error_type) if error_type not in (None, "") else None,
            error=str(result.get("error")) if result.get("error") not in (None, "") else None,
            warning=warning,
            raw_result_json=raw_result_json,
        ),
        template_values=build_failure_template_values(
            source_basename=fixture.source_basename,
            error=str(result.get("error")) if result.get("error") not in (None, "") else None,
        ),
    )


def _execute_chunk(
    *,
    chunk_number: int,
    fixtures: list[SourceFixtureRecord],
    output_generated_at: str,
    client: httpx.Client | None = None,
) -> dict[int, ExportRow]:
    if client is None:
        with make_client(timeout=BATCH_TIMEOUT_SECS) as owned_client:
            return _execute_chunk(
                chunk_number=chunk_number,
                fixtures=fixtures,
                output_generated_at=output_generated_at,
                client=owned_client,
            )

    row_map: dict[int, ExportRow] = {}
    payload = build_batch_request([fixture.as_batch_fixture() for fixture in fixtures])
    try:
        response = client.post(BATCH_ENDPOINT, json=payload, timeout=BATCH_TIMEOUT_SECS)
    except httpx.TimeoutException as exc:
        return _request_failure_rows(
            fixtures,
            output_generated_at=output_generated_at,
            batch_chunk_number=chunk_number,
            failure_tag="request_timeout",
            error_type=type(exc).__name__,
            error=timeout_diagnostics(
                exc,
                context=f"Batch ground-truth chunk {chunk_number}",
                timeout_secs=BATCH_TIMEOUT_SECS,
            ),
        )
    except httpx.RequestError as exc:
        return _request_failure_rows(
            fixtures,
            output_generated_at=output_generated_at,
            batch_chunk_number=chunk_number,
            failure_tag="request_error",
            error_type=type(exc).__name__,
            error=request_error_diagnostics(
                exc,
                context=f"Batch ground-truth chunk {chunk_number}",
            ),
        )

    batch_http_status = response.status_code
    try:
        body = response.json()
    except ValueError:
        error_text = diagnose(response)
        return _request_failure_rows(
            fixtures,
            output_generated_at=output_generated_at,
            batch_chunk_number=chunk_number,
            failure_tag="invalid_json_response",
            error_type=None,
            error=error_text,
        )

    if batch_http_status != 200:
        error_text = body if isinstance(body, str) else _json_dumps(body) or diagnose(response)
        return _request_failure_rows(
            fixtures,
            output_generated_at=output_generated_at,
            batch_chunk_number=chunk_number,
            failure_tag=f"http_{batch_http_status}",
            error_type=None,
            error=error_text,
        )

    results = body.get("results")
    if not isinstance(results, list):
        return _request_failure_rows(
            fixtures,
            output_generated_at=output_generated_at,
            batch_chunk_number=chunk_number,
            failure_tag="missing_results_array",
            error_type=None,
            error="batch response did not include a list `results` field",
        )

    for index, fixture in enumerate(fixtures):
        if index >= len(results):
            row_map[fixture.record_id] = ExportRow(
                metadata=_metadata_for_fixture(
                    fixture,
                    output_generated_at=output_generated_at,
                    batch_chunk_number=chunk_number,
                    batch_result_index=index,
                    batch_http_status=batch_http_status,
                    batch_result_correlation_id=None,
                    batch_elapsed_ms=None,
                    ok=False,
                    failure_tag="missing_result",
                    error_type=None,
                    error="batch response returned fewer results than requested items",
                    warning=fixture.batch_expected_warning,
                    raw_result_json=None,
                ),
                template_values=build_failure_template_values(
                    source_basename=fixture.source_basename,
                    error="batch response returned fewer results than requested items",
                ),
            )
            continue

        row_map[fixture.record_id] = _result_export_row(
            fixture,
            result=results[index],
            batch_chunk_number=chunk_number,
            batch_http_status=batch_http_status,
            output_generated_at=output_generated_at,
        )

    return row_map


def _execute_file_type(
    *,
    fixtures: list[SourceFixtureRecord],
    output_generated_at: str,
    max_concurrent_chunks: int = 1,
) -> tuple[list[ExportRow], int]:
    if max_concurrent_chunks < 1:
        raise ValueError("max_concurrent_chunks must be a positive integer")

    row_map: dict[int, ExportRow] = {}

    executable = [fixture for fixture in fixtures if fixture.include_in_batch]
    skipped = [fixture for fixture in fixtures if not fixture.include_in_batch]
    for fixture in skipped:
        row_map[fixture.record_id] = _skipped_export_row(fixture, output_generated_at=output_generated_at)

    chunk_specs = list(enumerate(_chunked(executable, BATCH_SAFE_ITEM_LIMIT), start=1))
    if max_concurrent_chunks == 1 or len(chunk_specs) <= 1:
        if chunk_specs:
            with make_client(timeout=BATCH_TIMEOUT_SECS) as client:
                for chunk_number, chunk in chunk_specs:
                    row_map.update(
                        _execute_chunk(
                            chunk_number=chunk_number,
                            fixtures=chunk,
                            output_generated_at=output_generated_at,
                            client=client,
                        )
                    )
    else:
        max_workers = min(max_concurrent_chunks, len(chunk_specs))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    _execute_chunk,
                    chunk_number=chunk_number,
                    fixtures=chunk,
                    output_generated_at=output_generated_at,
                )
                for chunk_number, chunk in chunk_specs
            ]
            for future in as_completed(futures):
                row_map.update(future.result())

    ordered_rows = [row_map[fixture.record_id] for fixture in fixtures]
    return ordered_rows, len(chunk_specs)


def _execute_file_type_plan(
    *,
    plan: FileTypePlan,
    fixtures: list[SourceFixtureRecord],
    output_generated_at: str,
    max_concurrent_chunks: int,
) -> _FileTypeExecution:
    try:
        export_rows, chunk_count = _execute_file_type(
            fixtures=fixtures,
            output_generated_at=output_generated_at,
            max_concurrent_chunks=max_concurrent_chunks,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Batch ground-truth export failed for fileType {plan.file_type}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    return _FileTypeExecution(
        plan=plan,
        fixtures=fixtures,
        export_rows=export_rows,
        chunk_count=chunk_count,
    )


def _execute_file_type_plans(
    *,
    plans: list[FileTypePlan],
    grouped: dict[str, list[SourceFixtureRecord]],
    output_generated_at: str,
    max_concurrent_chunks: int,
    max_concurrent_file_types: int,
) -> list[_FileTypeExecution]:
    if max_concurrent_file_types < 1:
        raise ValueError("max_concurrent_file_types must be a positive integer")

    if max_concurrent_file_types == 1 or len(plans) <= 1:
        return [
            _execute_file_type_plan(
                plan=plan,
                fixtures=grouped[plan.file_type],
                output_generated_at=output_generated_at,
                max_concurrent_chunks=max_concurrent_chunks,
            )
            for plan in plans
        ]

    max_workers = min(max_concurrent_file_types, len(plans))
    ordered_results: list[_FileTypeExecution | None] = [None] * len(plans)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(
                _execute_file_type_plan,
                plan=plan,
                fixtures=grouped[plan.file_type],
                output_generated_at=output_generated_at,
                max_concurrent_chunks=max_concurrent_chunks,
            ): index
            for index, plan in enumerate(plans)
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            ordered_results[index] = future.result()

    return [result for result in ordered_results if result is not None]


def plan_file_types(
    *,
    fixture_registry: Path | str,
    selected_file_types: set[str] | None = None,
) -> tuple[SourceRegistryParseResult, dict[str, list[SourceFixtureRecord]], list[FileTypePlan]]:
    parsed = parse_source_registry(fixture_registry)
    grouped = grouped_fixtures_by_file_type(parsed, selected_file_types=selected_file_types)
    plans = []
    for file_type, fixtures in sorted(grouped.items()):
        executable_rows = sum(1 for fixture in fixtures if fixture.include_in_batch)
        skipped_rows = len(fixtures) - executable_rows
        plans.append(
            FileTypePlan(
                file_type=file_type,
                total_rows=len(fixtures),
                executable_rows=executable_rows,
                skipped_rows=skipped_rows,
                chunk_count=len(_chunked([fixture for fixture in fixtures if fixture.include_in_batch], BATCH_SAFE_ITEM_LIMIT)),
            )
        )
    return parsed, grouped, plans


def run_batch_ground_truth_export(
    *,
    fixture_registry: Path | str,
    reference_workbook: Path | str,
    output_dir: Path | str | None,
    selected_file_types: set[str] | None,
    template_layout: TemplateLayout,
    max_concurrent_chunks: int = 1,
    max_concurrent_file_types: int = 1,
) -> BatchGroundTruthRunResult:
    if max_concurrent_chunks < 1:
        raise ValueError("max_concurrent_chunks must be a positive integer")
    if max_concurrent_file_types < 1:
        raise ValueError("max_concurrent_file_types must be a positive integer")

    parsed, grouped, plans = plan_file_types(
        fixture_registry=fixture_registry,
        selected_file_types=selected_file_types,
    )
    output_root = _ensure_output_dir(output_dir)
    workbooks_dir = output_root / "workbooks"
    batch_artifact_run_dir = _artifact_run_dir()
    output_generated_at = _utc_iso_now()
    execution_results = _execute_file_type_plans(
        plans=plans,
        grouped=grouped,
        output_generated_at=output_generated_at,
        max_concurrent_chunks=max_concurrent_chunks,
        max_concurrent_file_types=max_concurrent_file_types,
    )

    results: list[FileTypeExportResult] = []
    manifest_file_types: dict[str, Any] = {}

    for execution in execution_results:
        plan = execution.plan
        fixtures = execution.fixtures
        export_rows = execution.export_rows
        workbook_path = workbooks_dir / workbook_filename_for(plan.file_type)
        headers = write_workbook(
            file_type=plan.file_type,
            rows=export_rows,
            layout=template_layout,
            output_path=workbook_path,
        )

        success_rows = sum(1 for row in export_rows if row.metadata["ok"] is True)
        failed_rows = sum(1 for row in export_rows if row.metadata["ok"] is False)
        skipped_rows = sum(1 for fixture in fixtures if not fixture.include_in_batch)
        executable_rows = len(fixtures) - skipped_rows
        result = FileTypeExportResult(
            file_type=plan.file_type,
            workbook_path=workbook_path,
            total_rows=len(fixtures),
            executable_rows=executable_rows,
            success_rows=success_rows,
            failed_rows=failed_rows,
            skipped_rows=skipped_rows,
            chunk_count=execution.chunk_count,
        )
        results.append(result)
        manifest_file_types[plan.file_type] = {
            "workbook_path": str(workbook_path),
            "headers": headers,
            "total_rows": len(fixtures),
            "executable_rows": executable_rows,
            "success_rows": success_rows,
            "failed_rows": failed_rows,
            "skipped_rows": skipped_rows,
            "chunk_count": execution.chunk_count,
        }

    manifest_path = output_root / "manifest.json"
    manifest_payload = {
        "generated_at": output_generated_at,
        "fixture_registry": str(Path(fixture_registry).expanduser().resolve()),
        "source_workbook": str(parsed.source_workbook) if parsed.source_workbook is not None else None,
        "reference_workbook": str(Path(reference_workbook).expanduser().resolve()),
        "output_dir": str(output_root),
        "batch_artifact_run_dir": str(batch_artifact_run_dir),
        "safe_batch_item_limit": BATCH_SAFE_ITEM_LIMIT,
        "max_concurrent_chunks": max_concurrent_chunks,
        "max_concurrent_file_types": max_concurrent_file_types,
        "effective_max_concurrent_batch_requests": (
            max_concurrent_file_types * max_concurrent_chunks
        ),
        "selected_file_types": [plan.file_type for plan in plans],
        "skipped_rows": [
            {
                "source_row": fixture.source_row,
                "source_file_type": fixture.source_file_type,
                "normalized_file_type": fixture.file_type,
                "gcs_uri": fixture.gcs_uri,
                "skip_reason": fixture.skip_reason,
            }
            for fixture in parsed.fixtures
            if not fixture.include_in_batch
        ],
        "excluded_rows": [
            {
                "source_row": row.source_row,
                "raw_file_type": row.raw_file_type,
                "gcs_uri": row.gcs_uri,
                "reason": row.reason,
            }
            for row in parsed.excluded_rows
        ],
        "file_types": manifest_file_types,
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")

    return BatchGroundTruthRunResult(
        output_dir=output_root,
        manifest_path=manifest_path,
        batch_artifact_run_dir=batch_artifact_run_dir,
        selected_file_types=tuple(plan.file_type for plan in plans),
        file_type_results=tuple(results),
    )
