from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
import json
import os
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from tests.client import clear_iap_token_cache, make_client
from tests.diagnostics import diagnose, request_error_diagnostics, timeout_diagnostics
from tests.endpoints.artifact_runs import readable_utc_timestamp
from tests.endpoints.batch.artifacts import (
    BATCH_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR,
    batch_response_artifact_dir,
)
from tests.endpoints.batch.fixtures import BATCH_SAFE_ITEM_LIMIT, build_batch_request

from .excel import clean_workbook_filename_for, workbook_filename_for, write_workbook
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
from .triage import (
    build_recovery_triage_row,
    count_by,
    is_clean_candidate,
    write_recovery_triage_artifacts,
)

BATCH_ENDPOINT = "/v1/documents/batch"
DEFAULT_OUTPUT_ROOT = Path("reports") / "batch_ground_truth"
BATCH_TIMEOUT_SECS = 300.0
DEFAULT_TOKEN_EXPIRY_RETRIES = 1
DEFAULT_TRANSIENT_CHUNK_RETRIES = 1
DEFAULT_RATE_LIMIT_RETRIES = 1
DEFAULT_RATE_LIMIT_BACKOFF_SECS = 2.0
_TOKEN_EXPIRY_EXACT_MARKERS = (
    "openid connect token expired",
    "jwt has expired",
)


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


def _skip_failure_tag(fixture: SourceFixtureRecord) -> str:
    gt_skip_reason = fixture.gt_extraction_skip_reason
    if gt_skip_reason == "document_size_guard":
        return "document_size_guard"
    if gt_skip_reason == "multi_account_document":
        return "multi_account_document"
    if gt_skip_reason == "unsupported_fixture":
        return "unsupported_fixture"
    if gt_skip_reason == "quality_gate_no_payload":
        return "http_200_no_payload_quality_gate"

    reason = fixture.skip_reason
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
    batch_attempt_count: int | None,
    batch_retry_reason: str | None,
    batch_final_attempt_error_type: str | None,
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
        "gt_extraction_eligible": fixture.gt_extraction_eligible,
        "gt_extraction_excluded": not fixture.gt_extraction_eligible,
        "gt_extraction_skip_reason": fixture.gt_extraction_skip_reason,
        "gt_extraction_classification": fixture.gt_extraction_classification,
        "gt_clean_eligible": fixture.gt_clean_eligible,
        "negative_audit_useful": fixture.negative_audit_useful,
        "gt_recovery_action": fixture.gt_recovery_action,
        "batch_chunk_number": batch_chunk_number,
        "batch_result_index": batch_result_index,
        "batch_http_status": batch_http_status,
        "batch_result_correlation_id": batch_result_correlation_id,
        "batch_elapsed_ms": batch_elapsed_ms,
        "batch_attempt_count": batch_attempt_count,
        "batch_retry_reason": batch_retry_reason,
        "batch_final_attempt_error_type": batch_final_attempt_error_type,
        "ok": ok,
        "failure_tag": failure_tag,
        "error_type": error_type,
        "error": error,
        "warning": warning,
        "raw_result_json": raw_result_json,
        "output_generated_at": output_generated_at,
    }


