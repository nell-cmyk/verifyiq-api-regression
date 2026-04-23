"""Opt-in /documents/batch auth characterization.

Representative tenant-token auth coverage for `/documents/batch` is currently
blocked because staging has not produced confirmed 401/403 rejection semantics.
Recent opt-in characterization has shown a missing tenant token timing out and
an invalid tenant token returning `200`, so keep this out of the default batch
suite and opt in only when you want to re-characterize the blocker explicitly:

  RUN_BATCH_AUTH_CHARACTERIZATION=1 pytest tests/endpoints/batch/test_batch_auth_characterization.py -v
"""
from __future__ import annotations

import os

import httpx
import pytest

from tests.client import platform_auth_headers
from tests.config import require
from tests.diagnostics import diagnose, request_error_diagnostics, timeout_diagnostics
from tests.endpoints.batch.artifacts import attach as attach_batch_artifacts
from tests.endpoints.batch.fixtures import batch_fixture_context, build_batch_request, load_batch_fixtures

ENDPOINT = "/v1/documents/batch"
_AUTH_NEGATIVE_TIMEOUT_SECS = 30.0


if os.getenv("RUN_BATCH_AUTH_CHARACTERIZATION") != "1":
    raise RuntimeError(
        "The /documents/batch auth characterization is opt-in only. "
        "Set RUN_BATCH_AUTH_CHARACTERIZATION=1 explicitly before running "
        "`tests/endpoints/batch/test_batch_auth_characterization.py`."
    )


@pytest.fixture(scope="session")
def batch_fixtures():
    return load_batch_fixtures()


@pytest.fixture(scope="session")
def batch_context(batch_fixtures):
    return batch_fixture_context(batch_fixtures)


@pytest.fixture(scope="session")
def batch_request_payload(batch_fixtures):
    return build_batch_request(batch_fixtures)


def _assert_auth_rejection(
    client: httpx.Client,
    *,
    batch_request_payload: dict[str, object],
    batch_context: str,
    context: str,
) -> None:
    attach_batch_artifacts(client)
    try:
        resp = client.post(ENDPOINT, json=batch_request_payload)
    except httpx.TimeoutException as exc:
        pytest.fail(
            timeout_diagnostics(
                exc,
                context=f"Auth-negative '{context}'",
                timeout_secs=_AUTH_NEGATIVE_TIMEOUT_SECS,
                extra_context=batch_context,
            )
            + "\nAuth-negative coverage requires a confirmed 401/403 response; "
            "timeout is an ambiguous blocker, not a passing rejection."
        )
    except httpx.RequestError as exc:
        pytest.fail(
            request_error_diagnostics(
                exc,
                context=f"Auth-negative '{context}'",
                extra_context=batch_context,
            )
            + "\nAuth-negative coverage requires a confirmed 401/403 response; "
            "transport failure is ambiguous and does not close the coverage gap."
        )
    assert resp.status_code in (401, 403), (
        f"Auth-negative '{context}': expected confirmed 401/403 rejection, "
        f"got {resp.status_code}"
        + diagnose(resp)
        + batch_context
    )


class TestBatchAuth:
    def test_missing_token_rejected(self, batch_request_payload, batch_context):
        with httpx.Client(
            base_url=require("BASE_URL"),
            headers=platform_auth_headers(),
            timeout=_AUTH_NEGATIVE_TIMEOUT_SECS,
        ) as c:
            _assert_auth_rejection(
                c,
                batch_request_payload=batch_request_payload,
                batch_context=batch_context,
                context="missing X-Tenant-Token",
            )

    def test_invalid_token_rejected(self, batch_request_payload, batch_context):
        with httpx.Client(
            base_url=require("BASE_URL"),
            headers={
                **platform_auth_headers(),
                "X-Tenant-Token": "invalid-token-xyz",
            },
            timeout=_AUTH_NEGATIVE_TIMEOUT_SECS,
        ) as c:
            _assert_auth_rejection(
                c,
                batch_request_payload=batch_request_payload,
                batch_context=batch_context,
                context="invalid X-Tenant-Token",
            )
