# Workflow

## Purpose / Scope
Use this file as the canonical operator runbook for the current root checkout.

Use it for the normal end-to-end flow:
- set up the repo
- run the protected baseline
- opt into matrix or full regression when needed
- review artifacts
- use the guarded Git flow

Use [Command Registry](command-registry.md) for command classification and [Matrix Triage](matrix.md) for deeper matrix-specific triage details.

## Prerequisites
### Python deps
Install base repo deps before running the suite:

```powershell
pip install -r requirements.txt
```

Install tool-only deps only if you need fixture-registry generation:

```powershell
pip install -r tools/requirements.txt
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
2. Install the transcript-to-Obsidian automation once on this machine:

```powershell
python3 tools/install_session_capture_automation.py
```

3. Start the normal daily AI session flow in a spare terminal tab:

```powershell
python3 tools/start_ai_session.py
```

4. The startup wrapper resolves or opens today's canonical Obsidian note, prints concise status, and starts the existing foreground watcher only if it is not already running.
5. Do normal work in Codex or Claude Code. Claude stop hooks update the note automatically, and the foreground watcher keeps Codex transcripts synced into the same note with near-zero manual note-taking.
6. Make a narrow repo change.
7. Run the protected baseline:

```powershell
pytest tests/endpoints/parse/ -v
```

8. If the change touches broader `/parse` coverage, reporting, fixture mapping, or matrix triage, run the canonical matrix wrapper:

```powershell
python tools/reporting/run_parse_matrix_with_summary.py
```

9. If you want the stronger explicit gate, run full regression:

```powershell
python tools/run_parse_full_regression.py
```

10. Review generated artifacts from the validation surface you used.
11. If you want an immediate manual refresh outside the watcher, run the sync pipeline directly:

```powershell
python3 tools/session_capture_pipeline.py --sync
```

12. Review the diff, stage the intended files, and use the guarded Git flow:

```powershell
python tools/safe_git_commit.py --message "Describe the reviewed change"
```

## Protected Baseline
Mandatory default validation surface:

```powershell
pytest tests/endpoints/parse/ -v
```

Use it:
- for ordinary `/parse` changes
- before handoff or merge when baseline validation is needed
- as the default validation gate unless a task explicitly calls for broader coverage

Do not replace this with the matrix or full regression by default.

Baseline response artifacts:
- `reports/parse/responses/<test-case-id>__<description>__<timestamp>_<seq>.json`
- one raw JSON file per `/v1/documents/parse` call, written directly under `reports/parse/responses/`
- supported `/batch` runs also write one raw response artifact per `/v1/documents/batch` call to `reports/batch/batch_<timestamp>_<seq>.json`

## Matrix Flow
Canonical opt-in matrix surface:

```powershell
python tools/reporting/run_parse_matrix_with_summary.py
```

Use it:
- when you need broader `/parse` fileType coverage
- when triaging matrix-only behavior
- when you want saved terminal output plus the rendered matrix summary

Optional structured reporting:

```powershell
python tools/reporting/run_parse_matrix_with_summary.py --report
```

Use [Matrix Triage](matrix.md) for deeper matrix-specific debugging guidance.

## Full Regression Flow
Canonical stronger gate:

```powershell
python tools/run_parse_full_regression.py
```

Use it:
- when you want protected baseline first, then the opt-in matrix wrapper
- when a change needs a stronger explicit validation pass than the default baseline alone

Optional structured reporting:

```powershell
python tools/run_parse_full_regression.py --report
```

## Reporting And Artifact Review
Baseline artifacts:
- `reports/parse/responses/<test-case-id>__<description>__<timestamp>_<seq>.json`
- `reports/batch/batch_<timestamp>_<seq>.json` for supported `/batch` runs

Default matrix/reporting artifacts:
- `reports/parse/matrix/latest-terminal.txt`
- `reports/parse/matrix/latest-summary.md`

Optional structured report artifacts when `--report` is enabled:
- `reports/regression/<timestamp>/report.json`
- `reports/regression/<timestamp>/report.md`
- `reports/regression/LATEST.txt`

Default operator expectation:
- normal matrix runs should use `python tools/reporting/run_parse_matrix_with_summary.py`
- deeper rerendering and targeted reporting commands are secondary; see the [Command Registry](command-registry.md)

## Registry Refresh Rules
Run fixture-registry generation only when the curated source data has intentionally changed:

```powershell
python tools/generate_fixture_registry.py
```

Use it:
- after deliberate edits to `tools/fixture_registry_source/qa_fixture_registry.xlsx`
- after deliberate edits to `tools/fixture_registry_source/supplemental_fixture_registry.yaml`
- when the generated YAML must be refreshed to match the curated sources

Use JSON onboarding when a new fixture list arrives as a JSON file of `gs://` paths:

