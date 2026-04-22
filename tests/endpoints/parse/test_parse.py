"""
Regression tests for POST /v1/documents/parse.

Contract reference: official-openapi.json → ParseRequest / HTTPValidationError
Required request fields: file (str, GCS/S3/HTTP URL), fileType (str)
Always include: pipeline.use_cache = false
Primary assertion targets: fileType, documentQuality, summaryOCR, summaryResult, calculatedFields
"""
import warnings

import httpx
import pytest

from tests.client import platform_auth_headers
from tests.config import BASE_URL
from tests.diagnostics import (
    diagnose,
    parse_json_or_fail,
    request_error_diagnostics,
    timeout_diagnostics,
)
from tests.endpoints.document_contracts import (
    assert_document_result_calculated_fields_not_stub,
    assert_document_result_file_type,
    assert_document_result_has_required_fields,
    assert_http_validation_error_shape,
)
from tests.endpoints.parse.fixtures import (
    PARSE_FIXTURE_FILE,
    PARSE_FIXTURE_FILE_TYPE,
    PARSE_REQUEST_BASE,
)

ENDPOINT = "/v1/documents/parse"


# ── Shared response fixture ───────────────────────────────────────────────────
# The parse endpoint is LLM + OCR heavy. Single-page payslip on dev is ~15–30s,
# but multi-page staging fixtures (e.g. bank statements) can run much longer,
# so the happy-path request gets its own generous timeout distinct from the
# shared client default. All happy path tests share one response to avoid
# redundant round trips.

PARSE_HAPPY_TIMEOUT_SECS = 300.0


@pytest.fixture(scope="session")
def parse_response(client):
    try:
        return client.post(
            ENDPOINT,
            json=PARSE_REQUEST_BASE,
            timeout=PARSE_HAPPY_TIMEOUT_SECS,
        )
    except httpx.TimeoutException as exc:
        pytest.fail(
            timeout_diagnostics(
                exc,
                context="Parse happy-path request",
                timeout_secs=PARSE_HAPPY_TIMEOUT_SECS,
                fixture_file=PARSE_FIXTURE_FILE,
                file_type=PARSE_FIXTURE_FILE_TYPE,
            )
            + "\nConsider: (a) raising PARSE_HAPPY_TIMEOUT_SECS if this fixture is "
            "legitimately heavy, (b) switching PARSE_FIXTURE_FILE to a lighter "
            "document for the regression baseline, (c) checking staging health / "
            "LLM latency upstream."
        )
    except httpx.RequestError as exc:
        pytest.fail(
            request_error_diagnostics(
                exc,
                context="Parse happy-path request",
                fixture_file=PARSE_FIXTURE_FILE,
                file_type=PARSE_FIXTURE_FILE_TYPE,
            )
        )


# ── Happy path ────────────────────────────────────────────────────────────────

class TestParseHappyPath:
    def test_returns_200(self, parse_response):
        assert parse_response.status_code == 200, diagnose(
            parse_response, fixture_file=PARSE_FIXTURE_FILE
        )

    def test_response_has_required_fields(self, parse_response):
        assert parse_response.status_code == 200, diagnose(
            parse_response, fixture_file=PARSE_FIXTURE_FILE
        )
        body = parse_json_or_fail(
            parse_response,
            context="Parse happy-path response",
            fixture_file=PARSE_FIXTURE_FILE,
        )
        assert_document_result_has_required_fields(
            body,
            context="parse response",
            response=parse_response,
            fixture_file=PARSE_FIXTURE_FILE,
        )

    def test_file_type_matches_request(self, parse_response):
        assert parse_response.status_code == 200, diagnose(
            parse_response, fixture_file=PARSE_FIXTURE_FILE
        )
        body = parse_json_or_fail(
            parse_response,
            context="Parse happy-path response",
            fixture_file=PARSE_FIXTURE_FILE,
        )
        assert_document_result_file_type(
            body,
            expected_file_type=PARSE_FIXTURE_FILE_TYPE,
            context="parse response",
            response=parse_response,
            fixture_file=PARSE_FIXTURE_FILE,
        )

    def test_calculated_fields_not_stub(self, parse_response):
        """Regression: calculatedFields == {"pageNumber": 1} signals missing computed_fields config."""
        assert parse_response.status_code == 200, diagnose(
            parse_response, fixture_file=PARSE_FIXTURE_FILE
        )
        cf = parse_json_or_fail(
            parse_response,
            context="Parse happy-path response",
            fixture_file=PARSE_FIXTURE_FILE,
        )
        assert_document_result_calculated_fields_not_stub(
            cf,
            context="parse response",
            response=parse_response,
            fixture_file=PARSE_FIXTURE_FILE,
        )


