# Batch Ground-Truth Export

## Purpose
Use this workflow to run live `/v1/documents/batch` coverage across the local fixture source workbook and generate one Excel workbook per fileType for comparison, review, and future model-improvement work.

It does not mutate the source workbook or the reference workbook.

## Default Output Location
If you do not pass `--output-dir`, the workflow writes to:

```bash
reports/batch_ground_truth/batch_ground_truth_<timestamp>/
```

Each run writes:
- `workbooks/<fileType>__batch_ground_truth.xlsx` with an analyst-facing main sheet and a separate `_meta` traceability sheet
- `manifest.json`

Raw `/documents/batch` response artifacts still land in the normal batch artifact area:

```bash
reports/batch/batch_<timestamp>/
```

## Commands
Run one fileType:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx \
  --file-type Payslip
```

Run selected fileTypes:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx \
  --file-type Payslip \
  --file-type TIN,ACR
```

Run all discovered fileTypes from the source workbook:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx
```

Plan only, with no live API calls:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx \
  --plan
```

Optional source and output overrides:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --source-workbook /absolute/path/to/qa_fixture_registry.xlsx \
  --reference-workbook /absolute/path/to/reference.xlsx \
  --output-dir /absolute/path/to/output-dir \
  --file-type Payslip
```

## Inclusion And Skipping Rules
- `⚠ Verify` and other non-final status rows are included. Status is preserved in the output workbook and is not used as a batch gate.
- Composite source labels such as `BIRForm2303 || BIRExemptionCertificate` are split into one output row per normalized fileType.
- `No fileType` and `Fraud - Skipped` stay out of batch execution and are recorded in the run manifest as excluded source rows.
- Unsupported or malformed fixture paths are not silently dropped. They are surfaced in `manifest.json`, and the affected workbook row is marked failed with empty mapped value columns.

## Failed Rows
- Workbook generation continues even when some fixtures fail.
- Failed rows still appear in the main sheet.
- Main-sheet extracted value columns stay empty for failed rows.
- Main-sheet failure visibility is kept concise through `filename`, `parse_success`, and `error`.
- Full traceability and debug context remain available in the workbook `_meta` sheet, `manifest.json`, and the raw batch response artifacts.
- If an entire fileType fails, that fileType workbook is still generated.

## Heterogeneous Response Shapes
- The workflow keeps the main sheet close to the reference workbook's flat analyst-facing layout.
- Common response fields reuse the reference template columns when they are relevant and populated for the current fileType.
- FileType-specific fields that are not present in the template are appended in deterministic order with cleaner analyst-facing labels.
- Source/debug metadata and raw response context stay out of the main sheet and remain traceable through the workbook `_meta` sheet, `manifest.json`, and the raw batch response artifacts.
