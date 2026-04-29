from __future__ import annotations

import json

from tools.automation_hub import manifest, report_writer
from tools.automation_hub.reporting import EXCLUDED_BY_POLICY, REDACTED


def _read_payload(run_dir):
    return json.loads((run_dir / "run.json").read_text(encoding="utf-8"))


def test_synthetic_report_writer_emits_full_extended_dry_run_report(tmp_path) -> None:
    paths = report_writer.write_synthetic_report(output_root=tmp_path, run_id="unit-full")

    assert paths.run_dir == tmp_path / "unit-full"
    assert paths.json_path == paths.run_dir / "run.json"
    assert paths.markdown_path == paths.run_dir / "run.md"
    assert paths.latest_path.read_text(encoding="utf-8") == "unit-full\n"
    payload = _read_payload(paths.run_dir)
    assert payload["run_metadata"]["selected_suite"] == "extended"
    assert payload["run_metadata"]["endpoints_executed"] is False
    assert payload["run_metadata"]["endpoint_call_count"] == 0
    assert payload["selector"] == {"type": "full", "value": None}
    assert payload["selected_nodes"] == [
        node.node_id for node in manifest.DEFAULT_HUB_MANIFEST.ordered_nodes()
    ]
    assert payload["node_result_summaries"] == []
    assert payload["request_metadata"] == []
    assert payload["safe_response_metadata"] == []
    assert payload["response_body_policy"]["raw_response_bodies_present"] is False
    assert payload["response_body_policy"]["raw_response_body_persistence"] == "absent"


def test_synthetic_report_markdown_states_no_endpoints_were_executed(tmp_path) -> None:
    paths = report_writer.write_synthetic_report(
        output_root=tmp_path,
        hub_node="get-smoke.safe-read-only",
        run_id="unit-markdown",
    )

    markdown = paths.markdown_path.read_text(encoding="utf-8")
    assert "No endpoints were executed" in markdown
    assert "No request bodies, response bodies, document identifiers, GCS object names" in markdown
    assert "`node_result_summaries`, `request_metadata`, and `safe_response_metadata` are intentionally empty" in markdown


def test_synthetic_report_writer_filters_hub_node(tmp_path) -> None:
    paths = report_writer.write_synthetic_report(
        output_root=tmp_path,
        hub_node="get-smoke.safe-read-only",
        run_id="unit-node",
    )

    payload = _read_payload(paths.run_dir)
    assert payload["selector"] == {"type": "hub-node", "value": "get-smoke.safe-read-only"}
    assert payload["selected_nodes"] == ["get-smoke.safe-read-only"]
    assert payload["dependency_order"] == ["get-smoke.safe-read-only"]
    assert payload["prerequisite_closure"] == []


def test_synthetic_report_writer_includes_prerequisite_closure(tmp_path) -> None:
    paths = report_writer.write_synthetic_report(
        output_root=tmp_path,
        hub_node="document-processing.fraud-status.consumer",
        run_id="unit-closure",
    )

    payload = _read_payload(paths.run_dir)
    assert payload["selected_nodes"] == ["document-processing.fraud-status.consumer"]
    assert payload["dependency_order"] == [
        "document-processing.fraud-status.producer",
        "document-processing.fraud-status.consumer",
    ]
    assert payload["prerequisite_closure"] == ["document-processing.fraud-status.producer"]
    assert payload["node_plans"][0]["inclusion"] == "prerequisite for selected node"
    assert payload["node_plans"][1]["inclusion"] == "selected node"
    assert payload["dependency_inputs"]["document-processing.fraud-status.consumer"] == [
        {
            "name": "fraud_status.job_reference",
            "source_node_id": "document-processing.fraud-status.producer",
            "required": True,
        }
    ]


def test_synthetic_report_writer_filters_hub_group(tmp_path) -> None:
    paths = report_writer.write_synthetic_report(
        output_root=tmp_path,
        hub_group="get-smoke",
        run_id="unit-group",
    )

    payload = _read_payload(paths.run_dir)
    assert payload["selector"] == {"type": "hub-group", "value": "get-smoke"}
    assert payload["selected_nodes"] == ["get-smoke.health.core", "get-smoke.safe-read-only"]
    assert payload["dependency_order"] == ["get-smoke.health.core", "get-smoke.safe-read-only"]
    assert payload["node_plans"][0]["inclusion"] == "selected endpoint-group node"


def test_live_report_writer_emits_metadata_only_health_result(tmp_path) -> None:
    paths = report_writer.write_live_report(
        output_root=tmp_path,
        run_id="unit-live",
        endpoint_result={
            "node_id": "get-smoke.health.core",
            "endpoint_label": "GET /health",
            "method": "GET",
            "path": "/health",
            "status_code": 200,
            "expected_status_code": 200,
            "duration_ms": 12.5,
            "outcome": "passed",
            "safe_response_headers": {
                "content-type": "application/json",
                "set-cookie": "secret-cookie",
                "x-request-id": "raw-id",
            },
            "started_at": "2026-04-29T00:00:00Z",
            "completed_at": "2026-04-29T00:00:01Z",
            "response_body": {"raw": "do not persist"},
        },
    )

    payload = _read_payload(paths.run_dir)
    assert payload["run_metadata"]["report_kind"] == "automation_hub_live"
    assert payload["run_metadata"]["dry_run"] is False
    assert payload["run_metadata"]["endpoints_executed"] is True
    assert payload["selector"] == {"type": "hub-node", "value": "get-smoke.health.core"}
    assert payload["selected_nodes"] == ["get-smoke.health.core"]
    assert payload["node_result_summaries"] == [
        {
            "node_id": "get-smoke.health.core",
            "endpoint_label": "GET /health",
            "method": "GET",
            "path": "/health",
            "status_code": 200,
            "expected_status_code": 200,
            "duration_ms": 12.5,
            "outcome": "passed",
            "rerun_selector": "./.venv/bin/python tools/run_regression.py --suite extended --hub-node get-smoke.health.core",
        }
    ]
    assert payload["safe_response_metadata"][0]["headers"] == {"content-type": "application/json"}
    assert payload["response_body_policy"]["raw_response_bodies_present"] is False
    raw_json = paths.json_path.read_text(encoding="utf-8")
    assert "do not persist" not in raw_json
    assert "secret-cookie" not in raw_json
    assert "raw-id" not in raw_json


