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

Use [Command Registry](command-registry.md) for command classification, [Regression Runner Plan](regression-runner-plan.md) for the canonical-runner consolidation design, [Endpoint Coverage Inventory](endpoint-coverage-inventory.md) for current suite breadth, and [Matrix Triage](matrix.md) for deeper matrix-specific triage details.

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
```

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

10. If you want the stronger explicit gate, run full regression:

```bash
./.venv/bin/python tools/run_regression.py --suite full
```

11. If the change touches the GET smoke lane or cross-group GET coverage, run the canonical smoke suite:

```bash
./.venv/bin/python tools/run_regression.py --suite smoke
```

12. If the change touches `/documents/batch` tests, fixtures, or selected-fixture wrapper behavior, use the canonical batch selection:

```bash
./.venv/bin/python tools/run_regression.py --endpoint batch
./.venv/bin/python tools/run_regression.py --endpoint batch --fixtures-json /path/to/fixtures.json
```

13. Review generated artifacts from the validation surface you used.
14. If the task produced durable repo truth, promote it automatically in the same pass instead of leaving it only in Mind. Update `docs/knowledge-base/repo-roadmap.md` for project status and sequencing, `docs/operations/*` for command/workflow changes, `docs/knowledge-base/*` for durable findings, and `AGENTS.md` only for stable repo-wide rules.
15. Before handoff or commit, the agent should save an explicit durable Mind summary when needed and run the repo-local finish step. In Codex this remains explicit, but it should not be left for the user to remember:

```bash
./.venv/bin/python tools/mind_session.py save-summary --title "short-title" --body "Durable summary"
./.venv/bin/python tools/mind_session.py finish
```

16. Review the diff, stage the intended files, and use the guarded Git flow:

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

Current suite rule:
- `smoke` is opt-in.
- no-argument `tools/run_regression.py` still maps to the parse-only protected suite.
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

Delegated engines and compatibility/debug paths:

```bash
./.venv/bin/python -m pytest tests/endpoints/batch/ -v
./.venv/bin/python tools/run_batch_with_fixtures.py --fixtures-json /path/to/fixtures.json
```

Keep batch opt-in. Do not add `/documents/batch` to the default no-argument runner unless the roadmap explicitly changes the protected suite definition.

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
- Use `--validation full` only when the stronger full-regression gate is intentionally required.
- Use `--push` only when you are ready to push to the current branch's matching upstream.

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
