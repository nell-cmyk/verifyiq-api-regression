# Endpoint Coverage Inventory

## Purpose
Use this inventory to track practical API automation coverage at the endpoint-group level.

This is intentionally not a path-by-path busywork matrix. The current repo covers a small, high-value subset of the OpenAPI inventory, so the maintainable unit is the endpoint group plus its minimum required categories.

## Current Default-Suite Rule
- Canonical operator path: `./.venv/bin/python tools/run_regression.py`
- Current default live suite: parse-only `protected`
- Current stronger live gate: `./.venv/bin/python tools/run_regression.py --suite full`
- Current opt-in live GET smoke suite: `./.venv/bin/python tools/run_regression.py --suite smoke`
- `smoke` is now real, but it is not a broader current default

## Group Inventory

| Endpoint group | Approx. OpenAPI paths | Current automated coverage | Current categories covered | Minimum required categories | Priority | Onboarding status | Notes / blockers |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `parse` | 1 | Yes | protected live default, happy-path, auth-negative, request validation, selective contract, extended matrix | protected/smoke, contract, auth, negative | Critical | Covered | Current default suite. Success schema in `official-openapi.json` is still too generic; see `docs/knowledge-base/parse/openapi-drift-pilot.md`. |
| `batch` | 1 | Yes | happy-path, selective contract, validation, negative, partial-failure, safe-limit handling | smoke/protected candidate, contract, auth, negative | High | Partially covered | The default batch suite stays green; strict tenant-token auth characterization is quarantined behind `RUN_BATCH_AUTH_CHARACTERIZATION=1` until staging returns confirmed 401/403 rejection. Current repeated opt-in evidence is still blocking: missing `X-Tenant-Token` timed out after 30s, while invalid `X-Tenant-Token` has been observed returning `200` and timing out after 30s on later rerun. See `docs/knowledge-base/batch/auth-negative-blocker.md`. Default live selection is capped at 4 items. |
| `document-processing-adjacent` | 4 | No | none | smoke, contract, negative | High | Not onboarded | `/v1/documents/check-cache`, `/v1/documents/cache`, `/v1/documents/crosscheck`, and `/v1/documents/fraud-status/{job_id}` remain deferred. The fraud-status route is the most natural setup-backed next GET tranche after the no-path smoke slice. |
| `health` | 5 | Yes | opt-in GET smoke (200-only) across the full top-level `/health*` family | smoke, basic contract | Medium | Covered | The top-level health group is now covered through `./.venv/bin/python tools/run_regression.py --suite smoke`. Health-like `/api/v1/applications/health`, `/api/v1/admin/health`, and `/ai-gateway/health/gateway-circuit-breakers` are covered through neighboring groups. |
| `applications-api` | 35 | Yes | opt-in GET smoke on safe no-path health, list, and summary endpoints | smoke, contract, auth, negative | Medium | Partially covered | Covered now: `/api/v1/applications/health`, `/api/v1/applications/`, `/api/v1/applications/documents/pages`, `/api/v1/document-statistics`, and `/api/v1/activities/`. Deferred: path-param application/document detail routes plus canonical `format`-required export paths. Duplicate alias routes are excluded. |
| `monitoring` | 69 | Yes | opt-in GET smoke on safe no-path overview, list, report, export, golden-dataset, ground-truth, and drift endpoints | smoke, contract, auth, negative | Medium | Partially covered | 24 monitoring GET endpoints now return 200 in smoke. Deferred: correlation/doc detail routes, `timeseries/{metric}`, `providers` (422 without additional inputs), and `gcs/structure` (502). |
| `parser-studio` | 43 | Yes | opt-in GET smoke on safe current no-path auth-status, metadata, audit, tenant, and threshold endpoints | smoke, contract, auth, negative | Medium | Partially covered | Covered now: `auth/status` plus current v1 metadata/defaults/audit/tenants/fraud-thresholds routes. Legacy unversioned aliases are excluded. Deferred: current path-param doc-type/version routes. |
| `qa` | 15 | Yes | opt-in GET smoke on safe no-path queue, stats, report, threshold, and export endpoints | smoke, contract, auth, negative | Medium | Partially covered | Covered now: queue, stats, document types, tenants, summary/field-error reports, thresholds, export, and export preview. Deferred: correlation-id request/review routes plus the UI page `/qa`. |
| `admin` | 8 | No | none | isolated smoke only, negative, safety review | Low | Safety-blocked | Admin-style cache GETs are not in smoke yet: `/v1/admin/cache/stats` returned 422 without required `tenant_id`, and `/v1/admin/cache/health` returned 403. Never add this group casually to the default suite. |
| `other-service-surfaces` | 37 | Yes | opt-in GET smoke on selected safe gateway, benchmark, and utility list/health endpoints | explicit scope review first | Low | Partially covered | Covered now: `/ai-gateway/health/gateway-circuit-breakers`, `/api/v1/benchmark/jobs`, and `/api/v1/pii-cleanup/runs`. Deferred: gateway S3 routes, UI/debug routes, and other mixed utility surfaces. |

