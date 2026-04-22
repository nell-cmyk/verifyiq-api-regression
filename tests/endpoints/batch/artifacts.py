"""Raw /documents/batch response artifact export."""
from __future__ import annotations

import itertools
import json
import os
import threading
from pathlib import Path

import httpx
from tests.endpoints.artifact_runs import readable_utc_timestamp, resolve_run_folder

BATCH_ENDPOINT = "/v1/documents/batch"
BATCH_RESPONSE_ARTIFACT_DIR_ENV_VAR = "BATCH_RESPONSE_ARTIFACT_DIR"
BATCH_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR = "BATCH_RESPONSE_ARTIFACT_RUN_DIR_NAME"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_BATCH_ARTIFACT_DIR = _REPO_ROOT / "reports" / "batch"
_ARTIFACT_SEQUENCE = itertools.count(1)
_ARTIFACT_LOCK = threading.Lock()


def batch_response_artifact_dir() -> Path:
    override = os.getenv(BATCH_RESPONSE_ARTIFACT_DIR_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return _DEFAULT_BATCH_ARTIFACT_DIR


def batch_response_run_dir() -> Path:
    return resolve_run_folder(
        batch_response_artifact_dir(),
        prefix="batch",
        env_var=BATCH_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR,
    )


def _artifact_filename() -> str:
    stamp = readable_utc_timestamp()
    with _ARTIFACT_LOCK:
        sequence = next(_ARTIFACT_SEQUENCE)
    return f"batch_{stamp}_{sequence:04d}.json"


def write_batch_response_artifact(response: httpx.Response) -> Path | None:
    try:
        response.read()
    except Exception:
        pass

    try:
        text = response.text or ""
    except Exception:
        return None

    if not text or response.request.url.path != BATCH_ENDPOINT:
        return None

    try:
        json.loads(text)
    except Exception:
        return None

    out_dir = batch_response_run_dir()
    out_path = out_dir / _artifact_filename()
    out_path.write_text(text, encoding="utf-8")
    return out_path


def _on_batch_response(response: httpx.Response) -> None:
    if response.request.url.path != BATCH_ENDPOINT:
        return
    try:
        write_batch_response_artifact(response)
    except Exception:
        pass


def attach(client: httpx.Client) -> None:
    """Install batch-response export without disturbing existing client hooks."""
    existing = client.event_hooks or {}
    req_hooks = list(existing.get("request", []))
    resp_hooks = list(existing.get("response", []))
    if _on_batch_response not in resp_hooks:
        resp_hooks.append(_on_batch_response)
    client.event_hooks = {"request": req_hooks, "response": resp_hooks}
