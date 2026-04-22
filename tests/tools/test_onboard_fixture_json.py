from __future__ import annotations

import importlib.util
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "onboard_fixture_json.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("onboard_fixture_json", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_onboard_fixture_json_is_noop_for_existing_registry_paths(tmp_path):
    json_path = tmp_path / "fixtures.json"
    json_path.write_text(
        (
            '{"files": '
            '["gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/'
            '1118_Bank Statement_Philippine National Bank.pdf"]}'
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--json", str(json_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Already present in registry flow: 1" in completed.stdout
    assert "Added to supplemental registry: 0" in completed.stdout
    assert "No source-of-truth changes were required." in completed.stdout


def test_onboard_fixture_json_requires_explicit_file_type_for_unknown_folder(tmp_path):
    json_path = tmp_path / "fixtures.json"
    json_path.write_text(
        (
            '{"files": '
            '["gs://verifyiq-internal-testing/QA/GroundTruth/CompletelyNew/foo.pdf"]}'
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--json", str(json_path)],
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "Could not infer file_type for source folder 'CompletelyNew'" in completed.stderr


def test_onboard_fixture_json_skips_unsupported_entries(tmp_path):
    json_path = tmp_path / "fixtures.json"
    json_path.write_text(
        (
            '{"files": ['
            '"gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/'
            '1118_Bank Statement_Philippine National Bank.pdf",'
            '"gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/'
            'OCR-Gemini of 1160_Bank statement_PBCOM.png.xlsx"'
            "]}"
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--json", str(json_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Entries processed: 2" in completed.stdout
    assert "Skipped unsupported entries: 1" in completed.stdout
    assert "Already present in registry flow: 1" in completed.stdout
    assert "Added to supplemental registry: 0" in completed.stdout
    assert "OCR-Gemini of 1160_Bank statement_PBCOM.png.xlsx" in completed.stdout
    assert "unsupported file extension '.xlsx'" in completed.stdout


def test_onboard_fixture_json_regenerates_when_supplemental_is_ahead_of_generated(
    tmp_path,
    monkeypatch,
):
    module = _load_module()
    json_path = tmp_path / "fixtures.json"
    existing_path = (
        "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/"
        "1118_Bank Statement_Philippine National Bank.pdf"
    )
    stale_path = "gs://verifyiq-internal-testing/QA/GroundTruth/TIN/stale.pdf"
    json_path.write_text(f'{{"files": ["{existing_path}"]}}', encoding="utf-8")

    current_doc = {
        "fixtures": [
            {
                "gcs_uri": existing_path,
                "file_type": "BankStatement",
                "source_folder": "BankStatement",
            }
        ]
    }
    supplemental_doc = {
        "fixtures": [
            {
                "gcs_uri": stale_path,
                "file_type": "TIN",
            }
        ]
    }
    regenerate_calls: list[str] = []

    def fake_load_registry():
        return current_doc

    def fake_regenerate():
        regenerate_calls.append("called")
        current_doc["fixtures"].append(
            {
                "gcs_uri": stale_path,
                "file_type": "TIN",
                "source_folder": "TIN",
            }
        )

    monkeypatch.setattr(
        module,
        "normalize_fixture_json_entries",
        lambda _path: SimpleNamespace(
            entries=[{"gcs_uri": existing_path, "source_folder": "BankStatement"}],
            skipped=[],
        ),
    )
    monkeypatch.setattr(module, "load_registry", fake_load_registry)
    monkeypatch.setattr(module, "_load_supplemental_doc", lambda: supplemental_doc)
    monkeypatch.setattr(module, "_regenerate_registry_or_exit", fake_regenerate)

    exit_code = module.main(["--json", str(json_path)])

    assert exit_code == 0
    assert regenerate_calls == ["called"]
