"""Protected /parse happy-path helpers."""
from __future__ import annotations

from collections.abc import Callable
import warnings

import httpx

from tests.diagnostics import request_error_diagnostics, should_retry_transient_disconnect


def run_protected_parse_happy_path_request(
    send_request: Callable[[], httpx.Response],
    *,
    context: str,
    fixture_file: str,
    file_type: str,
    max_remote_disconnect_retries: int,
) -> httpx.Response:
    """Run the protected happy-path request with one narrow reconnect policy.

    This helper is import-safe and deterministic to unit test. It only retries
    when the server disconnects before sending any HTTP response at all.
    """
    for attempt in range(max_remote_disconnect_retries + 1):
        try:
            return send_request()
        except httpx.RequestError as exc:
            if should_retry_transient_disconnect(
                exc,
                attempt=attempt,
                max_retries=max_remote_disconnect_retries,
            ):
                warnings.warn(
                    request_error_diagnostics(
                        exc,
                        context=context,
                        fixture_file=fixture_file,
                        file_type=file_type,
                    )
                    + "\nRetrying the protected happy-path request once after a transport disconnect.",
                    stacklevel=2,
                )
                continue
            raise

    raise AssertionError("protected parse retry loop exhausted unexpectedly")
