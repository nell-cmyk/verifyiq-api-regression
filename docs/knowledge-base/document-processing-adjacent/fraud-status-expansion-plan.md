# Fraud Status Expansion Plan

## Scope
This page records the non-live design outcome for proposed coverage of:

```text
GET /v1/documents/fraud-status/{job_id}
```

Do not implement live coverage for this endpoint until the producer, owner,
expected statuses, response contract, artifact policy, and runner lane are
confirmed.

## Repo-Visible Evidence
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

## Design Decision
Endpoint group: keep this route in `document-processing-adjacent`.
It is document-processing tagged, fraud-detection related, and close to the
current parse/batch pillars, but it is not itself the existing parse or batch
entry point.

Safety class: proposed setup-backed read-only GET. The request is read-only, but
it is not safe to run without a fresh, legitimate fraud job ID created by an
approved producer in the same tenant/environment.

Producer requirement: identify an approved fresh fraud job source. The producer
may be an existing document-processing call, a fraud-specific async trigger, or
a curated fixture/setup endpoint, but the repo does not currently prove which.
Benchmark jobs, monitoring request IDs, correlation IDs, application document
IDs, and stale IDs must not be reused as fraud job IDs unless API-owner evidence
explicitly says they are valid for this route.

Owner requirement: the document-processing or fraud-detection API owner must
confirm the producer, tenant scoping, cache TTL, expected lifecycle statuses,
not-found/expired behavior, auth behavior, and which response fields are stable
enough for regression assertions. Platform/auth ownership may also be needed for
missing or invalid auth expectations.

## Expected Statuses
These are design expectations, not implemented assertions:

| Scenario | Current expectation |
| --- | --- |
| Valid fresh `job_id` | Expected to return `200` with a JSON object containing job status and, when complete, fraud detection results. Exact fields and status values remain unresolved. |
| Invalid `job_id` | Prior non-accepted probes with unrelated identifier families returned `404` and `Fraud job not found or expired.` Owner confirmation is required before asserting this. |
| Expired `job_id` | OpenAPI says jobs expire after tenant cache TTL. Prior message text groups not-found and expired together, but exact status/body/TTL remain unresolved. |
| Missing or invalid auth | OpenAPI says document-processing endpoints require API-key Authorization, while current live tests also use tenant-token headers. Expected `401`/`403` versus timeout/other behavior must be confirmed before auth-negative coverage. |

## Contract Expectations
Conservative contract from OpenAPI only:
- method: `GET`
- path: `/v1/documents/fraud-status/{job_id}`
- path parameter: required string `job_id`
- documented success: `200` JSON object with additional properties allowed
- documented validation failure: `422` HTTPValidationError
- descriptive behavior: poll async fraud detection job status; include fraud
  detection results when complete; jobs expire after tenant cache TTL

Do not assert these unresolved fields yet:
- success field names, including whether `status`, `job_id`, timestamps, or
  result containers are present
- lifecycle enum values for pending, running, complete, failed, expired, or
  cancelled states
- fraud result nesting, score fields, report fields, or document-derived details
- whether the response echoes tenant, document, request, or correlation identity
- exact body shape for invalid, expired, or unauthorized requests

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

## Runner Lane Recommendation
Initial implementation should use the opt-in GET smoke lane only if the producer
can be expressed as safe setup within `tests/endpoints/get_smoke/` and does not
create sensitive artifacts. The smoke test should skip only when an approved
producer/list prerequisite succeeds but returns no usable fresh fraud job ID.

If producing a fresh fraud job requires a mutating trigger, expensive parse-like
work, polling with long runtime, or sensitive result artifacts, use a future
endpoint-specific opt-in lane instead of `--suite smoke`.

Do not add this route to:
- the parse-only protected default
- existing protected CI
- broad live CI
- runner mappings before implementation evidence exists

## Promotion Criteria
Before adding tests or runner mappings, collect owner-backed evidence for:
1. The approved producer for a fresh tenant-valid fraud job ID.
2. The expected status lifecycle and terminal states.
3. Exact behavior for invalid and expired job IDs.
4. Expected missing and invalid auth behavior, including tenant-token handling if
   applicable.
5. Stable success contract fields safe for assertions.
6. Artifact handling rules for fraud detection results.
7. Runtime and polling limits that keep the suite stable.
8. Whether GET smoke is sufficient or an endpoint-specific opt-in lane is needed.

Before moving from proposed to covered, validation must include non-live runner
tests for any new mapping, dry-run proof for the selected lane, authorized live
characterization with a fresh fraud job ID, and docs updates that summarize
observed behavior without raw payloads.

## Next Action
Ask the document-processing or fraud-detection API owner to identify the approved
fresh fraud job producer and confirm the response/status/auth contract. Keep
`GET /v1/documents/fraud-status/{job_id}` blocked until that evidence exists.
