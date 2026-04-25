from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.fixtures.registry import load_canonical_fixtures, load_registry


def _write_registry(path, *, fixtures):
    payload = {
        "schema_version": 2,
        "source": "tools/fixture_registry_source/qa_fixture_registry.xlsx",
        "total": len(fixtures),
        "composite_rows_split": 0,
        "counts": {"confirmed": len(fixtures)},
        "fixtures": fixtures,
    }
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _fixture(**overrides):
    value = {
        "name": "fixture",
        "file_type": "Payslip",
        "gcs_uri": "gs://bucket/fixture.pdf",
        "source_folder": "Payslip",
        "source_file_type": "Payslip",
        "source_file_type_status": "✓",
        "source_assignee": "Thor",
        "source_workflow_status": "Pending",
        "source_row": 5,
        "verification_status": "confirmed",
        "enabled": True,
    }
    value.update(overrides)
    return value


def test_shared_registry_loader_validates_schema_and_records(tmp_path):
    registry_path = _write_registry(tmp_path / "fixture_registry.yaml", fixtures=[_fixture()])

    doc = load_registry(registry_path)

    assert doc["schema_version"] == 2
    assert doc["fixtures"][0]["source_file_type_status"] == "✓"
    assert [fixture["name"] for fixture in load_canonical_fixtures(registry_path)] == ["fixture"]


def test_shared_registry_loader_rejects_missing_required_fixture_keys(tmp_path):
    broken = _fixture()
    broken.pop("source_file_type")
    registry_path = _write_registry(tmp_path / "fixture_registry.yaml", fixtures=[broken])

    with pytest.raises(RuntimeError, match="missing required keys"):
        load_registry(registry_path)


def test_checked_in_shared_and_parse_compat_registries_are_identical():
    repo_root = Path(__file__).resolve().parents[2]
    shared_registry = repo_root / "tests" / "fixtures" / "fixture_registry.yaml"
    parse_compat_registry = repo_root / "tests" / "endpoints" / "parse" / "fixture_registry.yaml"

    assert shared_registry.read_bytes() == parse_compat_registry.read_bytes()
