# VerifyIQ Roadmap

## Purpose And Authority
This is the canonical planning source for VerifyIQ API regression automation.
Future agents should read this file first for project status, architecture direction, sequencing, priorities, blockers, and future-development decisions.

Keep operational commands and run sequences in `docs/operations/*`. Keep endpoint behavior, fixture knowledge, blockers, and triage findings in focused `docs/knowledge-base/*` pages. Do not create new roadmap, plan, audit, future-work, or handoff markdown files; update this roadmap or Mind instead.

## Current Repository Status
- Scope remains Python + pytest live regression automation for VerifyIQ API surfaces. Manual QA workflow, ticketing, pass-sync logic, deployment, and unrelated process automation stay out of scope.
- The canonical operator runner is `tools/run_regression.py`. Current safe discovery output confirms implemented live suites `protected`, `smoke`, and `full`; `extended` with non-live dry-run plan support plus two approved live health hub nodes, `get-smoke.health.core` for `GET /health` and `get-smoke.health.ready` for `GET /health/ready`; implemented endpoint groups `parse` and `batch`; implemented category selections `matrix`, `contract`, `auth`, and `negative`; and planned-but-unmapped category `legacy`.
- Canonical suite taxonomy is now explicit: `protected` remains the parse-only default; `smoke` remains the current broad opt-in GET smoke suite until `extended` reaches functional and documentation parity; `extended` is the future safe dependency-aware Automation Hub lane, with broad live execution still blocked; `full` remains a stronger parse gate; and future `workflow` is reserved for controlled mutation/stateful endpoint flows, blocked by default, and not implemented.
- Current category mappings are endpoint-specific, opt-in, backed by existing tests, and guarded by non-live runner tests: `/parse` maps `contract`, `auth`, `negative`, and `matrix`; `/documents/batch` maps `contract` and `negative`. `/documents/batch auth` remains deferred by the known auth-negative blocker.
- The no-argument runner maps to the parse-only protected suite. This is still the default live gate and must not silently broaden.
- Structured-report runner mappings are guarded by non-live runner tests: no-arg `--report` and `--suite protected --report` delegate to the baseline report helper, `--suite full --report` delegates to the full wrapper, and `--endpoint parse --category matrix --report` delegates to the matrix wrapper. `--suite extended --dry-run --report` writes synthetic non-live hub plan evidence only; approved live health-node selectors write metadata-only hub reports under `reports/hub/`.
- A separate concise `/documents/batch` summary surface is not planned for the normal runner right now. Normal batch validation remains opt-in and raw-artifact-only, while broad batch review belongs to the dedicated ground-truth export workbook, manifest, and recovery-planning workflow.
- The endpoint coverage inventory has been rechecked against current GET smoke tests and `official-openapi.json`; keep it current as smoke coverage changes, but do not treat inventory maintenance as a separate expansion decision.
- The repository strategy is to evolve into a broader VerifyIQ multi-endpoint API automation hub, with document parsing, `/documents/batch`, fraud detection, document-processing-adjacent behavior, and related quality/model validation remaining the core feature area and first-class priority.
- Automation Hub Expansion now has a non-live foundation plus a bounded health-only live executor tranche: `get-smoke.health.core` for `GET /health` and `get-smoke.health.ready` for `GET /health/ready`. The future target remains a dependency-aware safe endpoint hub behind `tools/run_regression.py`. `--suite extended --dry-run` is still the non-live dependency-plan preview, can be filtered with `--hub-node` or `--hub-group`, and can write synthetic plan evidence with `--report`; broad live `--suite extended`, live `--hub-group`, and all non-approved hub nodes remain blocked.
- The endpoint catalog should combine repo-owned tests, runner mappings, endpoint inventory decisions, fixture registry data, safe observed evidence, and `official-openapi.json`. The fixture registry is one data source, mainly for parse, batch, matrix, and specifically approved fixture-backed producers; it is not the universal Automation Hub data layer. OpenAPI is inventory and contract input only, never proof that a route is safe to execute live.
- Current automated live coverage includes `/v1/documents/parse`, `/v1/documents/batch`, and the opt-in cross-group GET smoke lane under `tests/endpoints/get_smoke/`, including maintainer-accepted provisional fraud-status coverage.
- Requests are live, not mocked. `tests/client.py` builds an `httpx.Client` from live environment settings and Google IAP credentials.
- `/parse` and `/documents/batch` use GCS-backed fixtures. `PARSE_FIXTURE_FILE` must remain a `gs://` URI, and batch selection reuses the generated fixture registry.
- The OpenAPI source is `official-openapi.json`. Treat it as the intended contract source and endpoint inventory input, not as automatic ground truth.
- Current OpenAPI drift comparison treats curated observed endpoint response shape as the runtime baseline against `official-openapi.json`, while keeping public API contract status separate from both observed behavior and the checked-in spec. The non-live `tools/reporting/openapi_runtime_drift.py` report currently compares `/parse`, `/documents/batch` envelope, provisional `/documents/fraud-status/{job_id}` top-level, and provisional `GET /monitoring/api/v1/golden-dataset/gcs/types` top-level baselines. `official-openapi.json` now has conservative observed-runtime alignment for fraud-status `fraudJobId`, `fraudStatus`, and `404`, plus monitoring GCS types `types` array shape; fraud terminal result fields, GCS category values, and child GCS endpoint shapes remain loose.
- Current contract coverage is manual and selective through `tests/endpoints/document_contracts.py`, with a narrow static `/parse` OpenAPI alignment guard in `tests/tools/test_official_openapi_parse_contract.py` plus the observed-runtime drift report. No generated OpenAPI validator or whole-response schema validation workflow is active yet.
- Non-live validation isolation is guarded by `tests/tools/test_config_bootstrap.py`, `tests/tools/test_safe_git_commit.py`, and `tests/tools/test_non_live_validation_isolation.py`: offline targets run with `VERIFYIQ_SKIP_DOTENV=1`, safe commit's `non-live` gate targets only `tests/tools/`, `tests/reporting/`, and `tests/skills/`, CI uses the same offline target set, and those target trees avoid direct imports of live parse/batch fixture modules.
- Checked-in CI has two lanes: `.github/workflows/protected-baseline.yml` for the secret-aware protected live baseline, and `.github/workflows/non-live-validation.yml` for offline tooling/reporting/skills validation plus safe runner discovery.
- Offline tooling, reporting, skills, and runner tests are expected to run with `VERIFYIQ_SKIP_DOTENV=1` so they do not require live env bootstrap.
- Repo-local Mind continuity is active for OpenCode and Codex. Active task state belongs in Mind, not repo docs; durable repo truth belongs in tracked docs by scope.