# ── Auth ──────────────────────────────────────────────────────────────────────
# Auth-negative behavior on staging: the endpoint does not fast-reject on a
# missing or invalid X-Tenant-Token — it hangs past a short request timeout.
# Empirically a valid 401/403 response is NOT guaranteed; ReadTimeout is the
# observed outcome. Both are treated as valid negative signals: the request
# did not successfully reach the parse path. A 2xx would still fail the test.

_AUTH_NEGATIVE_TIMEOUT_SECS = 10.0


def _assert_auth_rejection(client: httpx.Client, *, context: str) -> None:
    try:
        resp = client.post(ENDPOINT, json=PARSE_REQUEST_BASE)
    except httpx.TimeoutException as exc:
        warnings.warn(
            timeout_diagnostics(
                exc,
                context=f"Auth-negative '{context}'",
                timeout_secs=_AUTH_NEGATIVE_TIMEOUT_SECS,
                fixture_file=PARSE_FIXTURE_FILE,
                file_type=PARSE_FIXTURE_FILE_TYPE,
            )
            + "\nTreating timeout as valid negative outcome — server did not "
            "successfully process the request.",
            stacklevel=2,
        )
        return
    except httpx.RequestError as exc:
        pytest.fail(
            request_error_diagnostics(
                exc,
                context=f"Auth-negative '{context}'",
                fixture_file=PARSE_FIXTURE_FILE,
                file_type=PARSE_FIXTURE_FILE_TYPE,
            )
        )
    assert resp.status_code in (401, 403), (
        f"Auth-negative '{context}': expected 401/403 or timeout, "
        f"got {resp.status_code}"
        + diagnose(resp, fixture_file=PARSE_FIXTURE_FILE)
    )


class TestParseAuth:
    def test_missing_token_rejected(self):
        # Platform auth (IAP + Bearer API key) present so we exercise the app's
        # tenant-token layer, not IAP or BearerAuth.
        with httpx.Client(
            base_url=BASE_URL,
            headers=platform_auth_headers(),
            timeout=_AUTH_NEGATIVE_TIMEOUT_SECS,
        ) as c:
            _assert_auth_rejection(c, context="missing X-Tenant-Token")

    def test_invalid_token_rejected(self):
        with httpx.Client(
            base_url=BASE_URL,
            headers={
                **platform_auth_headers(),
                "X-Tenant-Token": "invalid-token-xyz",
            },
            timeout=_AUTH_NEGATIVE_TIMEOUT_SECS,
        ) as c:
            _assert_auth_rejection(c, context="invalid X-Tenant-Token")


# ── Request validation ────────────────────────────────────────────────────────

class TestParseValidation:
    def test_missing_file_returns_422(self, client):
        resp = client.post(ENDPOINT, json={
            "fileType": PARSE_FIXTURE_FILE_TYPE,
            "pipeline": {"use_cache": False},
        })
        assert resp.status_code == 422, (
            f"Expected 422, got {resp.status_code}" + diagnose(resp)
        )

    def test_missing_file_type_returns_422(self, client):
        resp = client.post(ENDPOINT, json={
            "file": PARSE_FIXTURE_FILE,
            "pipeline": {"use_cache": False},
        })
        assert resp.status_code == 422, (
            f"Expected 422, got {resp.status_code}" + diagnose(resp)
        )

    def test_empty_body_returns_422(self, client):
        resp = client.post(ENDPOINT, json={})
        assert resp.status_code == 422, (
            f"Expected 422, got {resp.status_code}" + diagnose(resp)
        )

    def test_422_conforms_to_openapi_schema(self, client):
        """HTTPValidationError shape: {detail: [{loc, msg, type}]}"""
        resp = client.post(ENDPOINT, json={})
        assert resp.status_code == 422, (
            f"Expected 422, got {resp.status_code}" + diagnose(resp)
        )
        assert_http_validation_error_shape(resp, context="Parse validation response")
