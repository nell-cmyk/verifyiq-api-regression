# Fraud Status Expansion Plan

## Scope
This page records the non-live design outcome for proposed coverage of:

```text
GET /v1/documents/fraud-status/{job_id}
```

Maintainer acceptance on 2026-04-28: the provisional regression contract below
is accepted for the smallest opt-in, artifact-free coverage tranche. This is
not owner-confirmed product contract.

## Evidence Classes
This page separates evidence from this regression repo from implementation
evidence verified in the API source. The regression repo remains the source of
truth for test harness behavior; the API source is used here only to refine the
implementation design before any live characterization.

## Repo-Local Evidence
- `official-openapi.json` tags the route as `document-processing`, names it
  "Get Fraud Status", and describes it as polling an async fraud detection job.
- OpenAPI says the route returns job status and, when complete, fraud detection
  results; jobs expire after the tenant cache TTL.
- OpenAPI defines path parameter `job_id` as a required string and includes an
  `authorization` header parameter.
- OpenAPI documents only a generic `200` object with
  `additionalProperties: true` and the shared `422` HTTPValidationError shape.
  It does not define stable success fields, status values, result nesting, or
  error envelopes for not-found/expired jobs.
- The current GET smoke lane under `tests/endpoints/get_smoke/` already supports
  setup-backed detail endpoints: list or prerequisite calls return identifiers,
  missing prerequisite data can skip, but bad statuses and malformed setup
  responses fail.
- Existing setup-backed identifier patterns include benchmark `job_id`,
  monitoring `correlation_id`, QA `correlation_id`, application IDs, document
  IDs, golden-dataset document IDs, document types, GCS categories, and GCS
  document IDs.
- Current docs record that benchmark job IDs and monitoring request-derived
  identifiers are not valid fraud job IDs; prior probes returned `404` with
  `Fraud job not found or expired.` Treat that as blocker evidence only, not as
  an accepted fixture source.
- The repo has no visible producer flow for a fresh fraud job ID. Existing
  `/parse` and `/documents/batch` coverage exercises document processing and
  fraud result fields, but no checked-in test or tool currently exposes an async
  fraud job producer.
- `tests/client.py` supplies IAP, API-key Authorization, and `X-Tenant-Token`
  headers for live API calls. Auth-negative behavior differs across current
  document-processing endpoints, so this endpoint needs owner-backed expected
  auth semantics before negative coverage.
- GET smoke currently writes no response artifacts. `/parse` and `/documents/batch`
  write raw generated artifacts under `reports/`, and docs treat those artifacts
  as sensitive local evidence rather than durable truth.

## External API Implementation Evidence
The API source was directly inspected through the configured GitHub connector in
`boost-capital/ai-parser-studio`:

- `app/api/routes/documents.py`
- `tests/unit/test_async_fraud.py`

Source-backed facts:
- `GET /v1/documents/fraud-status/{job_id}` rejects malformed job IDs before
  tenant lookup. The accepted format is `fj_` followed by 32 lowercase
  hexadecimal characters.
- Invalid job ID format returns `404` with `Fraud job not found or expired.`
- The endpoint requires API-key authorization through the shared
  `require_valid_api_key` path. Missing Authorization raises `401`; invalid API
  key raises `403`.
- Valid API keys produce a tenant `key_hash`; the endpoint calls
  `FraudJobStore.get_job_for_tenant(job_id, tenant_key_hash)`, so job lookup is
  tenant-scoped.
- Missing, expired, or wrong-tenant jobs return `404` with
  `Fraud job not found or expired.`
- `pending` and `running` jobs return only `fraudJobId` and `fraudStatus`.
- `complete` jobs return `fraudJobId`, `fraudStatus`, `fraudScore`,
  `authenticityScore`, `mathematicalFraudReport`, `metadataFraudReport`, and
  `completedAt`.
- `failed` jobs return `fraudJobId`, `fraudStatus`, sanitized `error`, and
  `completedAt`. The sanitized error maps internal errors into broad categories
  such as timeout, connection, model, or internal error.
- Async fraud scheduling can return a fraud job ID when async fraud is enabled
  and job creation succeeds.
- Async scheduling can also return `None`, which causes synchronous fraud
  fallback, so a parse request with async fraud requested is not guaranteed to
  produce a pollable fraud job ID.
