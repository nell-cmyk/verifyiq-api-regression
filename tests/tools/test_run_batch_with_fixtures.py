from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

WRAPPER_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "run_batch_with_fixtures.py"
)


def _load_wrapper_module():
    spec = importlib.util.spec_from_file_location("run_batch_with_fixtures", WRAPPER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_fake_runner(tmp_path: Path, *, exit_code: int = 0) -> Path:
    script_path = tmp_path / "fake_batch_runner.py"
    script_path.write_text(
        "\n".join(
            [
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "print(f\"BATCH_FIXTURES_JSON={os.getenv('BATCH_FIXTURES_JSON', '<unset>')}\")",
                "selection = os.getenv('BATCH_FIXTURES_JSON')",
                "if selection:",
                "    payload = json.loads(Path(selection).read_text(encoding='utf-8'))",
                "    entries = payload.get('fixtures') or payload.get('files') or []",
                "    print(f'SELECTION_COUNT={len(entries)}')",
                f"raise SystemExit({exit_code})",
            ]
        ),
        encoding="utf-8",
    )
    return script_path


def test_wrapper_runs_without_selection_json(tmp_path):
    fake_runner = _write_fake_runner(tmp_path)

    cmd = [
        sys.executable,
        str(WRAPPER_PATH),
        "--",
        sys.executable,
        str(fake_runner),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)

    assert completed.returncode == 0
    assert "Running batch command:" in completed.stdout
    assert "BATCH_FIXTURES_JSON=<unset>" in completed.stdout


def test_wrapper_sets_fixtures_json_env_for_custom_command(tmp_path):
    fake_runner = _write_fake_runner(tmp_path)
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        (
            '{"files": '
            '["gs://verifyiq-internal-testing/QA/GroundTruth/Cross match/'
            'TC02a_Payslip_Abuyan.pdf"]}'
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        str(WRAPPER_PATH),
        "--fixtures-json",
        str(selection_path),
        "--",
        sys.executable,
        str(fake_runner),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)

    assert completed.returncode == 0
    assert f"BATCH_FIXTURES_JSON={selection_path.resolve()}" in completed.stdout


def test_wrapper_reports_skipped_unsupported_fixture_entries(tmp_path):
    fake_runner = _write_fake_runner(tmp_path)
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        (
            '{"files": ['
            '"gs://verifyiq-internal-testing/QA/GroundTruth/Cross match/'
            'TC02a_Payslip_Abuyan.pdf",'
            '"gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/'
            'OCR-Gemini of 1160_Bank statement_PBCOM.png.xlsx"'
            "]}"
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        str(WRAPPER_PATH),
        "--fixtures-json",
        str(selection_path),
        "--",
        sys.executable,
        str(fake_runner),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)

    assert completed.returncode == 0
    assert "Skipped unsupported entries: 1" in completed.stdout
    assert "unsupported file extension '.xlsx'" in completed.stdout


def test_wrapper_rejects_json_with_only_unsupported_entries(tmp_path):
    fake_runner = _write_fake_runner(tmp_path)
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        (
            '{"files": ['
            '"gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/'
            'OCR-Gemini of 1160_Bank statement_PBCOM.png.xlsx"'
            "]}"
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        str(WRAPPER_PATH),
        "--fixtures-json",
        str(selection_path),
        "--",
        sys.executable,
        str(fake_runner),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)

    assert completed.returncode != 0
    assert "No supported fixture entries remained after filtering unsupported formats" in (
        completed.stderr or completed.stdout
    )
    assert "BATCH_FIXTURES_JSON=<unset>" not in completed.stdout


def test_default_pytest_command_targets_happy_path_class():
    wrapper = _load_wrapper_module()

    full_command = wrapper.default_pytest_command()
    happy_path_command = wrapper.default_pytest_command(happy_path_only=True)

    assert "tests/endpoints/batch/test_batch.py" in full_command
    assert "tests/endpoints/batch/test_batch.py::TestBatchHappyPath" in happy_path_command


def test_wrapper_chunks_large_selection_for_custom_command(tmp_path):
    fake_runner = _write_fake_runner(tmp_path)
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        json.dumps(
            {
                "files": [
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/1118_Bank Statement_Philippine National Bank.pdf",
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/1160_Bank statement_PBCOM.pdf",
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/1163_bank statement_MetroBank.pdf",
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/2026_01_21_statement_main.pdf",
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/514296736_1296515868755027_5596990479086624577_n.jpeg",
                ]
            }
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        str(WRAPPER_PATH),
        "--fixtures-json",
        str(selection_path),
        "--",
        sys.executable,
        str(fake_runner),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)

    assert completed.returncode == 0
    assert "Resolved 5 supported registry fixtures" in completed.stdout
    assert completed.stdout.count("BATCH_FIXTURES_JSON=") == 2
    assert "SELECTION_COUNT=4" in completed.stdout
    assert "SELECTION_COUNT=1" in completed.stdout


def test_wrapper_reports_registry_annotated_batch_warnings(tmp_path):
    fake_runner = _write_fake_runner(tmp_path)
    selection_path = tmp_path / "fixtures.json"
    selection_path.write_text(
        json.dumps(
            {
                "files": [
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/MJRL_MV Dela Cruz_Bank Statement (1).pdf",
                    "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/1118_Bank Statement_Philippine National Bank.pdf",
                ]
            }
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        str(WRAPPER_PATH),
        "--fixtures-json",
        str(selection_path),
        "--",
        sys.executable,
        str(fake_runner),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)

    assert completed.returncode == 0
    assert "Registry-annotated batch fixture warnings: 1" in completed.stdout
    assert "DocumentSizeGuardError" in completed.stdout
    assert "SELECTION_COUNT=2" in completed.stdout
