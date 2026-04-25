# Automation Test Suite Audit

## Executive Summary
This repository has a solid foundation for live `/v1/documents/parse` regression and a credible companion lane for `/v1/documents/batch`, but it is not yet a professional-grade API automation suite at repository scale.

The strongest areas are regression discipline around the protected `/parse` baseline, fixture and registry management, raw and structured artifact generation, offline coverage for runner and reporting utilities, canonical-runner parity for the current protected/smoke/full/matrix/batch mappings, and checked-in CI lanes. The largest remaining gaps are endpoint breadth, systematic contract validation, reporting parity beyond parse, and the live-environment coupling that is still inherent to endpoint suites.

Superseded audit findings: offline tooling/reporting/skills suites no longer depend on eager live client bootstrap at pytest import time, `docs/operations/endpoint-coverage-inventory.md` now exists, `.github/workflows/non-live-validation.yml` now runs the non-live validation lane, current parse-matrix and batch mappings are live-runnable through the canonical runner, protected CI artifact upload is available behind an explicit repository-variable gate, and the endpoint onboarding standard now exists. The most important next steps are to keep those guardrails current, run the planned `/parse` OpenAPI drift pilot, finish structured-reporting parity, and avoid wrapper deprecation until the documented criteria are met.

## Overall Assessment
Maturity rating: **Solid foundation**

That rating is appropriate because the repository already has a disciplined protected baseline, useful negative and validation coverage, deterministic fixture selection, opt-in matrix breadth, reporting artifacts, secret-aware live CI, non-live CI for tooling/reporting infrastructure, and a canonical runner for the current useful live selections. It is not yet **Professional-grade** because automation still covers a narrow subset of the OpenAPI surface, contract validation is still manual and selective, structured reporting is not fully consolidated under the runner, and live endpoint suites remain dependent on live environment configuration by design.

### Maturity Scorecard

| Dimension | Score | Reason |
| --- | --- | --- |
| Test strategy | 3/5 | `/parse` has a clear protected baseline and matrix/full layers, and the repo now has an opt-in cross-group GET smoke lane, but the per-endpoint minimum category bar is still incomplete. |
| Runner ergonomics | 4/5 | `tools/run_regression.py` now supports `--list`, `--dry-run`, live protected execution, live opt-in GET smoke, live `--suite full`, live parse matrix delegation, direct batch delegation, and selected-fixture batch delegation; structured-reporting parity is the main remaining runner gap. |
| Regression discipline | 4/5 | The default gate stays narrow, the matrix uses one canonical fixture per file type, and `/documents/batch` caps default live request size at four items. |
| Endpoint coverage | 2/5 | Live endpoint coverage is still narrow relative to 218 OpenAPI paths, but it now includes `/v1/documents/parse`, `/v1/documents/batch`, and an opt-in cross-group GET smoke lane. |
| Contract/schema validation | 2/5 | Shared assertions are useful, but success-response validation is selective and there is no systematic OpenAPI drift workflow in operation yet. |
| Fixture/test data management | 4/5 | The generated registry, canonical fixture policy, JSON normalization, and batch chunking logic are strong and deliberate. |
| Reporting/artifacts | 4/5 | Raw response capture, structured reports, redaction, and matrix summary rendering are materially better than a typical early-stage regression repo. |
| CI integration | 3/5 | The protected live baseline workflow is conservative and correct, a non-live tooling/reporting/skills lane exists, and protected raw artifact publishing is available behind an explicit opt-in variable; broader live lanes remain intentionally absent. |
| Reliability/flake control | 2/5 | Session-scoped live calls and safe request limits help, but the suite is still fully live and auth-negative timeout acceptance highlights upstream instability. |
| Documentation/contributor experience | 3/5 | The repo has substantial documentation, but the command story is still mixed and there is no concise guide for adding a new endpoint under a defined taxonomy. |
| Repo hygiene | 3/5 | Naming and structure are mostly consistent, but there are still overlapping wrappers, partial migration state, and a few command-surface inconsistencies. |
| Scalability for endpoint expansion | 3/5 | The roadmap anticipates expansion and the repo now has a coverage inventory, onboarding checklist, and non-live harness; enforcement is still mostly documentation-driven. |

