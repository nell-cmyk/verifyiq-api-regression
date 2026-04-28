from __future__ import annotations

import importlib

import httpx
import pytest


MODULE_NAME = "tests.endpoints.get_smoke.test_fraud_status"


def _module():
    return importlib.import_module(MODULE_NAME)


def _parse_response(status_code: int, body: dict[str, object]) -> httpx.Response:
    request = httpx.Request("POST", "https://verifyiq.example.test/v1/documents/parse")
    return httpx.Response(status_code, json=body, request=request)


def test_fraud_status_module_import_is_safe_without_live_env():
    module = _module()

    assert module.FRAUD_STATUS_MAX_POLLS == 6
    assert module.FRAUD_STATUS_POLL_INTERVAL_SECS == 10


def test_valid_fraud_job_id_pattern_accepts_only_lowercase_hex_shape():
    module = _module()

    assert module.is_valid_fraud_job_id("fj_" + ("a" * 32))
    assert not module.is_valid_fraud_job_id("fj_" + ("A" * 32))
    assert not module.is_valid_fraud_job_id("job_" + ("a" * 32))
    assert not module.is_valid_fraud_job_id("fj_" + ("a" * 31))


@pytest.mark.parametrize(
    ("status", "expected_keys"),
    [
        ("pending", {"fraudJobId", "fraudStatus"}),
        ("running", {"fraudJobId", "fraudStatus"}),
        (
            "complete",
            {
                "fraudJobId",
                "fraudStatus",
                "fraudScore",
                "authenticityScore",
                "mathematicalFraudReport",
                "metadataFraudReport",
                "completedAt",
            },
        ),
        ("failed", {"fraudJobId", "fraudStatus", "error", "completedAt"}),
    ],
)
def test_expected_keys_are_defined_for_each_allowed_fraud_status(status: str, expected_keys: set[str]):
    module = _module()

    assert module.expected_keys_for_status(status) == expected_keys


def test_status_shape_rejects_unexpected_top_level_keys():
    module = _module()
    body = {
        "fraudJobId": "fj_" + ("a" * 32),
        "fraudStatus": "running",
        "unexpected": "value",
    }

    with pytest.raises(pytest.fail.Exception, match="top-level keys did not match"):
        module.assert_fraud_status_shape(body)


def test_producer_skips_only_when_parse_accepts_without_fraud_job_id(monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "_post_async_fraud_parse", lambda client: _parse_response(200, {}))

    with pytest.raises(pytest.skip.Exception, match="returned 200 but no fraudJobId"):
        module._produce_fraud_job_id(object())


def test_producer_unexpected_status_fails_instead_of_skipping(monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "_post_async_fraud_parse", lambda client: _parse_response(503, {}))

    with pytest.raises(pytest.fail.Exception, match="unexpected status 503"):
        module._produce_fraud_job_id(object())