## Active Architecture Direction
- Keep one normal operator entry point: `./.venv/bin/python tools/run_regression.py`.
- Preserve the existing wrappers as delegated engines or compatibility/debug surfaces until parity, docs, CI, direct-use audits, and maintainer approval make removal safe.
- Keep the protected suite lean and parse-only until there is an explicit decision to redefine the default suite.
- Keep broader live coverage opt-in: GET smoke through `--suite smoke`, parse matrix through `--endpoint parse --category matrix`, full parse regression through `--suite full`, and batch through `--endpoint batch`.
- Keep the Automation Hub Expansion behind the canonical runner. The no-argument runner remains the parse-only protected suite, and hub planning must not imply that every endpoint is safe or currently runnable. The `extended` suite currently supports non-live dry-run preview, selector filtering, synthetic report generation, and approved live health-node selectors only: `get-smoke.health.core` for `GET /health` and `get-smoke.health.ready` for `GET /health/ready`.
- Keep `smoke` as the current broad GET smoke lane until `extended` reaches parity. Migration from `smoke` to `extended` requires functional parity, docs parity, CI behavior review, artifact behavior review, direct-use audit, a rollback path, and maintainer approval before smoke tests are renamed, deleted, deprecated, or replaced.
- Reserve future `workflow` for controlled mutation/stateful endpoints. It must stay blocked by default until each workflow has owner approval, non-destructive or reversible setup, isolated target data, cleanup/rollback rules, artifact policy, explicit selectors, non-live planning evidence, and CI exclusion or explicit CI approval.
- Keep category and suite taxonomy practical. Broaden endpoint automation through concrete endpoint-group needs rather than a generic framework ahead of evidence.
- Expand in phases using the endpoint-group onboarding checklist. Each new group needs repo-scope fit, safety class, suite lane, category depth, prerequisites, artifact expectations, runner mapping, CI eligibility, owner/blocker notes, and a default-suite decision.
- Keep document parsing, fraud detection, document-processing, and quality/model-validation surfaces first in the expansion queue. GET smoke is the current opt-in mechanism for safe read-only expansion.
- Keep OpenAPI drift work evidence-backed. Use safe existing run artifacts, summarize field shapes and decisions, and avoid storing raw payloads or secrets in docs.
- Treat `reports/` as disposable generated output. Promote only durable findings into docs and Mind.

