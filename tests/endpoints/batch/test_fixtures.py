from __future__ import annotations

import json

import pytest

from tests.endpoints.batch.fixtures import (
    BATCH_FIXTURES_JSON_ENV_VAR,
    BATCH_SAFE_ITEM_LIMIT,
    DEFAULT_BATCH_FILE_TYPES,
    batch_fixture_context,
    build_batch_request,
    load_batch_fixtures,
    load_default_batch_fixtures,
)
from tests.endpoints.parse.file_types import request_file_type_for
from tests.endpoints.parse.registry import load_canonical_fixtures


def test_load_default_batch_fixtures_uses_expected_registry_types():
    fixtures = load_default_batch_fixtures()

    assert [fixture["file_type"] for fixture in fixtures] == list(DEFAULT_BATCH_FILE_TYPES)


def test_build_batch_request_maps_registry_types_to_request_types():
    fixtures = load_default_batch_fixtures()

    payload = build_batch_request(fixtures)

    assert len(payload["items"]) == BATCH_SAFE_ITEM_LIMIT
    assert payload["pipeline"] == {"use_cache": False}
    assert [item["fileType"] for item in payload["items"]] == [
        request_file_type_for(file_type) for file_type in DEFAULT_BATCH_FILE_TYPES
    ]


def test_load_batch_fixtures_defaults_without_selection_json(monkeypatch):
    monkeypatch.delenv(BATCH_FIXTURES_JSON_ENV_VAR, raising=False)

    fixtures = load_batch_fixtures()

    assert [fixture["file_type"] for fixture in fixtures] == list(DEFAULT_BATCH_FILE_TYPES)


def test_load_batch_fixtures_supports_selected_json_and_preserves_order(tmp_path):
    defaults = load_default_batch_fixtures()
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        json.dumps(
            {
                "files": [
                    defaults[2]["gcs_uri"],
                    defaults[0]["gcs_uri"],
                ]
            }
        ),
        encoding="utf-8",
    )

    fixtures = load_batch_fixtures(selection_json_path=selection_path)

    assert [fixture["name"] for fixture in fixtures] == [
        defaults[2]["name"],
        defaults[0]["name"],
    ]


def test_load_batch_fixtures_reads_selection_from_env(monkeypatch, tmp_path):
    defaults = load_default_batch_fixtures()
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        json.dumps({"files": [defaults[1]["gcs_uri"]]}),
        encoding="utf-8",
    )
    monkeypatch.setenv(BATCH_FIXTURES_JSON_ENV_VAR, str(selection_path))

    fixtures = load_batch_fixtures()

    assert len(fixtures) == 1
    assert fixtures[0]["name"] == defaults[1]["name"]


def test_load_batch_fixtures_rejects_malformed_json(tmp_path):
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text("{", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Invalid fixture JSON"):
        load_batch_fixtures(selection_json_path=selection_path)


def test_load_batch_fixtures_rejects_missing_json_file(tmp_path):
    selection_path = tmp_path / "missing.json"

    with pytest.raises(RuntimeError, match="file does not exist"):
        load_batch_fixtures(selection_json_path=selection_path)


def test_load_batch_fixtures_rejects_all_unsupported_entries(tmp_path):
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        json.dumps(
            {
                "files": [
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/"
                    "OCR-Gemini of 1160_Bank statement_PBCOM.png.xlsx",
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="zero supported entries after filtering unsupported formats",
    ):
        load_batch_fixtures(selection_json_path=selection_path)


def test_load_batch_fixtures_rejects_more_than_safe_limit(tmp_path):
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        json.dumps(
            {
                "files": [
                    fixture["gcs_uri"]
                    for fixture in load_canonical_fixtures()[: BATCH_SAFE_ITEM_LIMIT + 1]
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="supports at most 4 items"):
        load_batch_fixtures(selection_json_path=selection_path)


def test_build_batch_request_rejects_empty_fixture_list():
    with pytest.raises(ValueError, match="at least one fixture"):
        build_batch_request([])


def test_build_batch_request_rejects_more_than_safe_limit():
    fixtures = load_default_batch_fixtures()

    with pytest.raises(ValueError, match="at most 4 fixtures"):
        build_batch_request([*fixtures, fixtures[0]])


def test_batch_fixture_context_includes_registry_and_request_file_types():
    fixtures = load_default_batch_fixtures()

    context = batch_fixture_context(fixtures)

    assert "registry fileType" in context
    assert "request fileType" in context
    assert "TINID" in context
