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

The 2026-04-28 VerifyIQ AI assistant fraud-status answer is treated as
source-code-backed supporting evidence only. It is not product-owner approval
and does not promote this endpoint beyond maintainer-accepted provisional
coverage.

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
- `official-openapi.json` documents `pipeline.use_cache` on `/parse` but does
  not document `pipeline.async_fraud`; treat `pipeline.async_fraud=true` as a
  hidden/internal setup knob unless an API owner explicitly approves it for
  regression use.
- The repo now has maintainer-accepted provisional producer coverage in
  `tests/endpoints/get_smoke/test_fraud_status.py`: one protected-fixture
  `/parse` request with hidden/internal `pipeline.async_fraud=true` is used to
  request a fresh fraud job ID for the opt-in GET smoke lane.
- That provisional producer is not an owner-approved public contract. The smoke
  test skips when `/parse` returns `200` without a usable `fraudJobId`, because
  async fraud scheduling can fall back to synchronous processing.
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
- The VerifyIQ AI assistant response adds source-backed scheduling context:
  async job creation depends on fraud detection being enabled, async fraud being
  requested, database/job-store availability, and available background
  processing capacity. Keep these as useful but owner-unconfirmed setup
  prerequisites until confirmed by the document-processing or fraud-detection
  owner.
- The latest VerifyIQ AI assistant producer answer adds source-backed setup
  context: `POST /v1/documents/parse` is the only known fraud-job producer, and
  there is no standalone create-fraud-job endpoint. The parse response
  `fraudStatus` setup meanings are: `pending` means an async job was created and
  its `fraudJobId` can be polled; `complete` means fraud ran synchronously
  inline; `skipped` means fraud was skipped by a completeness gate; and
  `disabled` means fraud detection was disabled. Treat this mapping as
  source-backed but owner-unconfirmed setup behavior, not as an owner-approved
  product contract.
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
regression setup flow, not an owner-approved setup flow. The knob is hidden from
the current OpenAPI request schema, and source-backed evidence shows scheduling
can return no job ID and fall back to synchronous fraud processing when fraud
detection or async scheduling prerequisites are not met.

Do not use benchmark jobs, monitoring request IDs, correlation IDs, application
document IDs, stale IDs, or hardcoded example job IDs as fraud job IDs. The
implemented smoke test derives the job ID from the bounded parse producer in
the same tenant and skips only when that producer returns `200` without a
usable `fraudJobId`.

Owner-confirmation gate: no API owner was available for this characterization.
That should not block further observed-runtime characterization from safe,
sanitized evidence. The document-processing or fraud-detection API owner must
still confirm whether the hidden/internal `pipeline.async_fraud=true` setup knob
may be used safely for regression setup, what tenant and fraud-detection
configuration is required, whether the staging job store and background
processing capacity are available and reliable, runtime/polling limits, and
which complete-result fields are stable enough for public-contract assertions.
Platform/auth ownership may also be needed if IAP, tenant-token, or gateway
behavior changes the API-key-only source contract observed in the API repo.
Use owner confirmation as the gate for public-contract promotion,
protected/default-suite inclusion, strict deep schemas, auth-negative behavior,
artifact policy changes, and long-lived guarantees.

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
- API source behavior: expired jobs intentionally share the same `404` outcome
  as malformed, missing, nonexistent, or wrong-tenant jobs; do not distinguish
  those cases in regression assertions without owner direction
- API source behavior: job lookup is tenant-scoped through the API key hash
- API source response shapes:
  - pending/running: `fraudJobId`, `fraudStatus`
  - complete: `fraudJobId`, `fraudStatus`, `fraudScore`,
    `authenticityScore`, `mathematicalFraudReport`, `metadataFraudReport`,
    `completedAt`
  - failed: `fraudJobId`, `fraudStatus`, sanitized `error`, `completedAt`

Do not assert these unresolved fields yet:
- parse-response fraud status values such as `pending`, `complete`, `skipped`,
  or `disabled`; they describe setup behavior, while the provisional poll
  endpoint contract remains limited to `pending`, `running`, `complete`, and
  `failed`
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

Lane audit on 2026-04-28 keeps this coverage in GET smoke for now because the
suite remains opt-in, `--suite smoke --dry-run` lists the protected parse fixture
environment required for setup, the module is import-safe without live env, and
the narrow fraud-status pytest node is available for focused validation. Move it
to an endpoint-specific opt-in lane if it becomes flaky, materially slows GET
smoke, routinely skips because async scheduling returns no `fraudJobId`, needs
raw artifacts or broader polling/retry behavior, or owner confirmation narrows
the safe setup path.

Do not add this route to:
- the parse-only protected default
- existing protected CI
- broad live CI
- batch mappings or `/batch auth`

## Promotion Criteria
Observed-runtime characterization may continue from artifact-free smoke
assertions, sanitized summaries, and current repo evidence. Before promoting
beyond maintainer-accepted provisional coverage, collect owner-backed evidence
for:
1. Whether hidden/internal `pipeline.async_fraud=true` may be used safely for
   regression setup, or whether a different public producer is required.
2. Tenant configuration needed for async fraud scheduling.
3. Whether `fraud_detection=true`, DB/job-store availability, and background
   processing capacity are required and stable in staging.
4. Expected cleanup/TTL behavior and whether all expired jobs should remain
   indistinguishable from nonexistent jobs at `404`.
5. Runtime and polling limits that keep the suite stable.
6. Whether GET smoke is sufficient or an endpoint-specific opt-in lane is needed.
7. Whether complete-result fields are stable enough for assertions.
8. Artifact handling rules for fraud detection results.
9. Whether gateway/IAP/tenant-token behavior changes auth expectations beyond
   the API-key behavior verified in the API source.

Before moving from provisional smoke coverage to owner-confirmed covered
status, validation must include dry-run proof for the selected lane, authorized
live validation with a fresh fraud job ID, and docs updates that summarize
observed behavior without raw payloads.

## Next Action
Continue observed-runtime characterization without waiting for owner
confirmation. The safe next tranche is to compare the current artifact-free
smoke top-level shape and 404 status evidence against `official-openapi.json`,
keeping terminal complete/failed result fields loose and avoiding raw fraud
payloads, job IDs, fixture URIs, or report values in tracked artifacts. Keep
`GET /v1/documents/fraud-status/{job_id}` labeled as maintainer-accepted
provisional coverage until owner confirmation exists.
