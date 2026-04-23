from __future__ import annotations

from collections import Counter
from copy import copy
from pathlib import Path

from openpyxl import Workbook, load_workbook

from tools.reporting.batch_ground_truth.excel import write_workbook
from tools.reporting.batch_ground_truth.models import ExportRow
from tools.reporting.batch_ground_truth.schema import (
    FIXED_METADATA_HEADERS,
    build_success_template_values,
    load_reference_template,
)
from tools.reporting.batch_ground_truth.source import parse_source_workbook
from tools.reporting.batch_ground_truth.workflow import plan_file_types


def _write_source_workbook(path: Path) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "All"
    sheet["A1"] = "QA Fixture Registry — POST /v1/documents/parse & /batch"
    sheet["A2"] = "Source: gs://verifyiq-internal-testing/QA/GroundTruth/"
    sheet["A4"] = "Folder"
    sheet["B4"] = "fileType"
    sheet["C4"] = "gsutil Path"
    sheet["D4"] = "fileType Status"
    sheet["E4"] = "Assignee"
    sheet["F4"] = "Status"

    rows = [
        (
            "Tax",
            "BIRForm2303 || BIRExemptionCertificate",
            "gs://verifyiq-internal-testing/QA/GroundTruth/Tax/example.pdf",
            "⚠ Verify",
            "Thor",
            "Pending",
        ),
        (
            "BankStatement",
            "BankStatement",
            "gs://verifyiq-internal-testing/QA/GroundTruth/BankStatement/example.png.xlsx",
            "✓",
            "Jane",
            "Pending",
        ),
        (
            "Missing",
            "No fileType",
            "gs://verifyiq-internal-testing/QA/GroundTruth/Missing/example.pdf",
            "✓",
            "Alex",
            "Pending",
        ),
    ]
    for row_index, row in enumerate(rows, start=5):
        for column_index, value in enumerate(row, start=1):
            sheet.cell(row_index, column_index, value)

    workbook.save(path)
    return path


def _write_reference_workbook(path: Path) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Payslip"
    headers = [
        "filename",
        "identified_type",
        "parse_success",
        "error",
        "summary_json",
        "raw_response_json",
    ]
    for index, header in enumerate(headers, start=1):
        cell = sheet.cell(1, index, header)
        font = copy(cell.font)
        font.bold = True
        cell.font = font
        sheet.column_dimensions[cell.column_letter].width = 24
    for index in range(1, len(headers) + 1):
        sheet.cell(2, index, None)
    sheet.freeze_panes = "A2"
    workbook.save(path)
    return path


def test_parse_source_workbook_splits_and_keeps_verify_rows(tmp_path):
    source_path = _write_source_workbook(tmp_path / "qa_fixture_registry.xlsx")

    parsed = parse_source_workbook(source_path)

    assert parsed.sheet_name == "All"
    assert len(parsed.fixtures) == 3
    split_types = [fixture.file_type for fixture in parsed.fixtures]
    assert split_types == ["BIRForm2303", "BIRExemptionCertificate", "BankStatement"]

    bir_fixture = parsed.fixtures[0]
    assert bir_fixture.include_in_batch is True
    assert bir_fixture.file_type_status == "⚠ Verify"
    assert bir_fixture.verification_status == "unverified"
    assert bir_fixture.source_file_type == "BIRForm2303 || BIRExemptionCertificate"

    bank_fixture = parsed.fixtures[-1]
    assert bank_fixture.include_in_batch is False
    assert bank_fixture.skip_reason == "unsupported file extension '.xlsx' (supported: PDF, PNG, JPG, JPEG, TIFF, TIF, HEIC, HEIF)"

    assert len(parsed.excluded_rows) == 1
    assert parsed.excluded_rows[0].raw_file_type == "No fileType"
    assert parsed.excluded_rows[0].reason == "excluded_file_type"


def test_plan_file_types_reports_executable_and_skipped_counts(tmp_path):
    source_path = _write_source_workbook(tmp_path / "qa_fixture_registry.xlsx")

    parsed, grouped, plans = plan_file_types(source_workbook=source_path)

    assert len(parsed.fixtures) == 3
    assert sorted(grouped) == ["BIRExemptionCertificate", "BIRForm2303", "BankStatement"]

    plan_by_type = {plan.file_type: plan for plan in plans}
    assert plan_by_type["BIRForm2303"].executable_rows == 1
    assert plan_by_type["BankStatement"].skipped_rows == 1