- Unit tests cover pending, running, complete, failed, invalid-format, not-found,
  wrong-tenant, scheduling success, scheduling failure, and sync fallback paths.

## Bounded Staging Characterization
Observed in bounded staging characterization on 2026-04-27 because no API owner
was available to confirm the intended producer and contract. This evidence is
provisional and not owner-confirmed.

Characterization bounds:
- At most one `/parse` producer attempt using the existing protected parse
  fixture and `pipeline.async_fraud=true`.
- At most six fraud-status polls with at most ten seconds between polls.
- Invalid-format and syntactically valid nonexistent job-id checks were limited
  to single authenticated GET requests.
- No full regression, matrix, batch, or broad smoke suite was run.
- The script printed only sanitized status codes, booleans, status labels, and
  top-level response keys. It did not write raw fraud-status artifacts.

Observed behavior:
- `/parse` accepted `pipeline.async_fraud=true` and returned `200`.
- A `fraudJobId` was returned and matched the expected `fj_` plus 32 lowercase
  hexadecimal character format.
- Fraud-status polling returned `200` responses with the observed sequence
  `running` then `complete`.
- The final complete response exposed only these top-level keys in recorded
  evidence: `authenticityScore`, `completedAt`, `fraudJobId`, `fraudScore`,
  `fraudStatus`, `mathematicalFraudReport`, and `metadataFraudReport`.
- Invalid-format `job_id` returned `404`.
- A syntactically valid but artificial nonexistent `job_id` returned `404`.

Provisional regression contract:
- A bounded producer using `pipeline.async_fraud=true` can produce a pollable
  fraud job in the current staging environment, but async scheduling is still
  not guaranteed by source evidence and remains not owner-confirmed.
- A minimal future assertion shape could check `200`, valid `fraudJobId` format,
  allowed `fraudStatus` transitions, and top-level key presence by terminal
  state. It should not assert raw fraud report contents.
- `404` is a reasonable provisional negative expectation for malformed and
  missing/not-found job IDs.
- Do not promote to covered until behavior is stable and artifact policy remains
  safe.

## Design Decision
Endpoint group: keep this route in `document-processing-adjacent`.
It is document-processing tagged, fraud-detection related, and close to the
current parse/batch pillars, but it is not itself the existing parse or batch
entry point.

Safety class: setup-backed read-only GET in the opt-in smoke lane. The status
request itself is read-only, but it is not safe to run without a fresh,
legitimate fraud job ID created in the same tenant/environment.

Producer: the implemented provisional setup flow is one `/parse` request using
the protected parse fixture with `pipeline.async_fraud=true`. A bounded staging
characterization observed this working once, but it is still a provisional
regression setup flow, not an owner-approved setup flow, because the API source
also shows scheduling can return no job ID and fall back to synchronous fraud
processing.

Do not use benchmark jobs, monitoring request IDs, correlation IDs, application
document IDs, stale IDs, or hardcoded example job IDs as fraud job IDs. The
implemented smoke test derives the job ID from the bounded parse producer in
the same tenant and skips only when that producer returns `200` without a
usable `fraudJobId`.

Owner requirement: no API owner was available for this characterization. The
document-processing or fraud-detection API owner must still confirm whether
`pipeline.async_fraud=true` is public and safe for regression setup, what tenant
configuration is required, whether the staging job store is available and
reliable, runtime/polling limits, and which complete-result fields are stable
enough for assertions. Platform/auth ownership may also be needed if IAP,
tenant-token, or gateway behavior changes the API-key-only source contract
observed in the API repo.

## Expected Statuses
These are design expectations from API source evidence plus observed in bounded
staging characterization where noted. They are not implemented regression
assertions and are not owner-confirmed:

| Scenario | Current expectation |
| --- | --- |
| Valid fresh pending or running `job_id` | Expected `200` with `fraudJobId` and `fraudStatus`. |
| Valid fresh complete `job_id` | Expected `200` with `fraudJobId`, `fraudStatus`, `fraudScore`, `authenticityScore`, `mathematicalFraudReport`, `metadataFraudReport`, and `completedAt`. |
| Valid fresh failed `job_id` | Expected `200` with `fraudJobId`, `fraudStatus`, sanitized `error`, and `completedAt`. |
| Invalid job ID format | Expected `404` with `Fraud job not found or expired.` |
| Missing, expired, or wrong-tenant job | Expected `404` with `Fraud job not found or expired.` |
| Missing API-key Authorization | Expected `401` from shared API-key auth. |
| Invalid API key | Expected `403` from shared API-key auth. |

