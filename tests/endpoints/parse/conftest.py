"""Local collection gate for the /parse fileType matrix.

The matrix runs one live parse per fileType (slow). It is excluded from default
collection so the protected baseline command
`pytest tests/endpoints/parse/ -v` stays visually unchanged. Opt in explicitly
by pointing pytest at the matrix module with `RUN_PARSE_MATRIX=1` set:

  RUN_PARSE_MATRIX=1 pytest tests/endpoints/parse/test_parse_matrix.py -v

Direct module execution without `RUN_PARSE_MATRIX=1` also fails inside the
matrix module so accidental live collection is blocked even when `collect_ignore`
does not apply.
"""
from __future__ import annotations

import contextvars
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from tests.reporting.redact import (
    MAX_BODY_BYTES,
    redact_body,
    redact_headers,
    truncate_text,
)

collect_ignore: list[str] = []
if os.getenv("RUN_PARSE_MATRIX") != "1":
    collect_ignore.append("test_parse_matrix.py")

_PARSE_ENDPOINT = "/v1/documents/parse"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PARSE_RESPONSES_ROOT = _REPO_ROOT / "reports" / "parse" / "responses"
_CURRENT_PARSE_NODEID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "parse_response_capture_nodeid",
    default=None,
)
_CURRENT_RUN_OUTPUT_DIR: Path | None = None
_ORIGINAL_HTTPX_SEND = None


def parse_response_output_dir() -> Path:
    return _CURRENT_RUN_OUTPUT_DIR or _PARSE_RESPONSES_ROOT


def _run_folder_name(started_at: datetime | None = None) -> str:
    ts = started_at or datetime.now(tz=timezone.utc)
    return ts.strftime("%Y%m%dT%H%M%S_%fZ")


def _current_run_output_dir() -> Path:
    if _CURRENT_RUN_OUTPUT_DIR is None:
        raise RuntimeError("Parse response output directory is not initialized")
    return _CURRENT_RUN_OUTPUT_DIR


def _is_parse_item(nodeid: str | None) -> bool:
    return bool(nodeid) and "tests/endpoints/parse/" in nodeid


def _case_output_path(nodeid: str) -> Path:
    parts = nodeid.split("::")
    label_parts = [Path(parts[0]).stem, *parts[1:]]
    raw_label = "__".join(part for part in label_parts if part)
    safe_label = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_label).strip("._")
    return _current_run_output_dir() / f"{safe_label or 'parse_response'}.json"


def _safe_json(text: str) -> tuple[Any | None, str | None]:
    try:
        return json.loads(text), None
    except Exception:
        return None, text


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _serialize_request(request: httpx.Request | None) -> dict[str, Any]:
    if request is None:
        return {}

    try:
        content = request.content or b""
    except Exception:
        content = b""

    text = content.decode("utf-8", errors="replace") if content else ""
    body_obj, body_text = _safe_json(text) if text else (None, None)
    truncated = False

    if body_obj is not None:
        body_obj = redact_body(body_obj)
    elif body_text is not None:
        body_text, truncated = truncate_text(body_text, MAX_BODY_BYTES)

    payload: dict[str, Any] = {
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "headers": redact_headers(dict(request.headers)),
    }
    if body_obj is not None:
        payload["body_kind"] = "json"
        payload["body"] = body_obj
    elif body_text is not None:
        payload["body_kind"] = "text"
        payload["body_text"] = body_text
        payload["body_truncated"] = truncated
    else:
        payload["body_kind"] = "empty"
    return payload


def _serialize_response(response: httpx.Response) -> dict[str, Any]:
    try:
        response.read()
    except Exception:
        pass

    try:
        text = response.text or ""
    except Exception:
        text = ""

    body_obj, body_text = _safe_json(text) if text else (None, None)
    truncated = False

    if body_obj is not None:
        body_obj = redact_body(body_obj)
    elif body_text is not None:
        body_text, truncated = truncate_text(body_text, MAX_BODY_BYTES)

    payload: dict[str, Any] = {
        "status_code": response.status_code,
        "headers": redact_headers(dict(response.headers)),
    }
    try:
        payload["elapsed_ms"] = round(response.elapsed.total_seconds() * 1000.0, 2)
    except Exception:
        pass

    if body_obj is not None:
        payload["body_kind"] = "json"
        payload["body"] = body_obj
    elif body_text is not None:
        payload["body_kind"] = "text"
        payload["body_text"] = body_text
        payload["body_truncated"] = truncated
    else:
        payload["body_kind"] = "empty"
    return payload