## Current Coverage Notes
- `official-openapi.json` currently exposes 218 paths.
- The current repo's meaningful live coverage now includes `/v1/documents/parse`, `/v1/documents/batch`, and the opt-in GET smoke lane.
- Parse matrix breadth is opt-in and intentionally limited to one canonical enabled fixture per registry file type.
- Batch coverage reuses registry-backed fixtures and enforces a safe default request size of 4 items.

## GET Smoke Selection Basis
- This repo does not contain the VerifyIQ server/router implementation or product UI/backend source, so there is no in-repo router-registration evidence to inspect directly.
- Current active GET inclusion therefore relies on the repo-native evidence that does exist: maintained smoke tests, the shared authenticated client in `tests/client.py`, current runner/doc command surfaces, live 200 characterization, and current v1 route structure in `official-openapi.json`.
- `official-openapi.json` is a supporting input, not sole truth.
- When a current v1 route and an unversioned or alias route coexist, only the current explicit route is counted in smoke; legacy/duplicate aliases are excluded and documented rather than padded into coverage totals.

## GET Smoke Coverage Implemented Now
Canonical runner path:

```bash
./.venv/bin/python tools/run_regression.py --suite smoke
```

Covered now with status-200 assertions:
- Health and health-like endpoints: `/health`, `/health/live`, `/health/ready`, `/health/detailed`, `/health/startup`, `/api/v1/applications/health`, `/api/v1/admin/health`, `/ai-gateway/health/gateway-circuit-breakers`
- Parser Studio endpoints: `/parser_studio/auth/status`, `/parser_studio/api/v1/document-types`, `/parser_studio/api/v1/pipeline-defaults`, `/parser_studio/api/v1/categories`, `/parser_studio/api/v1/field-types`, `/parser_studio/api/v1/audit-log`, `/parser_studio/api/v1/tenants`, `/parser_studio/api/v1/fraud-thresholds`
- Monitoring endpoints: `/monitoring/api/v1/overview`, `/monitoring/api/v1/requests`, `/monitoring/api/v1/endpoints`, `/monitoring/api/v1/tenants`, `/monitoring/api/v1/document-types`, `/monitoring/api/v1/errors`, `/monitoring/api/v1/fraud`, `/monitoring/api/v1/export`, `/monitoring/api/v1/export/preview`, `/monitoring/api/v1/document-types-list`, `/monitoring/api/v1/golden-dataset`, `/monitoring/api/v1/golden-dataset/stats`, `/monitoring/api/v1/golden-dataset/benchmark/latest`, `/monitoring/api/v1/golden-dataset/benchmark/recent`, `/monitoring/api/v1/golden-dataset/benchmark/stats`, `/monitoring/api/v1/golden-dataset/gcs/types`, `/monitoring/api/v1/audit-logs`, `/monitoring/api/v1/ground-truth/document-types`, `/monitoring/api/v1/ground-truth/review-models`, `/monitoring/api/v1/drift/overview`, `/monitoring/api/v1/drift/events`, `/monitoring/api/v1/drift/settings`, `/monitoring/api/v1/drift/scheduler-status`, `/monitoring/api/v1/drift/suppression-rules`
- QA endpoints: `/qa/api/v1/queue`, `/qa/api/v1/stats`, `/qa/api/v1/document-types`, `/qa/api/v1/tenants`, `/qa/api/v1/reports/summary`, `/qa/api/v1/reports/field-errors`, `/qa/api/v1/thresholds`, `/qa/api/v1/export`, `/qa/api/v1/export/preview`
- BLS API and utility endpoints: `/api/v1/applications/`, `/api/v1/applications/documents/pages`, `/api/v1/document-statistics`, `/api/v1/activities/`, `/api/v1/benchmark/jobs`, `/api/v1/pii-cleanup/runs`