## What The Repo Already Does Well
- Keeps the default live gate intentionally narrow. The protected baseline remains the repo's default signal in `README.md`, `AGENTS.md`, `docs/operations/workflow.md`, and `.github/workflows/protected-baseline.yml`.
- Separates broader `/parse` breadth from the default gate. `tests/endpoints/parse/conftest.py` hard-gates matrix collection behind `RUN_PARSE_MATRIX=1`, and `tools/run_regression.py --endpoint parse --category matrix` is the normal opt-in path.
- Uses deterministic fixture selection instead of uncontrolled matrix sprawl. `tests/endpoints/parse/registry.py` selects one canonical enabled fixture per distinct registry `file_type`, and the current registry resolves to 26 canonical fixtures out of 1,813 enabled records.
- Treats fixture data as curated source material. `tools/generate_fixture_registry.py`, `tools/onboard_fixture_json.py`, and `tests/endpoints/parse/fixture_json.py` enforce provenance, normalization, and unsupported-format filtering.
- Reuses live responses to reduce redundant API calls. `tests/endpoints/parse/test_parse.py` and `tests/endpoints/batch/test_batch.py` rely on session-scoped happy-path responses.
- Produces useful diagnostics and artifacts for live failures. `tests/diagnostics.py`, `tests/endpoints/parse/artifacts.py`, `tests/endpoints/batch/artifacts.py`, and `tests/reporting/*` make failures materially easier to classify.
- Centralizes shared response assertions. `tests/endpoints/document_contracts.py` avoids repeating required-field, fileType, calculated-field, and 422-shape checks.
- Covers runner and reporting utilities offline. `tests/tools/`, `tests/reporting/`, and `tests/skills/` provide non-live validation of wrapper logic, reporting behavior, registry onboarding, and redaction.
- Keeps CI conservative and secret-aware. `.github/workflows/protected-baseline.yml` only runs the protected live baseline and skips cleanly when secrets are missing.
- Preserves safety for live `/documents/batch` runs. `tests/endpoints/batch/fixtures.py` caps default request size at four items, and `tools/run_batch_with_fixtures.py` chunks larger selected sets.

## Main Gaps
- Live endpoint automation still covers only a small subset of the OpenAPI inventory, but it now extends beyond `/v1/documents/parse` and `/v1/documents/batch` through the opt-in GET smoke lane.
- The suite now has an explicit opt-in cross-endpoint GET smoke lane. `protected` remains the real default gate, while `smoke` is implemented as a bounded GET suite with 200 assertions for covered current endpoints plus exact-status checks for a small set of known non-200 surfaces.
- Contract and schema validation are still manual and selective. There is no checked-in OpenAPI validator, drift register, or observed-schema comparison workflow in operation.
- The canonical runner is now real for current protected, smoke, full, parse matrix, direct batch, and selected-fixture batch mappings. Structured reporting is still not fully consolidated under the runner.
- Offline tooling, reporting, skills, and runner tests are now isolated from eager live client bootstrap when run with `VERIFYIQ_SKIP_DOTENV=1`; live endpoint suites still require live environment configuration by design.
- Auth coverage is still shallow. `/parse` only checks missing and invalid tenant-token behavior; `/documents/batch` still has only an opt-in auth blocker characterization rather than a closed auth lane, and there is no deeper authz/permission model anywhere.
- The repo now has a maintained endpoint coverage inventory and onboarding checklist, but owner-area mapping and enforcement are still thin.
- CI now covers the live protected baseline and the non-live tooling/reporting/skills lane. The protected live workflow can publish raw parse artifacts only when `UPLOAD_PROTECTED_PARSE_ARTIFACTS=true`.
- The command story is improved, but direct pytest and wrapper surfaces still need compatibility/debug labels until the documented deprecation criteria are met.
- There is no explicit repo-level decision yet on whether this repository remains parse/batch-focused or becomes the broader multi-endpoint automation hub implied by the roadmap's endpoint-expansion phase.

## Detailed Assessment By Dimension

### 1. Test Strategy and Scope
- Current state: The live strategy is strong for `/parse` and decent for `/documents/batch`, and the repo now has an opt-in cross-group GET smoke lane under `tests/endpoints/get_smoke/`. `/parse` has happy-path, auth-negative, validation, and opt-in matrix coverage in `tests/endpoints/parse/test_parse.py` and `tests/endpoints/parse/test_parse_matrix.py`. `/documents/batch` has happy-path, validation, limit handling, and partial-failure coverage in `tests/endpoints/batch/test_batch.py`. The smoke lane now covers status-200 checks for safely testable current GET endpoints plus exact checks for the known `401`/`403`/`502` surfaces, while the remaining setup-backed, query-backed, and unstable GET routes are still deferred.
- Professional expectation: A professional API automation repo has a deliberately defined test model that distinguishes protected smoke, regression, contract/schema, auth/authz, negative, and extended lanes across the covered endpoint set.
- Gap: The current taxonomy exists mostly in docs and roadmap text, not as an enforced runnable model beyond the implemented protected, smoke, full, parse matrix, and batch selections.
- Recommended improvement: Define the minimum required category set per endpoint group and decide whether `protected` remains parse-only or evolves into a curated cross-endpoint smoke lane.
- Priority: P1
- Effort: Medium
- Risk if ignored: New coverage will be added inconsistently, and the default suite will either stay too narrow or bloat without a stable selection rule.

### 2. Regression Selection Discipline
- Current state: This is one of the repo's best areas. The protected baseline is narrow by design, the parse matrix uses one canonical fixture per file type, and batch runs enforce a safe item limit of four.
- Professional expectation: Default regression should be risk-based, lean, representative, and explicit about why each case is in or out.
- Gap: The repo now has an endpoint coverage inventory, but test-to-suite inclusion rules and the endpoint onboarding standard are still thin. The protected baseline command also selects the entire `tests/endpoints/parse/` package, which mixes live parse tests with offline registry-selection tests.
- Recommended improvement: Keep the endpoint inventory current and add a concise onboarding standard that documents which tests belong to `protected`, `smoke`, `full`, and `extended`, and why.
- Priority: P1
- Effort: Small
- Risk if ignored: Regression scope will become harder to reason about as more tests accumulate, and default-suite trust will erode.

