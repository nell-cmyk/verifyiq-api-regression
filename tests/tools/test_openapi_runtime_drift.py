from __future__ import annotations

import copy
import json

import tools.reporting.openapi_runtime_drift as drift


def _load_report() -> dict:
    openapi = drift.load_openapi()
    return drift.build_report(openapi)


def test_current_report_uses_runtime_baseline_principle() -> None:
    report = _load_report()

    assert "runtime baseline" in report["principle"]
    assert "not owner-approved public contract" in report["principle"]

    compared = {
        f"{endpoint['method']} {endpoint['path']}"
        for endpoint in report["observed_baselines"]
    }
    assert compared == {
        "POST /v1/documents/parse",
        "POST /v1/documents/batch",
        "GET /v1/documents/fraud-status/{job_id}",
    }


def test_batch_envelope_has_no_observed_drift_and_keeps_data_loose() -> None:
    report = _load_report()
    findings = report["findings"]

    batch_findings = [
        finding
        for finding in findings
        if finding["endpoint"] == "POST /v1/documents/batch"
    ]
    assert batch_findings == []

    batch_baseline = next(
        endpoint
        for endpoint in report["observed_baselines"]
        if endpoint["path"] == "/v1/documents/batch"
    )
    assert "$.results[].data" in batch_baseline["loose_paths"]


def test_compared_baselines_have_no_current_observed_drift_findings() -> None:
    report = _load_report()

    assert report["findings"] == []


def test_fraud_status_has_no_observed_drift_without_contract_promotion() -> None:
    report = _load_report()
    fraud_baseline = next(
        endpoint
        for endpoint in report["observed_baselines"]
        if endpoint["path"] == "/v1/documents/fraud-status/{job_id}"
    )

    assert "observed_runtime_only" in fraud_baseline["public_contract_status"]
    assert "not owner-confirmed public contract" in fraud_baseline["public_contract_status"]
    assert "$.mathematicalFraudReport" in fraud_baseline["loose_paths"]
    assert "$.metadataFraudReport" in fraud_baseline["loose_paths"]
    assert "$.error" in fraud_baseline["loose_paths"]

    assert [
        finding
        for finding in report["findings"]
        if finding["endpoint"] == "GET /v1/documents/fraud-status/{job_id}"
    ] == []


def test_batch_openapi_schema_documents_conservative_envelope() -> None:
    openapi = drift.load_openapi()
    responses = openapi["paths"]["/v1/documents/batch"]["post"]["responses"]

    assert responses["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/BatchResponse"
    }
    assert responses["400"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/BatchBadRequestResponse"
    }
    assert responses["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HTTPValidationError"
    }
    assert responses["429"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/BatchTimeoutRiskResponse"
    }

    batch_response = openapi["components"]["schemas"]["BatchResponse"]
    assert batch_response["type"] == "object"
    assert batch_response["additionalProperties"] is True
    assert batch_response.get("required", []) == []
    assert set(batch_response["properties"]) == {
        "summary",
        "results",
        "crosscheckResults",
    }

    assert batch_response["properties"]["summary"]["type"] == "object"
    assert batch_response["properties"]["summary"]["additionalProperties"] is True
    assert batch_response["properties"]["results"]["type"] == "array"
    assert batch_response["properties"]["results"]["items"] == {
        "$ref": "#/components/schemas/BatchResult"
    }
    assert batch_response["properties"]["crosscheckResults"]["type"] == "array"

    batch_result = openapi["components"]["schemas"]["BatchResult"]
    assert batch_result["type"] == "object"
    assert batch_result["additionalProperties"] is True
    assert batch_result.get("required", []) == []
    assert set(batch_result["properties"]) == {"index", "ok", "data"}
    assert batch_result["properties"]["index"]["type"] == "integer"
    assert batch_result["properties"]["ok"]["type"] == "boolean"
    assert batch_result["properties"]["data"]["anyOf"] == [
        {"additionalProperties": True, "type": "object"},
        {"type": "null"},
    ]

    bad_request = openapi["components"]["schemas"]["BatchBadRequestResponse"]
    assert bad_request["properties"]["detail"]["type"] == "string"
    assert "enum" not in bad_request["properties"]["detail"]

    timeout_risk = openapi["components"]["schemas"]["BatchTimeoutRiskResponse"]
    assert timeout_risk["properties"]["code"]["type"] == "string"
    assert timeout_risk["properties"]["retryable"]["type"] == "boolean"
    assert timeout_risk["properties"]["details"]["type"] == "object"
    assert timeout_risk["properties"]["details"]["additionalProperties"] is True