GET endpoints covered only after prerequisite/setup handling in this tranche:
- none

## Deferred GET Endpoints
### Requires query parameters or other request inputs
- `/v1/admin/cache/stats` requires `tenant_id` and returned `422` without it
- `/api/v1/applications/documents/export` requires `format` and returned `422` without it
- `/monitoring/api/v1/providers` returned `422` with the current no-input probe
- `/ai-gateway/s3/s3/list` returned `400`; safe request inputs still need characterization

### Requires path parameters or setup-backed identifiers
- `/v1/documents/fraud-status/{job_id}` requires `job_id`
- `/parser_studio/api/v1/document-types/{doc_type}`, `/parser_studio/api/v1/document-types/{doc_type}/versions`, `/parser_studio/api/v1/document-types/{doc_type}/prompt/versions`, `/parser_studio/api/v1/document-types/{doc_type}/prompt/versions/{version_id}`, and `/parser_studio/api/v1/tenants/{api_key}` require stable parser-studio identifiers
- `/monitoring/api/v1/timeseries/{metric}`, `/monitoring/api/v1/requests/{correlation_id}`, `/monitoring/api/v1/requests/{correlation_id}/retests`, `/monitoring/api/v1/requests/{correlation_id}/document`, `/monitoring/api/v1/requests/{correlation_id}/file`, `/monitoring/api/v1/requests/{correlation_id}/qa-review`, `/monitoring/api/v1/requests/{correlation_id}/fields`, `/monitoring/api/v1/requests/{correlation_id}/golden-status`, `/monitoring/api/v1/golden-dataset/{doc_id}`, `/monitoring/api/v1/golden-dataset/{doc_id}/file`, `/monitoring/api/v1/golden-dataset/gcs/types/{document_type}/variants`, `/monitoring/api/v1/golden-dataset/gcs/types/{document_type}/variants/{variant}/documents`, `/monitoring/api/v1/golden-dataset/gcs/preview/{document_type}/{variant}/{document_id}`, `/monitoring/api/v1/ground-truth/document-schema/{doc_type}`, and `/monitoring/api/v1/drift/trends/{document_type}` require monitoring, golden-dataset, or schema identifiers
- `/qa/api/v1/requests/{correlation_id}` and `/qa/api/v1/reviews/{correlation_id}` require QA review identifiers
- `/api/v1/benchmark/{job_id}/status`, `/api/v1/benchmark/{job_id}/result`, and `/api/v1/benchmark/{job_id}/preview` require benchmark job identifiers
- `/api/v1/applications/{application_id}`, `/api/v1/applications/{application_id}/documents`, `/api/v1/applications/{application_id}/documents/{document_id}/info`, `/api/v1/applications/{application_id}/documents/{document_id}/pages`, `/api/v1/applications/{application_id}/documents/{document_id}/export`, and `/api/v1/activities/document/{document_id}` require application or document identifiers
- `/ai-gateway/s3/s3/download/{file_path}` and `/ai-gateway/s3/s3/presigned-url/{file_path}` require file-path identifiers

