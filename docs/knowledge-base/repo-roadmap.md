# VerifyIQ Roadmap

## Purpose
This roadmap reflects the current repository state and defines the implementation path toward a clean, scalable API regression system with one canonical runner.

The target operating model is a lean, risk-based regression suite that stays practical for local use, scales as more VerifyIQ endpoints are added, and eventually replaces the current fragmented set of operator-facing Python test wrappers.

## Current Repository Status
- The existing roadmap already lived at `docs/knowledge-base/repo-roadmap.md`.
- The runner-consolidation design artifact now lives at `docs/operations/regression-runner-plan.md`.
- The canonical runner now lives at `tools/run_regression.py` and supports inventory-backed `--list`, `--dry-run`, live protected-baseline execution, live opt-in `--suite smoke` GET coverage, and live `--suite full` delegation to the existing full-regression wrapper.
- The checked-in protected-baseline CI workflow now calls `python tools/run_regression.py --suite protected` via the `setup-python` interpreter while preserving the existing secret-aware skip behavior and protected baseline scope.
- The repository is Python-first and uses `pytest`, `httpx`, `python-dotenv`, `google-auth`, and `pyyaml`.
- Live endpoint tests are under `tests/`, with current automated endpoint coverage focused on `/v1/documents/parse`, `/v1/documents/batch`, and the new opt-in cross-group GET smoke lane.
- Requests are live, not mocked. `tests/client.py` builds an `httpx.Client` from `BASE_URL`, `API_KEY`, `TENANT_TOKEN`, and Google IAP credentials.
- `/parse` uses GCS-backed fixtures from `PARSE_FIXTURE_FILE` and `PARSE_FIXTURE_FILE_TYPE`; `/documents/batch` also reuses registry-backed `gs://` fixtures.
- No local mock server, `responses`, `respx`, VCR, or similar replay layer was found in the active regression surfaces.
- The current checked-in CI surface is limited to `.github/workflows/protected-baseline.yml`, which runs the protected `/parse` baseline when required secrets are present.
- The OpenAPI source currently present in the repo is `official-openapi.json` at the repository root.
- `official-openapi.json` is OpenAPI `3.1.0` and contains many endpoint groups beyond current automated coverage, including `documents`, `applications`, `monitoring`, `parser_studio`, `qa`, `health`, and admin-style paths.
- Current contract coverage is manual and selective. Shared assertions live in `tests/endpoints/document_contracts.py`, and no full OpenAPI-driven validator or generated-schema workflow is currently in place.
- Current automated endpoint coverage is still narrower than the OpenAPI inventory, but it now extends beyond `/v1/documents/parse` and `/v1/documents/batch` through the opt-in GET smoke suite. Setup-backed, query-backed, auth-blocked, and safety-filtered GET endpoints remain explicitly deferred.
- The current repo-wide assessment artifact now lives at `docs/operations/automation-test-suite-audit.md` and should be used as the concrete gap and prioritization reference for near-term suite improvements.
- Offline tooling, reporting, and runner suites no longer depend on eager live client bootstrap at pytest import time; `VERIFYIQ_SKIP_DOTENV=1` is the explicit non-live validation switch for disabling repo `.env` loading.
- The repo now has a dedicated non-live CI lane at `.github/workflows/non-live-validation.yml` for `tests/tools/`, `tests/reporting/`, `tests/skills/`, and safe runner discovery checks.
- The current endpoint-group coverage inventory now lives at `docs/operations/endpoint-coverage-inventory.md`.
- The current `/v1/documents/parse` contract-drift pilot now lives at `docs/knowledge-base/parse/openapi-drift-pilot.md`.
- The protected `/parse` happy-path request now retries one `httpx.RemoteProtocolError` before failing so transient upstream disconnects are distinguished from persistent repo or service regressions without broad retry behavior.
- The repo now has an opt-in GET smoke suite under `tests/endpoints/get_smoke/`, callable through `./.venv/bin/python tools/run_regression.py --suite smoke`.
- The current GET smoke suite covers status-200 checks for safely testable no-path GET endpoints across `health`, `parser-studio`, `monitoring`, `qa`, `applications-api`, and selected gateway/benchmark utility surfaces; setup-backed, query-backed, and behavior-blocked GET endpoints remain sequenced follow-on tranches.
- Legacy parser-studio aliases and duplicate BLS alias routes are intentionally excluded from GET smoke and called out in `docs/operations/endpoint-coverage-inventory.md` instead of padding the coverage count.

