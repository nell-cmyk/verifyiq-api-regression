# Batch Ground-Truth Export

## Purpose
Use this workflow to run live `/v1/documents/batch` coverage across the shared generated fixture registry and generate one Excel workbook per fileType for comparison, review, and future model-improvement work.

The curated Excel workbook remains the human source. Regenerate `tests/fixtures/fixture_registry.yaml` from that workbook before exporting when fixture curation changes. The exporter itself does not mutate the source workbook, generated registry, or reference workbook.

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

Run all feasible fileTypes from the shared generated registry:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx
```

Run one fileType with bounded in-fileType chunk concurrency:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx \
  --file-type Payslip \
  --max-concurrent-chunks 2
```

Run selected fileTypes with bounded fileType and chunk concurrency:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx \
  --file-type Payslip \
  --file-type TIN,ACR \
  --max-concurrent-file-types 2 \
  --max-concurrent-chunks 2
```

Plan only, with no live API calls:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx \
  --plan
```

Optional registry and output overrides:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --fixture-registry /absolute/path/to/fixture_registry.yaml \
  --reference-workbook /absolute/path/to/reference.xlsx \
  --output-dir /absolute/path/to/output-dir \
  --file-type Payslip
```

Optional retry overrides:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx \
  --token-expiry-retries 1 \
  --transient-chunk-retries 1
```

## Fixture Registry Source
- The normal exporter path reads `tests/fixtures/fixture_registry.yaml`.
- `tools/generate_fixture_registry.py` writes that shared registry plus `tests/endpoints/parse/fixture_registry.yaml` as a generated `/parse` compatibility copy.
- `--source-workbook` is retained only as a migration guard and no longer drives normal export execution. To change export inputs, edit the curated workbook or supplemental YAML, run `./.venv/bin/python tools/generate_fixture_registry.py`, then rerun the exporter.

## Concurrency
- `--max-concurrent-file-types` controls how many fileTypes can execute at the same time.
- `--max-concurrent-chunks` controls how many `/documents/batch` chunks can be in flight at once within each fileType.
- Both defaults are `1`, which preserves the original fileType-sequential and chunk-sequential behavior.
- A starting setting for a full export is `--max-concurrent-file-types 2 --max-concurrent-chunks 2`.
- The approximate configured maximum in-flight `/documents/batch` requests is `max_concurrent_file_types * max_concurrent_chunks`; the manifest records this as `effective_max_concurrent_batch_requests`.
- Workbook and manifest writing stay single-threaded after fileType execution returns, and all raw batch response artifacts still land in one shared batch artifact run folder.
- The safe request size limit is unchanged: each batch request still contains at most `4` items.

## Chunk Retries
- The exporter keeps the default fileType and chunk execution model unchanged unless a recoverable chunk-level failure occurs.
- Confirmed IAP/OIDC/JWT token expiry, including `OpenID Connect token expired` and `JWT has expired`, clears the cached IAP token, recreates the HTTP client with a refreshed token, and retries the same chunk once by default.
- `httpx.ReadTimeout` and `httpx.RemoteProtocolError` retry the same chunk once by default. Other request errors are recorded without retry.
- Retry counts are configurable with `--token-expiry-retries` and `--transient-chunk-retries`; both default to `1`, and `0` disables that retry class.
- Application-level row failures from a completed `200` batch response are not retried. Expected fixture/API failures such as `DocumentSizeGuardError` or `MultiAccountDocumentError` and row-level `unusable_result` findings remain row failures for review.
- When token expiry retries are exhausted, rows are recorded with `failure_tag=persistent_token_expired` rather than a generic HTTP/request failure.

## Retry Observability
- The analyst-facing main sheet remains focused on `filename`, `parse_success`, `error`, and mapped fields.
- The `_meta` sheet includes `batch_attempt_count`, `batch_retry_reason`, and `batch_final_attempt_error_type` for retry tracing.
- `manifest.json` records the configured retry counts and a per-fileType `retry_summary` with rows retried, max attempt count, retry reasons, and final retry error types.

## Inclusion And Skipping Rules
- `⚠ Verify` and other non-final status rows are included. Status is preserved in the generated registry and output workbook, and is not used as a batch gate.
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
