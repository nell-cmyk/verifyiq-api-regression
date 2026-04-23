from __future__ import annotations

import httpx
import pytest

from tests.endpoints.parse.happy_path import run_protected_parse_happy_path_request


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://example.test/v1/documents/parse")


def _response() -> httpx.Response:
    return httpx.Response(200, request=_request(), json={"ok": True})


def test_remote_disconnect_retries_once_then_returns_success():
    calls = {"count": 0}

    def send_request() -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.RemoteProtocolError(
                "Server disconnected without sending a response.",
                request=_request(),
            )
        return _response()

    with pytest.warns(UserWarning, match="Retrying the protected happy-path request once"):
        response = run_protected_parse_happy_path_request(
            send_request,
            context="Parse happy-path request",
            fixture_file="gs://bucket/fixture.pdf",
            file_type="BankStatement",
            max_remote_disconnect_retries=1,
        )

    assert calls["count"] == 2
    assert response.status_code == 200


def test_remote_disconnect_fails_after_retry_budget_exhausted():
    calls = {"count": 0}

    def send_request() -> httpx.Response:
        calls["count"] += 1
        raise httpx.RemoteProtocolError(
            f"disconnect {calls['count']}",
            request=_request(),
        )

    with pytest.warns(UserWarning, match="Retrying the protected happy-path request once"):
        with pytest.raises(httpx.RemoteProtocolError, match="disconnect 2"):
            run_protected_parse_happy_path_request(
                send_request,
                context="Parse happy-path request",
                fixture_file="gs://bucket/fixture.pdf",
                file_type="BankStatement",
                max_remote_disconnect_retries=1,
            )

    assert calls["count"] == 2


def test_timeout_does_not_retry():
    calls = {"count": 0}

    def send_request() -> httpx.Response:
        calls["count"] += 1
        raise httpx.ReadTimeout("timed out", request=_request())

    with pytest.raises(httpx.TimeoutException, match="timed out"):
        run_protected_parse_happy_path_request(
            send_request,
            context="Parse happy-path request",
            fixture_file="gs://bucket/fixture.pdf",
            file_type="BankStatement",
            max_remote_disconnect_retries=1,
        )

    assert calls["count"] == 1


def test_non_disconnect_request_error_does_not_retry():
    calls = {"count": 0}

    def send_request() -> httpx.Response:
        calls["count"] += 1
        raise httpx.ConnectError("connect failed", request=_request())

    with pytest.raises(httpx.RequestError, match="connect failed"):
        run_protected_parse_happy_path_request(
            send_request,
            context="Parse happy-path request",
            fixture_file="gs://bucket/fixture.pdf",
            file_type="BankStatement",
            max_remote_disconnect_retries=1,
        )

    assert calls["count"] == 1
