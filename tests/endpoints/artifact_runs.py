"""Shared helpers for raw-response artifact run folders."""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from pathlib import Path

READABLE_UTC_TIMESTAMP_FORMAT = "%Y-%m-%d-T%H%M%S_%fZ"
_RUN_FOLDER_NAME_CACHE: dict[tuple[str, str], str] = {}
_RUN_FOLDER_LOCK = threading.Lock()


def readable_utc_timestamp() -> str:
    return datetime.now(tz=timezone.utc).strftime(READABLE_UTC_TIMESTAMP_FORMAT)


def default_run_folder_name(prefix: str) -> str:
    return f"{prefix}_{readable_utc_timestamp()}"


def ensure_run_folder_name(
    env: dict[str, str] | None,
    *,
    prefix: str,
    env_var: str,
) -> str:
    source = env if env is not None else os.environ
    existing = source.get(env_var, "").strip()
    if existing:
        return existing

    cache_key = (prefix, env_var)
    with _RUN_FOLDER_LOCK:
        folder_name = _RUN_FOLDER_NAME_CACHE.get(cache_key)
        if folder_name is None:
            folder_name = default_run_folder_name(prefix)
            _RUN_FOLDER_NAME_CACHE[cache_key] = folder_name

    if env is not None:
        env[env_var] = folder_name
    return folder_name


def resolve_run_folder(
    parent_dir: Path,
    *,
    prefix: str,
    env_var: str,
) -> Path:
    folder_name = ensure_run_folder_name(None, prefix=prefix, env_var=env_var)
    run_dir = parent_dir.resolve() / folder_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
