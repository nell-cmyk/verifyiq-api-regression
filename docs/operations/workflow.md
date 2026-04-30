# Workflow

## Purpose / Scope
Use this file as the canonical operator runbook for the current root checkout.

Use it for the normal end-to-end flow:
- read the roadmap
- inspect the repo surfaces the task touches
- set up the repo
- recover active context from Mind
- run the protected baseline
- opt into GET smoke when touching cross-group GET coverage
- opt into matrix or full regression when needed
- review artifacts
- use the guarded Git flow

Use [Command Registry](command-registry.md) for command classification, [Repo Roadmap](../knowledge-base/repo-roadmap.md) for planning and future-development direction, [Endpoint Coverage Inventory](endpoint-coverage-inventory.md) for current suite breadth, and [Matrix Triage](matrix.md) for deeper matrix-specific triage details.

Planning governance for development work lives in `AGENTS.md`: use `docs/knowledge-base/repo-roadmap.md` as the planning source of truth, and treat the repo itself as the source of truth for current implementation details.

## Prerequisites
### Python deps
Create the repo-local virtualenv once, then install the base deps:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

Install tool-only deps only if you need fixture-registry generation:

```bash
./.venv/bin/python -m pip install -r tools/requirements.txt
```

### Mind bootstrap
Install Mind once for local workflow memory, OpenCode integration, and repo-local Codex support:

```bash
curl -fsSL https://raw.githubusercontent.com/GabrielMartinMoran/mind/main/scripts/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"
mind help
mind setup opencode
```

The repo's normal OpenCode path is automatic after that. Repo-local session automation loads from `.opencode/opencode.json` and is documented in [Mind Session](mind-session.md).

For Codex in this repo, no extra global `mind setup codex` step is required. Trust the repo so Codex can load the checked-in `.codex/config.toml` and `.codex/hooks.json` layers.

Create the project space once only if you are debugging the wrapper before the automatic flow has done it for you:

```bash
mind create "projects/verifyiq-api-regression" "Persistent memory for VerifyIQ API regression automation" --tags "type:project"
```

Optional local Mind access surfaces:

```bash
mind serve start --detached
mind mcp start --http --detached
mind server-status
```

### Env setup
Copy `.env.example` to `.env`, then fill in the current environment values.

At a high level, the repo expects:
- live `/parse` environment settings such as `BASE_URL`, `TENANT_TOKEN`, and `API_KEY`
- Google IAP access configured through `IAP_CLIENT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`
- a valid GCS-backed happy-path fixture via `PARSE_FIXTURE_FILE`
- the matching request `fileType` via `PARSE_FIXTURE_FILE_TYPE`

### Live test prerequisites
- `PARSE_FIXTURE_FILE` must be a `gs://` URI.
- `/parse` happy-path tests use live API access; keep environment values aligned with the current target.
- The matrix remains opt-in; do not treat it as part of the default baseline.

## Non-live Validation
Canonical non-live validation for runner, reporting, and tooling changes:

```bash
VERIFYIQ_SKIP_DOTENV=1 ./.venv/bin/python -m pytest tests/tools/ tests/reporting/ tests/skills/ -v
```

Use it:
- before touching live suites when the change is purely tooling, reporting, docs-adjacent runner behavior, or automation infrastructure
- to prove the offline suites do not depend on `.env`, API secrets, or IAP bootstrap
- as the default CI lane for non-live repo validation

Safe runner discovery checks:

```bash
./.venv/bin/python tools/run_regression.py --list
./.venv/bin/python tools/run_regression.py --dry-run
./.venv/bin/python tools/run_regression.py --suite smoke --dry-run
./.venv/bin/python tools/run_regression.py --suite extended --dry-run
./.venv/bin/python tools/run_regression.py --suite extended --dry-run --hub-node get-smoke.health.core
./.venv/bin/python tools/run_regression.py --suite extended --dry-run --hub-node get-smoke.health.ready
./.venv/bin/python tools/run_regression.py --suite extended --dry-run --hub-group get-smoke
./.venv/bin/python tools/run_regression.py --suite extended --dry-run --report
```

