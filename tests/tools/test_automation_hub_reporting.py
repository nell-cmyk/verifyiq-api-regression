from __future__ import annotations

from tools.automation_hub import reporting


def test_default_evidence_contract_requires_hub_reporting_sections() -> None:
    contract = reporting.default_evidence_contract()

    assert "run_metadata" in contract.required_sections
    assert "selected_nodes" in contract.required_sections
    assert "node_result_summaries" in contract.required_sections
    assert "request_metadata" in contract.required_sections
    assert "safe_response_metadata" in contract.required_sections
    assert "response_body_policy" in contract.required_sections
    assert "dependency_inputs" in contract.required_sections
    assert "dependency_outputs" in contract.required_sections
    assert "rerun_selectors" in contract.required_sections
    assert "tokens" in contract.redaction_exclusions
    assert "raw document identifiers" in contract.redaction_exclusions
    assert "fraud results" in contract.redaction_exclusions
    assert "not automatically persisted" in contract.raw_response_body_policy


def test_redaction_excludes_sensitive_evidence_fields() -> None:
    evidence = {
        "request": {
            "headers": {
                "Authorization": "placeholder",
                "Cookie": "placeholder",
                "X-Tenant-Token": "placeholder",
                "X-API-Key": "placeholder",
                "Accept": "application/json",
            },
            "document_id": "placeholder",
            "gcs_object_name": "placeholder",
            "body": {"any": "value"},
        },
        "response": {
            "status_code": 200,
            "fraudStatus": "complete",
            "fraudScore": "placeholder",
            "mathematicalFraudReport": {"any": "value"},
            "artifact_payload": "placeholder",
            "exportPayload": "placeholder",
            "raw_body": {"any": "value"},
        },
    }

    sanitized = reporting.redact_evidence_metadata(evidence)

    assert sanitized["request"]["headers"]["Authorization"] == reporting.REDACTED
    assert sanitized["request"]["headers"]["Cookie"] == reporting.REDACTED
    assert sanitized["request"]["headers"]["X-Tenant-Token"] == reporting.REDACTED
    assert sanitized["request"]["headers"]["X-API-Key"] == reporting.REDACTED
    assert sanitized["request"]["headers"]["Accept"] == "application/json"
    assert sanitized["request"]["document_id"] == reporting.EXCLUDED_BY_POLICY
    assert sanitized["request"]["gcs_object_name"] == reporting.EXCLUDED_BY_POLICY
    assert sanitized["request"]["body"] == reporting.EXCLUDED_BY_POLICY
    assert sanitized["response"]["status_code"] == 200
    assert sanitized["response"]["fraudStatus"] == "complete"
    assert sanitized["response"]["fraudScore"] == reporting.EXCLUDED_BY_POLICY
    assert sanitized["response"]["mathematicalFraudReport"] == reporting.EXCLUDED_BY_POLICY
    assert sanitized["response"]["artifact_payload"] == reporting.EXCLUDED_BY_POLICY
    assert sanitized["response"]["exportPayload"] == reporting.EXCLUDED_BY_POLICY
    assert sanitized["response"]["raw_body"] == reporting.EXCLUDED_BY_POLICY


def test_artifact_policies_make_raw_body_persistence_explicit() -> None:
    metadata_policy = reporting.metadata_only_policy()
    controlled_policy = reporting.policy_controlled_body_policy()

    assert metadata_policy.raw_body_persistence == reporting.RAW_BODY_POLICY_DISALLOWED
    assert not metadata_policy.raw_body_allowed
    assert controlled_policy.raw_body_persistence == reporting.RAW_BODY_POLICY_POLICY_CONTROLLED
    assert controlled_policy.raw_body_allowed