## Current Validation Surface
| Surface | Canonical entry point | Current role | Status |
| --- | --- | --- | --- |
| Non-live tooling/reporting/skills | `VERIFYIQ_SKIP_DOTENV=1 ./.venv/bin/python -m pytest tests/tools/ tests/reporting/ tests/skills/ -v` | Safe offline validation for runner, reporting, skills, tooling, and the narrow `/parse` OpenAPI alignment guard | Current CI lane |
| Protected `/parse` baseline | `./.venv/bin/python tools/run_regression.py` | Default live gate; maps to `pytest tests/endpoints/parse/ -v` | Current default |
| Protected structured report | `./.venv/bin/python tools/run_regression.py --report` | Default suite plus structured `reports/regression/` artifacts | Opt-in |
| GET smoke | `./.venv/bin/python tools/run_regression.py --suite smoke` | Cross-group safe GET status coverage, exact-status guards, and bounded artifact-free fraud-status setup coverage | Opt-in |
| Parse matrix | `./.venv/bin/python tools/run_regression.py --endpoint parse --category matrix` | One canonical enabled fixture per registry fileType plus saved matrix summary | Opt-in |
| Focused `/parse` categories | `./.venv/bin/python tools/run_regression.py --endpoint parse --category contract|auth|negative` | Existing protected-suite tests selected by category without duplicating test logic | Opt-in |
| Full parse regression | `./.venv/bin/python tools/run_regression.py --suite full` | Protected baseline followed by matrix wrapper | Opt-in stronger gate |
| Batch validation | `./.venv/bin/python tools/run_regression.py --endpoint batch` | Live `/documents/batch` validation with safe default item limit | Opt-in |
| Focused `/documents/batch` categories | `./.venv/bin/python tools/run_regression.py --endpoint batch --category contract|negative` | Existing batch-suite tests selected by category without duplicating test logic | Opt-in |
| Selected batch fixtures | `./.venv/bin/python tools/run_regression.py --endpoint batch --fixtures-json /path/to/fixtures.json` | Targeted batch fixture execution through delegated wrapper | Opt-in |
| Runner discovery | `./.venv/bin/python tools/run_regression.py --list` and `--dry-run` | Non-executing inventory and command mapping | Safe discovery |
| Automation Hub preview | `./.venv/bin/python tools/run_regression.py --suite extended --dry-run [--report] [--hub-node NODE_ID | --hub-group ENDPOINT_GROUP]` | Non-live dependency graph and reporting-contract preview for the future hub; optional selectors bound the preview to a manifest slice plus prerequisites, and `--report` writes synthetic plan evidence under `reports/hub/` | Safe discovery |
| Automation Hub health nodes | `./.venv/bin/python tools/run_regression.py --suite extended --hub-node get-smoke.health.core` or `./.venv/bin/python tools/run_regression.py --suite extended --hub-node get-smoke.health.ready` | Approved live health-only hub executor tranche; each selector calls exactly one health endpoint and writes metadata-only `reports/hub/<run-id>/run.json` and `run.md` | Opt-in live; do not run without explicit approval |
| Future workflow lane | No command yet | Reserved for controlled mutation/stateful endpoint workflows after explicit safety, cleanup, artifact, selector, owner, and CI gates are met | Not implemented; blocked by default |