The `extended` dry-run commands above are non-live Automation Hub previews only. `--hub-node` and `--hub-group` filter discovery output to bounded manifest slices plus required prerequisites, but they do not prove live endpoint safety. Adding `--report` writes synthetic plan evidence under `reports/hub/` without endpoint calls or raw runtime evidence. Live `extended` execution is approved only for explicit health-node selectors: `./.venv/bin/python tools/run_regression.py --suite extended --hub-node get-smoke.health.core` calls `GET /health` only, and `./.venv/bin/python tools/run_regression.py --suite extended --hub-node get-smoke.health.ready` calls `GET /health/ready` only. Do not run either without explicit live validation approval.

Non-live OpenAPI drift report for curated observed runtime baselines:

```bash
VERIFYIQ_SKIP_DOTENV=1 ./.venv/bin/python tools/reporting/openapi_runtime_drift.py
```

Use it to compare current safe observed response-shape baselines against
`official-openapi.json`. Findings are observed runtime/spec drift only; they do
not automatically promote the observed shape to owner-approved public contract.
Provisional GET shapes such as fraud-status and monitoring GCS types may be
compared when the evidence is sanitized and artifact-free; deep terminal result
fields, GCS category values, and child endpoint shapes remain loose until
broader safe evidence or owner confirmation exists.

## Automation Hub Master Plan
Suite taxonomy:
- `protected` remains the no-argument parse-only default through `tools/run_regression.py`.
- `smoke` remains the current broad opt-in GET smoke suite until `extended` reaches parity and is approved as a replacement for any covered slice.
- `extended` is the future safe dependency-aware Automation Hub lane. Current broad live execution remains blocked; only non-live dry-run planning and the two explicit health-node selectors are approved today.
- `full` remains a stronger parse gate, not a broad all-endpoint regression.
- `workflow` is a future blocked-by-default lane for controlled mutation/stateful endpoints. It is not implemented and has no runnable command.

Endpoint catalog and data-source model:
- Use `docs/operations/endpoint-coverage-inventory.md` for endpoint-group catalog decisions.
- Use `official-openapi.json` as inventory and contract input only, not proof that a route is safe to execute.
- Use the fixture registry as one data source for parse, batch, matrix, and approved fixture-backed producers, not as the universal hub data layer.
- Model dependency values as named outputs and inputs with redacted reporting; do not couple consumers to raw response bodies.

Smoke-to-extended migration gates:
- Keep existing smoke tests and direct smoke validation available until functional parity, docs parity, CI behavior review, artifact behavior review, direct-use audit, rollback path, and maintainer approval are complete.
- Do not delete, rename, deprecate, or replace smoke tests, wrappers, compatibility facades, or generated compatibility copies as part of planning-only work.
- Default CI behavior does not change unless a separate approved CI decision changes it.

Future workflow lane gates:
- Treat mutation/stateful endpoints as blocked by default until owner approval, safe target data, setup, cleanup, rollback, artifact policy, explicit selectors, non-live validation, and CI policy are documented.
- Do not document workflow as runnable until implementation and maintainer approval exist.

Validation strategy for documentation-only hub planning:
- Use safe discovery and dry-run commands only; do not run live API calls.
- Run focused non-live runner and Automation Hub tests with `VERIFYIQ_SKIP_DOTENV=1`.
- Use `git diff --check` and `git status --short` to confirm formatting and scope.

Tranche sizing for documentation-only hub planning:
- Prefer the smallest coherent pass that completes a clearly supported catalog or planning unit. Do not split safe catalog normalization into one-line commits solely for narrowness.
- A broader docs-only pass is acceptable when every edit is backed by current repo evidence, stays in the approved planning/docs surface, preserves smoke coverage, and does not approve manifest, runner, CI, OpenAPI, report-generation, body-persistence, or live-execution changes.
- Stop at the first unsupported or approval-dependent boundary instead of padding the pass with speculative readiness language.

Next-tranche sequence:
1. Keep endpoint catalog normalization current as new evidence or endpoint groups appear; the current endpoint-group catalog is normalized.
2. Identify the next smoke-covered read-only candidate slice for `extended` without moving current `smoke` coverage or starting a new endpoint tranche by default.
3. Prove dry-run, selector, dependency, skip, blocked-live, and report behavior through non-live tests only for documented candidate slices.
4. Promote one narrow live-safe tranche at a time behind explicit selectors only after approval and a documented rollback path.
5. Leave `workflow` deferred until its blocked-by-default gates are approved.

