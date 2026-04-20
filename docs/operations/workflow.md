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
2. Make a narrow repo change.
3. Run the protected baseline:

```powershell
pytest tests/endpoints/parse/ -v
```

4. If the change touches broader `/parse` coverage, reporting, fixture mapping, or matrix triage, run the canonical matrix wrapper:

```powershell
python tools/reporting/run_parse_matrix_with_summary.py
```

5. If you want the stronger explicit gate, run full regression:

```powershell
python tools/run_parse_full_regression.py
```

6. Review generated artifacts if the matrix or reporting surfaces were used.
7. If the work will be resumed or handed off, update `docs/operations/current-handoff.md` with the active task state.
8. Review the diff, stage the intended files, and use the guarded Git flow:

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
Run fixture-registry generation only when the source spreadsheet has intentionally changed:

```powershell
python tools/generate_fixture_registry.py
```

Use it:
- after deliberate edits to `tools/fixture_registry_source/qa_fixture_registry.xlsx`
- when the generated YAML must be refreshed to match the spreadsheet

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

## Handoff State
- Use `docs/operations/current-handoff.md` only for lightweight active task state.
- Keep it focused on the current branch/task, not as a historical running log.
- Durable findings belong in `docs/knowledge-base/`, not in the handoff file.

## Optional Obsidian Staging
If you use Obsidian as a personal/project brain, keep the vault outside the repo and use it only as a capture/staging layer.

Suggested minimal note buckets outside the repo:
- `Inbox/`: raw ideas, snippets, questions, and follow-ups.
- `Sessions/`: date-scoped or branch-scoped working notes for the active task.
- `Promotion Queue/`: draft items that may deserve repo promotion after review.

Promotion rules:
- Keep raw terminal excerpts, hypotheses, personal reminders, and dead ends in Obsidian only.
- Promote validated workflow or command changes into `docs/operations/*`.
- Promote stable `/parse` findings into `docs/knowledge-base/parse/*`.
- Promote transient in-progress branch state only into `docs/operations/current-handoff.md`.
- Promote repo-wide planning only into `docs/knowledge-base/repo-roadmap.md`.

End-of-day audit:
1. Review the day's Obsidian notes against live repo state and the latest terminal output.
2. Leave anything speculative, personal, or transcript-style in Obsidian only.
3. Move active next-session state to `docs/operations/current-handoff.md` only if another agent or later session will need it.
4. Curate any validated durable truth into the correct repo doc in the same pass.
5. Mark the Obsidian item as promoted, deferred, or discarded so it does not linger as pseudo-truth.

Do not automate yet:
- vault sync into the repo
- auto-promotion from note tags or frontmatter
- scripts that rewrite repo docs from Obsidian files
- repo-tracked `.obsidian/` config, daily-note folders, or attachment stores

## What Not To Use By Default
- Do not use direct matrix pytest with manual `RUN_PARSE_MATRIX=1` as the normal operator path; use the matrix wrapper instead.
- Do not use `python tools/run_parse_with_report.py ...` as the default workflow; it is advanced/internal.
- Do not use `python tools/reporting/render_regression_summary.py ...` as a substitute for the normal matrix wrapper; it is for saved-output rerendering.
- Do not use historical `.codex` reporting paths from old notes or old artifacts; the current reporting surface is `tools/reporting/*` only.
