# Endpoint Coverage Inventory

## Purpose
Use this inventory to track practical API automation coverage at the endpoint-group level.

This is intentionally not a path-by-path busywork matrix. The repo is evolving toward broader VerifyIQ multi-endpoint API automation, so the maintainable unit is the endpoint group plus its minimum required categories, safety class, prerequisites, ownership, and suite lane.

## Current Default-Suite Rule
- Canonical operator path: `./.venv/bin/python tools/run_regression.py`
- Current default live suite: parse-only `protected`
- Current stronger live gate: `./.venv/bin/python tools/run_regression.py --suite full`
- Current opt-in live GET smoke suite: `./.venv/bin/python tools/run_regression.py --suite smoke`
- Current opt-in live batch selection: `./.venv/bin/python tools/run_regression.py --endpoint batch`
- Current non-live Automation Hub preview: `./.venv/bin/python tools/run_regression.py --suite extended --dry-run`
- Current approved live Automation Hub health nodes:
  - `./.venv/bin/python tools/run_regression.py --suite extended --hub-node get-smoke.health.core`
  - `./.venv/bin/python tools/run_regression.py --suite extended --hub-node get-smoke.health.ready`
- `smoke` is now real, but it is not a broader current default
- `extended` is the future safe dependency-aware Automation Hub lane; broad live execution remains blocked
- future `workflow` is reserved for controlled mutation/stateful endpoint flows, is blocked by default, and is not implemented
- broad live `--suite extended`, live `--hub-group`, and all non-approved hub nodes remain blocked

## Endpoint Catalog And Data Sources
This inventory is the durable endpoint-group catalog for planning, safety classification, suite assignment, and migration gates. It should stay aligned with current tests, runner mappings, command docs, safe observed evidence, and `official-openapi.json`, but none of those inputs is sufficient by itself.

Data-source policy:
- Repo-owned tests and runner mappings prove current automated behavior.
- `official-openapi.json` is inventory and contract input only. A listed route is not automatically safe to execute, current in staging, non-legacy, artifact-safe, or approved for live coverage.
- The fixture registry is one curated data source for parse, batch, matrix, and approved fixture-backed producers. It is not the universal Automation Hub data layer and should not be forced onto endpoint groups that need list-derived IDs, query parameters, service-side state, or owner-provided setup.
- Live observed evidence can characterize runtime behavior, but owner or maintainer approval is required before promoting it to public contract, default-suite behavior, or broader artifact policy.
- Sensitive dependency values should be modeled as named outputs and inputs with redacted report handling, not copied through raw response-body coupling.

## Group Inventory