## Canonical Planning Decisions
- `protected` currently means parse-only. `smoke` is real but opt-in and is not the default suite.
- `full` currently means a stronger parse gate, not broad repository regression.
- `extended` is the future dependency-aware safe Automation Hub lane. Its current broad live execution remains blocked; only the non-live preview and the two explicit health-node selectors are approved today.
- `workflow` is a future lane name for controlled mutation/stateful endpoint flows. It is not implemented and must not be documented as runnable until the blocked-by-default gates are satisfied.
- Long-term scope is broader multi-endpoint VerifyIQ API automation, but default-suite and CI expansion require explicit future decisions backed by runtime, stability, safety, ownership, and artifact-sensitivity evidence.
- Batch remains opt-in until fixture stability, auth behavior, runtime, and failure ownership justify any protected-suite change.
- Legacy direct pytest and wrapper commands stay documented only as implementation/debug, delegated engine, compatibility/debug, or advanced/internal surfaces.
- Existing parse, batch, matrix, full, reporting wrappers, GET smoke tests, compatibility facades, and generated compatibility copies must not be deleted, renamed, deprecated, or replaced until functional parity, docs parity, CI behavior review, artifact behavior review, direct-use audit, rollback path, and maintainer approval gates are satisfied.
- Do not delete `tools/run_parse_full_regression.py`, `tools/reporting/run_parse_matrix_with_summary.py`, `tools/run_batch_with_fixtures.py`, or `tools/run_parse_with_report.py` until the legacy-deprecation gates in this roadmap are met.
- Do not trust `official-openapi.json` blindly for success schemas while parse and batch `200` schemas remain generic objects.
- Do not add mutating admin, application-management, storage, debug, or UI surfaces to default automation; keep them excluded or safety-blocked unless separately approved with explicit safety classification and ownership.
- Do not normalize live instability with broad retries. Classify failures first and keep retries narrow, explicit, and endpoint-justified.

## Roadmap Phases
| Phase | Status | Scope | Exit signal |
| --- | --- | --- | --- |
| Phase 0: Inventory and guardrails | Largely complete; keep current | Command registry, endpoint inventory, non-live CI, safe discovery, fixture registry visibility | Docs and CI stay aligned as commands and coverage change |
| Phase 1: Suite taxonomy and onboarding rules | In progress | Define suite/category/risk rules for current and future endpoints | New endpoint proposals include safety class, suite lane, categories, fixtures/prereqs, artifacts, runner mapping, CI eligibility, and owner/blocker notes |
| Phase 2: Canonical runner parity | Implemented for current main paths; focused category policy audited | Preserve protected, smoke, full, matrix, focused parse categories, direct batch, focused batch categories, selected batch, list, dry-run, and non-targeted report mappings | Non-live tests prove command, flag, dry-run, env, and return-code behavior for each supported mapping |
| Phase 3: Contract and schema modernization | `/parse` pilot, conservative spec follow-up, static guard, non-live isolation guard, and observed-runtime drift report completed for the first tranche | Compare OpenAPI, tests, and safe observed artifacts for in-scope endpoints | Broaden `/batch` and other endpoint drift work only from safe artifacts, current observed-runtime evidence, or owner-backed questions; owner confirmation gates public-contract promotion rather than characterization |
| Phase 4: Legacy deprecation | Not started | Reduce direct wrapper/operator duplication only after parity and approval | Docs, CI, tests, direct imports, shell-outs, and compatibility expectations no longer require direct wrapper use |
| Phase 5: Reporting and CI maturity | In progress; non-targeted report mappings guarded; batch summary deferred | Keep non-live CI current, govern artifact publishing, improve report parity | CI and local docs tell the same runner story; sensitive live artifacts remain opt-in |
| Phase 6: Endpoint expansion | Phased and risk-gated | Evolve toward broader multi-endpoint VerifyIQ API automation while keeping document-processing surfaces first | New groups enter with explicit scope, safety, category depth, runner mapping, CI eligibility, ownership, and default-suite decision |

## Automation Hub Expansion Roadmap Item
Target state: evolve toward one canonical dependency-aware runner for safe, non-legacy VerifyIQ endpoint automation, still reached through `tools/run_regression.py`. The live suite name is `extended`, but broad execution remains blocked. Today, `--suite extended --dry-run` is available as a non-live dependency graph and reporting-contract preview; it can be filtered with `--hub-node` or `--hub-group` for bounded discovery, `--report` can write synthetic plan evidence, and live execution is approved only for explicit health-node selectors: `--hub-node get-smoke.health.core` and `--hub-node get-smoke.health.ready`.

