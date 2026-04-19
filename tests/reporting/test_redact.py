"""Unit tests for redaction. Runs offline; safe in default collection."""
from __future__ import annotations

from tests.reporting.redact import REDACTED, redact_body, redact_headers, truncate_text


def test_redact_headers_scrubs_known_auth_keys():
    headers = {
        "Authorization": "Bearer sk_live_abc",
        "Proxy-Authorization": "Bearer eyJhbGci...",
        "X-Tenant-Token": "tenant-xyz",
        "X-API-Key": "abc",
        "Cookie": "a=b",
        "Content-Type": "application/json",
        "X-Trace-Id": "t-42",
    }
    out = redact_headers(headers)
    assert out["Authorization"] == REDACTED
    assert out["Proxy-Authorization"] == REDACTED
    assert out["X-Tenant-Token"] == REDACTED
    assert out["X-API-Key"] == REDACTED
    assert out["Cookie"] == REDACTED
    # Non-secret headers pass through untouched.
    assert out["Content-Type"] == "application/json"
    assert out["X-Trace-Id"] == "t-42"


def test_redact_headers_is_case_insensitive():
    out = redact_headers({"authorization": "Bearer x", "X-TENANT-TOKEN": "y"})
    assert out["authorization"] == REDACTED
    assert out["X-TENANT-TOKEN"] == REDACTED


def test_redact_body_scrubs_nested_secret_keys():
    body = {
        "file": "gs://bucket/x.pdf",
        "fileType": "Payslip",
        "auth": {"access_token": "eyJ...", "refresh_token": "r-1"},
        "pipeline": {"use_cache": False},
        "items": [{"password": "hunter2", "label": "ok"}],
    }
    out = redact_body(body)
    assert out["file"] == "gs://bucket/x.pdf"
    assert out["fileType"] == "Payslip"
    assert out["auth"]["access_token"] == REDACTED
    assert out["auth"]["refresh_token"] == REDACTED
    assert out["pipeline"] == {"use_cache": False}
    assert out["items"][0]["password"] == REDACTED
    assert out["items"][0]["label"] == "ok"


def test_truncate_text_respects_limit():
    text = "a" * 10
    out, trunc = truncate_text(text, limit=4)
    assert out == "aaaa"
    assert trunc is True

    out2, trunc2 = truncate_text("short", limit=100)
    assert out2 == "short"
    assert trunc2 is False
