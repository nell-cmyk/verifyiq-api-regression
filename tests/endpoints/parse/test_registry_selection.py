from __future__ import annotations

import json

import pytest

from tests.endpoints.parse.fixture_json import normalize_fixture_json_entries
from tests.endpoints.parse.registry import fixture_test_id, load_selected_fixtures


def test_selected_fixtures_preserve_json_order_and_use_fixture_names(tmp_path):
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        json.dumps(
            {
                "files": [
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/1160_Bank statement_PBCOM.pdf",
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/1118_Bank Statement_Philippine National Bank.pdf",
                ]
            }
        ),
        encoding="utf-8",
    )

    fixtures = load_selected_fixtures(selection_path)

    assert [fixture["name"] for fixture in fixtures] == [
        "1160_Bank statement_PBCOM",
        "1118_Bank Statement_Philippine National Bank",
    ]
    assert [
        fixture_test_id(fixture, explicit_selection=True)
        for fixture in fixtures
    ] == [
        "1160_Bank statement_PBCOM",
        "1118_Bank Statement_Philippine National Bank",
    ]


def test_selected_fixtures_expand_composite_registry_rows_for_path_only_entries(tmp_path):
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        json.dumps(
            {
                "files": [
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BIR/2024_10_04_bir_registration_certificate_form_2303.jpeg",
                ]
            }
        ),
        encoding="utf-8",
    )

    fixtures = load_selected_fixtures(selection_path)

    assert [fixture["file_type"] for fixture in fixtures] == [
        "BIRExemptionCertificate",
        "BIRForm2303",
    ]


def test_selected_fixtures_allow_explicit_file_type_filtering(tmp_path):
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        json.dumps(
            {
                "fixtures": [
                    {
                        "gcs_uri": "gs://verifyiq-internal-testing/QA/GroundTruth/BIR/2024_10_04_bir_registration_certificate_form_2303.jpeg",
                        "file_type": "BIRForm2303",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    fixtures = load_selected_fixtures(selection_path)

    assert len(fixtures) == 1
    assert fixtures[0]["file_type"] == "BIRForm2303"
    assert fixtures[0]["name"] == "2024_10_04_bir_registration_certificate_form_2303__BIRForm2303"


def test_selected_fixtures_reject_malformed_json(tmp_path):
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text("{", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Invalid fixture JSON"):
        load_selected_fixtures(selection_path)


def test_normalize_fixture_json_entries_skip_unsupported_extensions(tmp_path):
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        json.dumps(
            {
                "files": [
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/1118_Bank Statement_Philippine National Bank.pdf",
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/OCR-Gemini of 1160_Bank statement_PBCOM.png.xlsx",
                ]
            }
        ),
        encoding="utf-8",
    )

    result = normalize_fixture_json_entries(selection_path)

    assert [entry["gcs_uri"] for entry in result.entries] == [
        "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/1118_Bank Statement_Philippine National Bank.pdf",
    ]
    assert [(item.gcs_uri, item.reason) for item in result.skipped] == [
        (
            "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/"
            "OCR-Gemini of 1160_Bank statement_PBCOM.png.xlsx",
            "unsupported file extension '.xlsx' (supported: PDF, PNG, JPG, JPEG, TIFF, TIF, HEIC, HEIF)",
        )
    ]


def test_selected_fixtures_skip_unsupported_paths_even_if_registry_contains_them(tmp_path):
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        json.dumps(
            {
                "files": [
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/1118_Bank Statement_Philippine National Bank.pdf",
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/OCR-Gemini of 1160_Bank statement_PBCOM.png.xlsx",
                ]
            }
        ),
        encoding="utf-8",
    )

    fixtures = load_selected_fixtures(selection_path)

    assert [fixture["name"] for fixture in fixtures] == [
        "1118_Bank Statement_Philippine National Bank",
    ]


def test_selected_fixtures_reject_all_unsupported_entries(tmp_path):
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
        load_selected_fixtures(selection_path)
