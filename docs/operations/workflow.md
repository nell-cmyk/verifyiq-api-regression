# Workflow

## Purpose / Scope
Use this file as the canonical operator runbook for the current root checkout.

Use it for the normal end-to-end flow:
- set up the repo
- recover active context from Mind
- run the protected baseline
- opt into matrix or full regression when needed
- review artifacts
- use the guarded Git flow

Use [Command Registry](command-registry.md) for command classification and [Matrix Triage](matrix.md) for deeper matrix-specific triage details.

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
Install Mind once for local workflow memory and OpenCode integration:

```bash
curl -fsSL https://raw.githubusercontent.com/GabrielMartinMoran/mind/main/scripts/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"
mind help
mind setup opencode
```

Create the project space once if it does not already exist:

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

## Normal Development Flow
1. Install deps and configure `.env` for the current target.
2. Install Mind and run `mind setup opencode` if this machine has not been bootstrapped yet.
3. Recover active context from Mind before changing code:

```bash
mind checkpoint list "projects/verifyiq-api-regression" --status active
mind checkpoint recover "projects/verifyiq-api-regression" --name <checkpoint-name>
mind search "<task keywords>" --space "projects/verifyiq-api-regression" --detail
```

4. If no active checkpoint exists yet for the current work, create or refresh one:

```bash
mind checkpoint set "projects/verifyiq-api-regression" "Goal" "Pending work" --notes "Current status"
```

5. Do normal work in OpenCode. After each significant decision, bug fix, pattern, or durable discovery, persist it in Mind:

```bash
mind add "projects/verifyiq-api-regression" "memory-name" "What: ... Why: ... Where: ... Learned: ..." --tags "cat:decision"
```

6. Make a narrow repo change.
7. Run the protected baseline:

```bash
./.venv/bin/python -m pytest tests/endpoints/parse/ -v
```

8. If the change touches broader `/parse` coverage, reporting, fixture mapping, or matrix triage, run the canonical matrix wrapper:

```bash
./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py
```

9. If you want the stronger explicit gate, run full regression:

```bash
./.venv/bin/python tools/run_parse_full_regression.py
```

10. Review generated artifacts from the validation surface you used.
11. Refresh or close the active checkpoint once the work segment is complete:

```bash
mind checkpoint list "projects/verifyiq-api-regression" --status active
mind checkpoint complete "projects/verifyiq-api-regression" "<checkpoint-name>" "Completed work summary"
```

12. Review the diff, stage the intended files, and use the guarded Git flow:

```bash
./.venv/bin/python tools/safe_git_commit.py --message "Describe the reviewed change"
```

## Protected Baseline
Mandatory default validation surface:

```bash
./.venv/bin/python -m pytest tests/endpoints/parse/ -v
```

Use it:
- for ordinary `/parse` changes
- before handoff or merge when baseline validation is needed
- as the default validation gate unless a task explicitly calls for broader coverage

Do not replace this with the matrix or full regression by default.

Baseline response artifacts:
- `reports/parse/responses/parse_<timestamp>/<test-case-id>__<description>__<timestamp>_<seq>.json`
- one raw JSON file per `/v1/documents/parse` call, grouped into one per-run folder under `reports/parse/responses/`
- supported `/batch` runs also write one raw response artifact per `/v1/documents/batch` call to `reports/batch/batch_<timestamp>/batch_<timestamp>_<seq>.json`

## Matrix Flow
Canonical opt-in matrix surface:

```bash
./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py
```

Use it:
- when you need broader `/parse` fileType coverage
- when triaging matrix-only behavior
- when you want saved terminal output plus the rendered matrix summary

Optional structured reporting:

```bash
./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py --report
```

Use [Matrix Triage](matrix.md) for deeper matrix-specific debugging guidance.

## Full Regression Flow
Canonical stronger gate:

```bash
./.venv/bin/python tools/run_parse_full_regression.py
```