| Endpoint group | Approx. OpenAPI paths | Current automated coverage | Current categories covered | Minimum required categories | Priority | Onboarding status | Notes / blockers |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `parse` | 1 | Yes | protected live default, happy-path, auth-negative, request validation, selective contract, extended matrix | protected/smoke, contract, auth, negative | Critical | Covered | Current default suite. `official-openapi.json` now documents optional `pipeline.use_cache` and a conservative success schema for the fields asserted by protected parse tests; see `docs/knowledge-base/parse/openapi-drift-pilot.md`. |
| `batch` | 1 | Yes | happy-path, selective contract, validation, negative, partial-failure, safe-limit handling | smoke/protected candidate, contract, auth, negative | High | Partially covered | The default batch suite stays green; strict tenant-token auth characterization is quarantined behind `RUN_BATCH_AUTH_CHARACTERIZATION=1` until staging returns confirmed 401/403 rejection. Current repeated opt-in evidence is still blocking: missing `X-Tenant-Token` timed out after 30s, while invalid `X-Tenant-Token` has been observed returning `200` and timing out after 30s on later rerun. See `docs/knowledge-base/batch/auth-negative-blocker.md`. Default live selection is capped at 4 items. |
| `document-processing-adjacent` | 4 | Partial | maintainer-accepted provisional GET smoke for fraud-status, bounded async parse setup, invalid/not-found negative checks | smoke, contract, negative | High | Partially covered/provisional | First expansion tranche is `GET /v1/documents/fraud-status/{job_id}` as a setup-backed, read-only fraud-detection status check in the opt-in GET smoke lane. External API source evidence identifies strict fraud job-id format, tenant-scoped lookup, status response shapes, equivalent `404` behavior for malformed/nonexistent/expired/wrong-tenant jobs, and the hidden/internal async fraud parse path as the likely producer. Observed in bounded staging characterization on 2026-04-27, the async parse producer returned a format-valid fraud job ID, bounded polling reached `complete`, and invalid-format plus artificial valid nonexistent job IDs returned `404`. Maintainer acceptance on 2026-04-28 allows provisional smoke coverage only; this is not owner-confirmed product contract. Current top-level observed-runtime OpenAPI alignment covers only `fraudJobId`, `fraudStatus`, and `404`; continue characterization from safe evidence without waiting for owner confirmation, but do not promote beyond provisional, add strict deep schemas, change artifact policy, or move into protected/default suites until setup prerequisites, behavior stability, and artifact policy are owner-confirmed. `/v1/documents/check-cache`, `/v1/documents/crosscheck`, and mutating `/v1/documents/cache` remain deferred pending request-shape, fixture, artifact, and owner review. |
| `health` | 5 | Yes | opt-in GET smoke on top-level `/health*` 200 routes plus exact-status checks for known admin-key surfaces; approved hub nodes `get-smoke.health.core` for `GET /health` and `get-smoke.health.ready` for `GET /health/ready` only | smoke, basic contract | Medium | Covered | The top-level health group is covered through `./.venv/bin/python tools/run_regression.py --suite smoke`, and the live-capable Automation Hub health tranche is limited to explicit `--hub-node get-smoke.health.core` or `--hub-node get-smoke.health.ready` selectors. Health-like `/api/v1/applications/health`, `/api/v1/admin/health`, and `/ai-gateway/health/gateway-circuit-breakers` are covered through neighboring groups but remain outside approved live hub execution. `/health/live`, `/health/detailed`, and `/health/startup` remain outside the approved live hub nodes. `/api/v1/health/database-pools` and `/api/v1/health/database-pools/metrics` are codified in smoke as expected `401` responses rather than treated as unresolved 200 targets. |
| `applications-api` | 41 | Yes | opt-in GET smoke on safe no-path, query-backed, and setup-backed detail endpoints | smoke, contract, auth, negative | Medium | Covered | Covered now: `/api/v1/applications/health`, `/api/v1/applications/`, `/api/v1/applications/{application_id}`, `/api/v1/applications/{application_id}/documents`, `/api/v1/applications/{application_id}/documents/{document_id}/info`, `/api/v1/applications/{application_id}/documents/{document_id}/pages`, `/api/v1/applications/{application_id}/documents/{document_id}/export`, `/api/v1/applications/documents/pages`, `/api/v1/applications/documents/export?format=json`, `/api/v1/document-statistics`, `/api/v1/activities/`, and `/api/v1/activities/document/{document_id}`. Duplicate alias routes are excluded. |
| `monitoring` | 69 | Yes | opt-in GET smoke on safe no-path and setup-backed detail endpoints across overview, request detail, timeseries, golden-dataset, ground-truth, GCS, and drift routes, plus one exact-status guard | smoke, contract, auth, negative | Medium | Partially covered | 42 monitoring GET endpoints now return 200 in smoke, including request detail/document/file/golden-status routes, the supported `timeseries` metrics, golden-dataset detail/file, ground-truth schema, drift trends, and GCS variants/documents/preview. Deferred: `providers` still lacks a legitimate 200 path, and `golden-dataset/export` needs artifact/output policy review before smoke inclusion. `/monitoring/api/v1/golden-dataset/gcs/structure` is now codified in smoke as the expected `502` response rather than treated as an unresolved 200 target. |
| `parser-studio` | 44 | Yes | opt-in GET smoke on safe current no-path and setup-backed detail/version endpoints | smoke, contract, auth, negative | Medium | Covered | Covered now: `auth/status`, current v1 metadata/defaults/audit/tenants/fraud-thresholds routes, `/parser_studio/api/v1/document-types/{doc_type}`, `/versions`, `/prompt/versions`, `/prompt/versions/{version_id}`, and `/tenants/{api_key}`. Legacy unversioned aliases are excluded. |
| `qa` | 15 | Yes | opt-in GET smoke on safe no-path and setup-backed detail endpoints | smoke, contract, auth, negative | Medium | Covered | Covered now: queue, stats, document types, tenants, request detail, review detail, summary/field-error reports, thresholds, export, and export preview. The UI page `/qa` remains excluded. |
| `admin` | 8 | No | exact-status guard on cache health; `cache/stats` remains blocked | isolated smoke only, negative, safety review | Low | Safety-blocked | `/v1/admin/cache/health` is now codified in smoke as the expected `403` response. `/v1/admin/cache/stats` still hits a `403` admin-password gate even after repo-derived tenant candidates are supplied. Never add this group casually to the default suite. |
| `other-service-surfaces` | 30 | Yes | opt-in GET smoke on selected safe gateway, benchmark, and utility list/health/detail endpoints | explicit scope review first | Low | Partially covered | Covered now: `/ai-gateway/health/gateway-circuit-breakers`, `/api/v1/benchmark/jobs`, `/api/v1/benchmark/{job_id}/status`, `/api/v1/benchmark/{job_id}/result`, `/api/v1/benchmark/{job_id}/preview`, and `/api/v1/pii-cleanup/runs`. Deferred: gateway S3 routes, legacy AI shortcut/cross-validation POST routes, UI/debug routes, and other mixed utility surfaces. |

## Normalized Automation Hub Catalog: Tranche 1
This tranche normalizes only the endpoint groups that already have explicit
nodes in `tools/automation_hub/manifest.py`. It does not change runner
behavior, suite membership, live execution approval, CI policy, or the
smoke-to-extended migration gates.

### `parse`
- Suite lane: current no-argument `protected` default through `tools/run_regression.py`; opt-in `full`, matrix, and focused category selections remain separate.
- Automation Hub status: currently covered through the delegated protected lane; represented in the hub manifest as `parse.protected` for non-live planning only, not approved live hub execution.
- Safety class: fixture-backed live document parse with policy-controlled raw response handling; not safe to broaden into default or live hub execution without a separate default-suite decision.
- Data sources: repo-owned `/parse` tests and runner mappings, `tests/endpoints/parse/file_types.py`, fixture registry data, safe observed report evidence, `official-openapi.json`, and the `/parse` OpenAPI drift pilot notes.
- Fixture or prerequisite needs: live API/IAP env, `TENANT_TOKEN`, `API_KEY`, `PARSE_FIXTURE_FILE` as a `gs://` URI, and matching `PARSE_FIXTURE_FILE_TYPE`.
- Artifact policy: protected and focused parse runs may write raw artifacts under `reports/parse/responses/`; structured reports are opt-in under `reports/regression/`; future hub body persistence remains policy-controlled.
- Owner, blocker, or approval notes: protected remains parse-only; owner or maintainer confirmation is still required before observed runtime shape is promoted beyond the current guarded contract.

