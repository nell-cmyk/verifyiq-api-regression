"""Compatibility facade for the shared generated fixture registry.

Historically `/parse` loaded `tests/endpoints/parse/fixture_registry.yaml`
directly. The generated registry now lives at `tests/fixtures/` so `/parse`,
`/documents/batch`, and future endpoint tooling can share one strict loader
and one machine-readable YAML source while keeping the public parse helper API
stable.
"""
from __future__ import annotations

from tests.fixtures.registry import (
    REGISTRY_PATH,
    REQUIRED_FIXTURE_KEYS,
    fixture_test_id,
    load_canonical_fixtures,
    load_matrix_fixtures,
    load_registry,
    load_selected_fixtures,
    resolve_selected_registry_fixtures,
)

__all__ = [
    "REGISTRY_PATH",
    "REQUIRED_FIXTURE_KEYS",
    "fixture_test_id",
    "load_canonical_fixtures",
    "load_matrix_fixtures",
    "load_registry",
    "load_selected_fixtures",
    "resolve_selected_registry_fixtures",
]
