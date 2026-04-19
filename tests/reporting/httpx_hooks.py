"""httpx event hooks that record request/response evidence for the Collector.

Attach via `attach(client)` on the shared httpx.Client. Never raise from inside
a hook — reporting must not fail tests.
"""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

from tests.reporting.collector import (
    CURRENT_NODEID,
    RequestRecord,
    ResponseRecord,
    get_collector,
)
from tests.reporting.redact import (
    MAX_BODY_BYTES,
    redact_body,
    redact_headers,
    truncate_text,
)


def _safe_json(text: str) -> tuple[Any, str | None]:
    """Try to parse JSON; return (obj, None) on success else (None, original_text)."""
    try:
        return json.loads(text), None
    except Exception:
        return None, text


def _on_request(request: httpx.Request) -> None:
    nodeid = CURRENT_NODEID.get()
    if not nodeid:
        return
    try:
        content_bytes = request.content or b""
        text = content_bytes.decode("utf-8", errors="replace") if content_bytes else ""
        body_obj, raw_text = _safe_json(text) if text else (None, None)
        truncated = False
        if body_obj is not None:
            body_obj = redact_body(body_obj)
        elif raw_text is not None:
            raw_text, truncated = truncate_text(raw_text, MAX_BODY_BYTES)

        rec = RequestRecord(
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            headers=redact_headers(dict(request.headers)),
            body=body_obj,
            body_text=raw_text,
            body_truncated=truncated,
            sent_at=time.time(),
        )
        get_collector().add_request(nodeid, rec)
    except Exception:
        # Never let reporting break a test.
        pass


def _on_response(response: httpx.Response) -> None:
    nodeid = CURRENT_NODEID.get()
    if not nodeid:
        return
    try:
        # Response content may be streaming; ensure it's read.
        try:
            response.read()
        except Exception:
            pass
        text = ""
        try:
            text = response.text or ""
        except Exception:
            text = ""
        body_obj, raw_text = _safe_json(text) if text else (None, None)
        truncated = False
        if body_obj is not None:
            body_obj = redact_body(body_obj)
        elif raw_text is not None:
            raw_text, truncated = truncate_text(raw_text, MAX_BODY_BYTES)

        elapsed_ms: float | None = None
        try:
            elapsed_ms = response.elapsed.total_seconds() * 1000.0
        except Exception:
            elapsed_ms = None

        rec = ResponseRecord(
            status=response.status_code,
            headers=redact_headers(dict(response.headers)),
            body=body_obj,
            body_text=raw_text,
            body_truncated=truncated,
            elapsed_ms=elapsed_ms,
            received_at=time.time(),
        )
        get_collector().add_response(nodeid, rec)
    except Exception:
        pass


def attach(client: httpx.Client) -> None:
    """Install request/response event hooks on a client, preserving any existing ones."""
    existing = client.event_hooks or {}
    req_hooks = list(existing.get("request", [])) + [_on_request]
    resp_hooks = list(existing.get("response", [])) + [_on_response]
    client.event_hooks = {"request": req_hooks, "response": resp_hooks}
