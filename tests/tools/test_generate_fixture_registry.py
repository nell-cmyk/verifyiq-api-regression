from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "generate_fixture_registry.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_fixture_registry", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_supplemental_fixtures_rejects_unsupported_extensions(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        module,
        "load_supplemental_registry_doc",
        lambda: {
            "fixtures": [
                {
                    "gcs_uri": (
                        "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/"
                        "OCR-Gemini of 1160_Bank statement_PBCOM.png.xlsx"
                    ),
                    "file_type": "BankStatement",
                }
            ]
        },
    )

    with pytest.raises(RuntimeError, match="unsupported 'gcs_uri'"):
        module._load_supplemental_fixtures(
            used_names=set(),
            existing_pairs=set(),
            counts=Counter(),
        )


def test_fixture_metadata_overrides_for_known_batch_guard_error():
    module = _load_module()

    expectations = {
        (
            "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/"
            "MJRL_MV Dela Cruz_Bank Statement (1).pdf"
        ): "Page count (456) exceeds limit (50)",
        (
            "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/"
            "MJRL_MV Dela Cruz_Bank Statement (4).pdf"
        ): "Page count (151) exceeds limit (50)",
    }

    for gcs_uri, expected_fragment in expectations.items():
        override = module.fixture_metadata_overrides_for(
            gcs_uri=gcs_uri,
            file_type="BankStatement",
        )

        assert override["batch_expected_error_type"] == "DocumentSizeGuardError"
        assert expected_fragment in override["batch_expected_error"]
        assert "page-limit warning" in override["batch_expected_warning"]
