from __future__ import annotations

import csv
from pathlib import Path

import tools.reporting.plan_batch_ground_truth_recovery as planner


TRIAGE_HEADERS = [
    "fileType",
    "source_row",
    "source_gcs_uri",
    "request_file_type",
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
                "source_row": "10",
                "source_gcs_uri": "gs://bucket/payslip.pdf",
                "request_file_type": "Payslip",
                "recovery_class": "transient_or_auth_failure",
                "failure_tag": "request_timeout",
                "batch_http_status": "",
            },
            {
                "fileType": "UMID",
                "source_row": "11",
                "source_gcs_uri": "gs://bucket/umid.pdf",
                "request_file_type": "UMID",
                "recovery_class": "rate_limited",
                "failure_tag": "http_429",
                "batch_http_status": "429",
            },
            {
                "fileType": "TINID",
                "source_row": "12",
                "source_gcs_uri": "gs://bucket/tin.pdf",
                "request_file_type": "TINID",
                "recovery_class": "invalid_json_5xx_review",
                "failure_tag": "invalid_json_response",
                "batch_http_status": "503",
            },
            {
                "fileType": "WaterUtilityBillingStatement",
                "source_row": "13",
                "source_gcs_uri": "gs://bucket/water.pdf",
                "request_file_type": "WaterUtilityBillingStatement",
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


def test_planner_row_level_generates_recovery_triage_csv_commands(tmp_path, capsys):
    triage_csv = _write_triage_csv(
        tmp_path / "recovery_triage.csv",
        [
            {
                "fileType": "ArticlesOfIncorporation",
                "source_row": "12",
                "source_gcs_uri": "gs://bucket/articles-12.pdf",
                "request_file_type": "ArticlesOfIncorporation",
                "recovery_class": "transient_or_auth_failure",
                "failure_tag": "request_timeout",
                "batch_http_status": "",
            },
            {
                "fileType": "UMID",
                "source_row": "99",
                "source_gcs_uri": "gs://bucket/umid-back.pdf",
                "request_file_type": "UMID",
                "recovery_class": "transient_or_auth_failure",
                "failure_tag": "invalid_json_response",
                "batch_http_status": "503",
            },
            {
                "fileType": "Payslip",
                "source_row": "100",
                "source_gcs_uri": "gs://bucket/payslip-quality.pdf",
                "request_file_type": "Payslip",
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
            "--row-level",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Recovery command mode: row-level" in captured.out
    assert "Retryable recovery rows: 1" in captured.out
    assert "Row-level recovery filter rows: 1" in captured.out
    assert "Invalid JSON 5xx review-only rows: 1" in captured.out
    assert f"--recovery-triage-csv {triage_csv}" in captured.out
    assert "--file-type ArticlesOfIncorporation" in captured.out
    assert "--file-type UMID" not in captured.out
    assert "--file-type Payslip" not in captured.out

    lines = captured.out.splitlines()
    plan_command = lines[lines.index("Plan command (no live calls):") + 1]
    live_command = lines[lines.index("Live command (operator-run only):") + 1]
    assert "--plan" in plan_command
    assert "--plan" not in live_command


def test_planner_excludes_historical_invalid_json_5xx_transient_rows(tmp_path, capsys):
    triage_csv = _write_triage_csv(
        tmp_path / "recovery_triage.csv",
        [
            {
                "fileType": "UMID",
                "source_row": "12",
                "source_gcs_uri": "gs://bucket/umid.pdf",
                "request_file_type": "UMID",
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
                "source_row": "12",
                "source_gcs_uri": "gs://bucket/articles.pdf",
                "request_file_type": "ArticlesOfIncorporation",
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
                "source_row": "12",
                "source_gcs_uri": "gs://bucket/payslip.pdf",
                "request_file_type": "Payslip",
                "recovery_class": "http_200_no_payload_quality_gate",
                "failure_tag": "http_200_no_payload_quality_gate",
                "batch_http_status": "200",
            },
            {
                "fileType": "TINID",
                "source_row": "13",
                "source_gcs_uri": "gs://bucket/tin.pdf",
                "request_file_type": "TINID",
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


def test_planner_row_level_fails_when_identity_columns_are_missing(tmp_path, capsys):
    triage_csv = _write_triage_csv(
        tmp_path / "recovery_triage.csv",
        [
            {
                "fileType": "Payslip",
                "recovery_class": "transient_or_auth_failure",
                "failure_tag": "request_timeout",
                "batch_http_status": "",
            }
        ],
        fieldnames=["fileType", "recovery_class", "failure_tag", "batch_http_status"],
    )
    reference_workbook = tmp_path / "reference.xlsx"
    reference_workbook.touch()

    exit_code = planner.main(
        [
            "--triage-csv",
            str(triage_csv),
            "--reference-workbook",
            str(reference_workbook),
            "--row-level",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "ERROR: triage CSV is missing required columns" in captured.err
    assert "source_row" in captured.err
    assert "source_gcs_uri" in captured.err
    assert "request_file_type" in captured.err
