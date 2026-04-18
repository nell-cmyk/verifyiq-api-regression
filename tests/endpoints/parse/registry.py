"""Loader + canonical selection over the generated /parse fixture registry.

The YAML is produced by `tools/generate_fixture_registry.py` from the QA
spreadsheet. This module is the thin read layer pytest uses to parametrize
multi-fileType coverage. No writes, no mutation, no side effects.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REGISTRY_PATH = Path(__file__).with_name("fixture_registry.yaml")


def load_registry() -> dict[str, Any]:
    """Return the parsed registry document, or an empty shell if missing."""
    if not REGISTRY_PATH.exists():
        return {"fixtures": [], "schema_version": None}
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"fixtures": []}


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
    return canonical