### 3. Runner and Command Ergonomics
- Current state: `tools/run_regression.py` supports inventory-backed `--list`, `--dry-run`, default protected execution, opt-in GET smoke, delegated full execution, delegated parse matrix execution, direct batch execution, and selected-fixture batch execution. The wrapper surfaces are still kept as delegated engines or compatibility/debug paths.
- Professional expectation: One clear operator command should front the suite, with precise list and dry-run behavior, predictable suite/endpoint/category targeting, and minimal overlap.
- Gap: Current useful live surfaces are callable from the canonical runner, but structured reporting remains split across `tools/run_parse_with_report.py` and delegated wrappers. Broader smoke semantics beyond the current GET 200 lane are still evolving.
- Recommended improvement: Finish structured-reporting parity and keep wrapper/direct pytest surfaces labeled as delegated, compatibility/debug, or advanced/internal until deprecation criteria are met.
- Priority: P1
- Effort: Medium
- Risk if ignored: Operator confusion remains, and future endpoint onboarding will duplicate command surfaces instead of simplifying them.

### 4. Test Architecture and Maintainability
- Current state: The package layout is small and understandable. Shared helpers like `tests/diagnostics.py`, `tests/endpoints/document_contracts.py`, and the artifact modules keep endpoint tests readable. Session-scoped fixtures reduce repeated live requests.
- Professional expectation: Adding a new endpoint should require a small number of obvious extension points and should not force duplicated client, fixture, artifact, and contract logic.
- Gap: The current architecture is proven for parse, batch, and GET smoke, but categories are not encoded as test metadata and live endpoint suites remain tied to live env loading.
- Recommended improvement: Preserve the current small-module approach, but define a lightweight onboarding template for new endpoint groups and move live-client setup behind fixtures that only load when needed.
- Priority: P1
- Effort: Medium
- Risk if ignored: The repo will become harder to extend cleanly, and maintainers will duplicate patterns instead of reusing them.

### 5. Test Data and Fixture Management
- Current state: Fixture handling is a clear strength. The spreadsheet-plus-supplemental-YAML flow, generated registry, canonical selection, JSON onboarding, and unsupported-format filtering are all intentional and well tested.
- Professional expectation: Test data should be traceable, deterministic, curated, safe, and easy to subset without mutating source-of-truth data casually.
- Gap: The system is parse-centric and externally dependent on `gs://` fixtures. There is no explicit fixture freshness check, availability audit, or environment-specific drift reporting. Batch fixture selection also depends on the parse registry.
- Recommended improvement: Keep the existing registry model, but add a lightweight health/inventory view for fixture availability and document how batch fixture policy should evolve if batch coverage broadens.
- Priority: P2
- Effort: Medium
- Risk if ignored: Fixture drift and environment-specific failures will stay hard to distinguish from actual API regressions.

### 6. Environment and Secrets Management
- Current state: The required live inputs are documented clearly in `AGENTS.md`, `docs/operations/workflow.md`, and `.env.example`. CI handles missing secrets correctly.
- Professional expectation: Live suites should fail clearly when secrets are missing, while offline/unit suites should remain runnable without live env configuration.
- Gap: The earlier eager-bootstrap problem is resolved for non-live tooling/reporting/skills validation when `VERIFYIQ_SKIP_DOTENV=1` is used. The remaining risk is regression: future shared fixtures or root imports could accidentally reintroduce live config loading into offline suites.
- Recommended improvement: Keep live-client creation behind fixtures, keep `VERIFYIQ_SKIP_DOTENV=1` in non-live validation, and add targeted tests when shared pytest infrastructure changes.
- Priority: P2
- Effort: Small
- Risk if ignored: Offline validation could regress and again require secrets or live env configuration.

### 7. Contract and Schema Validation
- Current state: Contract coverage is real but selective. `tests/endpoints/document_contracts.py` checks required fields, fileType echoing, calculated-field stub avoidance, and 422 validation shape. `/parse` and `/documents/batch` both reference `official-openapi.json` in test docstrings, but there is no general request/response schema validator.
- Professional expectation: Contract validation should be systematic enough to detect drift intentionally, with explicit rules for whether the fix belongs in the spec, the tests, or the service.
- Gap: Success-response schemas in `official-openapi.json` are generic object responses for both `/v1/documents/parse` and `/v1/documents/batch`, so current tests are stronger than the spec in some ways and looser in others. The request schemas also do not describe the repo's `pipeline.use_cache=false` field that the tests send.
- Recommended improvement: Implement the planned `/parse` contract-drift pilot using existing safe artifacts and fixtures, then extend that pattern to `/documents/batch` only after the pilot is stable.
- Priority: P0
- Effort: Medium
- Risk if ignored: Coverage claims will remain hard to trust, and spec drift will keep accumulating without ownership.