### `batch`
- Suite lane: endpoint-specific opt-in through `tools/run_regression.py --endpoint batch`; focused `contract` and `negative` categories are mapped, while `auth` remains deferred.
- Automation Hub status: currently covered through a delegated batch validation lane; represented in the hub manifest as `batch.validation` for non-live planning only, not approved live hub execution.
- Safety class: fixture-backed live batch POST with bounded request size and policy-controlled raw response handling; not a protected/default-suite candidate today.
- Data sources: repo-owned `/documents/batch` tests and runner mappings, generated fixture registry data, selected-fixture wrapper behavior, `official-openapi.json`, envelope-only observed-runtime drift coverage, and the batch auth-negative blocker note.
- Fixture or prerequisite needs: live batch env, registry-backed GCS fixtures, default item cap of 4, optional selected fixture JSON, and stable tenant-token behavior.
- Artifact policy: batch runs write raw artifacts under `reports/batch/`; future hub persistence remains policy-controlled; concise normal-run summary remains deferred.
- Owner, blocker, or approval notes: strict tenant-token auth coverage and `--endpoint batch --category auth` remain blocked until missing and invalid tenant-token requests return confirmed `401` or `403`; default-suite inclusion is deferred.

### `health`
- Suite lane: current opt-in `smoke` for top-level and health-like GET status checks; future `extended` live execution is approved only for explicit `--hub-node get-smoke.health.core` and `--hub-node get-smoke.health.ready` selectors.
- Automation Hub status: currently covered; `GET /health` and `GET /health/ready` are the only approved live hub nodes, while the broader `get-smoke.safe-read-only` manifest node remains delegated and non-live.
- Safety class: safe read-only metadata-only checks for the two approved top-level health nodes; other health-like or admin-gated routes require their existing group-specific handling.
- Data sources: GET smoke health tests, exact-status smoke guards, Automation Hub manifest and executor tests, `tools/run_regression.py` selector behavior, command docs, and `official-openapi.json`.
- Fixture or prerequisite needs: live API/IAP env for live health-node execution; no request body, path parameter, fixture registry, or list-derived identifier is needed for the two approved nodes.
- Artifact policy: normal smoke writes no artifacts; approved live hub health selectors write metadata-only `reports/hub/<run-id>/run.json`, `run.md`, and `reports/hub/LATEST.txt` without request or response bodies.
- Owner, blocker, or approval notes: approval is limited to `GET /health` and `GET /health/ready`; broad live `extended`, live `--hub-group`, and all other hub nodes remain blocked.

### `document-processing-adjacent`
- Suite lane: current maintainer-accepted provisional GET smoke coverage for `GET /v1/documents/fraud-status/{job_id}` only; future `extended` modeling is dry-run producer/consumer planning, not live execution.
- Automation Hub status: dependency producer plus dependency consumer in the hub manifest; the producer models a bounded parse setup that yields `fraud_status.job_reference`, and the consumer models the fraud-status top-level status check.
- Safety class: setup-backed read-only consumer with hidden/internal parse producer prerequisites; related `check-cache`, `crosscheck`, and cache mutation routes stay deferred pending request-shape, fixture, artifact, and owner review.
- Data sources: fraud-status smoke tests, non-live fraud-status helper tests, Automation Hub manifest and report-writer tests, safe observed staging characterization, `official-openapi.json`, the fraud-status expansion plan, and provisional OpenAPI runtime-drift coverage.
- Fixture or prerequisite needs: live API/IAP env, protected parse GCS fixture env, `pipeline.async_fraud=true`, tenant-scoped fraud job scheduling, job-store/background-capacity availability, and skip behavior when the producer returns `200` without a usable fraud job id.
- Artifact policy: no raw fraud-status artifacts by default; producer output must be represented as a sensitive alias, and reports may keep only safe top-level metadata unless separate approval allows deeper fraud result persistence.
- Owner, blocker, or approval notes: maintainer acceptance is provisional and not owner-confirmed product contract; public-contract promotion, strict deep schemas, protected/default-suite inclusion, auth-negative expansion, artifact policy changes, and live hub execution remain blocked pending owner confirmation and stability evidence.

## Normalized Automation Hub Catalog: Tranche 2
This tranche normalizes one additional smoke-covered endpoint group. It does not
move coverage from `smoke` to `extended`, add a hub manifest node, change CI
behavior, or approve broader live Automation Hub execution.

### `applications-api`
- Suite lane: current opt-in GET smoke through `tools/run_regression.py --suite smoke`; future `extended` consideration is migration-planning only until parity and approval gates are complete.
- Automation Hub status: currently covered through the delegated broad GET smoke lane; safe candidate for a future split hub node only after artifact policy, dependency semantics, and rollback expectations are documented and tested.
- Safety class: safe read-only and setup-backed read-only GET coverage; application/document detail checks depend on identifiers derived from prior list responses, and export-style GETs need artifact caution even when the smoke lane persists no bodies.
- Data sources: repo-owned GET smoke tests in `tests/endpoints/get_smoke/test_bls_api.py` and `test_bls_api_details.py`, shared smoke helper skip semantics, runner and command docs, endpoint inventory decisions, live smoke characterization recorded in this inventory, and `official-openapi.json` as inventory input only.
- Fixture or prerequisite needs: live API/IAP env, tenant/API auth, usable `applicationId` from `/api/v1/applications/`, usable document id from `/api/v1/applications/{application_id}/documents`, and `format=json` for the canonical applications export smoke path; no fixture-registry dependency is implied.
- Artifact policy: current smoke coverage writes no artifacts and should not persist raw application, document, page, activity, or export response bodies; future hub evidence should keep metadata, status, timing, safe dependency aliases, skip reasons, and rerun selectors unless owner-approved body retention exists.
- Owner, blocker, or approval notes: duplicate alias routes remain excluded, setup-backed detail tests may skip only for missing list-derived prerequisites, and no owner confirmation currently promotes this group into protected/default coverage or live `extended` execution.

