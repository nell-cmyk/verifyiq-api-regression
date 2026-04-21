"""Shared JSON input parsing for fixture onboarding and selected execution."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_LIST_KEYS = ("fixtures", "files", "paths", "uris")
_URI_KEYS = ("gcs_uri", "file", "path", "uri")
SUPPORTED_PARSE_EXTENSIONS = (
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".tif",
    ".heic",
    ".heif",
)
_ALLOWED_ENTRY_KEYS = {
    "name",
    "file_type",
    "source_folder",
    "source_file_type",
    "verification_status",
    "enabled",
}


@dataclass(frozen=True)
class SkippedFixtureJsonEntry:
    gcs_uri: str
    reason: str


@dataclass(frozen=True)
class FixtureJsonNormalizationResult:
    entries: list[dict[str, Any]]
    skipped: list[SkippedFixtureJsonEntry]


def _input_error(path: Path, message: str) -> ValueError:
    return ValueError(f"Invalid fixture JSON at {path}: {message}")


def fixture_extension(gcs_uri: str) -> str:
    base = gcs_uri.rsplit("/", 1)[-1].lower()
    if "." not in base:
        return ""
    return "." + base.rsplit(".", 1)[-1]


def unsupported_fixture_reason(gcs_uri: str) -> str | None:
    ext = fixture_extension(gcs_uri)
    if ext in SUPPORTED_PARSE_EXTENSIONS:
        return None

    label = ext or "<none>"
    supported = ", ".join(ext.lstrip(".").upper() for ext in SUPPORTED_PARSE_EXTENSIONS)
    return f"unsupported file extension {label!r} (supported: {supported})"


def infer_source_folder_from_gcs_uri(gcs_uri: str) -> str:
    if not isinstance(gcs_uri, str) or not gcs_uri.startswith("gs://"):
        raise ValueError(f"fixture path must be a gs:// URI, got {gcs_uri!r}")

    remainder = gcs_uri[5:]
    parts = [part for part in remainder.split("/") if part]
    if len(parts) < 2:
        raise ValueError(f"fixture path must include a folder and object name, got {gcs_uri!r}")

    if "GroundTruth" in parts:
        idx = parts.index("GroundTruth")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    if len(parts) >= 3:
        return parts[-2]

    raise ValueError(f"could not infer source folder from {gcs_uri!r}")


def _extract_entries(path: Path, payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in _LIST_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return value
        raise _input_error(path, f"expected one of {_LIST_KEYS}, found keys {sorted(payload)}")
    raise _input_error(path, f"top-level JSON must be a list or object, got {type(payload).__name__}")


def _normalize_entry(path: Path, raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        entry: dict[str, Any] = {"gcs_uri": raw}
    elif isinstance(raw, dict):
        uri_key = next((key for key in _URI_KEYS if isinstance(raw.get(key), str)), None)
        if uri_key is None:
            raise _input_error(path, f"fixture object is missing one of {_URI_KEYS}: {raw!r}")
        entry = {"gcs_uri": raw[uri_key]}
        for key in _ALLOWED_ENTRY_KEYS:
            if key in raw:
                entry[key] = raw[key]
    else:
        raise _input_error(
            path,
            f"fixture entries must be strings or objects, got {type(raw).__name__}",
        )

    gcs_uri = entry["gcs_uri"]
    if not isinstance(gcs_uri, str) or not gcs_uri.startswith("gs://"):
        raise _input_error(path, f"fixture path must be a gs:// URI, got {gcs_uri!r}")

    if "source_folder" not in entry or not entry["source_folder"]:
        entry["source_folder"] = infer_source_folder_from_gcs_uri(gcs_uri)

    for key in ("name", "file_type", "source_folder", "source_file_type", "verification_status"):
        value = entry.get(key)
        if isinstance(value, str):
            entry[key] = value.strip()

    return entry


def normalize_fixture_json_entries(path_like: str | Path) -> FixtureJsonNormalizationResult:
    path = Path(path_like).expanduser().resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise _input_error(path, "file does not exist") from exc
    except OSError as exc:
        raise _input_error(path, f"could not read file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise _input_error(path, f"JSON parse failed: {exc.msg}") from exc
    raw_entries = [_normalize_entry(path, raw) for raw in _extract_entries(path, payload)]

    seen: set[tuple[str, str | None]] = set()
    deduped: list[dict[str, Any]] = []
    for entry in raw_entries:
        key = (entry["gcs_uri"], entry.get("file_type"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)

    entries: list[dict[str, Any]] = []
    skipped: list[SkippedFixtureJsonEntry] = []
    for entry in deduped:
        reason = unsupported_fixture_reason(entry["gcs_uri"])
        if reason is not None:
            skipped.append(SkippedFixtureJsonEntry(gcs_uri=entry["gcs_uri"], reason=reason))
            continue
        entries.append(entry)

    return FixtureJsonNormalizationResult(entries=entries, skipped=skipped)


def load_fixture_json_entries(path_like: str | Path) -> list[dict[str, Any]]:
    return normalize_fixture_json_entries(path_like).entries
