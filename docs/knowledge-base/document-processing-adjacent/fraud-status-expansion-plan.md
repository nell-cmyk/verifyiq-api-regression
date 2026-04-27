# Fraud Status Expansion Plan

## Scope
This page records the non-live design outcome for proposed coverage of:

```text
GET /v1/documents/fraud-status/{job_id}
```

Do not implement live coverage for this endpoint until the producer setup,
staging prerequisites, artifact policy, and runner lane are confirmed.

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

## Design Decision
Endpoint group: keep this route in `document-processing-adjacent`.
It is document-processing tagged, fraud-detection related, and close to the
current parse/batch pillars, but it is not itself the existing parse or batch
entry point.

Safety class: proposed setup-backed read-only GET. The status request itself is
read-only, but it is not safe to run without a fresh, legitimate fraud job ID
created in the same tenant/environment.

Producer hypothesis: the likely producer is a `/parse` request that enables
async fraud scheduling and receives a fraud job ID in the parse response. This
is still a hypothesis for regression automation, not an approved setup flow,
because the API source also shows scheduling can return no job ID and fall back
to synchronous fraud processing.

Do not use benchmark jobs, monitoring request IDs, correlation IDs, application
document IDs, stale IDs, or hardcoded example job IDs as fraud job IDs. A future
test must derive the job ID from an approved fresh producer in the same tenant
or skip only after a safe prerequisite path succeeds without producing a usable
job ID.

Owner requirement: the document-processing or fraud-detection API owner must
confirm whether `pipeline.async_fraud=true` is public and safe for regression
setup, what tenant configuration is required, whether the staging job store is
available and reliable, runtime/polling limits, and which complete-result fields
are stable enough for assertions. Platform/auth ownership may also be needed if
IAP, tenant-token, or gateway behavior changes the API-key-only source contract
observed in the API repo.

## Expected Statuses
These are design expectations from API source evidence, not implemented
regression assertions:

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
Initial implementation may use the opt-in GET smoke lane only if the approved
producer can be expressed as safe, bounded setup within `tests/endpoints/get_smoke/`
and does not create sensitive artifacts. The smoke test should skip only when
the approved setup path succeeds but returns no usable fresh fraud job ID.

If producing a fresh fraud job requires a live parse request with
`pipeline.async_fraud=true`, long polling, staging DB/job-store assumptions, or
sensitive result artifacts, use a future endpoint-specific opt-in lane instead
of `--suite smoke`.

Do not add this route to:
- the parse-only protected default
- existing protected CI
- broad live CI
- runner mappings before implementation evidence exists

## Promotion Criteria
Before adding tests or runner mappings, collect owner-backed evidence for:
1. Whether `pipeline.async_fraud=true` is public and safe for regression setup.
2. Tenant configuration needed for async fraud scheduling.
3. Staging DB/job-store availability and expected cleanup/TTL behavior.
4. Runtime and polling limits that keep the suite stable.
5. Whether GET smoke is sufficient or an endpoint-specific opt-in lane is needed.
6. Whether complete-result fields are stable enough for assertions.
7. Artifact handling rules for fraud detection results.
8. Whether gateway/IAP/tenant-token behavior changes auth expectations beyond
   the API-key behavior verified in the API source.

Before moving from proposed to covered, validation must include non-live runner
tests for any new mapping, dry-run proof for the selected lane, authorized live
characterization with a fresh fraud job ID, and docs updates that summarize
observed behavior without raw payloads.

## Next Action
Ask the document-processing or fraud-detection API owner to confirm whether the
async fraud parse path is safe as a regression setup producer and whether the
source-backed response shapes are stable enough for assertions. Keep
`GET /v1/documents/fraud-status/{job_id}` blocked until that evidence exists.
