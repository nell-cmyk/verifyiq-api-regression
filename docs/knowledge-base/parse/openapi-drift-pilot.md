# /parse OpenAPI Drift Pilot

## Purpose
This document is the current safe contract-drift pilot for `/v1/documents/parse`.

It intentionally separates three things:
- what `official-openapi.json` says
- what the current tests assert
- what remains unresolved until fresh safe run artifacts are available

## Evidence Used In This Pass
- `official-openapi.json`
- `tests/endpoints/parse/test_parse.py`
- `tests/endpoints/batch/test_batch.py`
- `tests/endpoints/document_contracts.py`
- `tests/diagnostics.py`
- `tools/reporting/render_regression_summary.py`
- `docs/knowledge-base/parse/triage-patterns.md`

Current blocker:
- No checked-in `reports/` artifacts were present in the working tree during this pass, so the runtime-observed 200 and 422 payload shapes could not be re-compared from saved evidence.

## Current Non-Live Facts
- `official-openapi.json` documents `/v1/documents/parse` and `/v1/documents/batch` `200` responses as generic JSON objects with `additionalProperties: true`.
- Current parse tests assert stronger success behavior than the spec by requiring stable fields such as `fileType`, `documentQuality`, `summaryOCR`, `summaryResult`, and `calculatedFields`.
- Current batch tests assert stronger success behavior than the spec by requiring top-level keys such as `summary`, `results`, `cacheStatistics`, `crosscheckResults`, and `aggregated_gshare_fields`, plus per-item document-result expectations for successful items.
- Safe observed artifacts must come from approved protected, matrix, or batch runs. Do not create new live probes just for this pilot without explicit validation intent.
- Raw artifacts may contain sensitive response data, so drift notes should summarize field shapes and decisions rather than paste raw payloads.

## Intended Contract From OpenAPI

### Request
`ParseRequest` currently declares:
- required: `file`, `fileType`
- `file`: string
- `fileType`: string

### Validation Error
`HTTPValidationError` currently declares:
- top-level `detail`
- `detail` items reference `ValidationError`

### Success Response
The `200` response currently declares only:
- `type: object`
- `additionalProperties: true`

That means the success contract is effectively undocumented beyond "some JSON object".

## Current Test-Backed Behavior Expectations

### Request shape currently exercised by the repo
`tests/endpoints/parse/test_parse.py` and `tests/endpoints/parse/test_parse_matrix.py` send:
- `file`
- `fileType`
- `pipeline.use_cache = false`

### Validation behavior currently asserted
The repo asserts:
- missing `file` -> `422`
- missing `fileType` -> `422`
- empty body -> `422`
- validation body shape includes `detail: [{loc, msg, type}]`

### Success behavior currently asserted
The repo treats the following as required parse success fields:
- `fileType`
- `documentQuality`
- `summaryOCR`
- `summaryResult`
- `calculatedFields`

The repo also treats these as meaningful contract signals:
- response `fileType` should echo the mapped request `fileType`
- `calculatedFields == {"pageNumber": 1}` is a config-missing stub and not valid success output

## Confirmed Drift Or Underspecification

### 1. Request schema is underspecified for current repo-backed usage
Status: confirmed from repo evidence

Reason:
- current tests send `pipeline.use_cache = false`
- `ParseRequest` in `official-openapi.json` only documents `file` and `fileType`

Interpretation:
- either the spec is incomplete for accepted request behavior
- or the repo is depending on an undocumented request field that needs product/spec review

Current action:
- documented here only; no spec edit was made in this pass

### 2. Success schema is too generic for meaningful contract validation
Status: confirmed from repo evidence

Reason:
- current tests and docs assume a stable success shape with several named fields
- the OpenAPI `200` schema is only a generic object with `additionalProperties: true`

Interpretation:
- the spec is currently too weak to support systematic success-schema validation
- the repo's current tests are stronger than the published success contract in some ways and looser in others

Current action:
- documented here only; no spec edit was made in this pass

## Currently Matching Areas

### 1. Required request fields
Status: matches current tests

Evidence:
- `file` and `fileType` are required by `ParseRequest`
- the repo has direct 422 checks for missing `file` and missing `fileType`

### 2. Validation error envelope
Status: broadly aligned

Evidence:
- `HTTPValidationError` exposes `detail`
- the repo asserts `detail` exists, is a list, and includes `loc`, `msg`, and `type` in entries

## Unresolved Until Fresh Safe Artifacts Exist
- the actual observed 200 response field optionality across current protected fixtures
- whether the live 422 payload shape contains any fields beyond the current test assertions
- whether the live service officially accepts `pipeline.use_cache` as part of the intended request contract or merely tolerates it
- whether there are additional success fields that should be documented and asserted systematically

## Safe Next Step
When live env is already configured and a safe protected run is intentionally needed, use:

```bash
./.venv/bin/python tools/run_regression.py
```

Then compare:
- `official-openapi.json`
- fresh raw artifacts under `reports/parse/responses/`
- any structured output under `reports/regression/` when `--report` is enabled intentionally

## Pilot Next-Step Checklist
1. Artifact source: choose an approved protected run or matrix run and record the command, run date, and artifact directory. Use batch artifacts only for the later `/documents/batch` extension.
2. Sensitivity handling: inspect raw artifacts locally, summarize only field presence, type shape, and decision evidence, and avoid storing raw payloads, secrets, credentials, or full response bodies in docs or Mind.
3. Spec-vs-observed comparison: compare `ParseRequest`, `HTTPValidationError`, and the generic parse success schema against current request payloads, validation responses, and representative `200` artifacts.
4. Decision category: classify each mismatch as `spec stale`, `implementation bug`, `test stale`, or `unresolved owner question`.
5. Follow-up action: for accepted drift, update the spec or tests in a separate reviewed pass; for unresolved drift, leave a blocker note with the needed owner/evidence.

## Decision Boundary
- Do not update `official-openapi.json` until fresh safe evidence confirms whether `pipeline` belongs in the intended request contract and what the documented success schema should contain.
- Do not weaken the current parse tests to match the generic success schema; the schema is currently the weaker artifact.