Master-plan boundaries:
- `tools/run_regression.py` remains the single canonical operator entry point. New hub lanes should be exposed through it, not through a competing operator command.
- `protected` remains the no-argument parse-only default unless a later roadmap decision explicitly changes the default suite.
- `smoke` remains the current broad GET smoke suite while `extended` matures. Treat smoke tests as live coverage that must be preserved until the migration gates below are complete.
- `extended` should become the safe dependency-aware lane for read-only or approved setup-backed endpoints. Broad live execution remains blocked until each node has a safety classification, dependency contract, artifact policy, and validation evidence.
- `workflow` is reserved for future controlled mutation/stateful endpoints. It is blocked by default and not implemented.

Endpoint catalog and data-source model:
- Use `docs/operations/endpoint-coverage-inventory.md` as the durable endpoint-group catalog. Keep exact runnable commands in `docs/operations/command-registry.md` and operational flow in `docs/operations/workflow.md`.
- Use `official-openapi.json` as inventory and contract input only. A path appearing in OpenAPI does not prove that the route is safe, current, non-legacy, reachable in staging, or acceptable to execute live.
- Use the fixture registry as one data source for parse, batch, matrix, and specifically approved fixture-backed producers. Do not make it the universal hub data layer.
- Prefer named producer outputs and consumer inputs over raw response-body coupling. Sensitive identifiers should be represented by aliases, classifications, or redacted metadata in reports.
- Treat live observed evidence as runtime characterization unless an owner or maintainer explicitly promotes it to public contract.

Guardrails:
- Preserve the current parse-only protected default. Hub expansion must be explicit and opt-in until a later approved default-suite decision.
- Include only endpoint groups that have been classified as safe candidates or currently covered. Legacy/excluded, unsafe, admin, destructive, internal/debug, storage-risk, artifact-risk, auth-blocked, owner-unconfirmed, setup-dependent, and unknown endpoints stay out of the future safe hub until classified and approved.
- Model response-derived dependency values as named outputs in a run context, not as raw response-body coupling. Producers should expose validated output names, and consumers should request those names.
- Every executed endpoint/test should produce structured evidence. Raw response-body persistence is allowed only when that endpoint's artifact policy permits it.

Smoke-to-extended migration gates:
- Functional parity: `extended` covers the same intended safe GET/status behavior, setup skips, exact-status assertions, dependency handling, and failure semantics as the smoke coverage it would absorb.
- Docs parity: roadmap, endpoint inventory, command registry, workflow, and any endpoint-specific knowledge-base pages describe the new path and the retained fallback accurately.
- CI behavior review: current CI behavior remains unchanged unless a separate approved CI decision is made.
- Artifact behavior review: hub reports preserve or improve the current smoke artifact policy, including no raw artifacts for artifact-free smoke paths.
- Direct-use audit: checked-in docs, scripts, tests, shell-outs, imports, and known operator notes no longer depend on the old direct path as the primary surface.
- Rollback path: maintainers can re-enable or continue the previous smoke path without code archaeology if the migration regresses.
- Maintainer approval: a maintainer explicitly approves deprecation, rename, deletion, or replacement of smoke tests or compatibility surfaces.

Future workflow lane gates:
- Each workflow has a repo-scope fit, owner approval, safety classification, explicit target environment, and confirmation that mutation/state changes are allowed.
- Setup and cleanup are deterministic, bounded, and either reversible or isolated to disposable data.
- Selectors are explicit and blocked by default; broad workflow execution is not enabled by default or by CI without separate approval.
- Reports define request metadata, response metadata, state changes, cleanup result, redaction/exclusion rules, and artifact retention before live execution.
- Non-live planning and tests prove command mapping, skip behavior, dependency handling, return codes, and artifact contract before any live workflow run.
- Rollback, incident stop conditions, and maintainer approval are documented before implementation.

