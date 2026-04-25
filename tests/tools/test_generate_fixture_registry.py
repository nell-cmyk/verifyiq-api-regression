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


def test_help_exits_without_generating(monkeypatch, capsys):
    module = _load_module()

    def _should_not_run():
        raise AssertionError("registry generation should not run for --help")

    monkeypatch.setattr(module, "build_registry_document", _should_not_run)

    with pytest.raises(SystemExit) as exc:
        module.main(["--help"])

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "Generate the shared machine-readable fixture registry" in captured.out


def test_load_supplemental_fixtures_rejects_unsupported_extensions(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        module,
        "load_supplemental_registry_doc",
        lambda _path=module.SUPPLEMENTAL_YAML: {
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
        assert "GT exclusion" in override["batch_expected_warning"]
        assert override["gt_extraction_eligible"] is False
        assert override["gt_extraction_skip_reason"] == "document_size_guard"
        assert override["gt_extraction_classification"] == "fixture_too_large"
        assert override["gt_clean_eligible"] is False
        assert override["negative_audit_useful"] is True
        assert override["gt_recovery_action"] == "reduce_fixture"


def test_gt_extraction_override_loader_rejects_duplicate_fixture(tmp_path):
    module = _load_module()
    override_path = tmp_path / "gt_overrides.yaml"
    override_path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "groups:",
                "- metadata:",
                "    gt_extraction_eligible: false",
                "    gt_extraction_skip_reason: document_size_guard",
                "    gt_extraction_classification: fixture_too_large",
                "    gt_clean_eligible: false",
                "    negative_audit_useful: true",
                "    gt_recovery_action: reduce_fixture",
                "  fixtures:",
                "  - gcs_uri: gs://bucket/too-large.pdf",
                "    file_type: Payslip",
                "  - gcs_uri: gs://bucket/too-large.pdf",
                "    file_type: Payslip",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="duplicate fixture override"):
        module.fixture_metadata_overrides_for(
            gcs_uri="gs://bucket/too-large.pdf",
            file_type="Payslip",
            override_yaml=override_path,
        )


def test_write_registry_document_writes_shared_and_parse_compat_copies(tmp_path):
    module = _load_module()
    shared_path = tmp_path / "tests" / "fixtures" / "fixture_registry.yaml"
    parse_path = tmp_path / "tests" / "endpoints" / "parse" / "fixture_registry.yaml"
    doc = {
        "schema_version": module.SCHEMA_VERSION,
        "source": "tools/fixture_registry_source/qa_fixture_registry.xlsx",
        "total": 1,
        "composite_rows_split": 0,
        "counts": {"confirmed": 1},
        "fixtures": [
            {
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
        ],
    }

    module.write_registry_document(doc, output_paths=(shared_path, parse_path))

    shared = shared_path.read_text(encoding="utf-8")
    parse = parse_path.read_text(encoding="utf-8")
    assert shared == parse
    assert "schema_version: 2" in shared
    assert "source_file_type_status: ✓" in shared


def test_generated_registry_preserves_gt_extraction_metadata_in_both_outputs(tmp_path):
    module = _load_module()
    source_path = tmp_path / "source.xlsx"
    from tests.tools.test_export_batch_ground_truth import _write_source_workbook

    _write_source_workbook(source_path)
    shared_path = tmp_path / "tests" / "fixtures" / "fixture_registry.yaml"
    parse_path = tmp_path / "tests" / "endpoints" / "parse" / "fixture_registry.yaml"

    doc = module.build_registry_document(source_xlsx=source_path, supplemental_yaml=None)
    module.write_registry_document(doc, output_paths=(shared_path, parse_path))

    shared = shared_path.read_text(encoding="utf-8")
    parse = parse_path.read_text(encoding="utf-8")
    assert shared == parse
    assert "gt_extraction_eligible: false" in shared
    assert "gt_extraction_skip_reason: document_size_guard" in shared
    assert "gt_extraction_classification: fixture_too_large" in shared
    assert "gt_clean_eligible: false" in shared
    assert "negative_audit_useful: true" in shared
