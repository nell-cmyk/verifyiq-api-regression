"""Strict loader + canonical selection over the generated /parse fixture registry.

The YAML is produced by `tools/generate_fixture_registry.py` from the curated
fixture sources. This module is the thin read layer pytest uses to parametrize
multi-fileType coverage and opt-in selected-fixture runs. No writes, no
mutation, no side effects.

Canonical policy for now: take the FIRST enabled fixture for each distinct
`file_type` in generated YAML order.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from tests.endpoints.parse.fixture_json import normalize_fixture_json_entries

REGISTRY_PATH = Path(__file__).with_name("fixture_registry.yaml")
REQUIRED_FIXTURE_KEYS = (
    "name",
    "file_type",
    "gcs_uri",
    "source_row",
    "verification_status",
    "enabled",
)


def _registry_error(message: str) -> RuntimeError:
    return RuntimeError(
        f"Invalid /parse fixture registry at {REGISTRY_PATH}: {message}"
    )


def _validate_source_row(source_row: Any) -> bool:
    return isinstance(source_row, int) and not isinstance(source_row, bool)


def _validate_fixture(fixture: Any, *, index: int) -> None:
    if not isinstance(fixture, dict):
        raise _registry_error(f"fixture #{index} must be a mapping, got {type(fixture).__name__}")

    missing = [key for key in REQUIRED_FIXTURE_KEYS if key not in fixture]
    if missing:
        raise _registry_error(f"fixture #{index} is missing required keys: {missing}")

    name = fixture["name"]
    file_type = fixture["file_type"]
    gcs_uri = fixture["gcs_uri"]
    source_row = fixture["source_row"]
    verification_status = fixture["verification_status"]
    enabled = fixture["enabled"]

    if not isinstance(name, str) or not name.strip():
        raise _registry_error(f"fixture #{index} has invalid 'name': {name!r}")
    if file_type is not None and not isinstance(file_type, str):
        raise _registry_error(f"fixture #{index} has invalid 'file_type': {file_type!r}")
    if not isinstance(gcs_uri, str) or not gcs_uri.startswith("gs://"):
        raise _registry_error(f"fixture #{index} has invalid 'gcs_uri': {gcs_uri!r}")
    if not _validate_source_row(source_row):
        raise _registry_error(f"fixture #{index} has invalid 'source_row': {source_row!r}")
    if not isinstance(verification_status, str) or not verification_status.strip():
        raise _registry_error(
            f"fixture #{index} has invalid 'verification_status': {verification_status!r}"
        )
    if not isinstance(enabled, bool):
        raise _registry_error(f"fixture #{index} has invalid 'enabled': {enabled!r}")
    if enabled and (not isinstance(file_type, str) or not file_type.strip()):
        raise _registry_error(
            f"fixture #{index} is enabled but has invalid 'file_type': {file_type!r}"
        )


def load_registry() -> dict[str, Any]:
    """Return the parsed registry document after strict validation."""
    if not REGISTRY_PATH.exists():
        raise _registry_error(
            "registry file is missing. Regenerate it from the spreadsheet with "
            "`python tools/generate_fixture_registry.py`."
        )

    try:
        with REGISTRY_PATH.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise _registry_error(f"YAML parse failed: {exc}") from exc

    if not isinstance(doc, dict):
        raise _registry_error(f"top-level document must be a mapping, got {type(doc).__name__}")

    schema_version = doc.get("schema_version")
    if not _validate_source_row(schema_version):
        raise _registry_error(f"'schema_version' must be an integer, got {schema_version!r}")

    fixtures = doc.get("fixtures")
    if not isinstance(fixtures, list):
        raise _registry_error(f"'fixtures' must be a list, got {type(fixtures).__name__}")

    enabled_count = 0
    for index, fixture in enumerate(fixtures, start=1):
        _validate_fixture(fixture, index=index)
        if fixture["enabled"]:
            enabled_count += 1

    if enabled_count == 0:
        raise _registry_error("registry contains zero enabled fixtures")

    return doc


def load_canonical_fixtures() -> list[dict[str, Any]]:
    """Return one canonical enabled fixture per distinct `file_type`.

    Selection rule: iterate fixtures in YAML order (already sorted by the
    generator on (source_folder, file_type, name)) and take the FIRST enabled
    record encountered for each distinct `file_type`. Deterministic while
    the generator's sort contract holds.
    """
    doc = load_registry()
    seen: set[str] = set()
    canonical: list[dict[str, Any]] = []
    for fixture in doc.get("fixtures", []):
        if not fixture.get("enabled"):
            continue
        file_type = fixture.get("file_type")
        if not file_type or file_type in seen:
            continue
        seen.add(file_type)
        canonical.append(fixture)
    if not canonical:
        raise _registry_error("registry contains zero canonical fixtures after selection")
    return canonical


def fixture_test_id(fixture: dict[str, Any], *, explicit_selection: bool) -> str:
    if explicit_selection:
        return str(fixture["name"])
    return str(fixture["file_type"])


def resolve_selected_registry_fixtures(
    registry_fixtures: list[dict[str, Any]],
    selection_json_path: str | Path,
    *,
    error_factory: Callable[[str], RuntimeError],
) -> list[dict[str, Any]]:
    try:
        normalization = normalize_fixture_json_entries(selection_json_path)
    except ValueError as exc:
        raise error_factory(str(exc)) from exc
    entries = normalization.entries
    if not entries:
        if normalization.skipped:
            raise error_factory(
                "selected fixture JSON resolved to zero supported entries after filtering "
                "unsupported formats"
            )
        raise error_factory("selected fixture JSON resolved to zero fixture entries")

    by_uri: dict[str, list[dict[str, Any]]] = {}
    by_uri_and_type: dict[tuple[str, str], dict[str, Any]] = {}
    for fixture in registry_fixtures:
        gcs_uri = fixture["gcs_uri"]
        by_uri.setdefault(gcs_uri, []).append(fixture)
        file_type = fixture.get("file_type")
        if file_type:
            by_uri_and_type[(gcs_uri, file_type)] = fixture

    selected: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    missing: list[str] = []

    for entry in entries:
        gcs_uri = entry["gcs_uri"]
        explicit_file_type = entry.get("file_type")

        if explicit_file_type:
            fixture = by_uri_and_type.get((gcs_uri, explicit_file_type))
            matches = [fixture] if fixture else []
        else:
            matches = by_uri.get(gcs_uri, [])

        if not matches:
            if explicit_file_type:
                missing.append(f"{gcs_uri} ({explicit_file_type})")
            else:
                missing.append(gcs_uri)
            continue

        for fixture in matches:
            name = str(fixture["name"])
            if name in seen_names:
                continue
            seen_names.add(name)
            selected.append(fixture)

    if missing:
        raise error_factory(
            "selected fixture JSON references paths not present in the registry: "
            + ", ".join(missing)
        )
    if not selected:
        raise error_factory("selected fixture JSON resolved to zero registry fixtures")
    return selected


def load_selected_fixtures(selection_json_path: str | Path) -> list[dict[str, Any]]:
    return resolve_selected_registry_fixtures(
        load_registry().get("fixtures", []),
        selection_json_path,
        error_factory=_registry_error,
    )


def load_matrix_fixtures(*, selection_json_path: str | Path | None = None) -> list[dict[str, Any]]:
    if selection_json_path:
        return load_selected_fixtures(selection_json_path)
    return load_canonical_fixtures()