Automatic `Next Prompt` continuity:
- After completing an Automation Hub master-plan tranche or pass, include a copy-ready `Next Prompt` block in the final response unless the user explicitly opts out.
- This automatic prompt is scoped to Automation Hub master-plan work only. Do not emit it just because `docs/knowledge-base/repo-roadmap.md` changed for ordinary roadmap maintenance, audit-only work, commit/push-only work, unrelated endpoint findings, or one-off doc corrections.
- Generate the prompt after validation and final repo-state inspection. Check `git status --short`, re-read the Automation Hub roadmap section plus relevant operations docs, and use the actual final state rather than earlier assumptions.
- Include a commit SHA only when this pass created one. If the work is uncommitted, say so in the prompt's current-state line.
- The prompt should tell the next session to inspect `AGENTS.md`, `docs/knowledge-base/repo-roadmap.md`, `docs/operations/workflow.md`, `docs/operations/command-registry.md`, and `docs/operations/endpoint-coverage-inventory.md` before editing.
- The prompt must preserve the master-plan guardrails: `tools/run_regression.py` remains canonical; `protected` remains the parse-only default; `smoke` remains preserved until `extended` reaches parity and approval gates; broad live `extended` remains blocked except approved explicit health-node selectors; `workflow` remains future blocked-by-default unless approved groundwork is the selected tranche; and smoke tests, wrappers, compatibility facades, generated compatibility copies, and direct wrapper docs must not be renamed, deleted, deprecated, or replaced before the documented gates are satisfied. It should ask for the next smallest coherent pass, not an artificially one-line task.
- The prompt should default to implement plus validate, with no commit or push unless the user explicitly asks.

## Normal Development Flow
1. Install deps and configure `.env` for the current target.
2. Install Mind and run `mind setup opencode` if this machine has not been bootstrapped yet.
3. Open this repo in OpenCode or Codex.
4. OpenCode automatically recovers context, refreshes checkpoints on continuity events, and closes the active checkpoint on session end. Codex automatically recovers context and refreshes checkpoints around each turn, but still requires an explicit `finish` before handoff or commit.
5. If you need to validate or repair that automation explicitly, use the repo wrapper instead of raw mutating `mind` commands:

```bash
./.venv/bin/python tools/mind_session.py doctor
./.venv/bin/python tools/mind_session.py start
```

6. Read `docs/knowledge-base/repo-roadmap.md`, identify the roadmap phase, milestone, or next step the task advances, and inspect the relevant repo files before editing. If the task does not map cleanly, update the roadmap before or alongside the work.
7. Make a narrow repo change aligned with the roadmap and the current repo state.
8. Run the relevant validation command for the change. Use the non-live suite first for tooling/reporting changes, and use the canonical protected runner by default for live validation:

```bash
VERIFYIQ_SKIP_DOTENV=1 ./.venv/bin/python -m pytest tests/tools/ tests/reporting/ tests/skills/ -v
./.venv/bin/python tools/run_regression.py
```

9. If the change touches broader `/parse` coverage, reporting, fixture mapping, or matrix triage, run the canonical runner matrix selection:

```bash
./.venv/bin/python tools/run_regression.py --endpoint parse --category matrix
```

10. If the change needs a focused existing `/parse` category selection, use the canonical category mapping:

```bash
./.venv/bin/python tools/run_regression.py --endpoint parse --category contract
./.venv/bin/python tools/run_regression.py --endpoint parse --category auth
./.venv/bin/python tools/run_regression.py --endpoint parse --category negative
```

11. If you want the stronger explicit gate, run full regression:

```bash
./.venv/bin/python tools/run_regression.py --suite full
```

12. If the change touches the GET smoke lane or cross-group GET coverage, run the canonical smoke suite:

```bash
./.venv/bin/python tools/run_regression.py --suite smoke
```

13. If the change touches `/documents/batch` tests, fixtures, or selected-fixture wrapper behavior, use the canonical batch selection:

```bash
./.venv/bin/python tools/run_regression.py --endpoint batch
./.venv/bin/python tools/run_regression.py --endpoint batch --category contract
./.venv/bin/python tools/run_regression.py --endpoint batch --category negative
./.venv/bin/python tools/run_regression.py --endpoint batch --fixtures-json /path/to/fixtures.json
```

14. Review generated artifacts from the validation surface you used.
15. If the task produced durable repo truth, promote it automatically in the same pass instead of leaving it only in Mind. Update `docs/knowledge-base/repo-roadmap.md` for project status and sequencing, `docs/operations/*` for command/workflow changes, `docs/knowledge-base/*` for durable findings, and `AGENTS.md` only for stable repo-wide rules.
16. Before handoff or commit, the agent should save an explicit durable Mind summary when needed and run the repo-local finish step. In Codex this remains explicit, but it should not be left for the user to remember:

```bash
./.venv/bin/python tools/mind_session.py save-summary --title "short-title" --body "Durable summary"
./.venv/bin/python tools/mind_session.py finish
```

17. Review the diff, stage the intended files, and use the guarded Git flow:

```bash
./.venv/bin/python tools/safe_git_commit.py --message "Describe the reviewed change"
```

## Protected Baseline
Mandatory default validation surface:

```bash
./.venv/bin/python tools/run_regression.py
```

Optional protected structured reporting:

```bash
./.venv/bin/python tools/run_regression.py --report
```

Exact underlying implementation/debug path:

```bash
./.venv/bin/python -m pytest tests/endpoints/parse/ -v
```

Use it:
- for ordinary `/parse` changes
- before handoff or merge when baseline validation is needed
- as the default validation gate unless a task explicitly calls for broader coverage
- with `--report` when you need the same protected baseline plus structured `reports/regression/` artifacts

Current default-suite rule:
- `tools/run_regression.py` currently maps to the parse-only protected suite.
- `tools/run_regression.py --report` keeps the protected suite selection and delegates only to the existing baseline reporting helper.
- `smoke` is now a real opt-in GET suite, not a broader current default.

Do not replace this with the matrix or full regression by default.

Baseline response artifacts:
- `reports/parse/responses/parse_<timestamp>/<test-case-id>__<description>__<timestamp>_<seq>.json`
- one raw JSON file per `/v1/documents/parse` call, grouped into one per-run folder under `reports/parse/responses/`
- supported `/batch` runs also write one raw response artifact per `/v1/documents/batch` call to `reports/batch/batch_<timestamp>/batch_<timestamp>_<seq>.json`

## GET Smoke Flow
Canonical opt-in GET smoke surface:

```bash
./.venv/bin/python tools/run_regression.py --suite smoke
```

Exact underlying implementation/debug path:

```bash
./.venv/bin/python -m pytest tests/endpoints/get_smoke/ -v
```

Use it:
- when touching GET smoke coverage or expanding safely testable GET coverage beyond `parse` and `batch`
- when you need the current GET smoke signal for covered endpoints, including the small exact-status guard set for known non-200 surfaces
- when validating maintainer-accepted provisional fraud-status coverage; use the narrow pytest node when only that endpoint changed

Current suite rule:
- `smoke` is opt-in.
- no-argument `tools/run_regression.py` still maps to the parse-only protected suite.
- fraud-status smoke coverage uses one protected-fixture `/parse` setup request with `pipeline.async_fraud=true`, writes no raw artifacts, polls at most six times with at most ten seconds between polls, and skips only when the producer returns `200` without a usable `fraudJobId`.
- setup-dependent, query-dependent, auth-blocked, and otherwise deferred GET endpoints stay out of this suite until they have a legitimate 200 path.
- Setup-backed detail tests may skip only when their prerequisite list endpoint succeeds but returns no usable identifier data. Bad list status, malformed list payloads, and no-path list endpoints still fail/assert normally.

## Matrix Flow
Canonical opt-in matrix surface:

```bash
./.venv/bin/python tools/run_regression.py --endpoint parse --category matrix
```

Use it:
- when you need broader `/parse` fileType coverage
- when triaging matrix-only behavior
- when you want saved terminal output plus the rendered matrix summary

Optional structured reporting:

```bash
./.venv/bin/python tools/run_regression.py --endpoint parse --category matrix --report
```

