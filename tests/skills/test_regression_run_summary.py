from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests.endpoints.parse.file_types import request_file_type_for
from tests.endpoints.parse.registry import load_canonical_fixtures

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "reporting"
    / "render_regression_summary.py"
)


def _fixture_by_type(file_type: str) -> dict:
    fixtures = {
        fixture["file_type"]: fixture for fixture in load_canonical_fixtures()
    }
    return fixtures[file_type]


def _sample_pass_line(file_type: str, percent: int) -> str:
    return (
        "tests/endpoints/parse/test_parse_matrix.py::"
        f"test_parse_fixture_contract[{file_type}] PASSED [{percent:>3}%]"
    )


def _sample_fail_line(file_type: str, percent: int) -> str:
    return (
        "tests/endpoints/parse/test_parse_matrix.py::"
        f"test_parse_fixture_contract[{file_type}] FAILED [{percent:>3}%]"
    )


def _run_summary(
    tmp_path: Path,
    terminal_text: str,
    *,
    mode: str = "draft",
    generated_at: str = "2026-04-19T12:00:00Z",
    command: str = (
        f"{sys.executable} "
        "tools/reporting/run_parse_matrix_with_summary.py"
    ),
) -> tuple[str, str, Path]:
    input_path = tmp_path / "terminal.txt"
    output_path = tmp_path / "summary.md"
    promotion_path = tmp_path / "promotion-candidates.md"
    promotion_path.write_text("# Promotion Candidates\n\n## Entries\n\n", encoding="utf-8")
    input_path.write_text(terminal_text, encoding="utf-8")

    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "--endpoint",
        "parse",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--promotion-candidates-path",
        str(promotion_path),
        "--mode",
        mode,
        "--generated-at",
        generated_at,
        "--command",
        command,
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return completed.stdout, output_path.read_text(encoding="utf-8"), promotion_path


def test_draft_summary_includes_registry_api_and_candidate_suggestions(tmp_path):
    tin_fixture = _fixture_by_type("TIN")
    bank_fixture = _fixture_by_type("BankStatement")

    terminal_text = "\n".join(
        [
            "============================= test session starts =============================",
            "collecting ... collected 2 items",
            _sample_pass_line("TIN", 50),
            _sample_pass_line("BankStatement", 100),
            "============================== 2 passed in 12.34s ==============================",
        ]
    )

    stdout, summary_text, promotion_path = _run_summary(tmp_path, terminal_text, mode="draft")

    assert "Draft mode only" in stdout
    assert "Registry fileType" in summary_text
    assert "Request fileType" in summary_text
    assert "`TIN`" in summary_text
    assert f"`{request_file_type_for('TIN')}`" in summary_text
    assert str(tin_fixture["source_row"]) in summary_text
    assert bank_fixture["name"] in summary_text
    assert "Passed unverified canonicals: TIN." in summary_text
    assert "### Candidate: `2026-04-19 TIN" in summary_text
    assert (
        "Matrix run command: "
        f"`{sys.executable} tools/reporting/run_parse_matrix_with_summary.py`"
        in summary_text
    )
    assert ".codex/skills/regression-run-summary/scripts/run_parse_matrix_with_summary.py" not in summary_text
    assert "Request fileType used: `TINID`" in summary_text
    assert promotion_path.read_text(encoding="utf-8").strip() == "# Promotion Candidates\n\n## Entries"


def test_summary_classifies_timeout_and_proxy_like_failures(tmp_path):
    tin_fixture = _fixture_by_type("TIN")
    acr_fixture = _fixture_by_type("ACR")

    terminal_text = "\n".join(
        [
            "============================= test session starts =============================",
            "collecting ... collected 2 items",
            _sample_fail_line("TIN", 50),
            _sample_fail_line("ACR", 100),
            "",
            "__________________ test_parse_fixture_contract[TIN] ___________________",
            "E   Failed: Matrix parse timed out (ReadTimeout) after 300s.",
            "E     underlying: ReadTimeout('boom')",
            "",
            "__________________ test_parse_fixture_contract[ACR] ___________________",
            "E   Failed:",
            "E   -- diagnose --",
            "E     status:             302",
            "E     body[:400]:         <html>redirect</html>",
            "E     hints:",
            "E       - response body is HTML - likely IAP/proxy interception, not the API",
            "E       - body references Google auth/IAP - request may be blocked upstream",
            "",
            "=========================== short test summary info ===========================",
            "FAILED tests/endpoints/parse/test_parse_matrix.py::test_parse_fixture_contract[TIN]",
            "FAILED tests/endpoints/parse/test_parse_matrix.py::test_parse_fixture_contract[ACR]",
            "============================== 2 failed in 99.99s ==============================",
        ]
    )

    _, summary_text, _ = _run_summary(tmp_path, terminal_text, mode="draft")

    assert "| FAILED | timeout | TIN | TINID |" in summary_text
    assert f"| FAILED | auth-proxy | ACR | {request_file_type_for('ACR')} |" in summary_text
    assert str(tin_fixture["source_row"]) in summary_text
    assert acr_fixture["name"] in summary_text
    assert "Failure classes observed: auth-proxy, timeout." in summary_text


def test_apply_mode_appends_promotion_candidates_only(tmp_path):
    terminal_text = "\n".join(
        [
            "============================= test session starts =============================",
            "collecting ... collected 1 item",
            _sample_pass_line("TIN", 100),
            "============================== 1 passed in 4.56s ==============================",
        ]
    )

    stdout, summary_text, promotion_path = _run_summary(tmp_path, terminal_text, mode="apply")
    promotion_text = promotion_path.read_text(encoding="utf-8")

    assert "Applied 1 promotion candidate entry" in stdout
    assert "### Candidate: `2026-04-19 TIN" in promotion_text
    assert "Registry fileType: `TIN`" in promotion_text
    assert "Request fileType used: `TINID`" in promotion_text
    assert "No passed unverified canonical fixtures" not in summary_text