Use it:
- when you want protected baseline first, then the opt-in matrix wrapper
- when a change needs a stronger explicit validation pass than the default baseline alone

Optional structured reporting:

```bash
./.venv/bin/python tools/run_parse_full_regression.py --report
```

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
- normal matrix runs should use `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py`
- deeper rerendering and targeted reporting commands are secondary; see the [Command Registry](command-registry.md)

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
- regenerates `tests/endpoints/parse/fixture_registry.yaml` only when additions are required

Do not use it:
- as part of ordinary baseline or matrix runs
- as part of routine triage when the spreadsheet did not change

## Triage Flow
- Start from the latest terminal output, not from assumptions.
- Use the protected baseline first unless the issue is clearly matrix-scoped.
- If the issue is matrix-scoped, use the canonical matrix wrapper and review the saved artifacts.
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
- Resume work with `mind checkpoint list ...`, `mind checkpoint recover ...`, and `mind search ...`.
- Persist decisions, bug fixes, patterns, and config changes with `mind add ... --tags ...`.
- `mind setup opencode` installs OpenCode protocol instructions, local MCP wiring, and a non-blocking automation plugin for session and compaction continuity.
- Optional local web and API access is available through `mind serve start --detached` on `http://localhost:30303`.
- Optional local HTTP MCP access is available through `mind mcp start --http --detached` on `http://localhost:7438/mcp`.
- Keep active status and working context in Mind, not in repo docs.
- Promote only durable truth into the repo: governance to `AGENTS.md`, stable runbooks to `docs/operations/*`, and validated findings to `docs/knowledge-base/*`.
- `docs/operations/current-handoff.md` is pointer-only and must not hold live task state.

## Session Lifecycle
1. Start: list active checkpoints, recover the right checkpoint, and search for relevant task memories.
2. Continue: keep the active checkpoint current and add durable memories as decisions, discoveries, or fixes happen. OpenCode's Mind automation plugin assists session and compaction continuity after `mind setup opencode`.
3. End: complete the active checkpoint, then promote any durable truths into repo docs in the same pass.

## Mind Troubleshooting
- `mind` not found: ensure `~/.local/bin` is on `PATH`. If the launcher shim is missing or stale on this machine, use `~/.local/share/mind/mind` directly.
- OpenCode does not use Mind: rerun `mind setup opencode`, then inspect `~/.config/opencode/opencode.json` for `mcp.mind`, the managed instruction file, and the managed plugin.
- Need the web UI or HTTP API: run `mind serve start --detached`, then browse `http://localhost:30303`. Stop it with `mind serve stop`.
- Need the HTTP MCP endpoint: run `mind mcp start --http --detached`, confirm with `mind server-status`, and stop it with `mind mcp stop`.
- Active context looks stale: run `mind checkpoint list "projects/verifyiq-api-regression" --status active`, recover the intended checkpoint by name, then run `mind search "<keywords>" --space "projects/verifyiq-api-regression" --detail`.
- The project space does not exist yet: create it once with `mind create "projects/verifyiq-api-regression" "Persistent memory for VerifyIQ API regression automation" --tags "type:project"`.
- Multiple `mind` commands fail with `SQLITE_BUSY_RECOVERY`: rerun them sequentially instead of in parallel; Mind uses a local SQLite store.

## What Not To Use By Default
- Do not use direct matrix pytest with manual `RUN_PARSE_MATRIX=1` as the normal operator path; use the matrix wrapper instead.
- Do not use `./.venv/bin/python tools/run_parse_with_report.py ...` as the default workflow; it is advanced/internal.
- Do not use `./.venv/bin/python tools/reporting/render_regression_summary.py ...` as a substitute for the normal matrix wrapper; it is for saved-output rerendering.
- Do not use historical `.codex` reporting paths from old notes or old artifacts; the current reporting surface is `tools/reporting/*` only.
- Do not rebuild a repo-local note-taking workflow around Obsidian or transcript watchers; Mind is now the canonical memory and continuity layer.