Phases:
1. Endpoint classification: extend the endpoint inventory with hub planning statuses and evidence needed before safe inclusion.
2. Dependency mapping: identify dependency producers, dependency consumers, named outputs, prerequisite selectors, and skip semantics for each candidate group.
3. Reporting and artifact policy: define run metadata, selected nodes, endpoint result summaries, request metadata, safe response metadata/body policy, timing, dependency inputs/outputs, skips, failures, rerun selectors, and redaction/exclusion rules.
4. Hub runner implementation: add the future runner path behind `tools/run_regression.py` without changing the current protected default or documenting live `extended` execution as runnable before a live mapping exists.
5. Migration and wrapping: keep existing wrappers as delegated engines, compatibility/debug paths, or specialized workflows until equivalent hub coverage and artifact behavior are proven.
6. Validation: prove non-live graph/reporting behavior first, then gate live validation by endpoint safety, runtime, environment needs, and artifact policy.
7. Eventual CI decision: add hub CI only after stability, secret handling, artifact-retention policy, owner expectations, and suite scope are approved.

Existing wrappers and scripts remain until parity, documentation, CI references, direct-use audits, artifact behavior, and maintainer approval are complete. Do not delete, rename, or deprecate wrapper files as part of the documentation-first hub planning tranche.

Health live-capable tranche status: `tools/run_regression.py --suite extended --dry-run` still renders an endpoint-group oriented manifest preview with dependency order, named outputs, dependency skip semantics, artifact policy, and the scaffolded evidence/redaction contract. The manifest splits out `get-smoke.health.core` and `get-smoke.health.ready` as the only approved live nodes, representing `GET /health` and `GET /health/ready` only; broad `get-smoke.safe-read-only` remains delegated/non-live in the hub. Adding `--report` to dry-run writes disposable synthetic plan reports under `reports/hub/<run-id>/run.json` and `run.md`; approved live health-node execution writes metadata-only live reports to the same hub report tree. This path does not broaden the protected default or replace current delegated wrappers.

Next-tranche sequence:
1. Finish catalog normalization: mark each candidate group with suite lane, hub status, safety class, data sources, fixture/prerequisite needs, artifact policy, and owner/blocker notes.
2. Define migration candidates from `smoke` to `extended` without moving them yet. Start with read-only or already smoke-covered endpoints whose dependency inputs are simple and whose artifact policy is metadata-only.
3. Add or update non-live manifest/reporting tests before any broad live execution. Prove dry-run, selector, dependency, skip, and artifact-contract behavior first.
4. Promote one narrow live-safe tranche at a time through explicit selectors, keeping `smoke` as the fallback until parity and approval gates are complete.
5. Defer `workflow` implementation until controlled mutation/stateful endpoint gates are fully documented and approved.
6. Review CI only after local runner behavior, report artifacts, failure ownership, and rollback are proven.

## Next Endpoint-Group Expansion Proposal
Prioritize the `document-processing-adjacent` group, starting with `/v1/documents/fraud-status/{job_id}` as a setup-backed, read-only GET candidate. This keeps expansion aligned with the broader multi-endpoint hub strategy while staying close to the core document parsing and fraud-detection product area.

Confirmed facts:
- `official-openapi.json` exposes four adjacent document-processing routes beyond `/parse` and `/documents/batch`: `POST /v1/documents/check-cache`, `DELETE /v1/documents/cache`, `POST /v1/documents/crosscheck`, and `GET /v1/documents/fraud-status/{job_id}`.
- The current GET smoke lane already supports setup-backed detail endpoints and skip-on-missing-prerequisite behavior.
- The current inventory records `/v1/documents/fraud-status/{job_id}` as maintainer-accepted provisional smoke coverage; previously tried benchmark/monitoring identifiers remain invalid producer sources and returned not-found behavior.
- External API source evidence from `boost-capital/ai-parser-studio` plus the 2026-04-28 VerifyIQ AI assistant answer has refined the non-live design in `docs/knowledge-base/document-processing-adjacent/fraud-status-expansion-plan.md`: fraud job IDs use a strict `fj_` plus 32 lowercase-hex format, job lookup is tenant-scoped through the API key hash, source-backed response shapes exist for `pending`, `running`, `complete`, and `failed`, malformed/missing/expired/wrong-tenant jobs return equivalent `404`, and async scheduling depends on service-side fraud-detection/job-store/background-capacity prerequisites. The AI assistant answer is supporting evidence only, not owner confirmation.
- Observed in bounded staging characterization on 2026-04-27, with no API owner available: one `/parse` request using the protected fixture and hidden/internal `pipeline.async_fraud=true` setup knob returned a format-valid fraud job ID; bounded polling observed `running` then `complete`; invalid-format and artificial valid nonexistent job IDs returned `404`. This is a provisional regression contract only and is not owner-confirmed.
- Maintainer acceptance on 2026-04-28 promotes that provisional contract into smallest opt-in coverage under the GET smoke lane. The test uses one protected-fixture parse producer attempt, polls at most six times with at most ten seconds between polls, writes no raw artifacts, and asserts only status codes, job-id format, allowed statuses, and top-level keys.
- Lane audit on 2026-04-28 keeps fraud-status in GET smoke because the suite is opt-in, dry-run lists the protected parse fixture setup env, the implementation is artifact-free and import-safe without live env, and focused validation can target only `tests/endpoints/get_smoke/test_fraud_status.py`. Move it to an endpoint-specific opt-in lane if runtime, flakiness, skip frequency, artifact needs, or owner-confirmed setup constraints make the cross-group smoke lane too expensive.

