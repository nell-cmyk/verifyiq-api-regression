#!/usr/bin/env python3
"""Compare checked-in OpenAPI schemas with curated observed runtime baselines.

This report treats current observed endpoint response shape as the practical
runtime baseline for drift comparison. It does not promote observed behavior to
owner-approved public API contract.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "official-openapi.json"


@dataclass(frozen=True)
class ObservedField:
    path: str
    json_types: tuple[str, ...]
    evidence: tuple[str, ...]
    contract_status: str = "observed_runtime_only"
    loose: bool = False


@dataclass(frozen=True)
class ObservedResponse:
    status_code: int
    evidence: tuple[str, ...]
    fields: tuple[ObservedField, ...] = ()


@dataclass(frozen=True)
class ObservedEndpoint:
    method: str
    path: str
    comparison_scope: str
    evidence: tuple[str, ...]
    responses: tuple[ObservedResponse, ...]
    loose_paths: tuple[str, ...] = ()
    public_contract_status: str = "not_owner_confirmed"


@dataclass(frozen=True)
class DriftFinding:
    endpoint: str
    status_code: int
    kind: str
    observed: str
    openapi: str
    evidence: tuple[str, ...]
    contract_status: str


OBSERVED_BASELINES: tuple[ObservedEndpoint, ...] = (
    ObservedEndpoint(
        method="POST",
        path="/v1/documents/parse",
        comparison_scope=(
            "Protected /parse success and validation response envelope. Nested "
            "document-type fields remain loose."
        ),
        evidence=(
            "docs/knowledge-base/parse/openapi-drift-pilot.md",
            "tests/endpoints/parse/test_parse.py",
            "tests/tools/test_official_openapi_parse_contract.py",
        ),
        responses=(
            ObservedResponse(
                status_code=200,
                evidence=(
                    "docs/knowledge-base/parse/openapi-drift-pilot.md",
                    "tests/endpoints/document_contracts.py",
                ),
                fields=(
                    ObservedField("$.fileType", ("string",), ("tests/endpoints/document_contracts.py",)),
                    ObservedField(
                        "$.documentQuality",
                        ("string",),
                        ("tests/endpoints/document_contracts.py",),
                    ),
                    ObservedField("$.summaryOCR", ("array",), ("tests/endpoints/document_contracts.py",)),
                    ObservedField(
                        "$.summaryResult",
                        ("array",),
                        ("tests/endpoints/document_contracts.py",),
                    ),
                    ObservedField(
                        "$.calculatedFields",
                        ("array",),
                        ("tests/endpoints/document_contracts.py",),
                    ),
                ),
            ),
            ObservedResponse(
                status_code=422,
                evidence=(
                    "docs/knowledge-base/parse/openapi-drift-pilot.md",
                    "tests/endpoints/parse/test_parse.py",
                ),
                fields=(
                    ObservedField(
                        "$.detail",
                        ("array",),
                        ("tests/endpoints/document_contracts.py",),
                    ),
                ),
            ),
        ),
        loose_paths=("$.summaryOCR[]", "$.summaryResult[]", "$.calculatedFields[]"),
        public_contract_status=(
            "observed_runtime_plus_conservative_spec_alignment; unresolved owner "
            "questions remain for non-core fields"
        ),
    ),
    ObservedEndpoint(
        method="POST",
        path="/v1/documents/batch",
        comparison_scope=(
            "Envelope-only /documents/batch comparison from current tests and safe "
            "ground-truth summaries. results[].data is fileType-specific and loose."
        ),
        evidence=(
            "tests/endpoints/batch/test_batch.py",
            "docs/knowledge-base/batch/ground-truth-unusable-result-triage.md",
            "docs/operations/batch-ground-truth-export.md",
        ),
        responses=(
            ObservedResponse(
                status_code=200,
                evidence=("tests/endpoints/batch/test_batch.py",),
                fields=(
                    ObservedField("$.summary", ("object",), ("tests/endpoints/batch/test_batch.py",)),
                    ObservedField("$.results", ("array",), ("tests/endpoints/batch/test_batch.py",)),
                    ObservedField(
                        "$.crosscheckResults",
                        ("array",),
                        ("tests/endpoints/batch/test_batch.py",),
                    ),
                    ObservedField(
                        "$.results[].index",
                        ("integer",),
                        ("tests/endpoints/batch/test_batch.py",),
                    ),
                    ObservedField(
                        "$.results[].ok",
                        ("boolean",),
                        ("tests/endpoints/batch/test_batch.py",),
                    ),
                    ObservedField(
                        "$.results[].data",
                        ("object", "null"),
                        ("tests/endpoints/batch/test_batch.py",),
                        loose=True,
                    ),
                ),
            ),
            ObservedResponse(
                status_code=400,
                evidence=("tests/endpoints/batch/test_batch.py::TestBatchValidation::test_empty_items_returns_400",),
                fields=(ObservedField("$.detail", ("string",), ("tests/endpoints/batch/test_batch.py",)),),
            ),
            ObservedResponse(
                status_code=422,
                evidence=(
                    "tests/endpoints/batch/test_batch.py::TestBatchValidation::test_missing_items_returns_422",
                    "tests/endpoints/batch/test_batch.py::TestBatchValidation::test_missing_file_type_in_item_returns_422",
                    "tests/endpoints/batch/test_batch.py::TestBatchValidation::test_missing_file_in_item_returns_422",
                ),
                fields=(
                    ObservedField(
                        "$.detail",
                        ("array",),
                        ("tests/endpoints/document_contracts.py",),
                    ),
                ),
            ),
            ObservedResponse(
                status_code=429,
                evidence=(
                    "tests/endpoints/batch/test_batch.py::TestBatchValidation::test_more_than_safe_item_limit_returns_429",
                ),
                fields=(
                    ObservedField("$.code", ("string",), ("tests/endpoints/batch/test_batch.py",)),
                    ObservedField("$.retryable", ("boolean",), ("tests/endpoints/batch/test_batch.py",)),
                    ObservedField("$.details", ("object",), ("tests/endpoints/batch/test_batch.py",)),
                ),
            ),
        ),
        loose_paths=("$.results[].data",),
    ),
    ObservedEndpoint(
        method="GET",
        path="/v1/documents/fraud-status/{job_id}",
        comparison_scope=(
            "Provisional fraud-status GET smoke top-level shape only. Terminal "
            "result fields and fraud report contents remain loose."
        ),
        evidence=(
            "tests/endpoints/get_smoke/test_fraud_status.py",
            "docs/knowledge-base/document-processing-adjacent/fraud-status-expansion-plan.md",
            "docs/operations/endpoint-coverage-inventory.md",
        ),
        responses=(
            ObservedResponse(
                status_code=200,
                evidence=(
                    "tests/endpoints/get_smoke/test_fraud_status.py::assert_fraud_status_shape",
                    "docs/knowledge-base/document-processing-adjacent/fraud-status-expansion-plan.md",
                ),
                fields=(
                    ObservedField(
                        "$.fraudJobId",
                        ("string",),
                        ("tests/endpoints/get_smoke/test_fraud_status.py",),
                    ),
                    ObservedField(
                        "$.fraudStatus",
                        ("string",),
                        ("tests/endpoints/get_smoke/test_fraud_status.py",),
                    ),
                ),
            ),
            ObservedResponse(
                status_code=404,
                evidence=(
                    "tests/endpoints/get_smoke/test_fraud_status.py::"
                    "test_fraud_status_rejects_invalid_and_nonexistent_job_ids",
                    "docs/knowledge-base/document-processing-adjacent/fraud-status-expansion-plan.md",
                ),
            ),
        ),
        loose_paths=(
            "$.fraudScore",
            "$.authenticityScore",
            "$.mathematicalFraudReport",
            "$.metadataFraudReport",
            "$.completedAt",
            "$.error",
        ),
        public_contract_status=(
            "observed_runtime_only; maintainer-accepted provisional smoke "
            "coverage, not owner-confirmed public contract"
        ),
    ),
)


ENDPOINT_CLASSIFICATION: dict[str, list[str]] = {
    "safe_to_compare_now": [
        "POST /v1/documents/parse: protected response envelope from current tests and completed /parse drift pilot",
        "POST /v1/documents/batch: envelope-only response shape from current batch tests; results[].data remains loose",
        "GET /v1/documents/fraud-status/{job_id}: provisional opt-in smoke top-level shape and 404 status only; terminal result fields remain loose",
    ],
    "compare_using_existing_artifacts_only": [
        "POST /v1/documents/parse: use sanitized pilot notes and current static guard; do not require a fresh live run",
        "POST /v1/documents/batch: use tests, manifests, clean summaries, and triage summaries; avoid raw batch JSON and workbook cell payloads",
        "GET /v1/documents/fraud-status/{job_id}: use current artifact-free smoke assertions and sanitized planning notes; do not persist raw fraud responses or job IDs",
    ],
    "needs_fresh_sanitized_artifact": [
        "GET /v1/documents/fraud-status/{job_id}: complete/failed deep result schemas need fresh sanitized shape summaries or owner confirmation before spec tightening",
        "GET smoke groups beyond exact status checks: need per-endpoint sanitized shape summaries before response-schema comparison",
    ],
    "blocked_pending_owner_setup_auth_data": [
        "POST /v1/documents/batch auth-negative: blocked until missing/invalid X-Tenant-Token returns confirmed 401 or 403",
        "POST /v1/documents/check-cache and POST /v1/documents/crosscheck: need request-shape, fixture, artifact, and owner review",
        "GET /v1/admin/cache/stats, GET /monitoring/api/v1/providers, GET /ai-gateway/s3/s3/list: blocked by current status/setup behavior",
        "GET /monitoring/api/v1/golden-dataset/export: blocked pending artifact/output sensitivity policy",
    ],
    "excluded": [
        "Legacy duplicate aliases where current explicit v1 routes exist",
        "UI surfaces such as /parser_studio and /qa",
        "Debug/error routes such as /sentry-debug and /api/v1/sentry-debug",
        "Destructive/admin mutation routes such as cache deletes, truncate routes, bulk delete routes, and drift trigger/run mutation surfaces",
    ],
}


def load_openapi(path: Path = OPENAPI_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _schemas(openapi: dict[str, Any]) -> dict[str, Any]:
    return openapi.get("components", {}).get("schemas", {})


def _resolve_ref(openapi: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    prefix = "#/components/schemas/"
    if not ref.startswith(prefix):
        return schema
    return _schemas(openapi).get(ref.removeprefix(prefix), schema)


def _response_schema(
    openapi: dict[str, Any],
    endpoint: ObservedEndpoint,
    status_code: int,
) -> dict[str, Any] | None:
    operation = openapi.get("paths", {}).get(endpoint.path, {}).get(endpoint.method.lower())
    if not isinstance(operation, dict):
        return None
    response = operation.get("responses", {}).get(str(status_code))
    if not isinstance(response, dict):
        return None
    content = response.get("content", {})
    if not isinstance(content, dict):
        return None
    application_json = content.get("application/json", {})
    if not isinstance(application_json, dict):
        return None
    schema = application_json.get("schema")
    if not isinstance(schema, dict):
        return None
    return _resolve_ref(openapi, schema)


def _schema_types(openapi: dict[str, Any], schema: dict[str, Any] | None) -> set[str]:
    if not schema:
        return set()
    resolved = _resolve_ref(openapi, schema)
    schema_type = resolved.get("type")
    if isinstance(schema_type, str):
        return {schema_type}
    if isinstance(schema_type, list):
        return {item for item in schema_type if isinstance(item, str)}
    types: set[str] = set()
    for key in ("anyOf", "oneOf"):
        options = resolved.get(key, [])
        if isinstance(options, list):
            for option in options:
                if isinstance(option, dict):
                    types.update(_schema_types(openapi, option))
    return types


def _is_generic_object_schema(schema: dict[str, Any] | None) -> bool:
    if not schema:
        return False
    return (
        schema.get("type") == "object"
        and schema.get("additionalProperties") is True
        and not schema.get("properties")
    )


def _field_schema(
    openapi: dict[str, Any],
    response_schema: dict[str, Any] | None,
    observed_path: str,
) -> dict[str, Any] | None:
    if not response_schema:
        return None
    current = _resolve_ref(openapi, response_schema)
    for raw_segment in observed_path.removeprefix("$.").split("."):
        if not raw_segment:
            return None
        is_array = raw_segment.endswith("[]")
        segment = raw_segment.removesuffix("[]")
        properties = current.get("properties")
        if not isinstance(properties, dict):
            return None
        field = properties.get(segment)
        if not isinstance(field, dict):
            return None
        current = _resolve_ref(openapi, field)
        if is_array:
            items = current.get("items")
            if not isinstance(items, dict):
                return None
            current = _resolve_ref(openapi, items)
    return current


def compare_openapi_to_observed(
    openapi: dict[str, Any],
    baselines: tuple[ObservedEndpoint, ...] = OBSERVED_BASELINES,
) -> list[DriftFinding]:
    findings: list[DriftFinding] = []
    for endpoint in baselines:
        endpoint_label = f"{endpoint.method} {endpoint.path}"
        operation = openapi.get("paths", {}).get(endpoint.path, {}).get(endpoint.method.lower())
        if not isinstance(operation, dict):
            findings.append(
                DriftFinding(
                    endpoint=endpoint_label,
                    status_code=0,
                    kind="observed_endpoint_missing_from_openapi",
                    observed="endpoint has curated observed baseline",
                    openapi="path or method missing",
                    evidence=endpoint.evidence,
                    contract_status=endpoint.public_contract_status,
                )
            )
            continue

        for response in endpoint.responses:
            response_schema = _response_schema(openapi, endpoint, response.status_code)
            if response_schema is None:
                findings.append(
                    DriftFinding(
                        endpoint=endpoint_label,
                        status_code=response.status_code,
                        kind="observed_status_undocumented",
                        observed=f"HTTP {response.status_code}",
                        openapi="response status missing or lacks application/json schema",
                        evidence=response.evidence,
                        contract_status=endpoint.public_contract_status,
                    )
                )
                continue

            for observed_field in response.fields:
                if observed_field.loose:
                    continue
                field_schema = _field_schema(openapi, response_schema, observed_field.path)
                if field_schema is None:
                    kind = (
                        "generic_schema_under_documents_observed_field"
                        if _is_generic_object_schema(response_schema)
                        else "observed_field_undocumented"
                    )
                    findings.append(
                        DriftFinding(
                            endpoint=endpoint_label,
                            status_code=response.status_code,
                            kind=kind,
                            observed=(
                                f"{observed_field.path}: "
                                f"{'|'.join(observed_field.json_types)}"
                            ),
                            openapi="field not declared in response schema",
                            evidence=observed_field.evidence,
                            contract_status=observed_field.contract_status,
                        )
                    )
                    continue

                schema_types = _schema_types(openapi, field_schema)
                if schema_types and schema_types.isdisjoint(observed_field.json_types):
                    findings.append(
                        DriftFinding(
                            endpoint=endpoint_label,
                            status_code=response.status_code,
                            kind="observed_field_type_mismatch",
                            observed=(
                                f"{observed_field.path}: "
                                f"{'|'.join(observed_field.json_types)}"
                            ),
                            openapi=f"{observed_field.path}: {'|'.join(sorted(schema_types))}",
                            evidence=observed_field.evidence,
                            contract_status=observed_field.contract_status,
                        )
                    )
    return findings


def build_report(openapi: dict[str, Any]) -> dict[str, Any]:
    findings = compare_openapi_to_observed(openapi)
    return {
        "principle": (
            "Current observed endpoint response shape is the runtime baseline for "
            "drift comparison against official-openapi.json. Findings are observed "
            "drift, not owner-approved public contract."
        ),
        "openapi_path": str(OPENAPI_PATH.relative_to(REPO_ROOT)),
        "observed_baselines": [asdict(endpoint) for endpoint in OBSERVED_BASELINES],
        "endpoint_classification": ENDPOINT_CLASSIFICATION,
        "findings": [asdict(finding) for finding in findings],
    }


def _format_endpoint(endpoint: dict[str, Any]) -> str:
    return f"{endpoint['method']} {endpoint['path']}"


def format_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# OpenAPI Runtime Drift Report",
        "",
        report["principle"],
        "",
        "## Baselines Compared",
    ]
    for endpoint in report["observed_baselines"]:
        lines.append(f"- `{_format_endpoint(endpoint)}`: {endpoint['comparison_scope']}")
        if endpoint["loose_paths"]:
            loose = ", ".join(f"`{path}`" for path in endpoint["loose_paths"])
            lines.append(f"  - Loose paths: {loose}")

    lines.extend(["", "## Endpoint Classification"])
    for category, entries in report["endpoint_classification"].items():
        lines.append(f"### {category.replace('_', ' ').title()}")
        for entry in entries:
            lines.append(f"- {entry}")

    lines.extend(["", "## Findings"])
    findings = report["findings"]
    if not findings:
        lines.append("- No observed drift found for compared baselines.")
    else:
        for finding in findings:
            lines.append(
                "- "
                f"`{finding['endpoint']}` HTTP {finding['status_code']} "
                f"{finding['kind']}: observed {finding['observed']}; "
                f"OpenAPI {finding['openapi']}."
            )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--openapi",
        default=str(OPENAPI_PATH),
        help="Path to the OpenAPI JSON file. Defaults to official-openapi.json.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of Markdown.",
    )
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Exit 1 when observed drift findings are present.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    openapi_path = Path(args.openapi).expanduser()
    if not openapi_path.is_absolute():
        openapi_path = (REPO_ROOT / openapi_path).resolve()
    try:
        openapi = load_openapi(openapi_path)
    except OSError as exc:
        print(f"Unable to read OpenAPI file: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"Invalid OpenAPI JSON: {exc}", file=sys.stderr)
        return 2

    report = build_report(openapi)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_markdown_report(report), end="")

    if args.fail_on_drift and report["findings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