## Normalized Automation Hub Catalog: Tranche 3
This tranche normalizes one additional smoke-covered endpoint group. It does not
move coverage from `smoke` to `extended`, add a hub manifest node, change CI
behavior, or approve broader live Automation Hub execution.

### `qa`
- Suite lane: current opt-in GET smoke through `tools/run_regression.py --suite smoke`; future `extended` consideration is migration-planning only until parity and approval gates are complete.
- Automation Hub status: currently covered through the delegated broad GET smoke lane; safe candidate for a future split hub node only after queue-derived dependency behavior, artifact policy, and rollback expectations are documented and tested.
- Safety class: safe read-only and setup-backed read-only GET coverage for QA API JSON endpoints; the `/qa` UI surface remains excluded and is not an API smoke or hub target.
- Data sources: repo-owned GET smoke tests in `tests/endpoints/get_smoke/test_qa.py` and `test_qa_details.py`, shared smoke helper skip semantics, runner and command docs, endpoint inventory decisions, live smoke characterization recorded in this inventory, and `official-openapi.json` as inventory input only.
- Fixture or prerequisite needs: live API/IAP env, tenant/API auth, usable QA queue data from `/qa/api/v1/queue`, a queue-derived correlation identifier for `/qa/api/v1/requests/{correlation_id}`, and a queue-derived correlation identifier that returns `200` for `/qa/api/v1/reviews/{correlation_id}`; no fixture-registry dependency is implied.
- Artifact policy: current smoke coverage writes no artifacts and should not persist raw queue, review, request, report, threshold, export, or export-preview response bodies; future hub evidence should keep metadata, status, timing, safe dependency aliases, skip reasons, and rerun selectors unless owner-approved body retention exists.
- Owner, blocker, or approval notes: setup-backed detail tests may skip only for missing queue-derived prerequisites, review-detail candidate `404` responses are candidate-selection misses rather than covered endpoint success, and no owner confirmation currently promotes this group into protected/default coverage or live `extended` execution.

## Normalized Automation Hub Catalog: Tranche 4
This tranche normalizes one additional smoke-covered endpoint group. It does not
move coverage from `smoke` to `extended`, add a hub manifest node, change CI
behavior, or approve broader live Automation Hub execution.

### `parser-studio`
- Suite lane: current opt-in GET smoke through `tools/run_regression.py --suite smoke`; future `extended` consideration is migration-planning only until parity and approval gates are complete.
- Automation Hub status: currently covered through the delegated broad GET smoke lane; safe candidate for a future split hub node only after document-type, prompt-version, tenant-key dependency behavior, artifact policy, and rollback expectations are documented and tested.
- Safety class: safe read-only and setup-backed read-only GET coverage for current Parser Studio API JSON endpoints; legacy unversioned aliases, `/parser_studio`, and `/parser_studio/auth/login` remain excluded.
- Data sources: repo-owned GET smoke tests in `tests/endpoints/get_smoke/test_parser_studio.py` and `test_parser_studio_details.py`, shared smoke helper skip semantics, runner and command docs, endpoint inventory decisions, live smoke characterization recorded in this inventory, and `official-openapi.json` as inventory input only.
- Fixture or prerequisite needs: live API/IAP env, tenant/API auth, active `document_type` from `/parser_studio/api/v1/document-types`, a usable `version_id` from `/parser_studio/api/v1/document-types/{doc_type}/prompt/versions`, and a tenant `api_key` from `/parser_studio/api/v1/tenants`; no fixture-registry dependency is implied.
- Artifact policy: current smoke coverage writes no artifacts and should not persist raw document-type, prompt, audit, tenant, fraud-threshold, or configuration response bodies; future hub evidence should keep metadata, status, timing, safe dependency aliases, skip reasons, and rerun selectors unless owner-approved body retention exists.
- Owner, blocker, or approval notes: setup-backed detail tests may skip only for missing active document types, prompt version references, or tenant API keys; no owner confirmation currently promotes this group into protected/default coverage or live `extended` execution.

## Normalized Automation Hub Catalog: Tranche 5
This tranche normalizes one mixed, partially covered endpoint group. It does not
move coverage from `smoke` to `extended`, add a hub manifest node, change CI
behavior, or approve broader live Automation Hub execution.

### `other-service-surfaces`
- Suite lane: current opt-in GET smoke through `tools/run_regression.py --suite smoke` for the selected gateway health, benchmark, and utility list/detail subset only; future `extended` consideration is migration-planning only until parity and approval gates are complete.
- Automation Hub status: partially covered through the delegated broad GET smoke lane; any future split hub node needs scope review that separates covered read-only/status endpoints from storage, mutation, legacy, debug, and owner-unconfirmed surfaces before live execution is considered.
- Safety class: mixed. Covered smoke endpoints are safe read-only or setup-backed read-only GET checks for `/ai-gateway/health/gateway-circuit-breakers`, `/api/v1/benchmark/jobs`, `/api/v1/benchmark/{job_id}/status`, `/api/v1/benchmark/{job_id}/result`, `/api/v1/benchmark/{job_id}/preview`, and `/api/v1/pii-cleanup/runs`. Gateway S3 list/download/presigned-url routes, legacy AI shortcut routes, debug routes, POST/DELETE gateway/application/benchmark/PII cleanup routes, and other mixed utility surfaces remain deferred, excluded, or future workflow candidates until explicitly classified.
- Data sources: repo-owned GET smoke tests in `tests/endpoints/get_smoke/test_health.py`, `test_bls_api.py`, and `test_bls_api_details.py`, shared smoke helper skip semantics, runner and command docs, endpoint inventory decisions, OpenAPI runtime-drift classification notes, live smoke characterization recorded in this inventory, and `official-openapi.json` as inventory input only.
- Fixture or prerequisite needs: live API/IAP env, tenant/API auth, and a usable `job_id` from `/api/v1/benchmark/jobs` for benchmark detail checks; no fixture-registry dependency is implied. Deferred storage and mutation surfaces need owner-approved request inputs, setup data, cleanup or rollback rules, and artifact policy before any live automation.
- Artifact policy: current smoke coverage writes no artifacts and should not persist raw gateway, benchmark, PII cleanup, storage, file-path, or utility response bodies; future hub evidence should keep metadata, status, timing, safe dependency aliases, skip reasons, and rerun selectors unless owner-approved body retention exists.
- Owner, blocker, or approval notes: `/ai-gateway/s3/s3/list` remains blocked by current status/setup behavior, S3 download and presigned-url routes require file-path identifiers plus storage/artifact review, debug routes stay excluded, and mutation/stateful routes belong only in a future blocked-by-default `workflow` lane after owner approval and safety gates. No owner confirmation currently promotes this mixed group into protected/default coverage or live `extended` execution.

