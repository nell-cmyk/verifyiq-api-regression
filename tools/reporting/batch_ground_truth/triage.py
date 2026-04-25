from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
from typing import Any

from .models import ExportRow

TRIAGE_HEADERS = (
    "fileType",
    "source_row",
    "source_gcs_uri",
    "source_basename",
    "request_file_type",
    "response_fileType",
    "batch_http_status",
    "result_ok",
    "parse_success",
    "failure_tag",
    "error_type",
    "error",
    "extractionStatus",
    "documentQuality",
    "qualityCheck.issueDescription",
    "qualityScore",
    "summaryResult_count",
    "summaryOCR_count",
    "calculatedFields_count",
    "transactionsOCR_count",
    "batch_attempt_count",
    "batch_retry_reason",
    "gt_extraction_eligible",
    "gt_extraction_excluded",
    "gt_extraction_skip_reason",
    "gt_extraction_classification",
    "gt_clean_eligible",
    "negative_audit_useful",
    "gt_recovery_action",
    "recovery_class",
    "recovery_action",
    "gt_outcome_class",
    "gt_candidate_status",
)

MAIN_WORKBOOK_GT_STATUS_HEADERS = (
    "gt_outcome_class",
    "gt_candidate_status",
    "extractionStatus",
    "documentQuality",
    "quality_gate_reason",
    "request_file_type",
    "response_fileType",
    "source_row",
    "source_gcs_uri",
    "batch_result_correlation_id",
    "failure_tag",
    "error_type",
)

TRANSIENT_OR_AUTH_FAILURE_TAGS = {
    "persistent_token_expired",
    "request_timeout",
    "request_error",
}

MALFORMED_RESPONSE_TAGS = {
    "invalid_json_response",
    "missing_results_array",
    "missing_result",
}


def _raw_result(row: ExportRow) -> dict[str, Any] | None:
    raw = row.metadata.get("raw_result_json")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _data(row: ExportRow) -> dict[str, Any] | None:
    result = _raw_result(row)
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else None


def _dig(value: Any, *path: str) -> Any:
    current = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _sequence_count(data: dict[str, Any] | None, key: str) -> int | None:
    if not isinstance(data, dict) or key not in data:
        return None
    value = data.get(key)
    if not isinstance(value, list):
        return None
    return len(value)


def _has_usable_summary_result(data: dict[str, Any] | None) -> bool:
    summary_rows = data.get("summaryResult") if isinstance(data, dict) else None
    return bool(summary_rows) and isinstance(summary_rows, list) and isinstance(summary_rows[0], dict)


def _parsed_container_counts(data: dict[str, Any] | None) -> dict[str, int | None]:
    return {
        "summaryResult_count": _sequence_count(data, "summaryResult"),
        "summaryOCR_count": _sequence_count(data, "summaryOCR"),
        "calculatedFields_count": _sequence_count(data, "calculatedFields"),
        "transactionsOCR_count": _sequence_count(data, "transactionsOCR"),
    }


def _all_parsed_containers_present_and_empty(data: dict[str, Any] | None) -> bool:
    counts = _parsed_container_counts(data)
    return all(count == 0 for count in counts.values())


def _contains_any(value: Any, needles: tuple[str, ...]) -> bool:
    text = str(value or "").lower()
    return any(needle in text for needle in needles)


def _quality_check_has_failure(data: dict[str, Any] | None) -> bool:
    if not isinstance(data, dict):
        return False
    document_quality = data.get("documentQuality")
    issue_description = _dig(data, "qualityCheck", "issueDescription")
    if _contains_any(document_quality, ("failed", "too low")):
        return True
    if _contains_any(issue_description, ("failed", "too low")):
        return True

    findings = _dig(data, "qualityCheck", "qualityCheckFindings")
    if isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, dict) and str(finding.get("status") or "").lower() not in ("", "passed"):
                return True

    components = _dig(data, "qualityCheck", "qualityCheckComponents")
    if isinstance(components, list):
        for component in components:
            if isinstance(component, dict) and str(component.get("status") or "").lower() not in ("", "passed"):
                return True
    return False


def _result_ok(row: ExportRow) -> bool | None:
    result = _raw_result(row)
    if isinstance(result, dict) and "ok" in result:
        return bool(result.get("ok"))
    return None


def is_clean_candidate(row: ExportRow) -> bool:
    """Return True only for rows that mapped a usable parsed payload."""
    if row.metadata.get("ok") is not True:
        return False
    if row.metadata.get("failure_tag"):
        return False
    if row.metadata.get("error_type") or row.metadata.get("error"):
        return False
    if row.template_values.get("parse_success") is not True:
        return False
    return _has_usable_summary_result(_data(row))