Delegated engine and compatibility/debug path:

```bash
./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py
```

Use [Matrix Triage](matrix.md) for deeper matrix-specific debugging guidance.

## Parse Category Flow
Canonical focused `/parse` category surfaces:

```bash
./.venv/bin/python tools/run_regression.py --endpoint parse --category contract
./.venv/bin/python tools/run_regression.py --endpoint parse --category auth
./.venv/bin/python tools/run_regression.py --endpoint parse --category negative
```

Use them:
- when you want a narrower opt-in slice of the existing protected parse tests
- when a change is category-specific and does not need the whole protected baseline
- with `--dry-run` first when you only need to inspect mapped node IDs

Current mapping notes:
- `contract` targets existing successful response shape checks plus the current HTTPValidationError shape check.
- `auth` targets existing tenant-token auth-negative checks.
- `negative` targets existing missing-file, missing-fileType, empty-body, and validation-shape checks.
- `matrix` remains separate because it is an opt-in fileType breadth lane with wrapper-managed `RUN_PARSE_MATRIX=1`.

## Full Regression Flow
Canonical stronger gate:

```bash
./.venv/bin/python tools/run_regression.py --suite full
```

Exact underlying implementation/debug path:

```bash
./.venv/bin/python tools/run_parse_full_regression.py
```

Use it:
- when you want protected baseline first, then the opt-in matrix wrapper
- when a change needs a stronger explicit validation pass than the default baseline alone

Optional structured reporting:

```bash
./.venv/bin/python tools/run_regression.py --suite full --report
```

## Batch Validation Flow
Canonical opt-in batch surface:

```bash
./.venv/bin/python tools/run_regression.py --endpoint batch
```

Selected-fixture batch surface:

```bash
./.venv/bin/python tools/run_regression.py --endpoint batch --fixtures-json /path/to/fixtures.json
```

Focused batch category surfaces:

```bash
./.venv/bin/python tools/run_regression.py --endpoint batch --category contract
./.venv/bin/python tools/run_regression.py --endpoint batch --category negative
```

Delegated engines and compatibility/debug paths:

```bash
./.venv/bin/python -m pytest tests/endpoints/batch/ -v
./.venv/bin/python tools/run_batch_with_fixtures.py --fixtures-json /path/to/fixtures.json
```

Keep batch opt-in. Do not add `/documents/batch` to the default no-argument runner unless the roadmap explicitly changes the protected suite definition.

Current mapping notes:
- `contract` targets existing top-level structure, summary accounting, result order, per-item contract, and calculatedFields stub guard checks.
- `negative` targets existing missing-items, empty-items, over-limit, malformed-item, and unsupported-fileType partial-failure checks.
- `auth` is intentionally not mapped for `/documents/batch` while the auth-negative blocker remains open.

## Batch Auth Characterization
The default `/documents/batch` suite stays green by excluding the currently
blocked tenant-token auth characterization from normal collection. Opt in only
when you want to re-check that blocker explicitly:

```bash
RUN_BATCH_AUTH_CHARACTERIZATION=1 ./.venv/bin/python -m pytest tests/endpoints/batch/test_batch_auth_characterization.py -v
```

Use it:
- when you need fresh evidence about the current `batch` auth blocker
- when auth-layer or staging behavior may have changed

Current blocker note:
- `docs/knowledge-base/batch/auth-negative-blocker.md`

Do not treat timeout, transport failure, or an unexpected `200` as passing auth
coverage; this path is only complete when missing and invalid
`X-Tenant-Token` return confirmed `401` or `403` responses.

## Batch Ground-Truth Export
Use the dedicated batch ground-truth export workflow when you want one workbook
per fileType for comparison or model-improvement review:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx
```

Use `--file-type` to limit the run:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx \
  --file-type Payslip \
  --file-type TIN,ACR
```

Use `--plan` to inspect discovered fileTypes, skipped unsupported rows, and
planned chunk counts without calling the live endpoint:

```bash
./.venv/bin/python tools/reporting/export_batch_ground_truth.py \
  --reference-workbook /absolute/path/to/reference.xlsx \
  --plan
```

