"""Raw /documents/parse response artifact export."""
from __future__ import annotations

import contextvars
import itertools
import json
import os
import re
import threading
from pathlib import Path

import httpx
from tests.endpoints.artifact_runs import readable_utc_timestamp, resolve_run_folder

PARSE_ENDPOINT = "/v1/documents/parse"
PARSE_RESPONSE_ARTIFACT_DIR_ENV_VAR = "PARSE_RESPONSE_ARTIFACT_DIR"
PARSE_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR = "PARSE_RESPONSE_ARTIFACT_RUN_DIR_NAME"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_PARSE_ARTIFACT_DIR = _REPO_ROOT / "reports" / "parse" / "responses"
_CURRENT_PARSE_NODEID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "parse_response_capture_nodeid",
    default=None,
)
_ARTIFACT_SEQUENCE = itertools.count(1)
_ARTIFACT_LOCK = threading.Lock()


def parse_response_artifact_dir() -> Path:
    override = os.getenv(PARSE_RESPONSE_ARTIFACT_DIR_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return _DEFAULT_PARSE_ARTIFACT_DIR


def parse_response_run_dir() -> Path:
    return resolve_run_folder(
        parse_response_artifact_dir(),
        prefix="parse",
        env_var=PARSE_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR,
    )


def is_parse_item(nodeid: str | None) -> bool:
    return bool(nodeid) and "tests/endpoints/parse/" in nodeid


def set_current_parse_nodeid(nodeid: str | None) -> None:
    _CURRENT_PARSE_NODEID.set(nodeid if is_parse_item(nodeid) else None)


def clear_current_parse_nodeid() -> None:
    _CURRENT_PARSE_NODEID.set(None)


def _safe_label(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")


def _artifact_filename(nodeid: str) -> str:
    parts = nodeid.split("::")
    case_id_parts = [Path(parts[0]).stem]
    if len(parts) > 2:
        case_id_parts.extend(parts[1:-1])

    case_id = _safe_label("__".join(part for part in case_id_parts if part)) or "parse"
    description = _safe_label(parts[-1] if parts else "response") or "response"
    stamp = readable_utc_timestamp()
    with _ARTIFACT_LOCK:
        sequence = next(_ARTIFACT_SEQUENCE)
    return f"{case_id}__{description}__{stamp}_{sequence:04d}.json"


def write_parse_response_artifact(response: httpx.Response) -> Path | None:
    nodeid = _CURRENT_PARSE_NODEID.get()
    if not is_parse_item(nodeid) or response.request.url.path != PARSE_ENDPOINT:
        return None

    try:
        response.read()
    except Exception:
        pass

    try:
        text = response.text or ""
    except Exception:
        return None

    if not text:
        return None

    try:
        json.loads(text)
    except Exception:
        return None

    out_dir = parse_response_run_dir()
    out_path = out_dir / _artifact_filename(nodeid)
    out_path.write_text(text, encoding="utf-8")
    return out_path


def _on_parse_response(response: httpx.Response) -> None:
    if response.request.url.path != PARSE_ENDPOINT:
        return
    try:
        write_parse_response_artifact(response)
    except Exception:
        pass


def attach(client: httpx.Client) -> None:
    """Install parse-response export without disturbing existing client hooks."""
    existing = client.event_hooks or {}
    req_hooks = list(existing.get("request", []))
    resp_hooks = list(existing.get("response", []))
    if _on_parse_response not in resp_hooks:
        resp_hooks.append(_on_parse_response)
    client.event_hooks = {"request": req_hooks, "response": resp_hooks}