## Current Validation Surface

| Surface | Current entry point | Current purpose | Consolidation note |
| --- | --- | --- | --- |
| Protected `/parse` baseline | `./.venv/bin/python -m pytest tests/endpoints/parse/ -v` | Default live gate for `/parse` | Must remain behaviorally stable during migration |
| Opt-in GET smoke suite | `./.venv/bin/python tools/run_regression.py --suite smoke` | Curated live GET 200 smoke coverage across safely testable no-path endpoints | Keep opt-in; do not let it silently replace the protected default |
| `/parse` matrix | `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py` | Opt-in broader fileType coverage plus saved summary | Good candidate to become a runner subcommand/category |
| `/parse` full regression | `./.venv/bin/python tools/run_parse_full_regression.py` | Protected baseline followed by matrix | Strong signal that orchestration already exists but is fragmented |
| Targeted `/parse` reporting | `./.venv/bin/python tools/run_parse_with_report.py` | Internal reporting/debug helper | Should become internal-only after consolidation |
| Direct `/documents/batch` suite | `./.venv/bin/python -m pytest tests/endpoints/batch/ -v` | Live batch validation | Should be callable through the canonical runner |
| Selected-fixture `/documents/batch` wrapper | `./.venv/bin/python tools/run_batch_with_fixtures.py --fixtures-json ...` | Fixture-targeted batch runs | Useful migration input for endpoint/category targeting |

## Why Consolidation Is Needed
- The repo already has multiple valid ways to run regression coverage, but the operator command surface is fragmented across direct `pytest` entry points and several Python wrappers.
- `/parse` alone currently has baseline, matrix, full-regression, and targeted-reporting paths.
- `/documents/batch` has both direct pytest and wrapper-based execution.
- This makes it harder to answer basic operator questions: what is the default regression, what is the stronger regression, what is safe to run locally, and which command should CI call as more endpoints arrive.
- A single runner should simplify execution without discarding the useful logic already present in the existing wrappers.

## Existing Roadmap Items Worth Preserving
- Keep `docs/operations/` aligned with the live command surface whenever command behavior changes.
- Preserve the current protected `/parse` baseline behavior during migration instead of silently broadening the default gate.
- Keep the matrix opt-in until the new runner has clear suite boundaries and stable reporting.
- Keep the current GCS-backed fixture policy; do not add local file fallback for `/parse`.
- Preserve lean test architecture. Do not build a generic framework ahead of actual multi-endpoint need.
- Treat `reports/` as disposable generated output, not durable repo truth.
- Keep durable endpoint knowledge curated in docs and Mind, not as raw terminal logs in Git.

## Modernization Goal
Adopt one canonical regression entry point:

```bash
./.venv/bin/python tools/run_regression.py
```

The `tools/` path matches the repository's existing operator-facing CLI convention. During migration, `tools/run_regression.py` should stay thin and call reusable logic from existing `tools/` modules until coverage and reporting parity are proven.

## Target Command Interface

```bash
./.venv/bin/python tools/run_regression.py
./.venv/bin/python tools/run_regression.py --suite protected
./.venv/bin/python tools/run_regression.py --suite smoke
./.venv/bin/python tools/run_regression.py --suite full
./.venv/bin/python tools/run_regression.py --category auth
./.venv/bin/python tools/run_regression.py --category contract
./.venv/bin/python tools/run_regression.py --endpoint parse
./.venv/bin/python tools/run_regression.py --endpoint batch
./.venv/bin/python tools/run_regression.py --list
./.venv/bin/python tools/run_regression.py --dry-run
```

Planned runner expectations:
- One command can execute the default necessary regression suite.
- Targeting works by suite, category, endpoint group, and eventually risk level or tag.
- `--list` shows what would run and why it is included.
- `--dry-run` shows the exact underlying pytest nodeids or wrapper calls without hitting live endpoints.
- Output is concise at the top level and still preserves endpoint, fixture, and summary detail for failure diagnosis.
- Existing wrappers stay available only as migration inputs until the canonical runner has proven parity.