def _write_case_output(
    nodeid: str,
    *,
    request: httpx.Request | None = None,
    response: httpx.Response | None = None,
    exc: Exception | None = None,
    detail: str | None = None,
    source: str,
) -> Path:
    payload: dict[str, Any] = {
        "test_case": nodeid,
        "capture_source": source,
        "captured_at": _iso_now(),
        "request": _serialize_request(request or getattr(response, "request", None)),
    }

    if response is not None:
        payload["result"] = {
            "kind": "response",
            **_serialize_response(response),
        }
    elif exc is not None:
        payload["result"] = {
            "kind": "exception",
            "exception_type": exc.__class__.__name__,
            "message": str(exc),
        }
    else:
        payload["result"] = {
            "kind": "missing",
            "message": detail or (
                "No response or request exception was observed for this test case."
            ),
        }

    out_dir = _current_run_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = _case_output_path(nodeid)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_path


def _capturing_send(self, request: httpx.Request, *args, **kwargs):
    if request.url.path != _PARSE_ENDPOINT:
        return _ORIGINAL_HTTPX_SEND(self, request, *args, **kwargs)

    nodeid = _CURRENT_PARSE_NODEID.get()
    if not _is_parse_item(nodeid):
        return _ORIGINAL_HTTPX_SEND(self, request, *args, **kwargs)

    try:
        response = _ORIGINAL_HTTPX_SEND(self, request, *args, **kwargs)
    except httpx.RequestError as exc:
        _write_case_output(
            nodeid,
            request=request,
            exc=exc,
            source="httpx_send_exception",
        )
        raise

    _write_case_output(
        nodeid,
        request=request,
        response=response,
        source="httpx_send_response",
    )
    return response


def pytest_sessionstart(session):
    global _CURRENT_RUN_OUTPUT_DIR, _ORIGINAL_HTTPX_SEND

    _CURRENT_RUN_OUTPUT_DIR = _PARSE_RESPONSES_ROOT / _run_folder_name()
    _CURRENT_RUN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if _ORIGINAL_HTTPX_SEND is None:
        _ORIGINAL_HTTPX_SEND = httpx.Client.send
        httpx.Client.send = _capturing_send


def pytest_runtest_setup(item):
    _CURRENT_PARSE_NODEID.set(item.nodeid if _is_parse_item(item.nodeid) else None)


def pytest_runtest_call(item):
    _CURRENT_PARSE_NODEID.set(item.nodeid if _is_parse_item(item.nodeid) else None)


def pytest_runtest_teardown(item):
    if not _is_parse_item(item.nodeid):
        _CURRENT_PARSE_NODEID.set(None)
        return

    out_path = _case_output_path(item.nodeid)
    if out_path.exists():
        _CURRENT_PARSE_NODEID.set(None)
        return

    response = getattr(item, "funcargs", {}).get("parse_response")
    if isinstance(response, httpx.Response):
        _write_case_output(
            item.nodeid,
            response=response,
            source="shared_parse_response_fixture",
        )
    else:
        _write_case_output(
            item.nodeid,
            detail=(
                "Pytest completed the case without exposing a response object. "
                "This can happen when a shared fixture fails before the test receives "
                "its cached response."
            ),
            source="pytest_missing_response",
        )

    _CURRENT_PARSE_NODEID.set(None)


def pytest_sessionfinish(session, exitstatus):
    global _CURRENT_RUN_OUTPUT_DIR, _ORIGINAL_HTTPX_SEND

    if _ORIGINAL_HTTPX_SEND is not None:
        httpx.Client.send = _ORIGINAL_HTTPX_SEND
        _ORIGINAL_HTTPX_SEND = None
    _CURRENT_RUN_OUTPUT_DIR = None
