# /parse OpenAPI Drift Pilot

## Purpose
This document records the safe contract-drift pilot for `POST /v1/documents/parse`.

It separates:
- what `official-openapi.json` says
- what current regression tests assert
- what fresh protected-run artifacts show
- which follow-up changes belong in a later implementation pass

Raw response artifacts may contain sensitive parsed document data. This page stores
only sanitized field names, type shapes, run metadata, and evidence-backed
decisions.

## Fresh Pilot Run
- Run date: 2026-04-26
- Command: `./.venv/bin/python tools/run_regression.py --report`
- Runner mapping: protected `/parse` report, delegated by the canonical runner to `tools/run_parse_with_report.py --tier baseline`
- Exit status: `0`
- Result: `17 passed`, `0 failed`, `0 skipped`, `0 error`
- Duration: `71.69s`
- Endpoint: `/v1/documents/parse`
- fileType exercised: `BankStatement`
- Auth-negative note: missing and invalid tenant-token checks passed through the existing accepted timeout behavior.

Fresh generated artifacts inspected locally:
- Response artifact directory: `reports/parse/responses/parse_2026-04-26-T101220_053927Z/`
- Success artifact: `reports/parse/responses/parse_2026-04-26-T101220_053927Z/test_parse__TestParseHappyPath__test_returns_200__2026-04-26-T101220_055224Z_0001.json`
- Validation artifacts:
  - `reports/parse/responses/parse_2026-04-26-T101220_053927Z/test_parse__TestParseValidation__test_missing_file_returns_422__2026-04-26-T101240_677594Z_0002.json`
  - `reports/parse/responses/parse_2026-04-26-T101220_053927Z/test_parse__TestParseValidation__test_missing_file_type_returns_422__2026-04-26-T101241_023967Z_0003.json`
  - `reports/parse/responses/parse_2026-04-26-T101220_053927Z/test_parse__TestParseValidation__test_empty_body_returns_422__2026-04-26-T101241_364961Z_0004.json`
  - `reports/parse/responses/parse_2026-04-26-T101220_053927Z/test_parse__TestParseValidation__test_422_conforms_to_openapi_schema__2026-04-26-T101241_697550Z_0005.json`
- Structured report metadata: `reports/regression/20260426T101132Z/report.json`
- Structured report markdown: `reports/regression/20260426T101132Z/report.md`

Sensitivity note:
- The generated structured report markdown and raw JSON artifacts are local generated evidence only and must not be committed.
- `report.md` includes request/response details and parsed response content. Use it only for local inspection; do not copy raw bodies or fixture URIs into tracked docs or Mind.

## OpenAPI Contract Snapshot

### Request: `ParseRequest`
`official-openapi.json` declares:
- required: `file`, `fileType`
- `file`: string
- `fileType`: string

It does not declare `pipeline` or `pipeline.use_cache`.

### Success Response: `200`
`official-openapi.json` declares only:
- `type: object`
- `additionalProperties: true`

That means the success response is effectively documented as a generic object.

### Validation Error: `HTTPValidationError`
`official-openapi.json` declares:
- top-level `detail`
- `detail` items reference `ValidationError`
- `ValidationError` requires `loc`, `msg`, and `type`

The validation schema does not set `additionalProperties: false`.

## Current Test-Backed Expectations

### Request
`tests/endpoints/parse/test_parse.py` and related parse fixtures send:
- `file`
- `fileType`
- `pipeline.use_cache = false`

### Success
Current happy-path tests require:
- `fileType`
- `documentQuality`
- `summaryOCR`
- `summaryResult`
- `calculatedFields`

They also require:
- response `fileType` echoes the mapped request `fileType`
- `calculatedFields` is not the known config-missing stub object `{"pageNumber": 1}`

### Validation
Current validation tests require:
- missing `file` returns `422`
- missing `fileType` returns `422`
- empty body returns `422`
- validation body includes `detail` as a list, with `loc`, `msg`, and `type` on entries

## Fresh Observed Shapes

### Success `200` Top-Level Fields
The fresh success artifact had these top-level fields:

`_field_availability`, `_gshare_metadata`, `aggregateSummary`, `aggregatedFields`,
`authenticityScore`, `cacheDetails`, `cacheKey`, `calculatedFields`,
`completenessBreakdown`, `completenessScore`, `documentData`, `documentQuality`,
`extractionStatus`, `fileType`, `fraudCheckFindings`, `fraudReport`, `fraudScore`,
`fraudStatus`, `fromCache`, `gshare_fields`, `mathematicalFraudReport`,
`metadataFraudReport`, `qualityCheck`, `qualityScore`, `summaryOCR`,
`summaryResult`, `timings`, `transactionsOCR`.

Observed shape summary:

| Field | Fresh observed shape |
| --- | --- |
| `fileType` | string |
| `documentQuality` | string |
| `summaryOCR` | array of objects |
| `summaryResult` | array of objects |
| `calculatedFields` | array of objects |
| `transactionsOCR` | array of transaction-like objects |
| `documentData` | object with summary and transaction arrays |
| `qualityCheck` | object |
| `qualityScore` | number |
| `completenessScore` | number |
| `fraudScore` | number |
| `fraudStatus` | string |
| `fromCache` | boolean |
| `cacheDetails` | object |
| `timings` | object |

Fresh assertions relevant to the pilot:
- All current test-required success fields were present.
- Response `fileType` echoed the request fileType used by the protected fixture.
- `calculatedFields` was an array of objects with `pageNumber` plus calculated debit/credit fields.
- `calculatedFields` was not the known config-missing stub object.
- `calculatedFields` was not a singleton list containing only the known stub object.

### Validation `422` Shape
All four fresh validation artifacts had:
- top-level keys: `detail`
- `detail`: array of objects
- first detail entry keys: `input`, `loc`, `msg`, `type`
- `loc`: array
- `msg`: string
- `type`: string

The extra `input` key is compatible with the current OpenAPI validation schema because
the schema does not forbid additional validation-item properties.

## Drift Findings And Decisions

| Area | Evidence | Classification | Decision |
| --- | --- | --- | --- |
| `ParseRequest` omits `pipeline.use_cache` | Current tests always send `pipeline.use_cache=false`; the fresh protected report passed with that request member present. | `spec stale` plus `unresolved owner question` for exact optionality/schema breadth | Treat `pipeline.use_cache` as accepted request behavior that should be documented in a later spec pass. Owner/product review should confirm whether `pipeline` is optional, whether only `use_cache` is public, and what default applies when omitted. |
| `/parse` `200` schema is generic | OpenAPI says generic object; fresh success artifact and current tests show stable named fields. | `spec stale` | Strengthen the OpenAPI success schema in a later implementation pass instead of weakening tests. Start with the stable top-level fields current tests assert, then add conservative type shapes for consistently observed fields. |
| Current success tests are stronger than OpenAPI | Tests require named fields, fileType echo, and calculatedFields non-stub behavior. Fresh artifact satisfied those expectations. | No `test stale` finding | Leave tests unchanged for this audit pass. In a later implementation pass, consider adding narrow type-shape assertions only for fields the repo already treats as contract signals. |
| `HTTPValidationError` envelope | OpenAPI documents `detail` with `loc`, `msg`, and `type`; fresh 422 artifacts match that envelope and include compatible extra `input`. | No confirmed drift | No immediate spec or test change required. A later spec pass may optionally document `input` if the API owners consider it stable, but current tests should not require it yet. |
| `calculatedFields` stub guard | Fresh success artifact had non-stub calculated fields and the current guard passed. | No implementation bug observed | Keep the existing guard. Do not broaden conclusions beyond this protected fixture. |

## Recommendations

### Later `official-openapi.json` update
Recommended in a separate implementation pass:
- Add a conservative optional `pipeline` object to `ParseRequest`, including `use_cache` as a boolean.
- Strengthen the `/v1/documents/parse` `200` response beyond generic object.
- At minimum, document the stable top-level success fields currently asserted by tests: `fileType`, `documentQuality`, `summaryOCR`, `summaryResult`, and `calculatedFields`.
- Prefer conservative type shapes over overfitting to the full protected fixture payload, because the pilot used one protected fixture and not the full matrix.
- Optionally document the extra validation-item `input` field only if API owners confirm it is stable/public.

Do not update `official-openapi.json` in this audit tranche.

### Test update recommendation
Leave current parse tests unchanged in this audit tranche:
- Do not weaken tests to match the generic `200` schema.
- Do not require the extra validation `input` field yet.
- In a later implementation tranche, consider focused type-shape assertions for the already-required success fields after the OpenAPI success schema is updated.

### Follow-up implementation candidates
1. Update `official-openapi.json` for optional `pipeline.use_cache` and a conservative parse success schema.
2. Add or adjust non-live contract tests around the edited OpenAPI shape if the repo has a suitable static validation surface.
3. Consider one focused parse contract validation pass after the spec update, using the canonical runner category mapping rather than matrix/full coverage unless broader live coverage is explicitly approved.

## Pilot Status
Status: fresh `/parse` OpenAPI drift pilot completed for the protected baseline fixture on 2026-04-26.

Remaining unresolved owner questions:
- Is `pipeline.use_cache` an intended public request field or a tolerated internal override?
- Should `pipeline` permit only `use_cache`, or is a broader public pipeline-options object intended?
- Which non-core success fields are stable enough to document beyond the current test-required fields?
- Is validation-item `input` part of the intended public validation-error shape?