def test_build_success_template_values_maps_common_and_extra_fields():
    result = {
        "index": 0,
        "ok": True,
        "data": {
            "fileType": "TINID",
            "qualityScore": 91.2,
            "completenessScore": 97,
            "fraudScore": 5.5,
            "timings": {"llm_parsing_ms": {"total_ms": 1234.5}},
            "fraudReport": ["reason-a"],
            "fraudCheckFindings": [
                {"description": "reason-a"},
                {"description": "reason-b"},
            ],
            "metadataFraudReport": {"fraud_score": 2},
            "mathematicalFraudReport": {
                "is_fraudulent": False,
                "visual_fraud_detected": False,
                "visual_fraud_score": 0,
                "total_indicators": 1,
                "high_confidence_count": 0,
            },
            "transactionsOCR": [{"id": 1}],
            "summaryResult": [
                {
                    "document_type": "TINID",
                    "tin": "123-456-789",
                    "pageNumber": 1,
                    "custom_extra_field": "extra",
                }
            ],
            "calculatedFields": [
                {
                    "pageNumber": 1,
                    "calculated.match_score": 88,
                }
            ],
        },
    }

    template_values, extra_values = build_success_template_values(
        source_basename="fixture-name",
        request_file_type="TINID",
        result=result,
    )

    assert template_values["filename"] == "fixture-name"
    assert template_values["identified_type"] == "TINID"
    assert template_values["parse_success"] is True
    assert template_values["quality_score"] == 91.2
    assert template_values["parse_time_ms"] == 1234.5
    assert template_values["transactions_count"] == 1
    assert template_values["fraud_reasons"] == '["reason-a","reason-b"]'
    assert template_values["raw_response_json"].startswith('{"fileType":"TINID"')
    assert extra_values["custom_extra_field"] == "extra"
    assert extra_values["calculated_match_score"] == 88
    assert "document_type" not in extra_values
    assert "pageNumber" not in extra_values


def test_write_workbook_keeps_main_sheet_analyst_facing_and_writes_meta_sheet(tmp_path):
    reference_path = _write_reference_workbook(tmp_path / "reference.xlsx")
    layout = load_reference_template(reference_path)

    success_row = ExportRow(
        metadata={
            "source_row": 10,
            "source_gcs_uri": "gs://bucket/success.pdf",
            "source_file_type": "Payslip",
            "normalized_file_type": "Payslip",
            "request_file_type": "Payslip",
            "source_folder": "Payslip",
            "source_assignee": "Thor",
            "source_workflow_status": "Pending",
            "fixture_status_from_source": "✓",
            "batch_chunk_number": 1,
            "batch_result_index": 0,
            "batch_http_status": 200,
            "batch_result_correlation_id": "corr-1",
            "batch_elapsed_ms": 12.5,
            "ok": True,
            "failure_tag": None,
            "error_type": None,
            "error": None,
            "warning": None,
            "raw_result_json": '{"ok":true}',
            "output_generated_at": "2026-04-23T00:00:00+00:00",
        },
        template_values={
            "filename": "success.pdf",
            "identified_type": "Payslip",
            "parse_success": True,
            "error": None,
            "summary_json": '[{"document_type":"Payslip"}]',
            "raw_response_json": '{"fileType":"Payslip"}',
        },
        extra_values={"custom_field": "custom"},
    )
    failure_row = ExportRow(
        metadata={
            "source_row": 11,
            "source_gcs_uri": "gs://bucket/failure.pdf",
            "source_file_type": "Payslip",
            "normalized_file_type": "Payslip",
            "request_file_type": "Payslip",
            "source_folder": "Payslip",
            "source_assignee": "Thor",
            "source_workflow_status": "Pending",
            "fixture_status_from_source": "⚠ Verify",
            "batch_chunk_number": None,
            "batch_result_index": None,
            "batch_http_status": None,
            "batch_result_correlation_id": None,
            "batch_elapsed_ms": None,
            "ok": False,
            "failure_tag": "unsupported_fixture",
            "error_type": None,
            "error": "unsupported file extension '.xlsx'",
            "warning": None,
            "raw_result_json": None,
            "output_generated_at": "2026-04-23T00:00:00+00:00",
        },
        template_values={
            "filename": "failure.pdf",
            "parse_success": False,
            "error": "unsupported file extension '.xlsx'",
        },
    )

    output_path = tmp_path / "Payslip__batch_ground_truth.xlsx"
    headers = write_workbook(
        file_type="Payslip",
        rows=[success_row, failure_row],
        layout=layout,
        output_path=output_path,
    )

    workbook = load_workbook(output_path, data_only=False)
    sheet = workbook["Payslip"]
    meta_sheet = workbook["_meta"]
    main_headers = [sheet.cell(1, column).value for column in range(1, sheet.max_column + 1)]
    meta_headers = [meta_sheet.cell(1, column).value for column in range(1, meta_sheet.max_column + 1)]

    assert workbook.sheetnames == ["Payslip", "_meta"]
    assert sheet.freeze_panes == "A2"
    assert headers == ["filename", "identified_type", "parse_success", "error", "custom_field"]
    assert main_headers == headers
    assert "source_gcs_uri" not in headers
    assert "raw_result_json" not in headers
    assert Counter(headers)["error"] == 1

    filename_column = headers.index("filename") + 1
    parse_success_column = headers.index("parse_success") + 1
    error_column = headers.index("error") + 1
    assert sheet.cell(2, filename_column).value == "success.pdf"
    assert sheet.cell(3, filename_column).value == "failure.pdf"
    assert sheet.cell(3, parse_success_column).value is False
    assert sheet.cell(3, error_column).value == "unsupported file extension '.xlsx'"
    assert sheet.freeze_panes == "A2"

    assert meta_sheet.freeze_panes == "A2"
    assert meta_headers == list(FIXED_METADATA_HEADERS)
    source_uri_column = meta_headers.index("source_gcs_uri") + 1
    raw_result_column = meta_headers.index("raw_result_json") + 1
    assert meta_sheet.cell(2, source_uri_column).value == "gs://bucket/success.pdf"
    assert meta_sheet.cell(3, source_uri_column).value == "gs://bucket/failure.pdf"
    assert meta_sheet.cell(2, raw_result_column).value == '{"ok":true}'
    assert meta_sheet.cell(3, raw_result_column).value is None
