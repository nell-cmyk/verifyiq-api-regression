from __future__ import annotations

import csv
from pathlib import Path

import tools.reporting.plan_batch_ground_truth_recovery as planner


TRIAGE_HEADERS = [
    "fileType",
    "recovery_class",
    "failure_tag",
    "batch_http_status",
]


def _write_triage_csv(
    path: Path,
    rows: list[dict[str, str]],
    *,
    fieldnames: list[str] | None = None,
) -> Path:
    headers = fieldnames or TRIAGE_HEADERS
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_planner_generates_commands_for_retryable_file_types_only(tmp_path, capsys):
    triage_csv = _write_triage_csv(
        tmp_path / "recovery_triage.csv",
        [
            {
                "fileType": "Payslip",
                "recovery_class": "transient_or_auth_failure",
                "failure_tag": "request_timeout",
                "batch_http_status": "",
            },
            {
                "fileType": "UMID",
                "recovery_class": "rate_limited",
                "failure_tag": "http_429",
                "batch_http_status": "429",
            },
            {
                "fileType": "TINID",
                "recovery_class": "invalid_json_5xx_review",
                "failure_tag": "invalid_json_response",
                "batch_http_status": "503",
            },
            {
                "fileType": "WaterUtilityBillingStatement",
                "recovery_class": "http_200_no_payload_quality_gate",
                "failure_tag": "http_200_no_payload_quality_gate",
                "batch_http_status": "200",
            },
        ],
    )
    reference_workbook = tmp_path / "reference.xlsx"
    reference_workbook.touch()

    exit_code = planner.main(
        [
            "--triage-csv",
            str(triage_csv),
            "--reference-workbook",
            str(reference_workbook),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert "Total triage rows: 4" in captured.out
    assert "Retryable recovery rows: 2" in captured.out
    assert "Excluded/non-retryable rows: 2" in captured.out
    assert "Invalid JSON 5xx review-only rows: 1" in captured.out
    assert "- transient_or_auth_failure: 1" in captured.out
    assert "- rate_limited: 1" in captured.out
    assert "- Payslip: 1" in captured.out
    assert "- UMID: 1" in captured.out
    assert "--file-type Payslip" in captured.out
    assert "--file-type UMID" in captured.out
    assert "--file-type TINID" not in captured.out
    assert "--file-type WaterUtilityBillingStatement" not in captured.out
    assert "--plan" in captured.out


def test_planner_excludes_historical_invalid_json_5xx_transient_rows(tmp_path, capsys):
    triage_csv = _write_triage_csv(
        tmp_path / "recovery_triage.csv",
        [
            {
                "fileType": "UMID",
                "recovery_class": "transient_or_auth_failure",
                "failure_tag": "invalid_json_response",
                "batch_http_status": "503",
            },
        ],
    )
    reference_workbook = tmp_path / "reference.xlsx"
    reference_workbook.touch()

    exit_code = planner.main(
        [
            "--triage-csv",
            str(triage_csv),
            "--reference-workbook",
            str(reference_workbook),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Retryable recovery rows: 0" in captured.out
    assert "Invalid JSON 5xx review-only rows: 1" in captured.out
    assert "- invalid_json_5xx_review: 1" in captured.out
    assert "No retryable recovery candidates found" in captured.out
    assert "--file-type UMID" not in captured.out


def test_planner_infers_triage_csv_from_run_dir(tmp_path, capsys):
    run_dir = tmp_path / "batch_ground_truth_2026-04-25-T000000_000000Z"
    run_dir.mkdir()
    _write_triage_csv(
        run_dir / "recovery_triage.csv",
        [
            {
                "fileType": "ArticlesOfIncorporation",
                "recovery_class": "transient_or_auth_failure",
                "failure_tag": "request_error",
                "batch_http_status": "",
            },
        ],
    )
    reference_workbook = tmp_path / "reference.xlsx"
    reference_workbook.touch()

    exit_code = planner.main(
        [
            "--run-dir",
            str(run_dir),
            "--reference-workbook",
            str(reference_workbook),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"Triage CSV: {run_dir / 'recovery_triage.csv'}" in captured.out
    assert "--file-type ArticlesOfIncorporation" in captured.out


def test_planner_exits_zero_when_no_retryable_candidates(tmp_path, capsys):
    triage_csv = _write_triage_csv(
        tmp_path / "recovery_triage.csv",
        [
            {
                "fileType": "Payslip",
                "recovery_class": "http_200_no_payload_quality_gate",
                "failure_tag": "http_200_no_payload_quality_gate",
                "batch_http_status": "200",
            },
            {
                "fileType": "TINID",
                "recovery_class": "document_size_guard",
                "failure_tag": "document_size_guard",
                "batch_http_status": "200",
            },
        ],
    )
    reference_workbook = tmp_path / "reference.xlsx"
    reference_workbook.touch()

    exit_code = planner.main(
        [
            "--triage-csv",
            str(triage_csv),
            "--reference-workbook",
            str(reference_workbook),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Retryable recovery rows: 0" in captured.out
    assert "No retryable recovery candidates found" in captured.out
    assert "Plan command" not in captured.out
    assert "Live command" not in captured.out


def test_planner_fails_clearly_when_required_columns_are_missing(tmp_path, capsys):
    triage_csv = _write_triage_csv(
        tmp_path / "recovery_triage.csv",
        [{"fileType": "Payslip", "recovery_class": "transient_or_auth_failure"}],
        fieldnames=["fileType", "recovery_class"],
    )
    reference_workbook = tmp_path / "reference.xlsx"
    reference_workbook.touch()

    exit_code = planner.main(
        [
            "--triage-csv",
            str(triage_csv),
            "--reference-workbook",
            str(reference_workbook),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "ERROR: triage CSV is missing required columns" in captured.err
    assert "failure_tag" in captured.err
    assert "batch_http_status" in captured.err
