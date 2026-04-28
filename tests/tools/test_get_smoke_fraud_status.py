from __future__ import annotations

import importlib

import pytest


MODULE_NAME = "tests.endpoints.get_smoke.test_fraud_status"


def _module():
    return importlib.import_module(MODULE_NAME)


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