## Normalized Automation Hub Catalog: Tranche 6
This tranche normalizes one additional partially covered endpoint group. It does
not move coverage from `smoke` to `extended`, add a hub manifest node, change
runner behavior, change CI behavior, or approve broader live Automation Hub
execution.

### `monitoring`
- Suite lane: current opt-in GET smoke through `tools/run_regression.py --suite smoke` for the documented read-only/status subset only; future `extended` consideration is migration-planning only until parity and approval gates are complete.
- Automation Hub status: partially covered through the delegated broad GET smoke lane; safe candidate only for future split hub planning of the already smoke-covered read-only/status subset after dependency semantics, artifact policy, rerun selectors, and rollback expectations are documented and tested.
- Safety class: mixed. Current smoke coverage includes safe read-only no-path GET checks across overview, requests, endpoints, tenants, document types, errors, fraud, export preview/export status-style surfaces, golden-dataset summary/benchmark/status surfaces, audit logs, ground-truth document-type metadata, drift overview/events/settings/scheduler/suppression metadata, and supported timeseries metrics; setup-backed smoke checks depend on list-derived request correlation ids, golden-dataset document ids, document types, GCS categories, GCS variants, and GCS document identifiers. `/monitoring/api/v1/golden-dataset/gcs/structure` is covered only as an exact expected `502` guard.
- Data sources: repo-owned GET smoke tests in `tests/endpoints/get_smoke/test_monitoring.py`, `test_monitoring_details.py`, and `test_expected_status.py`, shared smoke helper skip semantics, runner and command docs, endpoint inventory decisions, OpenAPI runtime-drift classification notes, live smoke characterization recorded in this inventory, and `official-openapi.json` as inventory input only.
- Fixture or prerequisite needs: live API/IAP env and tenant/API auth; request detail checks need a usable `correlation_id` from `/monitoring/api/v1/requests`; golden-dataset detail/file checks need a usable document id from `/monitoring/api/v1/golden-dataset`; ground-truth schema and drift trends need a usable document type from `/monitoring/api/v1/ground-truth/document-types`; GCS variant/document/preview checks need usable category, variant, and document identifiers derived from the GCS types and variants responses. No fixture-registry dependency is implied.
- Artifact policy: current monitoring smoke coverage writes no artifacts and should not persist raw monitoring, request, golden-dataset, ground-truth, drift, export, GCS category, GCS object, or file response bodies. Future hub evidence should keep metadata, status, timing, safe dependency aliases, skip reasons, and rerun selectors unless owner-approved body retention exists. The provisional OpenAPI runtime-drift comparison for `GET /monitoring/api/v1/golden-dataset/gcs/types` covers only the top-level `types` array shape; concrete category values and child GCS endpoint schemas remain loose.
- Owner, blocker, or approval notes: `/monitoring/api/v1/providers` remains blocked because current repo evidence has not found a legitimate `200` path. `/monitoring/api/v1/golden-dataset/export` remains deferred pending allowed format, fixture/filter strategy, sensitivity boundary, and artifact/output policy review. GCS child endpoints and preview routes carry storage and sensitive-data risk even when smoke persists no bodies. Mutating or stateful monitoring routes, including cleanup, drift run/scheduled-run/trigger-run, drift event acknowledge/resolve, drift settings or suppression-rule mutation, golden-dataset create/update/delete/evaluate/evaluate-live/benchmark/stream, GCS import/imported delete, ground-truth OCR/upload/export/review actions, request add-to-golden/retest/mark-reviewed/field/QA-review mutation, and related delete routes, remain blocked, future `workflow` candidates, or owner-confirmation-needed before any live automation. No owner confirmation currently promotes this group into protected/default coverage or live `extended` execution.

## Normalized Automation Hub Catalog: Tranche 7
This tranche normalizes one safety-blocked endpoint group. It does not move
coverage from `smoke` to `extended`, add a hub manifest node, change runner
behavior, change CI behavior, approve positive admin smoke expansion, or approve
any live Automation Hub execution.

### `admin`
- Suite lane: blocked/deferred; no positive admin smoke expansion. Current narrow smoke evidence is limited to the existing `/v1/admin/cache/health` expected-`403` guard and the `/api/v1/admin/health` health-like `200` check through the health group.
- Automation Hub status: blocked/deferred; no manifest node, no live execution, and no `extended` migration candidate until owner approval and safety gates exist.
- Safety class: high-risk/admin mixed surface. Cache health/status routes expose operational state, cache delete routes mutate cache entries or tenant cache, and truncate routes are destructive data-deletion operations.
- Data sources: admin group inventory, expected-status and health GET smoke tests, Automation Hub manifest exclusions and approved health-node list, runner/command docs, live smoke characterization recorded in this inventory, and `official-openapi.json` as inventory input only.
- Fixture or prerequisite needs: none approved. Any future positive admin coverage would need owner-approved admin authentication, target environment, tenant or cache identifiers, disposable/isolated data where mutation is involved, cleanup or rollback rules, explicit selectors, and CI exclusion or approval.
- Artifact policy: no raw admin, cache, tenant, metric, key, truncation, or operational response bodies should be persisted. Future evidence should be metadata-only unless owner-approved redaction and retention rules exist.
- Owner, blocker, or approval notes: `/v1/admin/cache/stats` remains blocked by the admin-password gate; cache delete routes, tenant refresh-cache, document cache invalidation, and BLS truncate routes remain blocked, owner-confirmation-needed, or future `workflow` candidates. The existing health-like and expected-status smoke checks do not approve broader admin smoke coverage, broad `extended`, or live Automation Hub execution.