def test_fraud_status_openapi_schema_documents_only_conservative_top_level_shape() -> None:
    openapi = drift.load_openapi()
    responses = openapi["paths"]["/v1/documents/fraud-status/{job_id}"]["get"]["responses"]

    success_schema = responses["200"]["content"]["application/json"]["schema"]
    assert success_schema["type"] == "object"
    assert success_schema["additionalProperties"] is True
    assert success_schema.get("required", []) == []
    assert set(success_schema["properties"]) == {"fraudJobId", "fraudStatus"}
    assert success_schema["properties"]["fraudJobId"]["type"] == "string"
    assert success_schema["properties"]["fraudStatus"]["type"] == "string"
    assert "mathematicalFraudReport" not in success_schema["properties"]
    assert "metadataFraudReport" not in success_schema["properties"]
    assert "fraudScore" not in success_schema["properties"]
    assert "authenticityScore" not in success_schema["properties"]
    assert "completedAt" not in success_schema["properties"]
    assert "error" not in success_schema["properties"]

    not_found = responses["404"]["content"]["application/json"]["schema"]
    assert not_found["type"] == "object"
    assert not_found["additionalProperties"] is True
    assert not_found.get("required", []) == []
    assert not_found["properties"]["detail"]["type"] == "string"
    assert "enum" not in not_found["properties"]["detail"]

    assert responses["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HTTPValidationError"
    }


def test_endpoint_classification_covers_deferred_and_excluded_groups() -> None:
    report = _load_report()
    classification = report["endpoint_classification"]

    assert "safe_to_compare_now" in classification
    assert "compare_using_existing_artifacts_only" in classification
    assert "needs_fresh_sanitized_artifact" in classification
    assert "blocked_pending_owner_setup_auth_data" in classification
    assert "excluded" in classification
    assert any("/v1/documents/fraud-status" in item for item in classification["safe_to_compare_now"])
    assert any(
        "complete/failed deep result schemas" in item
        for item in classification["needs_fresh_sanitized_artifact"]
    )
    assert any("/v1/documents/check-cache" in item for item in classification["blocked_pending_owner_setup_auth_data"])
    assert any("Destructive/admin mutation routes" in item for item in classification["excluded"])


def test_comparator_detects_newly_missing_observed_parse_field() -> None:
    openapi = drift.load_openapi()
    modified = copy.deepcopy(openapi)
    parse_response = modified["components"]["schemas"]["ParseResponse"]
    parse_response["properties"].pop("summaryResult")
    parse_response["required"].remove("summaryResult")

    findings = drift.compare_openapi_to_observed(modified)

    assert any(
        finding.endpoint == "POST /v1/documents/parse"
        and finding.kind == "observed_field_undocumented"
            and finding.observed.startswith("$.summaryResult")
        for finding in findings
    )


def test_comparator_detects_newly_missing_observed_batch_envelope_field() -> None:
    openapi = drift.load_openapi()
    modified = copy.deepcopy(openapi)
    batch_response = modified["components"]["schemas"]["BatchResponse"]
    batch_response["properties"].pop("crosscheckResults")

    findings = drift.compare_openapi_to_observed(modified)

    assert any(
        finding.endpoint == "POST /v1/documents/batch"
        and finding.kind == "observed_field_undocumented"
        and finding.observed.startswith("$.crosscheckResults")
        for finding in findings
    )


def test_comparator_detects_newly_missing_observed_fraud_status_field() -> None:
    openapi = drift.load_openapi()
    modified = copy.deepcopy(openapi)
    success_schema = (
        modified["paths"]["/v1/documents/fraud-status/{job_id}"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]
    )
    success_schema["properties"].pop("fraudStatus")

    findings = drift.compare_openapi_to_observed(modified)

    assert any(
        finding.endpoint == "GET /v1/documents/fraud-status/{job_id}"
        and finding.kind == "observed_field_undocumented"
        and finding.observed.startswith("$.fraudStatus")
        for finding in findings
    )


def test_comparator_detects_newly_missing_observed_fraud_status_404() -> None:
    openapi = drift.load_openapi()
    modified = copy.deepcopy(openapi)
    modified["paths"]["/v1/documents/fraud-status/{job_id}"]["get"]["responses"].pop("404")

    findings = drift.compare_openapi_to_observed(modified)

    assert any(
        finding.endpoint == "GET /v1/documents/fraud-status/{job_id}"
        and finding.kind == "observed_status_undocumented"
        and finding.status_code == 404
        for finding in findings
    )


def test_cli_json_output(capsys) -> None:
    exit_code = drift.main(["--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["openapi_path"] == "official-openapi.json"
    assert report["findings"] == []
