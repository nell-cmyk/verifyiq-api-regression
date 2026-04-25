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
- `workbooks/<fileType>__batch_ground_truth.xlsx` with the primary GT evidence workbook for every exported source row, including parsed successes, parsed partial/null-field outcomes, fraud/quality-negative parsed outcomes, completed HTTP `200` quality-gated no-extraction outcomes, row-level API failures, unsupported fixtures, and execution failures
- `clean_workbooks/<fileType>__clean_ground_truth.xlsx` with the legacy strict parsed-field-only compatibility subset
- `manifest.json`
- `clean_manifest.json`
- `recovery_triage.json`
- `recovery_triage.csv`

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
  --transient-chunk-retries 1 \
  --rate-limit-retries 1 \
  --rate-limit-backoff-secs 2
```

Plan a targeted recovery rerun from a previous triage CSV, without calling the live API:

```bash
./.venv/bin/python tools/reporting/plan_batch_ground_truth_recovery.py \
  --run-dir reports/batch_ground_truth/batch_ground_truth_<timestamp> \
  --reference-workbook /absolute/path/to/reference.xlsx
```

The recovery planner accepts either `--run-dir` or `--triage-csv`, prints retryable and non-retryable triage counts, and emits both a paste-ready exporter `--plan` command and a live rerun command for only the affected fileTypes. It does not call `/documents/batch`, write report artifacts, or mutate registry metadata.

## Fixture Registry Source
- The normal exporter path reads `tests/fixtures/fixture_registry.yaml`.
- `tools/generate_fixture_registry.py` writes that shared registry plus `tests/endpoints/parse/fixture_registry.yaml` as a generated `/parse` compatibility copy.
- Durable GT extraction exclusions live in `tools/fixture_registry_source/gt_extraction_fixture_overrides.yaml`; edit that source and run `./.venv/bin/python tools/generate_fixture_registry.py` instead of manually editing generated registry YAML.
- Registry inclusion and GT extraction eligibility are separate. A fixture can stay in the broad registry for audit, negative coverage, or replacement planning while carrying `gt_extraction_eligible: false` for batch ground-truth extraction.
- Supported GT extraction skip reasons are `document_size_guard`, `multi_account_document`, `unsupported_fixture`, and `quality_gate_no_payload`. Supported classifications are `fixture_too_large`, `multi_account_fixture`, `unsupported_artifact`, and `fixture_quality_gate_failed`.
- `--source-workbook` is retained only as a migration guard and no longer drives normal export execution. To change export inputs, edit the curated workbook or supplemental YAML, run `./.venv/bin/python tools/generate_fixture_registry.py`, then rerun the exporter.

## Concurrency
- `--max-concurrent-file-types` controls how many fileTypes can execute at the same time.
- `--max-concurrent-chunks` controls how many `/documents/batch` chunks can be in flight at once within each fileType.
- Both defaults are `1`, which preserves the original fileType-sequential and chunk-sequential behavior.
- A starting setting for a full export is `--max-concurrent-file-types 2 --max-concurrent-chunks 2`.
- A full export at `--max-concurrent-file-types 4 --max-concurrent-chunks 4` can create up to 16 in-flight batch requests and may be too aggressive if the service returns a high HTTP `429` rate.
- The approximate configured maximum in-flight `/documents/batch` requests is `max_concurrent_file_types * max_concurrent_chunks`; the manifest records this as `effective_max_concurrent_batch_requests`.
- Workbook and manifest writing stay single-threaded after fileType execution returns, and all raw batch response artifacts still land in one shared batch artifact run folder.
- The safe request size limit is unchanged: each batch request still contains at most `4` items.

## Chunk Retries
- The exporter keeps the default fileType and chunk execution model unchanged unless a recoverable chunk-level failure occurs.
- Confirmed IAP/OIDC/JWT token expiry, including `OpenID Connect token expired` and `JWT has expired`, clears the cached IAP token, recreates the HTTP client with a refreshed token, and retries the same chunk once by default.
- `httpx.ReadTimeout` and `httpx.RemoteProtocolError` retry the same chunk once by default. Other request errors are recorded without retry.
- HTTP `429` means rate limiting or service pressure. The exporter retries the same chunk once by default, respects `Retry-After` when the response provides it, and otherwise uses bounded fallback backoff.
- Retry counts are configurable with `--token-expiry-retries`, `--transient-chunk-retries`, and `--rate-limit-retries`; all default to `1`, and `0` disables that retry class.
- `--rate-limit-backoff-secs` controls the fallback backoff for `429` retries when `Retry-After` is absent. It defaults to `2` seconds.
- Application-level row failures from a completed `200` batch response are not retried. Expected fixture/API failures such as `DocumentSizeGuardError` or `MultiAccountDocumentError` remain row failures for review. HTTP `200` quality-gated no-extraction results remain completed model-behavior evidence in the primary GT workbook even though they are not strict parsed-field successes.
- Invalid JSON returned with HTTP `5xx` is not retried or treated as a retryable transient/auth failure in this GT workflow. It remains a non-clean review row until artifact inspection confirms whether the issue belongs to API behavior, fixture quality, unsupported document side/content, or another cause.
- When token expiry retries are exhausted, rows are recorded with `failure_tag=persistent_token_expired` rather than a generic HTTP/request failure.
- When rate-limit retries are exhausted, rows are recorded with `failure_tag=http_429`, remain excluded from clean GT workbooks, and are triaged as rerun candidates rather than malformed responses.

## Retry Observability
- The analyst-facing main sheet keeps `filename`, `parse_success`, `error`, and mapped fields, and also includes compact GT outcome/status columns such as `gt_outcome_class`, `gt_candidate_status`, source identity, request/response fileType, correlation id, extraction status, and quality-gate evidence.
- The `_meta` sheet includes `batch_attempt_count`, `batch_retry_reason`, and `batch_final_attempt_error_type` for retry tracing.
- `manifest.json` records the configured retry counts, rate-limit backoff setting, and a per-fileType `retry_summary` with rows retried, max attempt count, retry reasons, and final retry error types.

## Inclusion And Skipping Rules
- `⚠ Verify` and other non-final status rows are included. Status is preserved in the generated registry and output workbook, and is not used as a batch gate.
- Composite source labels such as `BIRForm2303 || BIRExemptionCertificate` are split into one output row per normalized fileType.
- `No fileType` and `Fraud - Skipped` stay out of batch execution and are recorded in the run manifest as excluded source rows.
- Unsupported or malformed fixture paths are not silently dropped. They are surfaced in `manifest.json`, and the affected workbook row is marked failed with empty mapped value columns.
- Fixtures tagged with `gt_extraction_eligible: false` are skipped before live `/documents/batch` execution for GT export planning, counted as skipped/non-executable, and written as failed audit rows with explicit GT metadata.
- Skipping GT-ineligible fixtures only affects this GT extraction workflow. It does not delete fixtures, disable registry traceability, or make them unavailable for future negative/audit coverage.

## Failed And Negative Rows
- Workbook generation continues even when some fixtures fail.
- Failed and negative/model-behavior rows still appear in the primary GT workbook main sheet.
- Main-sheet extracted value columns stay empty when the API did not produce mapped parsed fields.
- Main-sheet failure and negative-outcome visibility is kept concise through `filename`, `parse_success`, `error`, and the GT outcome/status columns.
- Full traceability and debug context remain available in the workbook `_meta` sheet, `manifest.json`, `recovery_triage.*`, and the raw batch response artifacts.
- If an entire fileType fails, that fileType workbook is still generated.

## Legacy Strict Parsed-Only Workbooks
- Strict parsed-only workbooks are generated under `clean_workbooks/` for compatibility and include only rows that already mapped a reliable successful parsed payload.
- A row is included in a strict parsed-only workbook only when the exporter has `ok=true`, no `failure_tag`, no `error_type`, no `error`, `parse_success=true`, and a usable `summaryResult[0]` payload.
- Null or blank extracted fields do not remove a row from this legacy subset when the row otherwise has a usable successful parse. Blank values can be genuine extracted empty values.
- Strict parsed-only workbooks exclude unsupported fixtures, row-level API errors, retry-exhausted chunk failures, exhausted HTTP `429` rate-limit rows, expected warning results, quality-gated no-payload results, and malformed or unexpected successful response shapes.
- Excluding a row from the strict parsed-only workbook does not mean it is excluded from the primary GT workbook. Completed quality-gated no-extraction outcomes remain GT-relevant negative/model-behavior evidence in `workbooks/<fileType>__batch_ground_truth.xlsx`.
- `clean_manifest.json` records total selected source rows, strict parsed-only included rows, triaged rows, GT-extraction-excluded rows, counts by fileType, counts by recovery class, counts by ground-truth candidate status, and the paired primary and strict parsed-only workbook paths.

## Recovery Triage Artifacts
- `recovery_triage.json` and `recovery_triage.csv` contain every non-clean exported row.
- Triage rows include source identity, request and response fileType, HTTP and row status, parse success, failure details, retry metadata, GT extraction metadata, parsed-container counts, quality-gate details when available, `recovery_class`, `recovery_action`, and `gt_candidate_status`.
- Use recovery triage to decide whether a row should be targeted for rerun, reviewed for fixture quality, reviewed for fileType/source metadata, replaced, excluded from strict parsed-only compatibility output as-is, or retained as negative API/model-behavior evidence in the primary GT workbook.
- Use `tools/reporting/plan_batch_ground_truth_recovery.py` to turn a previous `recovery_triage.csv` into a conservative fileType-level targeted rerun plan. The planner treats only `transient_or_auth_failure` and `rate_limited` as retryable recovery classes, and it also excludes historical `failure_tag=invalid_json_response` rows with HTTP status `>=500` even if an older triage CSV labeled them as transient/auth failures.
- The exporter does not mutate the source registry, does not bulk-tag fixtures invalid, and does not convert non-clean rows into successful GT rows. Durable exclusions require fixture-registry source metadata followed by registry regeneration.

Common recovery classes:
- `rate_limited`: HTTP `429` rate limiting or service pressure after bounded retry exhaustion. Status: excluded from GT evidence for this run. Action: targeted rerun with lower concurrency or explicit backoff.
- `transient_or_auth_failure`: token expiry, timeout, request transport failure, or selected auth failures. Status: excluded from GT evidence for this run. Action: targeted rerun after retry/token/service recovery.
- `invalid_json_5xx_review`: HTTP `5xx` response whose body could not be parsed as JSON. Status: non-clean review row, not a retryable transient/auth recovery target. Action: inspect raw artifacts before deciding whether this is API behavior, fixture quality, unsupported-side/content, or another cause.
- `document_size_guard`: `DocumentSizeGuardError`. Action: exclude from clean GT as-is, or replace/reduce the fixture if clean GT coverage is still needed.
- `unsupported_fixture`: unsupported extension, missing GCS URI, or malformed GCS URI. Status: excluded from GT evidence because it was not executable as a reliable API input. Action: replace or correct the source artifact.
- `multi_account_document`: `MultiAccountDocumentError`. Action: split or replace if single-account clean GT is needed, otherwise keep outside clean GT as negative coverage.
- `http_200_no_payload_quality_gate`: HTTP `200` and row `ok=true`, but parsed containers are empty and extraction was not attempted because a quality gate failed. Status: included in the primary GT workbook as negative/model-behavior evidence. Action: inspect fixture quality if replacement or remediation is desired.
- `http_200_no_payload_unknown`: HTTP `200` and row `ok=true`, but no usable payload and no clear quality-gate reason. Action: API behavior review before GT use.
- `malformed_or_unexpected_response_shape`: response cannot be mapped and does not match a known no-payload quality-gate pattern. Action: API/exporter schema review.

## HTTP 429 Rate-Limited Rows
- HTTP `429` rows are rate-limit or service-pressure rows, not clean GT candidates and not invalid fixtures.
- If a later same-chunk retry returns a valid HTTP `200` payload, the exporter records the final successful rows normally with `batch_retry_reason=rate_limited`.
- If rate-limit retries are exhausted, the affected rows stay in the primary GT workbook with `failure_tag=http_429`, are excluded from GT evidence for this run, and appear in `recovery_triage.*` with `recovery_class=rate_limited`, `gt_candidate_status=gt_excluded_execution_failure`, and `recovery_action=targeted_rerun_with_lower_concurrency_or_backoff`.
- When a full run has a high `rate_limited` count, do not immediately repeat the same concurrency. Prefer targeted reruns for the affected fileTypes with lower pressure, such as `--max-concurrent-file-types 1 --max-concurrent-chunks 1`, then increase cautiously only after the 429 rate is acceptable.

## HTTP 200 No-Payload Rows
- HTTP `200` and row `ok=true` are completed API outcomes even when they do not contain parsed fields.
- Rows with empty `summaryOCR`, `summaryResult`, `calculatedFields`, and `transactionsOCR`, plus `extractionStatus=not_attempted`, are not strict parsed-field successes, but quality-gated no-extraction outcomes remain useful GT evidence for model and fixture behavior.
- When `documentQuality` or `qualityCheck.issueDescription` shows a quality-gate failure, the row is classified as `http_200_no_payload_quality_gate`.
- These rows are completed row-level API results, so the exporter does not retry them automatically. They remain in the same primary GT workbook with `parse_success=false`, blank mapped field columns, `gt_outcome_class=quality_gated_no_extraction`, and `gt_candidate_status=gt_included_negative_model_behavior`. They may also become strict parsed-field rows later if fixture quality is corrected, the fixture is replaced, or API behavior changes and a targeted rerun produces a usable parsed payload.
- A no-payload quality-gate row is not automatically skipped from future live GT extraction just because it appeared in recovery triage once. Future skipping requires explicit evidence-backed `quality_gate_no_payload` metadata in `tools/fixture_registry_source/gt_extraction_fixture_overrides.yaml`.

## Document Size Guard Rows
- `DocumentSizeGuardError` rows are classified as `document_size_guard`.
- They are not rerun candidates as-is because the API explicitly refused extraction due to a size or page guard.
- Their `gt_candidate_status` is `not_gt_candidate_currently`, and the recovery action is `exclude_from_clean_gt_or_replace_fixture`.
- This is not a generic invalid-fixture tag and does not imply deletion from all automation. These rows may still be useful as negative API guard coverage outside clean GT.
- Evidence-backed size/page guard fixtures should be tagged with `gt_extraction_eligible: false`, `gt_extraction_skip_reason: document_size_guard`, `gt_extraction_classification: fixture_too_large`, and a recovery action such as `reduce_fixture` or `replace_fixture`.

## Multi-Account Rows
- `MultiAccountDocumentError` rows are classified as `multi_account_document`.
- Confirmed multi-account fixtures are unsuitable for clean single-account GT extraction as-is, but they may remain useful as negative coverage or manual-review examples.
- Evidence-backed multi-account fixtures should be tagged with `gt_extraction_eligible: false`, `gt_extraction_skip_reason: multi_account_document`, `gt_extraction_classification: multi_account_fixture`, and `gt_recovery_action: split_fixture`.

## Heterogeneous Response Shapes
- The workflow keeps the main sheet close to the reference workbook's flat analyst-facing layout.
- Common response fields reuse the reference template columns when they are relevant and populated for the current fileType.
- FileType-specific fields that are not present in the template are appended in deterministic order with cleaner analyst-facing labels.
- Source/debug metadata and raw response context stay out of the main sheet and remain traceable through the workbook `_meta` sheet, `manifest.json`, and the raw batch response artifacts.