## Current Coverage Notes
- `official-openapi.json` currently exposes 218 paths.
- The current repo's meaningful live coverage now includes `/v1/documents/parse`, `/v1/documents/batch`, and the opt-in GET smoke lane.
- Parse matrix breadth is opt-in and intentionally limited to one canonical enabled fixture per registry file type.
- Batch coverage reuses registry-backed fixtures and enforces a safe default request size of 4 items.

## Automation Hub Planning Extensions
The planned Automation Hub Expansion should continue to use endpoint groups as the planning unit. Do not turn this inventory into path-by-path busywork, and do not treat an endpoint as safe just because it exists in `official-openapi.json`.

Hub planning statuses:
- `currently covered`: covered by the current protected, smoke, full, matrix, batch, or focused category surfaces.
- `safe candidate`: appears suitable for future hub inclusion after current evidence confirms non-legacy routing, non-destructive behavior, stable prerequisites, and acceptable artifact policy.
- `dependency producer`: produces a validated value that another endpoint can use through the hub run context.
- `dependency consumer`: requires one or more named outputs from earlier producer nodes.
- `workflow candidate`: may belong in a future controlled mutation/stateful lane after explicit owner, setup, cleanup, rollback, artifact, selector, validation, and CI gates are satisfied.
- `legacy/excluded`: legacy duplicate, UI route, debug route, destructive/admin mutation, or other explicitly excluded surface.
- `blocked/deferred`: blocked by auth behavior, owner confirmation, setup prerequisites, artifact/output policy, storage risk, or missing safe request shape.
- `unknown/pending audit`: not yet classified with enough repo or owner evidence for hub inclusion.

Dependency modeling:
- Response-derived values should be modeled as named outputs in a run context, not copied through raw response-body coupling.
- The current non-live `--suite extended --dry-run` preview models dependency order and named output/input relationships only; it does not execute endpoints or prove live safety. Live hub execution is approved only for `get-smoke.health.core` (`GET /health`) and `get-smoke.health.ready` (`GET /health/ready`).
- Producer endpoints should validate and publish only the named output needed by consumers. Reports should use safe aliases or classifications for sensitive dependency values.
- If a producer endpoint fails, dependent consumers should be skipped as dependency failed.
- If a producer succeeds but does not yield a safe usable value, dependent consumers should be skipped as missing prerequisite.
- Independent nodes that do not depend on the failed or missing prerequisite may continue.

Future hub reporting expectations:
- Every executed endpoint/test should produce structured evidence with run metadata, selected nodes, endpoint result summaries, request metadata, safe response metadata/body policy, timing, dependency inputs/outputs, skips, failures, and rerun selectors.
- The current reporting contract scaffold is used by synthetic dry-run reports and the approved live health-node report.
- Raw response bodies may be persisted only when the endpoint artifact policy allows it.
- Reports must redact or exclude tokens, cookies, auth headers, tenant/API keys, raw document IDs, raw GCS object names, sensitive bodies, fraud results, and artifact/export payloads unless explicitly approved.
- Treat `reports/` output as disposable runtime evidence. Promote durable endpoint behavior, blockers, workflow decisions, and validated findings into tracked docs by scope.

Smoke-to-extended migration gates:
- Keep `smoke` as the current broad GET smoke suite until `extended` reaches functional parity, docs parity, CI behavior review, artifact behavior review, direct-use audit, rollback path, and maintainer approval.
- Do not rename, delete, deprecate, or replace GET smoke tests merely because a node appears in the hub manifest.
- Each migrated endpoint group needs matching status expectations, setup-skip behavior, dependency failure semantics, artifact policy, rerun selectors, and non-live tests before live migration.
- Default CI behavior remains unchanged unless a separate approved CI decision updates it.

Future workflow lane gates:
- `workflow` is not implemented and has no current runnable command.
- Treat mutation/stateful endpoints as blocked by default until setup data, side effects, cleanup, rollback, artifact handling, ownership, and target environment are approved.
- Workflow candidates need explicit selectors and non-live planning/reporting proof before any live execution.

## GET Smoke Selection Basis
- This repo does not contain the VerifyIQ server/router implementation or product UI/backend source, so there is no in-repo router-registration evidence to inspect directly.
- Current active GET inclusion therefore relies on the repo-native evidence that does exist: maintained smoke tests, the shared authenticated client in `tests/client.py`, current runner/doc command surfaces, live 200 characterization, and current v1 route structure in `official-openapi.json`.
- `official-openapi.json` is a supporting input, not sole truth.
- When a current v1 route and an unversioned or alias route coexist, only the current explicit route is counted in smoke; legacy/duplicate aliases are excluded and documented rather than padded into coverage totals.
- Setup-backed detail tests should skip when their prerequisite list endpoint returns `200` but no usable identifier data. The skip reason must name the missing prerequisite. Do not skip list endpoint failures, bad statuses, malformed payloads, or list/no-path endpoint assertions.

## GET Smoke Coverage Implemented Now
Canonical runner path:

```bash
./.venv/bin/python tools/run_regression.py --suite smoke
```

Covered now with status-200 or bounded status assertions:
- Health and health-like endpoints: `/health`, `/health/live`, `/health/ready`, `/health/detailed`, `/health/startup`, `/api/v1/applications/health`, `/api/v1/admin/health`, `/ai-gateway/health/gateway-circuit-breakers`
- Document-processing-adjacent endpoint covered through bounded setup: `/v1/documents/fraud-status/{job_id}` uses one protected-fixture `/parse` producer request with hidden/internal `pipeline.async_fraud=true`, then polls at most six times with at most ten seconds between polls. Coverage is maintainer-accepted provisional, not owner-confirmed, and writes no raw artifacts.
- Parser Studio endpoints: `/parser_studio/auth/status`, `/parser_studio/api/v1/document-types`, `/parser_studio/api/v1/pipeline-defaults`, `/parser_studio/api/v1/categories`, `/parser_studio/api/v1/field-types`, `/parser_studio/api/v1/audit-log`, `/parser_studio/api/v1/tenants`, `/parser_studio/api/v1/fraud-thresholds`
- Monitoring endpoints: `/monitoring/api/v1/overview`, `/monitoring/api/v1/requests`, `/monitoring/api/v1/endpoints`, `/monitoring/api/v1/tenants`, `/monitoring/api/v1/document-types`, `/monitoring/api/v1/errors`, `/monitoring/api/v1/fraud`, `/monitoring/api/v1/export`, `/monitoring/api/v1/export/preview`, `/monitoring/api/v1/document-types-list`, `/monitoring/api/v1/golden-dataset`, `/monitoring/api/v1/golden-dataset/stats`, `/monitoring/api/v1/golden-dataset/benchmark/latest`, `/monitoring/api/v1/golden-dataset/benchmark/recent`, `/monitoring/api/v1/golden-dataset/benchmark/stats`, `/monitoring/api/v1/golden-dataset/gcs/types`, `/monitoring/api/v1/audit-logs`, `/monitoring/api/v1/ground-truth/document-types`, `/monitoring/api/v1/ground-truth/review-models`, `/monitoring/api/v1/drift/overview`, `/monitoring/api/v1/drift/events`, `/monitoring/api/v1/drift/settings`, `/monitoring/api/v1/drift/scheduler-status`, `/monitoring/api/v1/drift/suppression-rules`
- QA endpoints: `/qa/api/v1/queue`, `/qa/api/v1/stats`, `/qa/api/v1/document-types`, `/qa/api/v1/tenants`, `/qa/api/v1/reports/summary`, `/qa/api/v1/reports/field-errors`, `/qa/api/v1/thresholds`, `/qa/api/v1/export`, `/qa/api/v1/export/preview`
- BLS API and utility endpoints: `/api/v1/applications/`, `/api/v1/applications/documents/pages`, `/api/v1/applications/documents/export?format=json`, `/api/v1/document-statistics`, `/api/v1/activities/`, `/api/v1/benchmark/jobs`, `/api/v1/pii-cleanup/runs`

GET endpoints covered only after prerequisite/setup handling in this tranche:
- Parser Studio: `/parser_studio/api/v1/document-types/{doc_type}`, `/parser_studio/api/v1/document-types/{doc_type}/versions`, `/parser_studio/api/v1/document-types/{doc_type}/prompt/versions`, `/parser_studio/api/v1/document-types/{doc_type}/prompt/versions/{version_id}`, `/parser_studio/api/v1/tenants/{api_key}`
- Monitoring: `/monitoring/api/v1/requests/{correlation_id}`, `/monitoring/api/v1/requests/{correlation_id}/retests`, `/monitoring/api/v1/requests/{correlation_id}/document`, `/monitoring/api/v1/requests/{correlation_id}/file`, `/monitoring/api/v1/requests/{correlation_id}/qa-review`, `/monitoring/api/v1/requests/{correlation_id}/fields`, `/monitoring/api/v1/requests/{correlation_id}/golden-status`, `/monitoring/api/v1/golden-dataset/{doc_id}`, `/monitoring/api/v1/golden-dataset/{doc_id}/file`, `/monitoring/api/v1/ground-truth/document-schema/{doc_type}`, `/monitoring/api/v1/drift/trends/{document_type}`, `/monitoring/api/v1/timeseries/{metric}` for `requests`, `errors`, `latency`, and `latency_p95`, `/monitoring/api/v1/golden-dataset/gcs/types/{document_type}/variants`, `/monitoring/api/v1/golden-dataset/gcs/types/{document_type}/variants/{variant}/documents`, `/monitoring/api/v1/golden-dataset/gcs/preview/{document_type}/{variant}/{document_id}`
- QA: `/qa/api/v1/requests/{correlation_id}`, `/qa/api/v1/reviews/{correlation_id}`
- Benchmark and applications: `/api/v1/benchmark/{job_id}/status`, `/api/v1/benchmark/{job_id}/result`, `/api/v1/benchmark/{job_id}/preview`, `/api/v1/applications/{application_id}`, `/api/v1/applications/{application_id}/documents`, `/api/v1/applications/{application_id}/documents/{document_id}/info`, `/api/v1/applications/{application_id}/documents/{document_id}/pages`, `/api/v1/applications/{application_id}/documents/{document_id}/export`, `/api/v1/activities/document/{document_id}`

Codified now with exact expected-status assertions:
- `/api/v1/health/database-pools` -> `401`
- `/api/v1/health/database-pools/metrics` -> `401`
- `/v1/documents/fraud-status/not-a-fraud-job` -> `404`
- `/v1/documents/fraud-status/{artificial-valid-nonexistent-job-id}` -> `404`
- `/v1/admin/cache/health` -> `403`
- `/monitoring/api/v1/golden-dataset/gcs/structure` -> `502`

