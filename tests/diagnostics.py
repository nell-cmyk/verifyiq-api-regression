"""
Failure diagnostics for API regression tests.

Goal: when an assertion fails, output enough context to classify the failure
(API error vs IAP interception vs network vs fixture) without leaking secrets.
"""
from __future__ import annotations

import httpx
import pytest


def diagnose(resp: httpx.Response, *, fixture_file: str | None = None) -> str:
    """Return a multiline diagnostic block for an httpx.Response.

    Never includes the tenant token value — only presence.
    Body is truncated to keep pytest output readable.
    """
    req = resp.request
    tenant_present = bool(req.headers.get("X-Tenant-Token"))
    auth_present = bool(req.headers.get("Authorization"))
    proxy_auth_present = bool(req.headers.get("Proxy-Authorization"))
    content_type = resp.headers.get("content-type", "<missing>")
    location = resp.headers.get("location")

    body = resp.text or ""
    body_excerpt = body[:400].replace("\n", " ")
    if len(body) > 400:
        body_excerpt += f"... [+{len(body) - 400} chars]"

    hints: list[str] = []
    lowered_body = body[:2000].lower()
    if "<html" in lowered_body or "<!doctype html" in lowered_body:
        hints.append("response body is HTML — likely IAP/proxy interception, not the API")
    if "accounts.google.com" in lowered_body or "iap" in lowered_body:
        hints.append("body references Google auth/IAP — request may be blocked upstream")
    if resp.status_code in (301, 302, 303, 307, 308):
        hints.append(f"redirect to {location!r} — auth proxy may be in front of the API")
    if resp.status_code == 200 and "json" not in content_type.lower():
        hints.append("200 OK but non-JSON content-type — not a real API success")
    if "authorization header required" in lowered_body or "api key" in lowered_body:
        if not auth_present:
            hints.append("app requires Authorization: Bearer <API_KEY> — header missing on this request")
        else:
            hints.append("app rejected Authorization — API_KEY may be wrong, revoked, or for wrong environment")
    if "invalid iap credentials" in lowered_body and not proxy_auth_present:
        hints.append("IAP rejected request — Proxy-Authorization: Bearer <iap_token> missing")

    lines = [
        "",
        "── diagnose ──",
        f"  method:             {req.method}",
        f"  url:                {req.url}",
        f"  Authorization:      {'present' if auth_present else 'MISSING'}",
        f"  Proxy-Authorization:{'present' if proxy_auth_present else 'MISSING'}",
        f"  X-Tenant-Token:     {'present' if tenant_present else 'MISSING'}",
        f"  status:             {resp.status_code}",
        f"  content-type:       {content_type}",
    ]
    if location:
        lines.append(f"  location:           {location}")
    if fixture_file is not None:
        lines.append(f"  fixture:            {fixture_file}")
    lines.append(f"  body[:400]:         {body_excerpt}")
    if hints:
        lines.append("  hints:")
        lines.extend(f"    - {h}" for h in hints)
    lines.append("──────────────")
    return "\n".join(lines)


def _request_failure_block(
    exc: Exception,
    *,
    fixture_file: str | None = None,
    file_type: str | None = None,
    timeout_secs: float | None = None,
    extra_context: str = "",
) -> str:
    request = getattr(exc, "request", None)
    method = getattr(request, "method", "<unknown>")
    url = getattr(request, "url", "<unknown>")

    lines = [
        "",
        "── request failure ──",
        f"  exception:          {type(exc).__name__}",
        f"  method:             {method}",
        f"  url:                {url}",
    ]
    if timeout_secs is not None:
        lines.append(f"  timeout_secs:       {timeout_secs:.0f}")
    if file_type is not None:
        lines.append(f"  fileType:           {file_type}")
    if fixture_file is not None:
        lines.append(f"  fixture:            {fixture_file}")
    lines.append(f"  underlying:         {exc!r}")
    lines.append("──────────────")
    details = "\n".join(lines)
    if extra_context:
        details += extra_context
    return details


def timeout_diagnostics(
    exc: httpx.TimeoutException,
    *,
    context: str,
    timeout_secs: float,
    fixture_file: str | None = None,
    file_type: str | None = None,
    extra_context: str = "",
) -> str:
    return (
        f"{context} timed out after {timeout_secs:.0f}s."
        + _request_failure_block(
            exc,
            fixture_file=fixture_file,
            file_type=file_type,
            timeout_secs=timeout_secs,
            extra_context=extra_context,
        )
    )


def request_error_diagnostics(
    exc: httpx.RequestError,
    *,
    context: str,
    fixture_file: str | None = None,
    file_type: str | None = None,
    extra_context: str = "",
) -> str:
    return (
        f"{context} transport error ({type(exc).__name__})."
        + _request_failure_block(
            exc,
            fixture_file=fixture_file,
            file_type=file_type,
            extra_context=extra_context,
        )
    )


def parse_json_or_fail(
    resp: httpx.Response,
    *,
    context: str,
    fixture_file: str | None = None,
    extra_context: str = "",
) -> dict:
    """Parse JSON defensively so non-JSON responses fail with classifiable output."""
    try:
        return resp.json()
    except ValueError as exc:
        pytest.fail(
            f"{context} was not valid JSON: {exc}"
            + diagnose(resp, fixture_file=fixture_file)
            + extra_context
        )