### 8. Reporting, Observability, and Artifacts
- Current state: Reporting is ahead of most repos at this stage. Raw parse and batch response artifacts are captured. The parse matrix wrapper saves terminal output, renders a Markdown summary, and can emit structured JSON and Markdown regression reports. Redaction is centralized.
- Professional expectation: Reports should help diagnose failures quickly, avoid leaking secrets, and support comparison between runs locally and in CI.
- Gap: Reporting depth is much stronger for parse than batch. There is no checked-in historical comparison workflow, and protected CI artifact upload is intentionally disabled unless a repository variable opts in. The current checkout also does not contain generated `reports/`, so recent real-run output quality was not assessable here.
- Recommended improvement: Keep the existing artifact model, treat protected artifact upload as sensitive and opt-in, and decide whether batch needs a parallel post-run summary surface.
- Priority: P1
- Effort: Medium
- Risk if ignored: Failures stay diagnosable locally but less useful in CI and across time.

### 9. CI/CD Integration
- Current state: There is one checked-in live workflow, `.github/workflows/protected-baseline.yml`, and it is appropriately conservative.
- Professional expectation: CI should run fast non-live validation on every change and reserve live suites for the right gated lanes, with artifact publishing where live evidence matters.
- Gap: The repo now runs the offline tooling, reporting, skills, and runner discovery checks in CI. The protected live lane can publish raw artifacts only behind an explicit variable gate, so artifact access policy remains an operational decision.
- Recommended improvement: Keep the non-live lane current as runner mappings expand, and keep protected-run artifact publishing opt-in before considering any broader live CI coverage.
- Priority: P1
- Effort: Small
- Risk if ignored: Regressions in wrappers, reporters, and command mapping can land undetected until someone runs them manually.

### 10. Reliability and Flake Control
- Current state: The repo takes some good precautions. Live happy-path calls are session-scoped, parse and batch timeouts are explicit, batch size is capped, and known warning fixtures are annotated in the registry.
- Professional expectation: Live suites should minimize flake through stable fixture selection, explicit runtime envelopes, clear failure classification, and good separation between product failures and environment failures.
- Gap: The suite is still fully live, there is no retry or quarantine strategy, and parse auth-negative coverage currently treats timeout as an acceptable negative outcome because the upstream behavior is unstable.
- Recommended improvement: Keep retries off by default, but add explicit flake tracking and a small preflight or classification layer so environment/auth-proxy failures are easier to separate from product regressions.
- Priority: P1
- Effort: Medium
- Risk if ignored: The repo will have difficulty broadening CI or default coverage without increasing noise.

### 11. Coverage Visibility and Endpoint Expansion
- Current state: The roadmap acknowledges expansion, and `docs/operations/endpoint-coverage-inventory.md` now maps endpoint groups to current automation status and blockers.
- Professional expectation: A professional suite has a living inventory that shows what is covered, what is not, and what the minimum onboarding bar is for a new endpoint.
- Gap: The repo can answer endpoint-group status and onboarding requirements from one inventory, but the checklist is not enforced by tooling.
- Recommended improvement: Keep the compact endpoint coverage inventory and onboarding checklist current as smoke and endpoint coverage evolve.
- Priority: P0
- Effort: Medium
- Risk if ignored: Expansion will be ad hoc, and regression scope will become harder to rationalize.

### 12. Safety and Non-Destructive Behavior
- Current state: Default behavior is cautious. The protected baseline is narrow, the parse matrix is opt-in, batch runs cap request size, and the runner offers `--list` and `--dry-run` for non-executing discovery.
- Professional expectation: Live API repos should default to safe behavior and require deliberate opt-in for broader or riskier actions.
- Gap: Safety is good for the current endpoints, but there is no formal safety classification framework yet for future endpoint groups, especially if mutating admin or application endpoints ever enter scope.
- Recommended improvement: Before any endpoint expansion beyond parse and batch, classify candidate endpoints by destructive risk and explicitly keep mutating or admin-style paths out of default automation.
- Priority: P2
- Effort: Small
- Risk if ignored: Future endpoint expansion could accidentally normalize unsafe live calls.

### 13. Documentation and Contributor Experience
- Current state: The repo has more documentation than most automation repos at this stage. `README.md`, `AGENTS.md`, `docs/operations/*`, and the roadmap give contributors useful context.
- Professional expectation: A new engineer should be able to answer three questions quickly: what is the default suite, how do I run non-live checks, and how do I add a new endpoint under the current strategy.
- Gap: Direct pytest and wrapper surfaces still exist for valid compatibility/debug reasons, so docs must keep labels sharp. Endpoint onboarding is now documented, but enforcement remains manual.
- Recommended improvement: Keep one normal runner path in docs, preserve wrapper labels, and turn the onboarding checklist into enforced review expectations as endpoint coverage grows.
- Priority: P1
- Effort: Small
- Risk if ignored: New contributors will continue to learn the suite by reverse-engineering the repo rather than following one clean path.