## Definition Of Necessary Regression

### Include By Default
- Smoke checks for the most important endpoints and auth layers.
- Critical user and API flows with representative happy-path coverage.
- Contract and schema checks for selected request and response shapes.
- Authentication and authorization checks.
- Representative negative behavior and high-risk edge cases.
- Previously broken behavior and high-usage endpoint coverage.

### Avoid By Default
- Duplicate checks spread across multiple wrappers.
- Exhaustive permutations that do not materially increase confidence.
- Slow matrix-style breadth in the default path unless the endpoint risk justifies it.
- Broad tests with unclear failure ownership.
- Blind OpenAPI-only validation when live behavior and the spec may have drifted.

## Regression Taxonomy

| Dimension | Planned values | Current repo grounding |
| --- | --- | --- |
| Suite | `protected`, `smoke`, `full`, `extended` | `parse` baseline is the current protected default; `smoke` is now the opt-in GET smoke suite; matrix and full are already separate |
| Category | `smoke`, `critical-path`, `contract`, `auth`, `negative`, `integration`, `slow`, `legacy` | Current tests already map naturally to happy path, auth, validation, matrix breadth, and batch limits |
| Endpoint group | `parse`, `batch`, then broader groups such as `documents`, `applications`, `monitoring`, `parser-studio`, `qa`, `health-admin` | Current automation now covers `parse`, `batch`, and an opt-in GET smoke layer across broader groups identified from `official-openapi.json` |
| Risk level | `critical`, `high`, `standard`, `extended` | Needed once more endpoints are onboarded so the default suite stays lean |

Initial categorization of current endpoint coverage:
- `parse`: smoke, critical-path, auth, contract, negative, extended matrix.
- `batch`: smoke candidate, critical-path, contract, negative, integration-live, extended selected-fixture runs.
- `health`: smoke, GET 200 on the full top-level `/health*` family.
- `parser-studio`: smoke, GET 200 on safe no-path auth-status, metadata, audit, tenant, and threshold endpoints.
- `monitoring`: smoke, GET 200 on safe no-path overview, list, report, golden-dataset, export, and drift endpoints.
- `qa`: smoke, GET 200 on safe no-path queue, stats, report, threshold, and export endpoints.
- `applications-api`: smoke, GET 200 on safe no-path BLS/API health, list, pages, and summary endpoints.
- `other-service-surfaces`: smoke, GET 200 on selected gateway, benchmark, and utility list/health endpoints.
- `legacy`: current standalone wrappers that remain temporarily available during migration.

## Contract And Schema Validation Strategy
- Treat `official-openapi.json` as the initial contract source, not automatic ground truth.
- Keep contract validation separate from schema discovery.
- Contract validation means checking requests and responses against the intended OpenAPI contract.
- Schema discovery means capturing current live request and response shapes from safe existing regression flows and comparing them with the spec.

### Pilot Strategy
1. Start with `/v1/documents/parse` because it is the protected baseline, already has stable live fixtures, and already writes response artifacts.
2. Use existing safe regression inputs only: current `gs://` fixtures, current baseline tests, current matrix wrapper, and current saved artifacts and reports.
3. Capture representative request and response shapes for `200` and validation-error flows from existing runs rather than from new destructive probing.
4. Compare observed shapes against `ParseRequest`, `HTTPValidationError`, and current success-response assumptions in `official-openapi.json`.
5. Document confirmed drift explicitly and decide whether the fix belongs in the spec, the tests, or both.
6. Extend the same workflow to `/v1/documents/batch` only after the `/parse` pilot produces a stable pattern.

### Drift Handling Rules
- If the spec is clearly stale and live behavior is accepted product behavior, update the spec and keep the tests aligned.
- If live behavior is incorrect, preserve the failing test or add a targeted regression guard.
- If ownership is unclear, record the mismatch as known drift and do not silently treat the spec as authoritative.

## Legacy Script Deprecation Strategy

