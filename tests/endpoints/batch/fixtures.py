"""Fixture selection and payload helpers for /documents/batch."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Sequence

from tests.endpoints.parse.file_types import request_file_type_for
from tests.endpoints.parse.registry import (
    load_canonical_fixtures,
    load_registry,
    resolve_selected_registry_fixtures,
)

BATCH_SAFE_ITEM_LIMIT = 4
BATCH_FIXTURES_JSON_ENV_VAR = "BATCH_FIXTURES_JSON"
DEFAULT_BATCH_FILE_TYPES = (
    "Payslip",
    "PhilippineNationalID",
    "TIN",
    "ACR",
)


def _batch_selection_error(message: str) -> RuntimeError:
    return RuntimeError(f"Invalid /batch fixture selection: {message}")


def _canonical_fixture_lookup() -> dict[str, dict[str, Any]]:
    return {
        str(fixture["file_type"]): fixture
        for fixture in load_canonical_fixtures()
        if fixture.get("file_type")
    }


def load_default_batch_fixtures(
    *,
    file_types: Sequence[str] = DEFAULT_BATCH_FILE_TYPES,
) -> list[dict[str, Any]]:
    if not file_types:
        raise RuntimeError("Default /batch fixture selection requires at least one fileType.")

    lookup = _canonical_fixture_lookup()
    missing = [file_type for file_type in file_types if file_type not in lookup]
    if missing:
        raise RuntimeError(
            "Default /batch fixture selection is missing canonical fixtures for: "
            + ", ".join(missing)
        )

    fixtures = [lookup[file_type] for file_type in file_types]
    if len(fixtures) > BATCH_SAFE_ITEM_LIMIT:
        raise RuntimeError(
            f"Default /batch fixture selection exceeds the safe live limit of "
            f"{BATCH_SAFE_ITEM_LIMIT} items."
        )
    return fixtures


def batch_selection_json_path() -> str | None:
    value = os.getenv(BATCH_FIXTURES_JSON_ENV_VAR, "").strip()
    return value or None


def load_selected_batch_fixtures(selection_json_path: str | Path) -> list[dict[str, Any]]:
    selected = resolve_selected_registry_fixtures(
        load_registry().get("fixtures", []),
        selection_json_path,
        error_factory=_batch_selection_error,
    )
    if len(selected) > BATCH_SAFE_ITEM_LIMIT:
        raise _batch_selection_error(
            "selected fixture JSON resolved to "
            f"{len(selected)} fixtures; /documents/batch supports at most "
            f"{BATCH_SAFE_ITEM_LIMIT} items per request."
        )
    return selected


def load_batch_fixtures(
    *,
    selection_json_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    resolved_selection = selection_json_path or batch_selection_json_path()
    if resolved_selection:
        return load_selected_batch_fixtures(resolved_selection)
    return load_default_batch_fixtures()


def build_batch_request(fixtures: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not fixtures:
        raise ValueError("Batch request requires at least one fixture.")
    if len(fixtures) > BATCH_SAFE_ITEM_LIMIT:
        raise ValueError(
            f"Batch request supports at most {BATCH_SAFE_ITEM_LIMIT} fixtures per request."
        )

    items: list[dict[str, str]] = []
    for index, fixture in enumerate(fixtures):
        gcs_uri = fixture.get("gcs_uri")
        registry_file_type = fixture.get("file_type")
        if not isinstance(gcs_uri, str) or not gcs_uri.startswith("gs://"):
            raise ValueError(
                f"Fixture #{index} has invalid 'gcs_uri' for /batch: {gcs_uri!r}"
            )
        if not isinstance(registry_file_type, str) or not registry_file_type.strip():
            raise ValueError(
                f"Fixture #{index} has invalid 'file_type' for /batch: {registry_file_type!r}"
            )
        items.append(
            {
                "file": gcs_uri,
                "fileType": request_file_type_for(registry_file_type),
            }
        )
    return {
        "items": items,
        "pipeline": {"use_cache": False},
    }


def batch_fixture_context(fixtures: Sequence[dict[str, Any]]) -> str:
    lines = ["", "-- batch fixtures --"]
    for index, fixture in enumerate(fixtures):
        registry_file_type = str(fixture.get("file_type", ""))
        lines.append(f"  [{index}] name:              {fixture.get('name')!r}")
        lines.append(f"  [{index}] registry fileType: {registry_file_type!r}")
        lines.append(
            f"  [{index}] request fileType:  {request_file_type_for(registry_file_type)!r}"
        )
        lines.append(f"  [{index}] source_row:        {fixture.get('source_row')}")
        lines.append(f"  [{index}] gcs_uri:           {fixture.get('gcs_uri')!r}")
        if fixture.get("batch_expected_warning"):
            lines.append(f"  [{index}] batch warning:     {fixture.get('batch_expected_warning')!r}")
            lines.append(
                f"  [{index}] expected error:    {fixture.get('batch_expected_error_type')!r} / "
                f"{fixture.get('batch_expected_error')!r}"
            )
    lines.append("-------------------")
    return "\n".join(lines)