### 14. Professional Repo Hygiene
- Current state: Naming is mostly consistent, repo scope is documented, and obsolete `.codex` reporting entry points are largely called out as removed.
- Professional expectation: A professional repo keeps the user-facing command surface clean, clearly distinguishes legacy paths, and minimizes stale references.
- Gap: Parse still has multiple overlapping entry points (`pytest`, matrix wrapper, full wrapper, targeted report wrapper, and canonical runner). They are now labeled more clearly, but deprecation is not complete.
- Recommended improvement: Keep legacy wrappers until deprecation criteria are met, and continue tightening docs so the runner remains the normal operator story.
- Priority: P2
- Effort: Medium
- Risk if ignored: Surface-area duplication will continue to grow faster than the test suite itself.

## Endpoint Coverage Assessment
The current live-covered endpoint groups are:

- `/v1/documents/parse`
- `/v1/documents/batch`
- opt-in GET smoke coverage across current active no-path GET endpoints in `health`, `parser-studio`, `monitoring`, `qa`, `applications-api`, and selected utility surfaces

Supporting offline endpoint-adjacent coverage exists for:

- parse fixture registry selection and JSON normalization in `tests/endpoints/parse/test_registry_selection.py`
- parse and batch artifact writers in `tests/endpoints/test_parse_artifacts.py` and `tests/endpoints/batch/test_artifacts.py`
- batch fixture selection logic in `tests/endpoints/batch/test_fixtures.py`

OpenAPI inventory context:

- `official-openapi.json` currently exposes 218 path entries.
- Top-level groups include `v1`, `api`, `monitoring`, `parser_studio`, `qa`, `health`, `admin`, `ai-gateway`, `ai_parse`, `ai_parse_batch`, `ai_crosscheck`, and `sentry-debug`.

Endpoint groups and sub-surfaces still not yet fully automated in this repo include at least:

- document-adjacent GETs such as `/v1/documents/check-cache`, `/v1/documents/cache`, `/v1/documents/crosscheck`, and `/v1/documents/fraud-status/{job_id}`
- setup-backed application, monitoring, benchmark, and QA detail routes that need identifiers before they can assert 200 cleanly
- required-query or input-backed GETs such as cache stats, provider stats, export routes, and gateway storage list routes
- admin-style cache paths and other explicitly safety-filtered surfaces

Which gaps matter most depends on repo charter.

- If this repo remains intentionally parse/batch-focused, the highest-value gap is not breadth for its own sake. It is stronger category depth and better contract discipline on the endpoints already in scope.
- If the roadmap's broader endpoint-expansion phase is still the intended future, the next high-value candidates should stay close to the current document-processing domain first, especially `/v1/documents/check-cache`, `/v1/documents/crosscheck`, and a minimal safe health lane.
- Monitoring, parser-studio, QA, and admin paths should not enter the suite by default until there is an explicit scope decision and a risk-ranked onboarding rule.

How coverage should expand without bloating regression:

- Add a coverage inventory before adding more endpoints.
- Require a minimum category set for any new endpoint: smoke or protected, contract, negative, and explicit safety classification.
- Start expansion from safe, non-destructive, high-usage document-processing paths.
- Keep new endpoint breadth out of the default lane until runtime, fixture, and ownership are understood.

Limitation: this audit intentionally does not attempt a full OpenAPI path-by-path matrix because the spec is broad, includes internal and admin-style surfaces, and the current repo charter is still narrower than the full inventory.

## Regression Suite Quality Assessment
Protected baseline quality:

- Strong where it matters most today. `tests/endpoints/parse/test_parse.py` covers happy path, tenant-token auth-negative behavior, missing field validation, and 422 schema shape.
- Operationally disciplined. The default protected command is stable and still the only checked-in live CI gate.
- Not perfectly isolated. The protected package run also includes offline parse package tests, so the boundary is a package boundary rather than a precisely curated live-only inventory.

Full suite quality:

- `tools/run_parse_full_regression.py` is a reasonable stronger gate because it runs protected baseline first and matrix second while sharing one parse artifact run directory.
- It is still only a stronger parse gate, not a wider repo-level regression suite.

Parse matrix quality:

- Strong regression-selection discipline. One canonical enabled fixture per file type keeps the matrix meaningful instead of exhaustive.
- Good observability. The wrapper captures terminal output, renders summaries, supports targeted fixture JSON, and can emit structured reports.
- Limited assertion depth by design. The matrix only checks generic contract expectations, not file-type-specific semantics.

Batch coverage quality:

- Stronger than a basic happy-path lane. `tests/endpoints/batch/test_batch.py` checks happy path, top-level structure, per-item contract, empty request behavior, over-limit handling, item validation, and partial failure.
- Still missing auth-negative coverage and deeper contract/schema automation.

Default command safety:

- Good. The direct default remains the narrow parse baseline. `tools/run_regression.py --list` and `--dry-run` provide safe discovery. The parse matrix is code-gated.

What should not be added to default regression yet:

- full parse matrix breadth
- default batch inclusion without an explicit smoke/protected decision
- OpenAPI-wide endpoint coverage
- destructive or admin-style endpoints
- exhaustive fixture permutations

## Contract and Schema Validation Assessment
`official-openapi.json` should remain the intended contract source, but not assumed ground truth. That is the right posture and matches both the roadmap and current repo reality.

Current request and response validation is not systematic enough yet:

- Request validation coverage is partial and manual. `/parse` and `/documents/batch` both assert 422 shapes and a few request-missing-field cases.
- Success-response validation is manual and selective. `tests/endpoints/document_contracts.py` checks a small required-field set plus specific regressions, but it does not validate whole response shapes.
- The OpenAPI success schemas for `/v1/documents/parse` and `/v1/documents/batch` are generic object responses, which means the spec is currently too weak to serve as sufficient success-schema validation by itself.
- The repo sends `pipeline.use_cache=false` for both parse and batch flows, but the current `ParseRequest` and `BatchRequest` schemas only expose `file` and `fileType` or `items`. That is a concrete contract-drift candidate.

Should schema discovery from current safe endpoint behavior be added?

- Yes.
- The repo already has the right raw materials: protected parse responses, parse matrix artifacts, batch artifacts, and opt-in structured reports.
- Schema discovery should be derived from those safe existing flows, not from broader endpoint exploration.

How OpenAPI drift should be handled:

- Keep a narrow drift register tied to specific endpoints and payload/response fields.
- If accepted live behavior is better than the spec, update the spec.
- If the test is outdated, update the test.
- If ownership is unclear, record the mismatch and do not silently pretend the spec is authoritative.

Recommended pilot endpoint:

- `/v1/documents/parse`

Why:

- It is the protected baseline.
- It already writes raw response artifacts.
- It already has validation and auth-negative coverage.
- The roadmap already names it as the contract-drift pilot.

## Runner and CI Assessment
`tools/run_regression.py` current state:

- Good current canonical runner for the supported suite and endpoint selections.
- It supports inventory-backed `--list` and `--dry-run` for protected, smoke, full, parse matrix, batch, and batch-with-fixtures mappings.
- It supports live execution for `--suite protected`, `--suite smoke`, `--suite full`, `--endpoint parse --category matrix`, `--endpoint batch`, and `--endpoint batch --fixtures-json ...`.
- Planned suites and categories are still visible, but category-level mappings such as `contract`, `auth`, and `negative` are not yet runnable.

Remaining runner gaps:

- structured reporting remains split across delegated wrappers and `tools/run_parse_with_report.py`
- categories such as `contract`, `auth`, and `negative` are planned but not mapped
- legacy direct pytest and wrapper commands remain documented as delegated engines, compatibility/debug paths, or advanced/internal paths, so deprecation boundaries still need active maintenance

Legacy wrapper status:

- `tools/run_parse_full_regression.py` remains useful as the delegated full-regression engine.
- `tools/reporting/run_parse_matrix_with_summary.py` is still the delegated parse matrix engine.
- `tools/run_batch_with_fixtures.py` contains meaningful chunking and warning logic worth preserving.
- `tools/run_parse_with_report.py` is the clearest over-duplicated surface and best deprecation candidate once reporting parity exists in the runner.

Protected CI status:

- Correctly narrow.
- Secret-aware.
- Still aligned with the protected baseline philosophy.
- Raw artifact publishing exists, but only behind the explicit repository variable `UPLOAD_PROTECTED_PARSE_ARTIFACTS=true`.

What should go into CI next:

- keep non-live runner discovery checks aligned as mappings evolve
- use protected live artifact publishing only when artifact access and sensitivity are acceptable
- broader live lanes only after runtime, stability, and ownership are understood

What should not go into CI next:

- always-on parse matrix
- always-on full regression
- always-on batch live execution
- broader endpoint live lanes before scope, runtime, and stability are measured

## Recommended Roadmap Additions

### Immediate Next Steps

| Item | Reason | Expected Value | Suggested Owner Area | Validation Criteria |
| --- | --- | --- | --- | --- |
| Preserve non-live pytest isolation | The former eager live-bootstrap gap is resolved for tooling/reporting/skills validation; keep it from regressing. | Protects fast local and CI feedback without secrets. | Test infrastructure | `VERIFYIQ_SKIP_DOTENV=1 ./.venv/bin/python -m pytest tests/tools/ tests/reporting/ tests/skills/ -v` runs in a clean env. |
| Maintain the endpoint coverage inventory and onboarding checklist | The repo now has `docs/operations/endpoint-coverage-inventory.md`; it still needs to stay aligned as smoke and endpoint coverage evolve. | Keeps expansion and regression scope decisions evidence-based. | QA architecture / docs | The checked-in inventory maps covered groups, categories, priority, gaps, onboarding requirements, and CI eligibility. |
| Execute the `/parse` contract-drift pilot | Contract validation is the biggest quality-system gap in current coverage claims. | Creates a repeatable way to reconcile spec, tests, and live behavior. | Contract/schema | One checked-in drift artifact exists for `/v1/documents/parse` with explicit decisions. |
| Finish structured-reporting parity | Current live runner parity is stronger, but targeted report behavior still lives outside the runner. | Reduces contributor confusion and supports future wrapper deprecation. | Runner / operations docs | README, workflow, and command registry all tell the same primary-runner story, with report-specific exceptions labeled advanced/internal. |

