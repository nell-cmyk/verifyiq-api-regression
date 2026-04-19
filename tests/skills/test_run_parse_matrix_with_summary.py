from __future__ import annotations

import subprocess
import sys
from pathlib import Path

WRAPPER_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "reporting"
    / "run_parse_matrix_with_summary.py"
)


def _write_fake_runner(tmp_path: Path, text: str, exit_code: int) -> Path:
    script_path = tmp_path / "fake_runner.py"
    script_path.write_text(
        "\n".join(
            [
                "import sys",
                f"sys.stdout.write({text!r})",
                f"raise SystemExit({exit_code})",
            ]
        ),
        encoding="utf-8",
    )
    return script_path


def _run_wrapper(
    tmp_path: Path,
    fake_runner: Path,
    *,
    mode: str = "draft",
) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
    terminal_output = tmp_path / "latest-terminal.txt"
    summary_output = tmp_path / "latest-summary.md"
    promotion_path = tmp_path / "promotion-candidates.md"
    promotion_path.write_text("# Promotion Candidates\n\n## Entries\n\n", encoding="utf-8")

    cmd = [
        sys.executable,
        str(WRAPPER_PATH),
        "--mode",
        mode,
        "--terminal-output",
        str(terminal_output),
        "--summary-output",
        str(summary_output),
        "--promotion-candidates-path",
        str(promotion_path),
        "--",
        sys.executable,
        str(fake_runner),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    return completed, terminal_output, summary_output, promotion_path


def test_wrapper_runs_command_and_generates_summary(tmp_path):
    fake_runner = _write_fake_runner(
        tmp_path,
        "\n".join(
            [
                "============================= test session starts =============================",
                "collecting ... collected 1 item",
                "tests/endpoints/parse/test_parse_matrix.py::test_parse_fixture_contract[TIN] PASSED [100%]",
                "============================== 1 passed in 4.56s ==============================",
            ]
        ),
        0,
    )

    completed, terminal_output, summary_output, promotion_path = _run_wrapper(tmp_path, fake_runner)

    assert completed.returncode == 0
    assert terminal_output.exists()
    assert summary_output.exists()
    assert "Running matrix command:" in completed.stdout
    assert "PASSED [100%]" in terminal_output.read_text(encoding="utf-8")
    summary_text = summary_output.read_text(encoding="utf-8")
    assert "Registry fileType" in summary_text
    assert "Request fileType" in summary_text
    assert "TINID" in summary_text
    assert ".codex/skills/regression-run-summary/scripts/run_parse_matrix_with_summary.py" not in summary_text
    assert promotion_path.read_text(encoding="utf-8").strip() == "# Promotion Candidates\n\n## Entries"


def test_wrapper_preserves_nonzero_matrix_exit_but_still_writes_summary(tmp_path):
    fake_runner = _write_fake_runner(
        tmp_path,
        "\n".join(
            [
                "============================= test session starts =============================",
                "collecting ... collected 1 item",
                "tests/endpoints/parse/test_parse_matrix.py::test_parse_fixture_contract[ACR] FAILED [100%]",
                "",
                "__________________ test_parse_fixture_contract[ACR] ___________________",
                "E   Failed:",
                "E   -- diagnose --",
                "E     status:             302",
                "E     body[:400]:         <html>redirect</html>",
                "E     hints:",
                "E       - response body is HTML - likely IAP/proxy interception, not the API",
                "=========================== short test summary info ===========================",
                "FAILED tests/endpoints/parse/test_parse_matrix.py::test_parse_fixture_contract[ACR]",
                "============================== 1 failed in 4.56s ==============================",
            ]
        ),
        1,
    )

    completed, terminal_output, summary_output, _ = _run_wrapper(tmp_path, fake_runner)

    assert completed.returncode == 1
    assert terminal_output.exists()
    assert summary_output.exists()
    summary_text = summary_output.read_text(encoding="utf-8")
    assert "auth-proxy" in summary_text