## Deferred GET Endpoints
### Requires query parameters or other request inputs
- `/v1/admin/cache/stats` requires `tenant_id`; repo-native candidate values derived from `TENANT_TOKEN` and `/parser_studio/api/v1/tenants` still returned `403` with `"Invalid admin password. Access denied."`
- `/monitoring/api/v1/providers` still does not have a legitimate 200 path; no-input, `preset`, and explicit provider probes all returned `422`, with the live validation error still reporting `provider` as null
- `/ai-gateway/s3/s3/list` still does not have a legitimate 200 path; no-input and spec-backed `bucket`/`prefix`/`max_keys` probes all returned `400` with `"Invalid file path"`

### Requires artifact or output policy review
- `/monitoring/api/v1/golden-dataset/export` is a current non-legacy GET route in `official-openapi.json`, but it exports active golden-dataset records. Keep it out of smoke until the allowed format, fixture/filter strategy, sensitivity boundary, and artifact handling policy are confirmed.

### Requires path parameters or setup-backed identifiers
- `/v1/documents/fraud-status/{job_id}` now has maintainer-accepted provisional smoke coverage. It still requires a fresh tenant-scoped fraud job id from the bounded async parse producer, and scheduling can fall back to synchronous fraud and return no job ID, in which case the smoke test skips clearly. Continue observed-runtime top-level characterization from safe artifact-free evidence, but keep this endpoint out of owner-confirmed covered status until hidden/internal setup safety, staging fraud-detection/job-store/background-capacity prerequisites, artifact policy, runner lane, and the not owner-confirmed provisional regression contract are confirmed. See `docs/knowledge-base/document-processing-adjacent/fraud-status-expansion-plan.md`.
- `/ai-gateway/s3/s3/download/{file_path}` and `/ai-gateway/s3/s3/presigned-url/{file_path}` require file-path identifiers

### Expected-status current surfaces codified outside the 200-smoke objective
- `/api/v1/health/database-pools` is expected to return `401`
- `/api/v1/health/database-pools/metrics` is expected to return `401`
- `/v1/admin/cache/health` is expected to return `403`
- `/monitoring/api/v1/golden-dataset/gcs/structure` is expected to return `502`

### Explicitly excluded legacy/not-current endpoints
- `/parser_studio/api/categories` and `/parser_studio/api/field-types` are excluded as legacy unversioned aliases of the covered current v1 routes `/parser_studio/api/v1/categories` and `/parser_studio/api/v1/field-types`
- `/parser_studio/api/document-types` and `/parser_studio/api/document-types/{doc_type}` are excluded as legacy unversioned aliases of the current v1 document-type routes
- `/api/v1/documents/pages` is excluded as a duplicate alias of the covered current route `/api/v1/applications/documents/pages`
- `/api/v1/documents/export` is excluded as a duplicate alias of the canonical applications export route `/api/v1/applications/documents/export`
- `/api/v1/{application_id}/documents`, `/api/v1/{application_id}/documents/{document_id}/info`, `/api/v1/{application_id}/documents/{document_id}/pages`, and `/api/v1/{application_id}/documents/{document_id}/export` are excluded as duplicate alias forms of the explicit `/api/v1/applications/{application_id}/...` routes

### UI, debug, or explicit scope/safety deferrals
- `/parser_studio`, `/parser_studio/auth/login`, and `/qa` are UI surfaces rather than API JSON smoke targets
- `/sentry-debug` and `/api/v1/sentry-debug` are explicit debug/error routes and should stay out of smoke

## Planning Boundary
This file records current coverage, deferrals, blockers, and onboarding requirements.
Roadmap sequencing and priority decisions live in `docs/knowledge-base/repo-roadmap.md`.

## Endpoint Group Onboarding Checklist
Before a new endpoint group is added here as "in progress" or "covered", keep the decision endpoint-group based and record:

1. Repo scope fit: why the endpoint group belongs in VerifyIQ API regression automation.
2. Live automation safety class: safe read-only, setup-backed read-only, guarded negative, high-risk/admin, or out of scope.
3. Required suite lane: `protected`, `smoke`, future `extended`, `full`, endpoint-specific opt-in, future `workflow`, or deferred.
4. Minimum categories before "covered": at least the group's agreed smoke/status signal plus the relevant contract, auth/validation, and negative expectations.
5. Fixture or prerequisite needs: `gs://` fixtures, selected fixture JSON, list-derived identifiers, query parameters, tenant/admin prerequisites, or explicit blockers.
6. Artifact expectations: whether the group writes raw artifacts, summary artifacts, structured reports, or no artifacts.
7. Runner mapping requirement: the canonical `tools/run_regression.py` selection or the reason runner mapping is deferred.
8. CI eligibility: whether the group is eligible for non-live CI, protected live CI, opt-in/scheduled live CI, or local-only validation.
9. Owner and blocker notes: the current owner area, known upstream blocker, and evidence needed before promotion.
10. Hub planning status: currently covered, safe candidate, dependency producer, dependency consumer, legacy/excluded, blocked/deferred, or unknown/pending audit.
11. Dependency contract: named outputs the group can produce, named inputs it consumes, and dependency-failure or missing-prerequisite skip behavior.
12. Structured evidence policy: safe metadata/body handling, redaction/exclusion requirements, rerun selectors, and whether raw body persistence is allowed for the group.
13. Data-source fit: which inputs support the decision, such as tests, runner mappings, OpenAPI, fixture registry, list-derived identifiers, safe observed evidence, or owner notes.
14. Migration gate status: whether smoke-to-extended, wrapper/facade replacement, generated-copy retirement, or future workflow gates are not started, in progress, blocked, or approved.