### Near-Term Improvements

| Item | Reason | Expected Value | Suggested Owner Area | Validation Criteria |
| --- | --- | --- | --- | --- |
| Extend non-live CI discovery as runner mappings grow | The non-live workflow exists; future runner mappings should be added deliberately. | Protects the non-live infrastructure that operators depend on. | CI / tooling | The non-live workflow runs successfully without secrets and covers current safe discovery surfaces. |
| Enforce the minimum endpoint onboarding bar | New endpoints have a checklist but no tooling or review gate. | Prevents uneven or low-value endpoint expansion. | QA architecture | New endpoint proposals include safety class, suite lane, required categories, fixtures/prereqs, artifacts, runner mapping, CI eligibility, and owner/blocker notes. |
| Add auth-negative coverage for `/documents/batch` | Batch has no auth lane today. | Brings batch closer to parse coverage maturity. | Endpoint tests | `/documents/batch` has at least one supported auth-negative scenario. |
| Decide whether `protected` stays parse-only or becomes cross-endpoint smoke | The roadmap and docs still mix these ideas. | Stabilizes regression selection discipline. | QA strategy / roadmap | The roadmap and runner taxonomy use one explicit default-suite definition. |

### Medium-Term Improvements

| Item | Reason | Expected Value | Suggested Owner Area | Validation Criteria |
| --- | --- | --- | --- | --- |
| Keep batch and parse-matrix runner parity covered | The canonical runner now delegates these paths, so regressions need to stay caught offline. | Simplifies operator execution and deprecation planning. | Runner / tooling | Batch and parse matrix remain callable through the runner with parity to current wrappers. |
| Govern protected live artifact publishing | Live failures need triage value, but raw artifacts can be sensitive. | Improves remote triage only when explicitly enabled. | CI / reporting | CI uploads protected-run artifacts only when `UPLOAD_PROTECTED_PARSE_ARTIFACTS=true`, with short retention and no arbitrary `reports/` upload. |
| Add a lightweight fixture health view | The repo relies heavily on curated remote fixtures. | Helps distinguish fixture drift from service regressions. | Fixtures / reporting | A non-live command or doc summarizes fixture counts, statuses, and notable warnings. |
| Extend contract-drift workflow to `/documents/batch` | Batch should follow parse once the parse pilot is stable. | Makes contract discipline consistent across in-scope endpoints. | Contract/schema | `/documents/batch` has a checked-in drift note or schema assessment. |

### Later Improvements

| Item | Reason | Expected Value | Suggested Owner Area | Validation Criteria |
| --- | --- | --- | --- | --- |
| Add the next safe document-processing endpoint group | Broader API coverage should start near the current domain, not from unrelated admin surfaces. | Expands value without exploding suite scope. | Endpoint expansion | The next endpoint enters with explicit categories, safety class, and runner mapping. |
| Deprecate overlapping wrapper surfaces | The repo currently carries too many overlapping command paths. | Reduces maintenance drag and operator ambiguity. | Runner / docs | Legacy wrappers are clearly secondary or removed only after runner parity is proven. |
| Add historical comparison for report artifacts | Current reporting is strong per run but weak across runs. | Improves flake analysis and trend visibility. | Reporting | Reports can compare run-to-run failure classes or pass counts. |

## What Not To Do Yet
- Do not make parse matrix, full regression, or batch live coverage part of the default no-argument regression until runtime and failure ownership are better characterized.
- Do not deprecate `tools/run_parse_full_regression.py`, `tools/reporting/run_parse_matrix_with_summary.py`, or `tools/run_batch_with_fixtures.py` before the direct-use and compatibility/debug criteria in `docs/operations/regression-runner-plan.md` are met.
- Do not trust `official-openapi.json` blindly for success-schema validation while the current spec still uses generic object responses for parse and batch.
- Do not expand CI to broad live suites just because offline infrastructure tests now run in CI; broad live lanes still need explicit runtime, stability, and ownership decisions.
- Do not chase exhaustive endpoint or fixture permutations; keep selection risk-based and representative.
- Do not add mutating admin, monitoring, or application-management endpoints to default automation without an explicit safety framework.
- Do not solve live instability with blanket retries as the first move; classify failures before normalizing them.