Default outputs land under:
- `reports/batch_ground_truth/batch_ground_truth_<timestamp>/workbooks/*.xlsx`
- `reports/batch_ground_truth/batch_ground_truth_<timestamp>/manifest.json`
- raw batch response artifacts continue under `reports/batch/batch_<timestamp>/...`

See [Batch Ground-Truth Export](batch-ground-truth-export.md) for the full
operator notes on inclusion, failure rows, and heterogeneous response mapping.

## Reporting And Artifact Review
Baseline artifacts:
- `reports/parse/responses/parse_<timestamp>/<test-case-id>__<description>__<timestamp>_<seq>.json`
- `reports/batch/batch_<timestamp>/batch_<timestamp>_<seq>.json` for supported `/batch` runs

Default matrix/reporting artifacts:
- `reports/parse/matrix/latest-terminal.txt`
- `reports/parse/matrix/latest-summary.md`

Optional structured report artifacts when `--report` is enabled:
- `reports/regression/<timestamp>/report.json`
- `reports/regression/<timestamp>/report.md`
- `reports/regression/LATEST.txt`

Automation Hub report artifacts when `--suite extended --dry-run --report` or an approved live health-node selector is enabled:
- `reports/hub/<run-id>/run.json`
- `reports/hub/<run-id>/run.md`
- `reports/hub/LATEST.txt`

Default operator expectation:
- protected structured reporting should use `./.venv/bin/python tools/run_regression.py --report`
- normal matrix runs should use `./.venv/bin/python tools/run_regression.py --endpoint parse --category matrix`
- matrix and full structured reporting should add `--report` to their canonical runner commands
- deeper rerendering and targeted reporting commands are secondary; see the [Command Registry](command-registry.md)

Protected CI artifact upload:
- `.github/workflows/protected-baseline.yml` uploads raw `reports/parse/responses/` artifacts only when repository variable `UPLOAD_PROTECTED_PARSE_ARTIFACTS` is exactly `true`.
- Uploaded artifacts are raw and unredacted, so leave upload disabled unless the run environment and artifact access are appropriate.
- Retention is 7 days, and protected suite selection remains unchanged.

## Registry Refresh Rules
Run fixture-registry generation only when the curated source data has intentionally changed:

```bash
./.venv/bin/python tools/generate_fixture_registry.py
```

Use it:
- after deliberate edits to `tools/fixture_registry_source/qa_fixture_registry.xlsx`
- after deliberate edits to `tools/fixture_registry_source/supplemental_fixture_registry.yaml`
- when the generated YAML must be refreshed to match the curated sources

Use JSON onboarding when a new fixture list arrives as a JSON file of `gs://` paths:

```bash
./.venv/bin/python tools/onboard_fixture_json.py --json path/to/fixtures.json
```

This command:
- checks the JSON input against the current registry flow
- skips unsupported file formats explicitly before onboarding
- writes only missing supported fixtures into `tools/fixture_registry_source/supplemental_fixture_registry.yaml`
- regenerates `tests/fixtures/fixture_registry.yaml` and the generated `/parse` compatibility copy at `tests/endpoints/parse/fixture_registry.yaml` only when additions are required

Do not use it:
- as part of ordinary baseline or matrix runs
- as part of routine triage when the spreadsheet did not change

## Triage Flow
- Start from the latest terminal output, not from assumptions.
- Use the protected baseline first unless the issue is clearly matrix-scoped.
- If the issue is matrix-scoped, use the canonical runner matrix selection and review the saved artifacts.
- For matrix-specific evidence rules and fileType triage, use [Matrix Triage](matrix.md).

## Safe Git Flow
- Review the diff first.
- Stage only the intended files.
- Use `./.venv/bin/python tools/safe_git_commit.py --message "Describe the reviewed change"` for the guarded mechanical commit step.
- Use `--validation non-live` for documentation, tooling, reporting, or skills changes where live API validation is intentionally out of scope.
- Use `--validation full` only when the stronger full-regression gate is intentionally required.
- Do not commit or push unless the user explicitly asks for it.
- Use `--push` only when explicitly requested and when you are ready to push to the current branch's matching upstream.