```powershell
python tools/onboard_fixture_json.py --json path\to\fixtures.json
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
- Use `python tools/safe_git_commit.py --message "Describe the reviewed change"` for the guarded mechanical commit step.
- Use `--validation full` only when the stronger full-regression gate is intentionally required.
- Use `--push` only when you are ready to push to the current branch's matching upstream.

## Active Session State
- Obsidian now replaces `docs/operations/current-handoff.md` for active state, handoff, working context, and ongoing task tracking.
- Canonical active state lives outside the repo at `/Users/nellvalenzuela/Documents/QA Workbench/Sessions/YYYY-MM-DD - verifyiq-api-regression.md`.
- Use `python3 tools/start_ai_session.py` as the normal daily startup command; it resolves or opens today's note and hands off to the same foreground watcher when needed.
- Resolve or open today's note directly with `python3 tools/obsidian_session.py --today --open` only when you want the note helper without starting the wrapper.
- Find the latest active context when resuming older work with `python3 tools/obsidian_session.py --latest`.
- `tools/session_capture_pipeline.py` rebuilds the note's automated sections from local Codex transcripts in `~/.codex/sessions/` and Claude Code transcripts in `~/.claude/projects/`.
- After `python3 tools/install_session_capture_automation.py`, Claude Code updates the note on `Stop`, `StopFailure`, and `SessionEnd`.
- On this Mac, keep `python3 tools/session_capture_pipeline.py --watch --quiet` running in a foreground terminal tab for Codex live syncing and Claude backfill. The repo lives under `~/Documents`, so the foreground watcher is more reliable than a background launch agent.
- Keep active status, working context, blockers, validation state, and next step in the external session note, not in repo docs. Manual note edits are optional when the automation is running.
- Promote only durable truth into the repo: governance to `AGENTS.md`, stable runbooks to `docs/operations/*`, and validated findings to `docs/knowledge-base/*`.
- `docs/operations/current-handoff.md` is a pointer-only deprecation file and must not hold live task state.

## Session Lifecycle
1. Start: run `python3 tools/start_ai_session.py` in a spare terminal tab.
2. Continue: rely on the automated `Automated active state` and `Automated session log` sections for near-zero-manual session capture; Claude hooks update on stop events, and the foreground watcher keeps Codex and Claude transcripts normalized into the same note.
3. End: confirm the latest `Next step`, blockers, and promotion targets look correct in the automated note sections, then promote any durable truths into repo docs in the same pass.

## AI Session Startup Troubleshooting
- Watcher already running: if `python3 tools/start_ai_session.py` says a watcher is already running, leave that watcher tab in place and keep working. If you intentionally want a fresh watcher, stop the old watcher with `Ctrl-C` in its tab, then rerun `python3 tools/start_ai_session.py`.
- Obsidian does not open: the command still resolves today's note first. Rerun `python3 tools/obsidian_session.py --today --open` or open `/Users/nellvalenzuela/Documents/QA Workbench/Sessions/YYYY-MM-DD - verifyiq-api-regression.md` directly in Obsidian.
- Claude hooks are not installed: run `python3 tools/install_session_capture_automation.py` once, then rerun `python3 tools/start_ai_session.py`. The startup wrapper reports hook status but does not install hooks for you.
- Today's note does not update: first confirm the `python3 tools/start_ai_session.py` watcher tab is still running. If you need an immediate refresh, run `python3 tools/session_capture_pipeline.py --sync`.
- Duplicate watcher concerns: use `python3 tools/start_ai_session.py` as the only normal startup command. Do not start a second manual `python3 tools/session_capture_pipeline.py --watch --quiet` tab unless you have already stopped the original watcher.

## What Not To Use By Default
- Do not use direct matrix pytest with manual `RUN_PARSE_MATRIX=1` as the normal operator path; use the matrix wrapper instead.
- Do not use `python tools/run_parse_with_report.py ...` as the default workflow; it is advanced/internal.
- Do not use `python tools/reporting/render_regression_summary.py ...` as a substitute for the normal matrix wrapper; it is for saved-output rerendering.
- Do not use historical `.codex` reporting paths from old notes or old artifacts; the current reporting surface is `tools/reporting/*` only.
