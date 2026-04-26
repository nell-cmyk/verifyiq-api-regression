from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "official-openapi.json"

PARSE_SUCCESS_REQUIRED_FIELDS = {
    "fileType",
    "documentQuality",
    "summaryOCR",
    "summaryResult",
    "calculatedFields",
}


def _load_openapi() -> dict[str, Any]:
    return json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))


def _schemas(openapi: dict[str, Any]) -> dict[str, Any]:
    return openapi["components"]["schemas"]


def _resolve_schema_ref(openapi: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    assert isinstance(ref, str), f"Expected schema $ref, got {schema!r}"
    prefix = "#/components/schemas/"
    assert ref.startswith(prefix), f"Unexpected schema ref: {ref!r}"
    return _schemas(openapi)[ref.removeprefix(prefix)]


def test_parse_request_documents_optional_pipeline_use_cache() -> None:
    openapi = _load_openapi()
    parse_request = _schemas(openapi)["ParseRequest"]

    assert set(parse_request["required"]) == {"file", "fileType"}
    assert "pipeline" not in parse_request["required"]

    pipeline_schema = parse_request["properties"]["pipeline"]
    pipeline_refs = [
        item["$ref"]
        for item in pipeline_schema["anyOf"]
        if "$ref" in item
    ]
    assert pipeline_refs == ["#/components/schemas/ParsePipelineOptions"]

    pipeline_options = _schemas(openapi)["ParsePipelineOptions"]
    assert pipeline_options["properties"]["use_cache"]["type"] == "boolean"
    assert "use_cache" not in pipeline_options.get("required", [])


def test_parse_success_response_uses_conservative_parse_response_schema() -> None:
    openapi = _load_openapi()
    response_schema = (
        openapi["paths"]["/v1/documents/parse"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]
    )

    assert response_schema == {"$ref": "#/components/schemas/ParseResponse"}
    parse_response = _resolve_schema_ref(openapi, response_schema)

    assert parse_response["type"] == "object"
    assert parse_response["additionalProperties"] is True
    assert set(parse_response["required"]) == PARSE_SUCCESS_REQUIRED_FIELDS

    properties = parse_response["properties"]
    assert properties["fileType"]["type"] == "string"
    assert properties["documentQuality"]["type"] == "string"

    for field in ("summaryOCR", "summaryResult", "calculatedFields"):
        field_schema = properties[field]
        assert field_schema["type"] == "array"
        assert field_schema["items"]["type"] == "object"
        assert field_schema["items"]["additionalProperties"] is True


def test_parse_validation_error_schema_remains_available() -> None:
    openapi = _load_openapi()
    validation_response = (
        openapi["paths"]["/v1/documents/parse"]["post"]["responses"]["422"]
        ["content"]["application/json"]["schema"]
    )

    assert validation_response == {"$ref": "#/components/schemas/HTTPValidationError"}
    validation_error = _resolve_schema_ref(openapi, validation_response)

    assert validation_error["type"] == "object"
    assert validation_error["properties"]["detail"]["type"] == "array"
    assert (
        validation_error["properties"]["detail"]["items"]["$ref"]
        == "#/components/schemas/ValidationError"
    )