## Active Session State
- Mind now replaces `docs/operations/current-handoff.md` for active state, handoff, working context, and ongoing task tracking.
- Canonical project space: `projects/verifyiq-api-regression`.
- `mind setup opencode` installs the global Mind MCP and protocol wiring for OpenCode.
- `.opencode/opencode.json` adds the repo-local OpenCode plugin and skill that automate start, checkpoint refresh, compaction continuity, and finish handling.
- Trusted `.codex/config.toml` and `.codex/hooks.json` add the repo-local Codex MCP plus checkpoint-continuity wiring.
- `./.venv/bin/python tools/mind_session.py ...` is the fallback/debug surface when the automatic flow needs inspection or an explicit durable summary.
- Optional local web and API access is available through `mind serve start --detached` on `http://localhost:30303`.
- Optional local HTTP MCP access is available through `mind mcp start --http --detached` on `http://localhost:7438/mcp`.
- Keep active status and working context in Mind, not in repo docs.
- Promote only durable truth into the repo: governance to `AGENTS.md`, stable runbooks to `docs/operations/*`, and validated findings to `docs/knowledge-base/*`.
- `docs/operations/current-handoff.md` is pointer-only and must not hold live task state.

## Session Lifecycle
1. Start: OpenCode loads the repo-local plugin, and Codex loads the trusted repo-local config plus hooks. Both paths recover or create the active continuity checkpoint automatically.
2. Continue: OpenCode refreshes checkpoints on its continuity events, and Codex refreshes checkpoints around each turn. Use `tools/mind_session.py save-summary` only when you need an explicit durable project memory before handoff or commit.
3. End: OpenCode runs `tools/mind_session.py finish` on session end. Codex does not expose an equivalent session-end hook here, so run `tools/mind_session.py finish` explicitly before handoff or commit. Promote any durable truths into repo docs in the same pass.

## Mind Troubleshooting
- `mind` not found: ensure `~/.local/bin` is on `PATH`. If the launcher shim is missing or stale on this machine, use `~/.local/share/mind/mind` directly.
- Repo plugin not loading: inspect `.opencode/opencode.json`, then run `opencode debug config` from the repo root.
- Codex project config not loading: trust the repo, inspect `.codex/config.toml` and `.codex/hooks.json`, then restart Codex.
- Wrapper health check: run `./.venv/bin/python tools/mind_session.py doctor`.
- Force explicit recovery: run `./.venv/bin/python tools/mind_session.py start`.
- Force explicit checkpoint refresh: run `./.venv/bin/python tools/mind_session.py checkpoint`.
- Need an explicit durable summary before handoff or commit: run `./.venv/bin/python tools/mind_session.py save-summary ...` or `finish`.
- Need the web UI or HTTP API: run `mind serve start --detached`, then browse `http://localhost:30303`. Stop it with `mind serve stop`.
- Need the HTTP MCP endpoint: run `mind mcp start --http --detached`, confirm with `mind server-status`, and stop it with `mind mcp stop`.
- Active context still looks stale after `start`: use raw `mind search "<keywords>" --space "projects/verifyiq-api-regression" --detail` as a troubleshooting fallback.
- The project space does not exist yet: the wrapper should create it automatically, but `mind create "projects/verifyiq-api-regression" "Persistent memory for VerifyIQ API regression automation" --tags "type:project"` remains available as a last-resort fallback.
- Multiple `mind` commands fail with `SQLITE_BUSY_RECOVERY`: rerun them sequentially instead of in parallel; Mind uses a local SQLite store and the wrapper already serializes access.

## What Not To Use By Default
- Do not use direct matrix pytest with manual `RUN_PARSE_MATRIX=1` as the normal operator path; use the matrix wrapper instead.
- Do not use `./.venv/bin/python tools/run_parse_with_report.py ...` as the default workflow; use `tools/run_regression.py --report` for normal protected structured reports, and keep the helper for advanced/internal targeting.
- Do not use `./.venv/bin/python tools/reporting/render_regression_summary.py ...` as a substitute for the normal matrix wrapper; it is for saved-output rerendering.
- Do not use historical `.codex` reporting paths from old notes or old artifacts; the current reporting surface is `tools/reporting/*` only.
- Do not rebuild a repo-local note-taking workflow around Obsidian or transcript watchers; Mind is now the canonical memory and continuity layer.