Proposal:
- First implementation tranche: implemented as artifact-free, bounded, opt-in GET smoke coverage. Do not add it to the parse-only protected default.
- Minimum categories before promoting the group beyond provisional status: observed-runtime smoke/status signal, conservative top-level shape from safe evidence, auth/validation expectations, and documented negative behavior for invalid or expired job ids. Owner confirmation remains the gate for public-contract promotion, protected/default-suite inclusion, strict deep schemas, artifact policy changes, auth-negative expansion, and long-lived guarantees.
- Deferred within this group: `DELETE /v1/documents/cache` remains mutating; `POST /v1/documents/check-cache` and `POST /v1/documents/crosscheck` need request-shape, fixture, artifact, and owner review before live automation.

## Prioritized Next Work
1. Re-run the opt-in `/documents/batch` tenant-token auth characterization only after auth-layer or staging behavior changes. Keep it out of the default suite and out of mapped batch `auth` until missing and invalid tenant-token requests return confirmed `401` or `403`.
2. Broaden `/documents/batch` OpenAPI drift work beyond the current envelope-only observed-runtime report only when fresh safe batch artifacts or owner-backed contract questions are available; follow the completed `/parse` pilot pattern and keep raw payloads out of docs.
3. Continue observed-runtime characterization for `GET /v1/documents/fraud-status/{job_id}` and provisional `GET /monitoring/api/v1/golden-dataset/gcs/types` only beyond the current top-level OpenAPI alignment when additional safe sanitized evidence exists. Keep owner confirmation as the gate for public-contract promotion, protected/default-suite inclusion, strict complete-result schemas, GCS category-value or child-endpoint schemas, auth-negative expansion, artifact policy changes, and long-lived guarantees.

## Blockers And Deferred Items
- `/documents/batch` auth-negative coverage and `--endpoint batch --category auth` mapping are blocked by live behavior: missing tenant-token requests have timed out, and invalid tenant-token requests have returned `200` and timed out in observed opt-in runs. See `docs/knowledge-base/batch/auth-negative-blocker.md`.
- `/documents/batch` concise runner-summary work is deferred. Existing batch raw artifacts are sensitive, normal batch runs are bounded and assertion-driven, selected-fixture wrapper output already reports selection/chunk/warning context, and broad batch review is covered by the ground-truth export workflow rather than the normal regression runner.
- `/parse` OpenAPI drift pilot evidence is documented from a fresh protected report run, `official-openapi.json` now includes optional `pipeline.use_cache` plus a conservative parse success schema, and the aligned shape is guarded by a narrow non-live JSON inspection test. The observed-runtime drift report compares `/parse`, `/documents/batch` envelope, provisional fraud-status top-level, and provisional monitoring GCS types top-level baselines against the checked-in spec without treating observed behavior as owner-approved contract; the current compared baselines are aligned. Non-live validation isolation is also statically guarded.
- Remaining true GET 200-smoke backlog is limited to three still-blocked endpoints plus one artifact-policy deferred export endpoint: `/v1/admin/cache/stats`, `/monitoring/api/v1/providers`, `/ai-gateway/s3/s3/list`, and `/monitoring/api/v1/golden-dataset/export`. Fraud-status has maintainer-accepted provisional opt-in smoke coverage and can continue observed-runtime characterization from safe top-level evidence, but remains blocked from owner-confirmed status pending producer and contract confirmation; keep exact-status guards for known `401`, `403`, and `502` surfaces. See `docs/operations/endpoint-coverage-inventory.md`.
- Default batch inclusion is deferred until batch auth, runtime, fixture stability, and failure ownership are better characterized.
- Broader live CI lanes are deferred until runtime, stability, ownership, and artifact sensitivity are understood.
- Legacy wrapper deprecation is deferred until all deprecation gates below are satisfied.

