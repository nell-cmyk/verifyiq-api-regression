"""Shared contract assertions for document parsing endpoints."""
from __future__ import annotations

from typing import Any

import httpx

from tests.diagnostics import diagnose, parse_json_or_fail

DOCUMENT_RESULT_REQUIRED_FIELDS = (
    "fileType",
    "documentQuality",
    "summaryOCR",
    "summaryResult",
    "calculatedFields",
)


def _diagnostic_suffix(
    *,
    response: httpx.Response | None = None,
    fixture_file: str | None = None,
    extra_context: str = "",
) -> str:
    suffix = ""
    if response is not None:
        suffix += diagnose(response, fixture_file=fixture_file)
    return suffix + extra_context


def assert_document_result_has_required_fields(
    result: dict[str, Any],
    *,
    context: str,
    response: httpx.Response | None = None,
    fixture_file: str | None = None,
    extra_context: str = "",
) -> None:
    missing = [field for field in DOCUMENT_RESULT_REQUIRED_FIELDS if field not in result]
    assert not missing, (
        f"Missing fields in {context}: {missing}"
        + _diagnostic_suffix(
            response=response,
            fixture_file=fixture_file,
            extra_context=extra_context,
        )
    )


def assert_document_result_file_type(
    result: dict[str, Any],
    *,
    expected_file_type: str,
    context: str,
    response: httpx.Response | None = None,
    fixture_file: str | None = None,
    extra_context: str = "",
) -> None:
    assert result.get("fileType") == expected_file_type, (
        f"{context} fileType mismatch: expected {expected_file_type!r}, "
        f"got {result.get('fileType')!r}"
        + _diagnostic_suffix(
            response=response,
            fixture_file=fixture_file,
            extra_context=extra_context,
        )
    )


def assert_document_result_calculated_fields_not_stub(
    result: dict[str, Any],
    *,
    context: str,
    response: httpx.Response | None = None,
    fixture_file: str | None = None,
    extra_context: str = "",
) -> None:
    assert result.get("calculatedFields") != {"pageNumber": 1}, (
        f"{context} calculatedFields is the config-missing stub value"
        + _diagnostic_suffix(
            response=response,
            fixture_file=fixture_file,
            extra_context=extra_context,
        )
    )


def assert_http_validation_error_shape(
    response: httpx.Response,
    *,
    context: str,
    fixture_file: str | None = None,
    extra_context: str = "",
) -> dict[str, Any]:
    body = parse_json_or_fail(
        response,
        context=context,
        fixture_file=fixture_file,
        extra_context=extra_context,
    )
    assert "detail" in body, (
        f"Missing 'detail' in validation response for {context}"
        + _diagnostic_suffix(
            response=response,
            fixture_file=fixture_file,
            extra_context=extra_context,
        )
    )
    assert isinstance(body["detail"], list), (
        f"'detail' must be a list in validation response for {context}"
        + _diagnostic_suffix(
            response=response,
            fixture_file=fixture_file,
            extra_context=extra_context,
        )
    )
    if body["detail"]:
        err = body["detail"][0]
        for key in ("loc", "msg", "type"):
            assert key in err, (
                f"Missing '{key}' in validation error entry for {context}"
                + _diagnostic_suffix(
                    response=response,
                    fixture_file=fixture_file,
                    extra_context=extra_context,
                )
            )
    return body
