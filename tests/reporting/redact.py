"""Centralized redaction for report artifacts.

All header/body scrubbing goes through this module so there is exactly one
place to audit for secret leakage.
"""
from __future__ import annotations

from typing import Any, Mapping

REDACTED = "[REDACTED]"

# Case-insensitive header allowlist to scrub. Anything even remotely auth/
# token/cookie related goes here.
_REDACT_HEADERS = frozenset(
    h.lower()
    for h in (
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-tenant-token",
        "x-api-key",
        "x-goog-iap-jwt-assertion",
        "x-goog-authenticated-user-email",
        "x-goog-authenticated-user-id",
    )
)

# Keys inside JSON bodies that look secret-ish. Conservative — only true
# secret names, not user data.
_REDACT_BODY_KEYS = frozenset(
    k.lower()
    for k in (
        "authorization",
        "access_token",
        "refresh_token",
        "id_token",
        "api_key",
        "apikey",
        "tenant_token",
        "password",
        "secret",
        "client_secret",
    )
)

MAX_BODY_BYTES = 64_000


def redact_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    if not headers:
        return {}
    out: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in _REDACT_HEADERS:
            out[k] = REDACTED
        else:
            out[k] = str(v)
    return out


def redact_body(obj: Any) -> Any:
    """Deep-redact secret-looking keys in nested JSON. Leaves other data alone."""
    if isinstance(obj, Mapping):
        return {
            k: (REDACTED if isinstance(k, str) and k.lower() in _REDACT_BODY_KEYS else redact_body(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [redact_body(v) for v in obj]
    return obj


def truncate_text(text: str, limit: int = MAX_BODY_BYTES) -> tuple[str, bool]:
    """Return (possibly-truncated text, truncated flag)."""
    if text is None:
        return "", False
    b = text.encode("utf-8", errors="replace")
    if len(b) <= limit:
        return text, False
    return b[:limit].decode("utf-8", errors="replace"), True