## Transition, Refactor, And Deprecation Gates
Before renaming, deleting, deprecating, or replacing smoke tests, wrappers, compatibility facades, generated compatibility copies, or direct wrapper documentation, all of these must be true:
- The canonical runner covers the same use case and preserves required artifact behavior.
- Non-live tests prove command, flag, dry-run, return-code, and env propagation parity.
- At least one approved live validation pass has proven artifact behavior where live validation is appropriate.
- README, workflow, command registry, and CI identify the runner path as canonical and the wrapper as delegated, compatibility/debug, or advanced/internal.
- No checked-in CI, automation, runbook, import, or shell-out requires the direct wrapper command as the primary path.
- Direct imports, shell-outs, tests, and compatibility/debug expectations have been audited separately.
- A rollback path exists and is documented before the old surface is removed.
- A maintainer explicitly approves compaction, deprecation, rename, replacement, or deletion.

Documentation-only validation strategy for this roadmap tranche:
- Do not run live API calls for docs-only Automation Hub planning updates.
- Use `./.venv/bin/python tools/run_regression.py --list`, `./.venv/bin/python tools/run_regression.py --dry-run`, `./.venv/bin/python tools/run_regression.py --suite smoke --dry-run`, and `./.venv/bin/python tools/run_regression.py --suite extended --dry-run` to confirm command discovery without execution.
- Run focused non-live Automation Hub and runner tests with `VERIFYIQ_SKIP_DOTENV=1`.
- Run `git diff --check` and review `git status --short`.

Commit and push policy:
- Documentation-only planning work should not commit or push unless the user explicitly asks for it.
- If a commit is requested, use the guarded flow in `tools/safe_git_commit.py`; for documentation-only changes, prefer `--validation non-live`.
- Push only when explicitly requested and after the intended branch, diff, validation scope, and remote target are clear.

## Historical Context Worth Preserving
- The repository used to have several overlapping planning artifacts. Their current planning content has been consolidated here so agents do not need to search multiple markdown files for progression decisions.
- The canonical runner now lives under `tools/`, not `scripts/`, matching repo-owned executable command convention.
- Protected CI has already cut over to `python tools/run_regression.py --suite protected` while preserving secret-aware skip behavior.
- Non-live CI now protects tooling, reporting, skills, and runner discovery surfaces without live secrets.
- The endpoint coverage inventory and onboarding checklist exist; the remaining work is to keep them current and use them consistently.
- The batch ground-truth export workflow is an operational/reporting workflow, not a default regression lane.

## Preserved References
- Commands and classifications: `docs/operations/command-registry.md`
- End-to-end operator flow: `docs/operations/workflow.md`
- Endpoint group coverage and GET deferrals: `docs/operations/endpoint-coverage-inventory.md`
- Matrix triage: `docs/operations/matrix.md`
- Batch ground-truth export runbook: `docs/operations/batch-ground-truth-export.md`
- Mind workflow: `docs/operations/mind-session.md` and pointer-only `docs/operations/current-handoff.md`
- `/parse` durable knowledge: `docs/knowledge-base/parse/`
- `/batch` durable blockers and GT findings: `docs/knowledge-base/batch/`

## Roadmap Maintenance Rules
- Update this file whenever project sequencing, priorities, blockers, default-suite policy, endpoint-expansion direction, or deprecation state changes.
- Keep this file concise. Link to runbooks and durable findings instead of copying command encyclopedias, raw audits, or transcript-style notes.
- When docs disagree, trust current code, tests, CI, runner behavior, and current docs in that order.
- For documentation-only roadmap changes, do not run live API tests. Use safe discovery, grep/reference checks, markdown review, and non-live pytest only when relevant.