## Contract Expectations
Conservative contract from OpenAPI plus verified API source evidence:
- method: `GET`
- path: `/v1/documents/fraud-status/{job_id}`
- path parameter: required string `job_id`, accepted only when it uses the
  `fj_` plus 32 lowercase hexadecimal character format
- documented success: `200` JSON object with additional properties allowed
- documented validation failure: `422` HTTPValidationError
- descriptive behavior: poll async fraud detection job status; include fraud
  detection results when complete; jobs expire after tenant cache TTL
- API source behavior: malformed, missing, expired, and wrong-tenant jobs return
  `404`, not `422`
- API source behavior: job lookup is tenant-scoped through the API key hash
- API source response shapes:
  - pending/running: `fraudJobId`, `fraudStatus`
  - complete: `fraudJobId`, `fraudStatus`, `fraudScore`,
    `authenticityScore`, `mathematicalFraudReport`, `metadataFraudReport`,
    `completedAt`
  - failed: `fraudJobId`, `fraudStatus`, sanitized `error`, `completedAt`

Do not assert these unresolved fields yet:
- whether complete-result report fields are stable enough for external
  regression assertions
- whether optional fields may be null or omitted in some real job states
- whether any gateway/IAP/tenant-token layer changes the raw app auth behavior
- whether the response echoes tenant, document, request, or correlation identity
- whether failed-job error categories are stable enough to assert beyond
  presence of a sanitized error string

## Artifact Policy
Do not persist raw fraud-status responses by default. A completed fraud job may
include fraud detection results, document-derived indicators, scores, metadata,
or other sensitive content. Future implementation should prefer:
- status-code assertions and minimal shape checks in live tests
- summarized shape evidence in tracked docs
- redacted local notes only when a field shape needs owner review
- no committed raw payloads, tokens, fixture URIs, job IDs, or sensitive values

If a future endpoint-specific lane needs artifacts, they must stay under ignored
generated report paths and must be explicitly documented as raw and unredacted.
The complete-job fields `mathematicalFraudReport` and `metadataFraudReport` are
especially sensitive; tracked docs should describe only field names and high-level
shape, not values.

## Runner Lane Recommendation
Implemented lane: opt-in GET smoke, with the canonical command:

```bash
./.venv/bin/python tools/run_regression.py --suite smoke
```

Narrow validation and debugging should target only the fraud-status smoke tests:

```bash
./.venv/bin/python -m pytest tests/endpoints/get_smoke/test_fraud_status.py -v
```

The implemented coverage is artifact-free, uses at most one `/parse` producer
request, polls fraud status at most six times with at most ten seconds between
polls, and asserts only status codes, job-id format, allowed `fraudStatus`
values, and top-level response keys for the observed state. It also asserts
`404` for invalid-format and artificial syntactically valid nonexistent job IDs.

Do not add this route to:
- the parse-only protected default
- existing protected CI
- broad live CI
- batch mappings or `/batch auth`

## Promotion Criteria
Before promoting beyond maintainer-accepted provisional coverage, collect
owner-backed evidence for:
1. Whether `pipeline.async_fraud=true` is public and safe for regression setup.
2. Tenant configuration needed for async fraud scheduling.
3. Staging DB/job-store availability and expected cleanup/TTL behavior.
4. Runtime and polling limits that keep the suite stable.
5. Whether GET smoke is sufficient or an endpoint-specific opt-in lane is needed.
6. Whether complete-result fields are stable enough for assertions.
7. Artifact handling rules for fraud detection results.
8. Whether gateway/IAP/tenant-token behavior changes auth expectations beyond
   the API-key behavior verified in the API source.

Before moving from provisional smoke coverage to owner-confirmed covered
status, validation must include dry-run proof for the selected lane, authorized
live validation with a fresh fraud job ID, and docs updates that summarize
observed behavior without raw payloads.

## Next Action
Keep asking the document-processing or fraud-detection API owner to confirm
whether the async fraud parse path is safe as a regression setup producer and
whether the source-backed and staging-observed response shapes are stable enough
for assertions. Keep `GET /v1/documents/fraud-status/{job_id}` labeled as
maintainer-accepted provisional coverage until owner confirmation exists.