## Professional Target State
- Command surface: one clearly documented primary command, `./.venv/bin/python tools/run_regression.py`, with transparent `--list` and `--dry-run` behavior and stable suite, endpoint, and category targeting.
- Test taxonomy: explicit `protected`, `smoke`, `full`, and `extended` suite semantics, with endpoint-level categories such as `contract`, `auth`, `negative`, and `integration` defined before expansion.
- Coverage model: a living inventory that shows each endpoint group's current status, priority, safety class, and required minimum category bar.
- Fixture strategy: deterministic curated registries, targeted subset support, remote-fixture traceability, and clear handling of known-warning fixtures.
- Reporting and artifacts: raw response artifacts, per-run summaries, structured reports, redaction, and CI artifact publishing for the live lanes that matter.
- CI model: offline infrastructure tests on every change, protected live parse coverage on gated conditions, and broader live lanes only as explicit opt-in or scheduled jobs.
- Schema validation model: OpenAPI is the intended contract source, observed safe behavior is captured separately, and drift decisions are recorded explicitly instead of guessed.
- Deprecation model: legacy wrappers stay until runner parity, docs, CI, direct-use, and compatibility/debug criteria are met, then direct use is reduced deliberately instead of drifting indefinitely.

## Prioritized Action Plan

| Priority | Action | Why it matters | Effort | Risk | Validation signal | Roadmap phase or doc to update |
| --- | --- | --- | --- | --- | --- | --- |
| Guardrail | Keep offline pytest suites decoupled from live env imports | Preserves fast non-live validation and CI without secrets. | Small | Medium | Offline pytest suites run cleanly with `VERIFYIQ_SKIP_DOTENV=1`. | `docs/operations/workflow.md`, `.github/workflows/non-live-validation.yml` |
| Guardrail | Keep the checked-in endpoint coverage inventory and onboarding checklist current | Keeps scope, gaps, and next additions explicit. | Small | Medium | One document maps covered and uncovered endpoint groups plus required categories, safety class, artifacts, runner mapping, CI eligibility, and owner/blocker notes. | Phase 0 / Phase 6 |
| P0 | Run the `/parse` contract-drift pilot | Creates a real contract reconciliation workflow. | Medium | High | Parse drift decisions are documented against safe artifacts. | Phase 3 |
| P1 | Extend non-live CI only as safe discovery surfaces grow | Protects the runner and reporting infrastructure continuously. | Small | Medium | CI passes without live secrets and fails on wrapper regressions. | Phase 5, `.github/workflows/non-live-validation.yml` |
| P1 | Decide whether `protected` remains parse-only or evolves into curated smoke | Stabilizes default-suite identity. | Small | High | Roadmap, workflow docs, and runner all define the same default suite. | Phase 1 |
| P1 | Enforce the minimum endpoint onboarding standard | Prevents uneven coverage as endpoints are added. | Medium | Medium | New endpoint proposals include categories, safety class, fixture plan, artifact expectations, runner mapping, CI eligibility, and owner/blocker notes. | Phase 1 / Phase 6 |
| P1 | Add `/documents/batch` auth-negative coverage | Closes a basic category gap on an in-scope endpoint. | Small | Medium | Batch endpoint has at least one reliable auth-negative check. | Phase 1 |
| P1 | Converge docs around the real operator path | Reduces confusion between direct pytest, wrappers, and runner usage. | Small | Medium | README, workflow, and command registry no longer disagree on the normal path. | `README.md`, `docs/operations/*` |
| P1 | Govern CI artifact publishing for protected runs | Improves remote diagnosis only when artifact sensitivity is acceptable. | Small | Medium | Protected CI exposes downloadable raw artifacts only when `UPLOAD_PROTECTED_PARSE_ARTIFACTS=true` and retains them briefly. | Phase 5, `.github/workflows/protected-baseline.yml` |
| P2 | Keep parse matrix runner parity covered | Prevents regression in delegated matrix execution. | Small | Medium | Runner can execute parse matrix with current wrapper behavior preserved. | Phase 4 |
| P2 | Keep batch runner parity covered | Prevents regression in delegated batch execution. | Small | Medium | Runner executes batch and batch-with-fixtures parity paths. | Phase 4 |
| P2 | Add a fixture health or inventory view | Makes fixture drift easier to separate from service regressions. | Medium | Low | Non-live output summarizes registry size, canonical coverage, and warnings. | Phase 0 / docs |
| P2 | Add batch-oriented summary reporting comparable to parse matrix summaries | Reporting quality is currently uneven across in-scope endpoints. | Medium | Low | Batch runs can emit a concise structured summary and failure classification. | Phase 5 / reporting docs |
| P3 | Add the next safe document-processing endpoint only after scope is explicit | Prevents expansion by accident. | Medium | Medium | New endpoint onboarding follows the defined template and stays out of default regression initially. | Phase 6 |

## Open Questions
- Is this repository intentionally staying parse-and-batch-focused, or is it still expected to become the broader multi-endpoint automation hub implied by the roadmap's endpoint-expansion phase?
- Should `/documents/batch` join the default no-argument regression after reliability characterization, or remain an explicitly named lane?
- Who owns spec-versus-behavior reconciliation when `official-openapi.json` and accepted live behavior diverge?
- Which safe, non-destructive document-processing endpoint should be the first expansion target after parse and batch, if expansion remains in scope?
- What CI runtime budget is acceptable for protected live coverage, any future smoke lane, and any scheduled extended lane?
