from __future__ import annotations

import httpx

from tests.diagnostics import (
    is_remote_disconnect_error,
    request_error_diagnostics,
    should_retry_transient_disconnect,
)


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://example.test/v1/documents/parse")


def test_is_remote_disconnect_error_detects_remote_protocol_error():
    exc = httpx.RemoteProtocolError(
        "Server disconnected without sending a response.",
        request=_request(),
    )

    assert is_remote_disconnect_error(exc) is True


def test_should_retry_transient_disconnect_only_retries_with_budget_remaining():
    exc = httpx.RemoteProtocolError(
        "Server disconnected without sending a response.",
        request=_request(),
    )

    assert should_retry_transient_disconnect(exc, attempt=0, max_retries=1) is True
    assert should_retry_transient_disconnect(exc, attempt=1, max_retries=1) is False


def test_request_error_diagnostics_adds_remote_disconnect_guidance():
    exc = httpx.RemoteProtocolError(
        "Server disconnected without sending a response.",
        request=_request(),
    )

    message = request_error_diagnostics(
        exc,
        context="Parse happy-path request",
        fixture_file="gs://bucket/fixture.pdf",
        file_type="BankStatement",
    )

    assert "RemoteProtocolError" in message
    assert "closed by the server before any HTTP response was sent" in message
    assert "Re-run the single happy-path parse test once" in message
