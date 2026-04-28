from __future__ import annotations

import re
import time
from typing import Any

import httpx
import pytest

from tests.diagnostics import request_error_diagnostics, timeout_diagnostics


PARSE_ENDPOINT = "/v1/documents/parse"
FRAUD_STATUS_PREFIX = "/v1/documents/fraud-status/"
ASYNC_PARSE_TIMEOUT_SECS = 300.0
FRAUD_STATUS_TIMEOUT_SECS = 30.0
FRAUD_STATUS_MAX_POLLS = 6
FRAUD_STATUS_POLL_INTERVAL_SECS = 10
FRAUD_JOB_ID_RE = re.compile(r"^fj_[a-f0-9]{32}$")
ALLOWED_FRAUD_STATUSES = {"pending", "running", "complete", "failed"}
EXPECTED_KEYS_BY_STATUS = {
    "pending": {"fraudJobId", "fraudStatus"},
    "running": {"fraudJobId", "fraudStatus"},
    "complete": {
        "fraudJobId",
        "fraudStatus",
        "fraudScore",
        "authenticityScore",
        "mathematicalFraudReport",
        "metadataFraudReport",
        "completedAt",
    },
    "failed": {"fraudJobId", "fraudStatus", "error", "completedAt"},
}


@pytest.fixture
def artifact_free_client() -> httpx.Client:
    from tests.client import platform_auth_headers
    from tests.config import require

    with httpx.Client(
        base_url=require("BASE_URL"),
        headers={
            **platform_auth_headers(),
            "X-Tenant-Token": require("TENANT_TOKEN"),
        },
        timeout=60.0,
    ) as client:
        yield client


def _json_object(response: httpx.Response, *, context: str) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        pytest.fail(f"{context} returned non-JSON response.")
    if not isinstance(body, dict):
        pytest.fail(f"{context} returned JSON {type(body).__name__}, expected object.")
    return body


def _find_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = _find_key(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_key(child, key)
            if found is not None:
                return found
    return None


def is_valid_fraud_job_id(value: object) -> bool:
    return isinstance(value, str) and bool(FRAUD_JOB_ID_RE.fullmatch(value))


def expected_keys_for_status(status: str) -> set[str]:
    return EXPECTED_KEYS_BY_STATUS[status]


def assert_fraud_status_shape(body: dict[str, Any], *, expected_job_id: str | None = None) -> str:
    raw_status = body.get("fraudStatus")
    if not isinstance(raw_status, str):
        pytest.fail("Fraud-status response did not include string fraudStatus.")
    fraud_status = raw_status.strip()
    if fraud_status not in ALLOWED_FRAUD_STATUSES:
        pytest.fail(f"Fraud-status response returned unsupported fraudStatus {fraud_status!r}.")

    actual_keys = set(body)
    expected_keys = expected_keys_for_status(fraud_status)
    if actual_keys != expected_keys:
        pytest.fail(
            "Fraud-status response top-level keys did not match the provisional "
            f"{fraud_status!r} shape; got {sorted(actual_keys)!r}, expected {sorted(expected_keys)!r}."
        )

    raw_job_id = body.get("fraudJobId")
    if not is_valid_fraud_job_id(raw_job_id):
        pytest.fail("Fraud-status response did not include a format-valid fraudJobId.")
    if expected_job_id is not None and raw_job_id != expected_job_id:
        pytest.fail("Fraud-status response did not echo the produced fraudJobId.")

    return fraud_status


def _post_async_fraud_parse(client: httpx.Client) -> httpx.Response:
    from tests.endpoints.parse.fixtures import PARSE_FIXTURE_FILE, PARSE_FIXTURE_FILE_TYPE

    payload = {
        "file": PARSE_FIXTURE_FILE,
        "fileType": PARSE_FIXTURE_FILE_TYPE,
        "pipeline": {"use_cache": False, "async_fraud": True},
    }
    try:
        return client.post(PARSE_ENDPOINT, json=payload, timeout=ASYNC_PARSE_TIMEOUT_SECS)
    except httpx.TimeoutException as exc:
        pytest.fail(
            timeout_diagnostics(
                exc,
                context="Fraud-status async parse producer",
                timeout_secs=ASYNC_PARSE_TIMEOUT_SECS,
            )
        )
    except httpx.RequestError as exc:
        pytest.fail(
            request_error_diagnostics(
                exc,
                context="Fraud-status async parse producer",
            )
        )


def _get_fraud_status(client: httpx.Client, job_id: str) -> httpx.Response:
    try:
        return client.get(FRAUD_STATUS_PREFIX + job_id, timeout=FRAUD_STATUS_TIMEOUT_SECS)
    except httpx.TimeoutException as exc:
        pytest.fail(
            timeout_diagnostics(
                exc,
                context="Fraud-status poll",
                timeout_secs=FRAUD_STATUS_TIMEOUT_SECS,
            )
        )
    except httpx.RequestError as exc:
        pytest.fail(request_error_diagnostics(exc, context="Fraud-status poll"))


def _produce_fraud_job_id(client: httpx.Client) -> str:
    response = _post_async_fraud_parse(client)
    if response.status_code != 200:
        pytest.fail(
            "Fraud-status async parse producer returned unexpected status "
            f"{response.status_code}; expected 200."
        )

    body = _json_object(response, context="Fraud-status async parse producer")
    fraud_job_id = _find_key(body, "fraudJobId")
    if fraud_job_id is None:
        pytest.skip(
            "Skipping setup-backed fraud-status GET smoke: async parse producer "
            "returned 200 but no fraudJobId; treating as sync fallback or missing async scheduling."
        )
    if not is_valid_fraud_job_id(fraud_job_id):
        pytest.fail("Fraud-status async parse producer returned malformed fraudJobId.")
    return fraud_job_id


def test_fraud_status_rejects_invalid_and_nonexistent_job_ids(artifact_free_client: httpx.Client):
    invalid_response = _get_fraud_status(artifact_free_client, "not-a-fraud-job")
    assert invalid_response.status_code == 404

    nonexistent_job_id = "fj_" + ("0" * 32)
    nonexistent_response = _get_fraud_status(artifact_free_client, nonexistent_job_id)
    assert nonexistent_response.status_code == 404


def test_fraud_status_async_parse_job_smoke(artifact_free_client: httpx.Client):
    fraud_job_id = _produce_fraud_job_id(artifact_free_client)
    final_status = ""

    for poll_index in range(FRAUD_STATUS_MAX_POLLS):
        if poll_index:
            time.sleep(FRAUD_STATUS_POLL_INTERVAL_SECS)

        response = _get_fraud_status(artifact_free_client, fraud_job_id)
        if response.status_code == 404:
            pytest.fail("Fraud-status poll returned 404 for a freshly produced fraudJobId.")
        if response.status_code != 200:
            pytest.fail(
                "Fraud-status poll returned unexpected status "
                f"{response.status_code}; expected 200 or terminal 404."
            )

        body = _json_object(response, context="Fraud-status poll")
        final_status = assert_fraud_status_shape(body, expected_job_id=fraud_job_id)
        if final_status in {"complete", "failed"}:
            return

    assert final_status in {"pending", "running"}