def _skipped_export_row(fixture: SourceFixtureRecord, *, output_generated_at: str) -> ExportRow:
    error = fixture.batch_expected_error or fixture.skip_reason
    return ExportRow(
        metadata=_metadata_for_fixture(
            fixture,
            output_generated_at=output_generated_at,
            batch_chunk_number=None,
            batch_result_index=None,
            batch_http_status=None,
            batch_result_correlation_id=None,
            batch_elapsed_ms=None,
            batch_attempt_count=None,
            batch_retry_reason=None,
            batch_final_attempt_error_type=None,
            ok=False,
            failure_tag=_skip_failure_tag(fixture),
            error_type=fixture.batch_expected_error_type,
            error=error,
            warning=fixture.batch_expected_warning,
            raw_result_json=None,
        ),
        template_values=build_failure_template_values(
            source_basename=fixture.source_basename,
            error=error,
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
    batch_http_status: int | None = None,
    batch_attempt_count: int | None = 1,
    batch_retry_reason: str | None = None,
    batch_final_attempt_error_type: str | None = None,
) -> dict[int, ExportRow]:
    rows: dict[int, ExportRow] = {}
    for fixture in fixtures:
        rows[fixture.record_id] = ExportRow(
            metadata=_metadata_for_fixture(
                fixture,
                output_generated_at=output_generated_at,
                batch_chunk_number=batch_chunk_number,
                batch_result_index=None,
                batch_http_status=batch_http_status,
                batch_result_correlation_id=None,
                batch_elapsed_ms=None,
                batch_attempt_count=batch_attempt_count,
                batch_retry_reason=batch_retry_reason,
                batch_final_attempt_error_type=batch_final_attempt_error_type,
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
    batch_attempt_count: int,
    batch_retry_reason: str | None,
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
                    batch_attempt_count=batch_attempt_count,
                    batch_retry_reason=batch_retry_reason,
                    batch_final_attempt_error_type=None,
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
                batch_attempt_count=batch_attempt_count,
                batch_retry_reason=batch_retry_reason,
                batch_final_attempt_error_type=None,
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
            batch_attempt_count=batch_attempt_count,
            batch_retry_reason=batch_retry_reason,
            batch_final_attempt_error_type=None,
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


def _retry_reason_text(retry_reasons: list[str]) -> str | None:
    if not retry_reasons:
        return None
    return ",".join(dict.fromkeys(retry_reasons))


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _rate_limit_retry_after_seconds(
    response: httpx.Response,
    *,
    retry_index: int,
    backoff_secs: float,
) -> float:
    retry_after = response.headers.get("Retry-After", "").strip()
    if retry_after:
        try:
            seconds = float(retry_after)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
            except (TypeError, ValueError):
                retry_at = None
            if retry_at is not None:
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                seconds = (retry_at - datetime.now(tz=timezone.utc)).total_seconds()
            else:
                seconds = None
        if seconds is not None:
            return max(0.0, seconds)

    return backoff_secs * (2 ** max(0, retry_index - 1))


def _retry_summary(rows: list[ExportRow]) -> dict[str, Any]:
    attempt_counts = [
        row.metadata.get("batch_attempt_count")
        for row in rows
        if isinstance(row.metadata.get("batch_attempt_count"), int)
    ]
    return {
        "rows_with_retries": sum(1 for count in attempt_counts if count > 1),
        "max_batch_attempt_count": max(attempt_counts, default=0),
        "batch_retry_reasons": dict(
            Counter(
                str(row.metadata["batch_retry_reason"])
                for row in rows
                if row.metadata.get("batch_retry_reason")
            )
        ),
        "batch_final_attempt_error_types": dict(
            Counter(
                str(row.metadata["batch_final_attempt_error_type"])
                for row in rows
                if row.metadata.get("batch_final_attempt_error_type")
            )
        ),
    }


def _response_text_for_detection(response: httpx.Response, body: Any | None = None) -> str:
    parts: list[str] = []
    if body not in (None, "", [], {}):
        if isinstance(body, str):
            parts.append(body)
        else:
            parts.append(_json_dumps(body) or str(body))
    try:
        if response.text:
            parts.append(response.text)
    except Exception:
        pass
    return "\n".join(parts)


def _is_token_expiry_response(response: httpx.Response, body: Any | None = None) -> bool:
    text = _response_text_for_detection(response, body=body).lower()
    if not text:
        return False
    if any(marker in text for marker in _TOKEN_EXPIRY_EXACT_MARKERS):
        return True
    return (
        response.status_code in (401, 403)
        and "expired" in text
        and any(marker in text for marker in ("token", "jwt", "oidc", "openid connect"))
    )


class _BatchClientHandle:
    def __init__(self) -> None:
        self.client: httpx.Client | None = None
        self._lock = threading.Lock()

    def __enter__(self) -> _BatchClientHandle:
        self.client = make_client(timeout=BATCH_TIMEOUT_SECS)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        self.close()
        return False

    def close(self) -> None:
        client = self.client
        if client is None:
            return
        close = getattr(client, "close", None)
        if callable(close):
            close()
        self.client = None

    def iap_token(self) -> str | None:
        client = self.client
        if client is None:
            return None
        headers = getattr(client, "headers", {})
        proxy_authorization = (
            headers.get("Proxy-Authorization") if hasattr(headers, "get") else None
        )
        if not isinstance(proxy_authorization, str):
            return None
        prefix = "Bearer "
        if not proxy_authorization.startswith(prefix):
            return None
        return proxy_authorization[len(prefix) :].strip() or None

    def refresh_iap_token(self) -> None:
        with self._lock:
            clear_iap_token_cache(expired_token=self.iap_token())
            self.close()
            self.client = make_client(timeout=BATCH_TIMEOUT_SECS)

    def post(self, url: str, *, json: dict[str, object], timeout: float) -> httpx.Response:
        if self.client is None:
            raise RuntimeError("Batch ground-truth HTTP client is not initialized.")
        return self.client.post(url, json=json, timeout=timeout)


def _execute_chunk(
    *,
    chunk_number: int,
    fixtures: list[SourceFixtureRecord],
    output_generated_at: str,
    client_handle: _BatchClientHandle | None = None,
    token_expiry_retries: int = DEFAULT_TOKEN_EXPIRY_RETRIES,
    transient_chunk_retries: int = DEFAULT_TRANSIENT_CHUNK_RETRIES,
    rate_limit_retries: int = DEFAULT_RATE_LIMIT_RETRIES,
    rate_limit_backoff_secs: float = DEFAULT_RATE_LIMIT_BACKOFF_SECS,
) -> dict[int, ExportRow]:
    if token_expiry_retries < 0:
        raise ValueError("token_expiry_retries must be a non-negative integer")
    if transient_chunk_retries < 0:
        raise ValueError("transient_chunk_retries must be a non-negative integer")
    if rate_limit_retries < 0:
        raise ValueError("rate_limit_retries must be a non-negative integer")
    if rate_limit_backoff_secs < 0:
        raise ValueError("rate_limit_backoff_secs must be non-negative")

    if client_handle is None:
        with _BatchClientHandle() as owned_client_handle:
            return _execute_chunk(
                chunk_number=chunk_number,
                fixtures=fixtures,
                output_generated_at=output_generated_at,
                client_handle=owned_client_handle,
                token_expiry_retries=token_expiry_retries,
                transient_chunk_retries=transient_chunk_retries,
                rate_limit_retries=rate_limit_retries,
                rate_limit_backoff_secs=rate_limit_backoff_secs,
            )

    row_map: dict[int, ExportRow] = {}
    payload = build_batch_request([fixture.as_batch_fixture() for fixture in fixtures])
    attempt_count = 0
    token_expiry_retry_count = 0
    transient_retry_count = 0
    rate_limit_retry_count = 0
    retry_reasons: list[str] = []

    while True:
        attempt_count += 1
        try:
            response = client_handle.post(BATCH_ENDPOINT, json=payload, timeout=BATCH_TIMEOUT_SECS)
        except httpx.ReadTimeout as exc:
            if transient_retry_count < transient_chunk_retries:
                transient_retry_count += 1
                retry_reasons.append("read_timeout")
                continue
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
                batch_attempt_count=attempt_count,
                batch_retry_reason=_retry_reason_text(retry_reasons),
                batch_final_attempt_error_type=type(exc).__name__,
            )
        except httpx.RemoteProtocolError as exc:
            if transient_retry_count < transient_chunk_retries:
                transient_retry_count += 1
                retry_reasons.append("remote_protocol_error")
                continue
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
                batch_attempt_count=attempt_count,
                batch_retry_reason=_retry_reason_text(retry_reasons),
                batch_final_attempt_error_type=type(exc).__name__,
            )
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
                batch_attempt_count=attempt_count,
                batch_retry_reason=_retry_reason_text(retry_reasons),
                batch_final_attempt_error_type=type(exc).__name__,
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
                batch_attempt_count=attempt_count,
                batch_retry_reason=_retry_reason_text(retry_reasons),
                batch_final_attempt_error_type=type(exc).__name__,
            )

        batch_http_status = response.status_code
        if batch_http_status == 429:
            if rate_limit_retry_count < rate_limit_retries:
                rate_limit_retry_count += 1
                retry_reasons.append("rate_limited")
                _sleep(
                    _rate_limit_retry_after_seconds(
                        response,
                        retry_index=rate_limit_retry_count,
                        backoff_secs=rate_limit_backoff_secs,
                    )
                )
                continue
            return _request_failure_rows(
                fixtures,
                output_generated_at=output_generated_at,
                batch_chunk_number=chunk_number,
                failure_tag="http_429",
                error_type=None,
                error=diagnose(response),
                batch_http_status=batch_http_status,
                batch_attempt_count=attempt_count,
                batch_retry_reason=_retry_reason_text(retry_reasons),
                batch_final_attempt_error_type="RateLimited",
            )

        try:
            body = response.json()
        except ValueError:
            error_text = diagnose(response)
            if _is_token_expiry_response(response):
                if token_expiry_retry_count < token_expiry_retries:
                    token_expiry_retry_count += 1
                    retry_reasons.append("token_expired")
                    client_handle.refresh_iap_token()
                    continue
                return _request_failure_rows(
                    fixtures,
                    output_generated_at=output_generated_at,
                    batch_chunk_number=chunk_number,
                    failure_tag="persistent_token_expired",
                    error_type="TokenExpired",
                    error=error_text,
                    batch_http_status=batch_http_status,
                    batch_attempt_count=attempt_count,
                    batch_retry_reason=_retry_reason_text(retry_reasons),
                    batch_final_attempt_error_type="TokenExpired",
                )
            return _request_failure_rows(
                fixtures,
                output_generated_at=output_generated_at,
                batch_chunk_number=chunk_number,
                failure_tag="invalid_json_response",
                error_type=None,
                error=error_text,
                batch_http_status=batch_http_status,
                batch_attempt_count=attempt_count,
                batch_retry_reason=_retry_reason_text(retry_reasons),
            )

        if _is_token_expiry_response(response, body=body):
            error_text = body if isinstance(body, str) else _json_dumps(body) or diagnose(response)
            if token_expiry_retry_count < token_expiry_retries:
                token_expiry_retry_count += 1
                retry_reasons.append("token_expired")
                client_handle.refresh_iap_token()
                continue
            return _request_failure_rows(
                fixtures,
                output_generated_at=output_generated_at,
                batch_chunk_number=chunk_number,
                failure_tag="persistent_token_expired",
                error_type="TokenExpired",
                error=str(error_text),
                batch_http_status=batch_http_status,
                batch_attempt_count=attempt_count,
                batch_retry_reason=_retry_reason_text(retry_reasons),
                batch_final_attempt_error_type="TokenExpired",
            )

        if batch_http_status != 200:
            error_text = body if isinstance(body, str) else _json_dumps(body) or diagnose(response)
            return _request_failure_rows(
                fixtures,
                output_generated_at=output_generated_at,
                batch_chunk_number=chunk_number,
                failure_tag=f"http_{batch_http_status}",
                error_type=None,
                error=str(error_text),
                batch_http_status=batch_http_status,
                batch_attempt_count=attempt_count,
                batch_retry_reason=_retry_reason_text(retry_reasons),
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
                batch_http_status=batch_http_status,
                batch_attempt_count=attempt_count,
                batch_retry_reason=_retry_reason_text(retry_reasons),
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
                        batch_attempt_count=attempt_count,
                        batch_retry_reason=_retry_reason_text(retry_reasons),
                        batch_final_attempt_error_type=None,
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
                batch_attempt_count=attempt_count,
                batch_retry_reason=_retry_reason_text(retry_reasons),
            )

        return row_map


