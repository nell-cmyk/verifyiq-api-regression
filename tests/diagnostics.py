"""
Failure diagnostics for API regression tests.

Goal: when an assertion fails, output enough context to classify the failure
(API error vs IAP interception vs network vs fixture) without leaking secrets.
"""
from __future__ import annotations

import httpx


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