def classify_export_row(row: ExportRow) -> dict[str, str]:
    if is_clean_candidate(row):
        return {
            "recovery_class": "clean_success",
            "recovery_action": "include_in_gt_workbook",
            "gt_outcome_class": "parsed_response",
            "gt_candidate_status": "gt_included_parsed",
        }

    failure_tag = str(row.metadata.get("failure_tag") or "")
    error_type = str(row.metadata.get("error_type") or "")
    error = str(row.metadata.get("error") or "")
    batch_http_status = row.metadata.get("batch_http_status")
    data = _data(row)
    gt_extraction_skip_reason = str(row.metadata.get("gt_extraction_skip_reason") or "")

    if failure_tag == "document_size_guard" or gt_extraction_skip_reason == "document_size_guard":
        return {
            "recovery_class": "document_size_guard",
            "recovery_action": "exclude_from_clean_gt_or_replace_fixture",
            "gt_outcome_class": "api_guard_rejection",
            "gt_candidate_status": "not_gt_candidate_currently",
        }

    if failure_tag == "multi_account_document" or gt_extraction_skip_reason == "multi_account_document":
        return {
            "recovery_class": "multi_account_document",
            "recovery_action": "split_or_replace_fixture_or_keep_as_negative_coverage",
            "gt_outcome_class": "api_guard_rejection",
            "gt_candidate_status": "fixture_review_required",
        }

    if (
        failure_tag == "http_200_no_payload_quality_gate"
        or gt_extraction_skip_reason == "quality_gate_no_payload"
    ):
        if row.metadata.get("gt_extraction_excluded") is True:
            return {
                "recovery_class": "http_200_no_payload_quality_gate",
                "recovery_action": "registry_metadata_excluded_from_live_gt_extraction",
                "gt_outcome_class": "registry_excluded",
                "gt_candidate_status": "gt_excluded_by_registry_metadata",
            }
        return {
            "recovery_class": "http_200_no_payload_quality_gate",
            "recovery_action": "include_as_negative_model_behavior_gt",
            "gt_outcome_class": "quality_gated_no_extraction",
            "gt_candidate_status": "gt_included_negative_model_behavior",
        }

    if error_type == "DocumentSizeGuardError" or "DocumentSizeGuardError" in error:
        return {
            "recovery_class": "document_size_guard",
            "recovery_action": "exclude_from_clean_gt_or_replace_fixture",
            "gt_outcome_class": "api_guard_rejection",
            "gt_candidate_status": "not_gt_candidate_currently",
        }

    if error_type == "MultiAccountDocumentError" or "MultiAccountDocumentError" in error:
        return {
            "recovery_class": "multi_account_document",
            "recovery_action": "split_or_replace_fixture_or_keep_as_negative_coverage",
            "gt_outcome_class": "api_guard_rejection",
            "gt_candidate_status": "fixture_review_required",
        }

    if failure_tag in {"unsupported_fixture", "missing_gcs_uri", "invalid_gcs_uri"}:
        return {
            "recovery_class": "unsupported_fixture",
            "recovery_action": "replace_fixture_or_correct_source_artifact",
            "gt_outcome_class": "unexecutable_fixture",
            "gt_candidate_status": "gt_excluded_unexecutable_fixture",
        }

    if failure_tag in TRANSIENT_OR_AUTH_FAILURE_TAGS:
        return {
            "recovery_class": "transient_or_auth_failure",
            "recovery_action": "targeted_rerun_after_retry_or_token_fix",
            "gt_outcome_class": "execution_failure",
            "gt_candidate_status": "gt_excluded_execution_failure",
        }

    if failure_tag == "http_429" or batch_http_status == 429:
        return {
            "recovery_class": "rate_limited",
            "recovery_action": "targeted_rerun_with_lower_concurrency_or_backoff",
            "gt_outcome_class": "execution_failure",
            "gt_candidate_status": "gt_excluded_execution_failure",
        }

    if failure_tag.startswith("http_"):
        try:
            status_code = int(failure_tag.rsplit("_", 1)[-1])
        except ValueError:
            status_code = 0
        if status_code in {401, 403} or status_code >= 500:
            return {
                "recovery_class": "transient_or_auth_failure",
                "recovery_action": "targeted_rerun_after_retry_or_token_fix",
                "gt_outcome_class": "execution_failure",
                "gt_candidate_status": "gt_excluded_execution_failure",
            }

    if (
        failure_tag == "unusable_result"
        and batch_http_status == 200
        and _result_ok(row) is True
        and isinstance(data, dict)
        and _all_parsed_containers_present_and_empty(data)
        and data.get("extractionStatus") == "not_attempted"
    ):
        if _quality_check_has_failure(data):
            return {
                "recovery_class": "http_200_no_payload_quality_gate",
                "recovery_action": "include_as_negative_model_behavior_gt",
                "gt_outcome_class": "quality_gated_no_extraction",
                "gt_candidate_status": "gt_included_negative_model_behavior",
            }
        return {
            "recovery_class": "http_200_no_payload_unknown",
            "recovery_action": "review_api_behavior_before_gt",
            "gt_outcome_class": "no_payload_unknown",
            "gt_candidate_status": "api_behavior_review_required",
        }

    if failure_tag == "invalid_json_response" and isinstance(batch_http_status, int) and batch_http_status >= 500:
        return {
            "recovery_class": "transient_or_auth_failure",
            "recovery_action": "targeted_rerun_after_retry_or_token_fix",
            "gt_outcome_class": "execution_failure",
            "gt_candidate_status": "gt_excluded_execution_failure",
        }

    if failure_tag in MALFORMED_RESPONSE_TAGS or failure_tag == "unusable_result":
        return {
            "recovery_class": "malformed_or_unexpected_response_shape",
            "recovery_action": "review_api_or_exporter_schema",
            "gt_outcome_class": "unreliable_response_shape",
            "gt_candidate_status": "api_behavior_review_required",
        }

    if failure_tag in {"skipped", "expected_warning_result", "result_error"}:
        return {
            "recovery_class": "malformed_or_unexpected_response_shape",
            "recovery_action": "manual_api_or_fixture_review",
            "gt_outcome_class": "api_or_fixture_review",
            "gt_candidate_status": "inconclusive",
        }

    return {
        "recovery_class": "malformed_or_unexpected_response_shape",
        "recovery_action": "manual_api_or_fixture_review",
        "gt_outcome_class": "api_or_fixture_review",
        "gt_candidate_status": "inconclusive",
    }