| Current surface | Near-term status | End-state |
| --- | --- | --- |
| `pytest tests/endpoints/parse/ -v` | Keep as protected baseline implementation and debug surface | Still valid for direct pytest debugging, but no longer the primary operator command |
| `tools/reporting/run_parse_matrix_with_summary.py` | Reuse internally from the canonical runner | Internal helper or compatibility wrapper |
| `tools/run_parse_full_regression.py` | Keep during migration for parity checks | Deprecated after `tools/run_regression.py --suite full` is proven |
| `tools/run_parse_with_report.py` | Keep as advanced/debug-only during migration | Internal-only or removed if superseded by runner flags |
| `pytest tests/endpoints/batch/ -v` | Keep as a direct debug path | No longer primary operator command |
| `tools/run_batch_with_fixtures.py` | Reuse for targeted batch selection while runner coverage is built | Deprecated or retained as an internal utility |

Deprecation rules:
- Do not delete wrappers until their useful coverage is callable through `tools/run_regression.py`.
- Do not remove docs references until CI and local workflow references have moved.
- Mark old entry points as legacy before removal so operators can transition without ambiguity.

## CI And Local Execution Strategy
- Local execution remains first-class. The runner must be discoverable and safe for developers before it becomes a CI dependency.
- Keep the current protected-baseline workflow unchanged until the canonical runner reproduces the same behavior with equal or better clarity.
- The checked-in protected-baseline workflow now calls `tools/run_regression.py --suite protected` for the default gate.
- Add a separate `full` or `extended` CI lane only after runtime and secret requirements are understood.
- Preserve the existing secret-aware skip behavior for live environments.
- Reuse existing artifact patterns where possible so migration does not destroy diagnosability.

Expected reporting behavior for the canonical runner:
- Top-level pass or fail summary by suite, endpoint, and category.
- Clear indication of which underlying tests or wrappers ran.
- Direct links or paths to generated artifacts such as `reports/parse/...`, `reports/batch/...`, and `reports/regression/...`.
- Failure summaries that identify endpoint, fixture, request type, and contract-vs-behavior context when relevant.

## Phased Plan

| Phase | Priority | Scope | Exit criteria |
| --- | --- | --- | --- |
| Phase 0: Repository and runner inventory | Highest | Map every current regression command, the endpoint coverage it provides, duplication, and gaps between repo automation and OpenAPI inventory | Each existing runner surface is mapped to suites, categories, and a migration disposition |
| Phase 1: Regression taxonomy | Highest | Define suite names, category rules, endpoint-group naming, and what counts as necessary regression | Current `/parse` and `/batch` tests are classified without changing runtime behavior |
| Phase 2: One-runner design | Highest | Define `tools/run_regression.py`, its CLI contract, list and dry-run behavior, and how it delegates to existing logic | CLI contract is approved and can express current baseline, batch, matrix, and full flows |
| Phase 3: Contract and schema modernization | High | Pilot OpenAPI drift detection on `/parse`, then extend to `/batch` | One endpoint has a documented discovery workflow and drift decision process |
| Phase 4: Legacy migration | High | Route current useful wrapper behavior through the canonical runner and mark old commands as legacy | Operators can use one runner for normal work; old wrappers are clearly secondary |
| Phase 5: CI and reporting cutover | Medium | Move CI from direct command strings to canonical runner suites and unify summaries | CI calls one runner for the default gate and keeps extended coverage separate |
| Phase 6: Endpoint expansion | Medium | Add remaining VerifyIQ endpoints through the same taxonomy and risk model | Each new endpoint group enters with explicit suite, category, and contract expectations |

## Milestones Ordered By Priority
1. Publish a current-state inventory that maps every existing regression command to its endpoint coverage, suite intent, and future status.
2. Freeze the taxonomy for `suite`, `category`, `endpoint`, and `risk` labels using current `/parse` and `/batch` coverage as the first examples.
3. Implement the CLI contract for `tools/run_regression.py` on paper before code changes begin.
4. Use `/v1/documents/parse` as the contract-drift pilot and document how OpenAPI mismatches are handled.
5. Bring `/documents/batch` under the same runner interface with targeted fixture-selection support.
6. Confirm the protected CI cutover remains stable before broader canonical-runner execution paths are enabled.
7. Deprecate fragmented legacy wrappers once operator docs and CI no longer depend on them.
8. Add the next endpoint group only after it is categorized, risk-ranked, and mapped into the runner.