def _execute_file_type(
    *,
    fixtures: list[SourceFixtureRecord],
    output_generated_at: str,
    max_concurrent_chunks: int = 1,
    token_expiry_retries: int = DEFAULT_TOKEN_EXPIRY_RETRIES,
    transient_chunk_retries: int = DEFAULT_TRANSIENT_CHUNK_RETRIES,
    rate_limit_retries: int = DEFAULT_RATE_LIMIT_RETRIES,
    rate_limit_backoff_secs: float = DEFAULT_RATE_LIMIT_BACKOFF_SECS,
) -> tuple[list[ExportRow], int]:
    if max_concurrent_chunks < 1:
        raise ValueError("max_concurrent_chunks must be a positive integer")
    if token_expiry_retries < 0:
        raise ValueError("token_expiry_retries must be a non-negative integer")
    if transient_chunk_retries < 0:
        raise ValueError("transient_chunk_retries must be a non-negative integer")
    if rate_limit_retries < 0:
        raise ValueError("rate_limit_retries must be a non-negative integer")
    if rate_limit_backoff_secs < 0:
        raise ValueError("rate_limit_backoff_secs must be non-negative")

    row_map: dict[int, ExportRow] = {}

    executable = [fixture for fixture in fixtures if fixture.include_in_batch]
    skipped = [fixture for fixture in fixtures if not fixture.include_in_batch]
    for fixture in skipped:
        row_map[fixture.record_id] = _skipped_export_row(fixture, output_generated_at=output_generated_at)

    chunk_specs = list(enumerate(_chunked(executable, BATCH_SAFE_ITEM_LIMIT), start=1))
    if max_concurrent_chunks == 1 or len(chunk_specs) <= 1:
        if chunk_specs:
            with _BatchClientHandle() as client_handle:
                for chunk_number, chunk in chunk_specs:
                    row_map.update(
                        _execute_chunk(
                            chunk_number=chunk_number,
                            fixtures=chunk,
                            output_generated_at=output_generated_at,
                            client_handle=client_handle,
                            token_expiry_retries=token_expiry_retries,
                            transient_chunk_retries=transient_chunk_retries,
                            rate_limit_retries=rate_limit_retries,
                            rate_limit_backoff_secs=rate_limit_backoff_secs,
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
                    token_expiry_retries=token_expiry_retries,
                    transient_chunk_retries=transient_chunk_retries,
                    rate_limit_retries=rate_limit_retries,
                    rate_limit_backoff_secs=rate_limit_backoff_secs,
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
    token_expiry_retries: int,
    transient_chunk_retries: int,
    rate_limit_retries: int = DEFAULT_RATE_LIMIT_RETRIES,
    rate_limit_backoff_secs: float = DEFAULT_RATE_LIMIT_BACKOFF_SECS,
) -> _FileTypeExecution:
    try:
        export_rows, chunk_count = _execute_file_type(
            fixtures=fixtures,
            output_generated_at=output_generated_at,
            max_concurrent_chunks=max_concurrent_chunks,
            token_expiry_retries=token_expiry_retries,
            transient_chunk_retries=transient_chunk_retries,
            rate_limit_retries=rate_limit_retries,
            rate_limit_backoff_secs=rate_limit_backoff_secs,
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
    token_expiry_retries: int,
    transient_chunk_retries: int,
    rate_limit_retries: int = DEFAULT_RATE_LIMIT_RETRIES,
    rate_limit_backoff_secs: float = DEFAULT_RATE_LIMIT_BACKOFF_SECS,
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
                token_expiry_retries=token_expiry_retries,
                transient_chunk_retries=transient_chunk_retries,
                rate_limit_retries=rate_limit_retries,
                rate_limit_backoff_secs=rate_limit_backoff_secs,
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
                token_expiry_retries=token_expiry_retries,
                transient_chunk_retries=transient_chunk_retries,
                rate_limit_retries=rate_limit_retries,
                rate_limit_backoff_secs=rate_limit_backoff_secs,
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
    token_expiry_retries: int = DEFAULT_TOKEN_EXPIRY_RETRIES,
    transient_chunk_retries: int = DEFAULT_TRANSIENT_CHUNK_RETRIES,
    rate_limit_retries: int = DEFAULT_RATE_LIMIT_RETRIES,
    rate_limit_backoff_secs: float = DEFAULT_RATE_LIMIT_BACKOFF_SECS,
) -> BatchGroundTruthRunResult:
    if max_concurrent_chunks < 1:
        raise ValueError("max_concurrent_chunks must be a positive integer")
    if max_concurrent_file_types < 1:
        raise ValueError("max_concurrent_file_types must be a positive integer")
    if token_expiry_retries < 0:
        raise ValueError("token_expiry_retries must be a non-negative integer")
    if transient_chunk_retries < 0:
        raise ValueError("transient_chunk_retries must be a non-negative integer")
    if rate_limit_retries < 0:
        raise ValueError("rate_limit_retries must be a non-negative integer")
    if rate_limit_backoff_secs < 0:
        raise ValueError("rate_limit_backoff_secs must be non-negative")

    parsed, grouped, plans = plan_file_types(
        fixture_registry=fixture_registry,
        selected_file_types=selected_file_types,
    )
    output_root = _ensure_output_dir(output_dir)
    workbooks_dir = output_root / "workbooks"
    clean_workbooks_dir = output_root / "clean_workbooks"
    batch_artifact_run_dir = _artifact_run_dir()
    output_generated_at = _utc_iso_now()
    execution_results = _execute_file_type_plans(
        plans=plans,
        grouped=grouped,
        output_generated_at=output_generated_at,
        max_concurrent_chunks=max_concurrent_chunks,
        max_concurrent_file_types=max_concurrent_file_types,
        token_expiry_retries=token_expiry_retries,
        transient_chunk_retries=transient_chunk_retries,
        rate_limit_retries=rate_limit_retries,
        rate_limit_backoff_secs=rate_limit_backoff_secs,
    )

    results: list[FileTypeExportResult] = []
    manifest_file_types: dict[str, Any] = {}
    clean_manifest_file_types: dict[str, Any] = {}
    all_triage_rows: list[dict[str, Any]] = []

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

        clean_rows = [row for row in export_rows if is_clean_candidate(row)]
        triage_rows = [
            build_recovery_triage_row(row)
            for row in export_rows
            if not is_clean_candidate(row)
        ]
        clean_workbook_path = clean_workbooks_dir / clean_workbook_filename_for(plan.file_type)
        clean_headers = write_workbook(
            file_type=plan.file_type,
            rows=clean_rows,
            layout=template_layout,
            output_path=clean_workbook_path,
        )
        all_triage_rows.extend(triage_rows)

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
            clean_workbook_path=clean_workbook_path,
            clean_rows=len(clean_rows),
            triaged_rows=len(triage_rows),
        )
        results.append(result)
        manifest_file_types[plan.file_type] = {
            "workbook_path": str(workbook_path),
            "clean_workbook_path": str(clean_workbook_path),
            "headers": headers,
            "clean_headers": clean_headers,
            "total_rows": len(fixtures),
            "executable_rows": executable_rows,
            "success_rows": success_rows,
            "failed_rows": failed_rows,
            "skipped_rows": skipped_rows,
            "clean_rows": len(clean_rows),
            "triaged_rows": len(triage_rows),
            "chunk_count": execution.chunk_count,
            "retry_summary": _retry_summary(export_rows),
        }
        clean_manifest_file_types[plan.file_type] = {
            "source_rows": len(fixtures),
            "audit_workbook_path": str(workbook_path),
            "clean_workbook_path": str(clean_workbook_path),
            "clean_rows": len(clean_rows),
            "triaged_rows": len(triage_rows),
        }

    manifest_path = output_root / "manifest.json"
    recovery_triage_json_path = output_root / "recovery_triage.json"
    recovery_triage_csv_path = output_root / "recovery_triage.csv"
    clean_manifest_path = output_root / "clean_manifest.json"
    total_source_rows = sum(len(execution.fixtures) for execution in execution_results)
    clean_rows_by_file_type = {
        file_type: payload["clean_rows"]
        for file_type, payload in clean_manifest_file_types.items()
    }
    triaged_rows_by_file_type = {
        file_type: payload["triaged_rows"]
        for file_type, payload in clean_manifest_file_types.items()
    }
    gt_extraction_excluded_by_file_type = {
        execution.plan.file_type: sum(
            1 for fixture in execution.fixtures if not fixture.gt_extraction_eligible
        )
        for execution in execution_results
    }
    clean_manifest_payload = {
        "generated_at": output_generated_at,
        "fixture_registry": str(Path(fixture_registry).expanduser().resolve()),
        "source_workbook": str(parsed.source_workbook) if parsed.source_workbook is not None else None,
        "reference_workbook": str(Path(reference_workbook).expanduser().resolve()),
        "output_dir": str(output_root),
        "audit_workbooks_dir": str(workbooks_dir),
        "clean_workbooks_dir": str(clean_workbooks_dir),
        "recovery_triage_json": str(recovery_triage_json_path),
        "recovery_triage_csv": str(recovery_triage_csv_path),
        "total_source_rows": total_source_rows,
        "clean_included_rows": sum(clean_rows_by_file_type.values()),
        "triaged_rejected_rows": len(all_triage_rows),
        "clean_rows_by_fileType": clean_rows_by_file_type,
        "triaged_rows_by_fileType": triaged_rows_by_file_type,
        "gt_extraction_excluded_rows": sum(gt_extraction_excluded_by_file_type.values()),
        "gt_extraction_excluded_rows_by_fileType": gt_extraction_excluded_by_file_type,
        "triaged_rows_by_recovery_class": count_by(all_triage_rows, "recovery_class"),
        "triaged_rows_by_gt_candidate_status": count_by(all_triage_rows, "gt_candidate_status"),
        "file_types": clean_manifest_file_types,
    }
    write_recovery_triage_artifacts(
        rows=all_triage_rows,
        json_path=recovery_triage_json_path,
        csv_path=recovery_triage_csv_path,
    )
    clean_manifest_path.write_text(json.dumps(clean_manifest_payload, indent=2) + "\n", encoding="utf-8")

    manifest_payload = {
        "generated_at": output_generated_at,
        "fixture_registry": str(Path(fixture_registry).expanduser().resolve()),
        "source_workbook": str(parsed.source_workbook) if parsed.source_workbook is not None else None,
        "reference_workbook": str(Path(reference_workbook).expanduser().resolve()),
        "output_dir": str(output_root),
        "clean_manifest": str(clean_manifest_path),
        "recovery_triage_json": str(recovery_triage_json_path),
        "recovery_triage_csv": str(recovery_triage_csv_path),
        "batch_artifact_run_dir": str(batch_artifact_run_dir),
        "safe_batch_item_limit": BATCH_SAFE_ITEM_LIMIT,
        "max_concurrent_chunks": max_concurrent_chunks,
        "max_concurrent_file_types": max_concurrent_file_types,
        "effective_max_concurrent_batch_requests": (
            max_concurrent_file_types * max_concurrent_chunks
        ),
        "token_expiry_retries": token_expiry_retries,
        "transient_chunk_retries": transient_chunk_retries,
        "rate_limit_retries": rate_limit_retries,
        "rate_limit_backoff_secs": rate_limit_backoff_secs,
        "selected_file_types": [plan.file_type for plan in plans],
        "skipped_rows": [
            {
                "source_row": fixture.source_row,
                "source_file_type": fixture.source_file_type,
                "normalized_file_type": fixture.file_type,
                "gcs_uri": fixture.gcs_uri,
                "skip_reason": fixture.skip_reason,
                "gt_extraction_eligible": fixture.gt_extraction_eligible,
                "gt_extraction_skip_reason": fixture.gt_extraction_skip_reason,
                "gt_extraction_classification": fixture.gt_extraction_classification,
                "gt_recovery_action": fixture.gt_recovery_action,
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
        clean_manifest_path=clean_manifest_path,
        recovery_triage_json_path=recovery_triage_json_path,
        recovery_triage_csv_path=recovery_triage_csv_path,
    )