def build_main_workbook_status_values(row: ExportRow) -> dict[str, Any]:
    data = _data(row)
    classification = classify_export_row(row)
    return {
        "gt_outcome_class": classification["gt_outcome_class"],
        "gt_candidate_status": classification["gt_candidate_status"],
        "extractionStatus": data.get("extractionStatus") if isinstance(data, dict) else None,
        "documentQuality": data.get("documentQuality") if isinstance(data, dict) else None,
        "quality_gate_reason": _dig(data, "qualityCheck", "issueDescription"),
        "request_file_type": row.metadata.get("request_file_type"),
        "response_fileType": data.get("fileType") if isinstance(data, dict) else None,
        "source_row": row.metadata.get("source_row"),
        "source_gcs_uri": row.metadata.get("source_gcs_uri"),
        "batch_result_correlation_id": row.metadata.get("batch_result_correlation_id"),
        "failure_tag": row.metadata.get("failure_tag"),
        "error_type": row.metadata.get("error_type"),
    }


def build_recovery_triage_row(row: ExportRow) -> dict[str, Any]:
    data = _data(row)
    result = _raw_result(row)
    counts = _parsed_container_counts(data)
    classification = classify_export_row(row)
    return {
        "fileType": row.metadata.get("normalized_file_type"),
        "source_row": row.metadata.get("source_row"),
        "source_gcs_uri": row.metadata.get("source_gcs_uri"),
        "source_basename": row.template_values.get("filename"),
        "request_file_type": row.metadata.get("request_file_type"),
        "response_fileType": data.get("fileType") if isinstance(data, dict) else None,
        "batch_http_status": row.metadata.get("batch_http_status"),
        "result_ok": bool(result.get("ok")) if isinstance(result, dict) and "ok" in result else None,
        "parse_success": row.template_values.get("parse_success"),
        "failure_tag": row.metadata.get("failure_tag"),
        "error_type": row.metadata.get("error_type"),
        "error": row.metadata.get("error"),
        "extractionStatus": data.get("extractionStatus") if isinstance(data, dict) else None,
        "documentQuality": data.get("documentQuality") if isinstance(data, dict) else None,
        "qualityCheck.issueDescription": _dig(data, "qualityCheck", "issueDescription"),
        "qualityScore": (
            data.get("qualityScore")
            if isinstance(data, dict) and data.get("qualityScore") is not None
            else _dig(data, "qualityCheck", "qualityScore")
        ),
        "summaryResult_count": counts["summaryResult_count"],
        "summaryOCR_count": counts["summaryOCR_count"],
        "calculatedFields_count": counts["calculatedFields_count"],
        "transactionsOCR_count": counts["transactionsOCR_count"],
        "batch_attempt_count": row.metadata.get("batch_attempt_count"),
        "batch_retry_reason": row.metadata.get("batch_retry_reason"),
        "gt_extraction_eligible": row.metadata.get("gt_extraction_eligible"),
        "gt_extraction_excluded": row.metadata.get("gt_extraction_excluded"),
        "gt_extraction_skip_reason": row.metadata.get("gt_extraction_skip_reason"),
        "gt_extraction_classification": row.metadata.get("gt_extraction_classification"),
        "gt_clean_eligible": row.metadata.get("gt_clean_eligible"),
        "negative_audit_useful": row.metadata.get("negative_audit_useful"),
        "gt_recovery_action": row.metadata.get("gt_recovery_action"),
        **classification,
    }


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(row.get(key) or "<none>") for row in rows))


def write_recovery_triage_artifacts(
    *,
    rows: list[dict[str, Any]],
    json_path: Path,
    csv_path: Path,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(TRIAGE_HEADERS), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