## Success Criteria And Validation Gates
- There is exactly one documented primary regression command for normal operator use.
- `tools/run_regression.py --list` and `--dry-run` explain suite contents without hitting live endpoints.
- Current `/parse` baseline behavior remains intact throughout migration.
- `tools/run_regression.py --suite smoke` provides the single entry point for the implemented GET smoke layer while keeping the default no-argument path unchanged.
- Current `/documents/batch` coverage is callable through the canonical runner before batch wrappers are deprecated.
- The default suite stays lean and diagnostically clear; broader or slower coverage is explicitly named and opt-in.
- `/parse` and `/batch` both have explicit category labels for smoke, contract, auth or validation, negative, and extended coverage where applicable.
- The OpenAPI drift workflow is documented and exercised on at least one safe endpoint before broader contract claims are made.
- CI and docs point to the same canonical runner surface before legacy wrappers are removed.

## Risks, Assumptions, And Open Questions
- Assumption: the current `/parse` and `/documents/batch` live regression calls are acceptable safe test-environment operations because the repo already depends on them.
- Assumption: `official-openapi.json` is useful for endpoint inventory and initial contract definitions, but it may include internal, deprecated, or stale surfaces.
- Risk: consolidating under one `tools/` runner must preserve the current wrapper semantics, artifacts, and opt-in boundaries.
- Risk: live-environment dependencies, GCS fixture availability, and IAP credentials will continue to constrain what can run by default in CI.
- Risk: broad endpoint expansion without risk-based gating will recreate the current confusion at a larger scale.
- Open question: should `/documents/batch` join the default no-argument regression immediately, or remain a named suite until fixture stability and runtime are better characterized?
- Open question: which remaining OpenAPI endpoint groups are highest business priority after `parse` and `batch`?
- Open question: which parts of the large OpenAPI inventory are still active product surface versus internal or deprecated endpoints?

## Recommended Next Implementation Steps
1. Use `docs/operations/regression-runner-plan.md` as the implementation design artifact for runner consolidation.
2. Keep `./.venv/bin/python tools/run_regression.py` aligned with the exact protected and full wrapper behavior while live execution settles.
3. Add live execution mapping for direct parse matrix targeting and targeted batch flows only after the delegated full path is stable.
4. Define metadata for current `/parse` and `/batch` tests so the future runner can target them by suite and category without duplicating logic.
5. Extend the `/v1/documents/parse` drift pilot with fresh safe response artifacts so the remaining spec-vs-behavior questions can be resolved explicitly.
6. Re-run the opt-in `/documents/batch` auth characterization until both missing and invalid tenant-token requests return confirmed 401/403 rejection; current evidence is still blocking because missing-token requests time out while invalid-token requests can return `200`, so keep the blocker out of the default batch suite and keep the auth gap open. See `docs/knowledge-base/batch/auth-negative-blocker.md`.

## Sequenced Next Tranches For GET Smoke
1. Add required-query or other input-backed GET smoke coverage for `/v1/admin/cache/stats`, `/monitoring/api/v1/providers`, `/api/v1/applications/documents/export`, `/api/v1/documents/export`, and `/ai-gateway/s3/s3/list` once their safe request inputs are characterized.
2. Add setup-backed detail GET smoke coverage by deriving identifiers from the already-covered list/status endpoints for `/v1/documents/fraud-status/{job_id}`, the deferred `parser-studio` detail/version routes, the deferred `monitoring` detail/timeseries/golden-dataset routes, the deferred `qa` correlation-id routes, the deferred benchmark detail routes, and the deferred application/document detail routes.
3. Resolve current GET auth or behavior blockers before promotion into smoke: `/api/v1/health/database-pools`, `/api/v1/health/database-pools/metrics`, `/v1/admin/cache/health`, `/parser_studio/api/document-types`, and `/monitoring/api/v1/golden-dataset/gcs/structure`.
4. Decide whether UI, debug, and explicit admin/storage GET surfaces such as `/parser_studio`, `/parser_studio/auth/login`, `/qa`, `/sentry-debug`, `/api/v1/sentry-debug`, and the AI Gateway file download/presign routes belong in API automation at all.