def test_synthetic_report_writer_redacts_or_excludes_sensitive_metadata(tmp_path) -> None:
    paths = report_writer.write_synthetic_report(
        output_root=tmp_path,
        hub_node="get-smoke.safe-read-only",
        run_id="unit-redaction",
        extra_metadata={
            "headers": {
                "Authorization": "placeholder auth material",
                "Cookie": "placeholder cookie material",
                "X-Tenant-Token": "placeholder tenant material",
                "X-API-Key": "placeholder api material",
                "Accept": "application/json",
            },
            "document_id": "placeholder document identifier",
            "gcs_object_name": "placeholder object name",
            "response_body": {"placeholder": "sensitive body"},
            "fraudResults": {"placeholder": "fraud detail"},
            "artifact_payload": "placeholder artifact material",
            "exportPayload": "placeholder export material",
        },
    )

    payload = _read_payload(paths.run_dir)
    sanitized = payload["sanitized_metadata"]
    assert sanitized["headers"]["Authorization"] == REDACTED
    assert sanitized["headers"]["Cookie"] == REDACTED
    assert sanitized["headers"]["X-Tenant-Token"] == REDACTED
    assert sanitized["headers"]["X-API-Key"] == REDACTED
    assert sanitized["headers"]["Accept"] == "application/json"
    assert sanitized["document_id"] == EXCLUDED_BY_POLICY
    assert sanitized["gcs_object_name"] == EXCLUDED_BY_POLICY
    assert sanitized["response_body"] == EXCLUDED_BY_POLICY
    assert sanitized["fraudResults"] == EXCLUDED_BY_POLICY
    assert sanitized["artifact_payload"] == EXCLUDED_BY_POLICY
    assert sanitized["exportPayload"] == EXCLUDED_BY_POLICY

    raw_json = paths.json_path.read_text(encoding="utf-8")
    assert "placeholder auth material" not in raw_json
    assert "placeholder document identifier" not in raw_json
    assert "placeholder object name" not in raw_json
    assert "placeholder artifact material" not in raw_json
    assert "placeholder export material" not in raw_json


def test_live_report_writer_redacts_or_excludes_sensitive_metadata(tmp_path) -> None:
    paths = report_writer.write_live_report(
        output_root=tmp_path,
        run_id="unit-live-redaction",
        endpoint_result={
            "node_id": "get-smoke.health.core",
            "endpoint_label": "GET /health",
            "method": "GET",
            "path": "/health",
            "status_code": 200,
            "expected_status_code": 200,
            "duration_ms": 3.0,
            "outcome": "passed",
            "safe_response_headers": {"content-type": "application/json"},
            "started_at": "2026-04-29T00:00:00Z",
            "completed_at": "2026-04-29T00:00:01Z",
        },
        extra_metadata={
            "headers": {
                "Authorization": "placeholder auth material",
                "Cookie": "placeholder cookie material",
                "X-Tenant-Token": "placeholder tenant material",
                "X-API-Key": "placeholder api material",
                "Accept": "application/json",
            },
            "document_id": "placeholder document identifier",
            "gcs_uri": "gs://bucket/raw-object",
            "response_body": {"placeholder": "sensitive body"},
            "fraudStatus": "placeholder fraud status",
            "fraudScore": "placeholder fraud detail",
            "artifact_payload": "placeholder artifact material",
            "exportPayload": "placeholder export material",
        },
    )

    payload = _read_payload(paths.run_dir)
    sanitized = payload["sanitized_metadata"]
    assert sanitized["headers"]["Authorization"] == REDACTED
    assert sanitized["headers"]["Cookie"] == REDACTED
    assert sanitized["headers"]["X-Tenant-Token"] == REDACTED
    assert sanitized["headers"]["X-API-Key"] == REDACTED
    assert sanitized["headers"]["Accept"] == "application/json"
    assert sanitized["document_id"] == EXCLUDED_BY_POLICY
    assert sanitized["gcs_uri"] == EXCLUDED_BY_POLICY
    assert sanitized["response_body"] == EXCLUDED_BY_POLICY
    assert sanitized["fraudStatus"] == EXCLUDED_BY_POLICY
    assert sanitized["fraudScore"] == EXCLUDED_BY_POLICY
    assert sanitized["artifact_payload"] == EXCLUDED_BY_POLICY
    assert sanitized["exportPayload"] == EXCLUDED_BY_POLICY

    raw_json = paths.json_path.read_text(encoding="utf-8")
    assert "placeholder auth material" not in raw_json
    assert "placeholder document identifier" not in raw_json
    assert "gs://bucket/raw-object" not in raw_json
    assert "placeholder fraud status" not in raw_json
    assert "placeholder fraud detail" not in raw_json
    assert "placeholder artifact material" not in raw_json