### Current auth or behavior blockers
- `/api/v1/health/database-pools` returned `401`
- `/api/v1/health/database-pools/metrics` returned `401`
- `/v1/admin/cache/health` returned `403`
- `/monitoring/api/v1/golden-dataset/gcs/structure` returned `502`

### Explicitly excluded legacy/not-current endpoints
- `/parser_studio/api/categories` and `/parser_studio/api/field-types` are excluded as legacy unversioned aliases of the covered current v1 routes `/parser_studio/api/v1/categories` and `/parser_studio/api/v1/field-types`
- `/parser_studio/api/document-types` and `/parser_studio/api/document-types/{doc_type}` are excluded as legacy unversioned aliases of the current v1 document-type routes
- `/api/v1/documents/pages` is excluded as a duplicate alias of the covered current route `/api/v1/applications/documents/pages`
- `/api/v1/documents/export` is excluded as a duplicate alias of the canonical applications export route `/api/v1/applications/documents/export`
- `/api/v1/{application_id}/documents`, `/api/v1/{application_id}/documents/{document_id}/info`, `/api/v1/{application_id}/documents/{document_id}/pages`, and `/api/v1/{application_id}/documents/{document_id}/export` are excluded as duplicate alias forms of the explicit `/api/v1/applications/{application_id}/...` routes

### UI, debug, or explicit scope/safety deferrals
- `/parser_studio`, `/parser_studio/auth/login`, and `/qa` are UI surfaces rather than API JSON smoke targets
- `/sentry-debug` and `/api/v1/sentry-debug` are explicit debug/error routes and should stay out of smoke

## Sequenced Next Tranches For Remaining GET Work
1. Add required-query or input-backed GET smoke coverage for `/v1/admin/cache/stats`, `/monitoring/api/v1/providers`, `/api/v1/applications/documents/export`, and `/ai-gateway/s3/s3/list` once their safe request inputs are characterized.
2. Add setup-backed detail GET smoke coverage by deriving identifiers from the already-covered list/status endpoints for the deferred path-parameter routes under `document-processing-adjacent`, `parser-studio`, `monitoring`, `qa`, `benchmark`, and `applications-api`.
3. Resolve the current GET auth/behavior blockers before promoting them into smoke: `/api/v1/health/database-pools`, `/api/v1/health/database-pools/metrics`, `/v1/admin/cache/health`, and `/monitoring/api/v1/golden-dataset/gcs/structure`.
4. Decide whether UI/debug and explicit admin/storage surfaces such as `/parser_studio`, `/parser_studio/auth/login`, `/qa`, `/sentry-debug`, `/api/v1/sentry-debug`, and the AI Gateway file routes belong in API automation at all.

## Onboarding Rule For New Endpoint Groups
Before a new endpoint group is added here as "in progress" or "covered", define:

1. Why the endpoint belongs in this repo's scope.
2. Whether the endpoint is safe for live automation.
3. The minimum categories required for first onboarding.
4. Whether the endpoint belongs in the default `protected` suite, a future `smoke` suite, or an opt-in lane only.
5. Which fixtures or live prerequisites the endpoint needs.

## Immediate Follow-ups
- Re-run the opt-in `batch` auth characterization after any auth-layer or staging change; the blocker remains open until both missing and invalid tenant-token requests return confirmed 401/403 rejection.
- Start the next GET tranche with the required-query endpoints that already surface concrete request-shape gaps (`tenant_id`, `format`, provider inputs, and safe AI Gateway list inputs).
- Extend the parse OpenAPI drift pilot with safe observed artifacts from a future protected run.
- Do not broaden the default suite until a deliberate cross-endpoint smoke composition exists.
