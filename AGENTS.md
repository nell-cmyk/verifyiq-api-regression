# AGENTS.md

## Scope
This repository is only for VerifyIQ API regression automation.

Keep Codex narrowly scoped to this suite:
- Python + pytest only
- API regression coverage and maintenance only

Do not add or mix in:
- manual QA workflow
- ClickUp workflow
- pass sync logic
- bug ticket logic
- unrelated process or project-management automation

## Current Baseline
`/parse` is the current prototype endpoint and reference baseline for this repository.

Protected baseline:
- Command: `pytest tests/endpoints/parse/ -v`
- Current expected result: `10 passed, 2 warnings`

Additional explicit tier commands:
- Matrix only: `python .codex/skills/regression-run-summary/scripts/run_parse_matrix_with_summary.py`
- Full regression: `python tools/run_parse_full_regression.py`

Use the latest terminal output as the source of truth for status, regressions, and validation results.
If terminal output conflicts with assumptions or docs, trust the terminal output.

Preserve already-working behavior.
Do not change passing behavior unless explicitly asked.

## Debugging Rule
Use evidence-first debugging for any triage work.

Start with the latest terminal output and the actual failing response details before proposing causes or fixes.
Inspect response-body contract clues, status codes, headers, and fixture metadata before escalating to broader theories.
Under the current repo policy, request `fileType` comes from the explicit repo mapping in `tests/endpoints/parse/file_types.py`.
Current aliases: `TIN -> TINID`, `ACR -> ACRICard`, `WaterBill -> WaterUtilityBillingStatement`.
When a matrix failure involves `fileType`, diagnose the registry label, the mapped request label, and the returned response label directly.
If evidence is incomplete, say so plainly instead of guessing.

## Session Continuity
Use curated session notes only as restart context.
Current code, terminal output, and Git state override any saved session log or prior summary.

## Fixture Rules
GCS-backed fixtures are required for `/parse`.
`PARSE_FIXTURE_FILE` must be a `gs://` URI.
Request `fileType` follows the explicit repo mapping in `tests/endpoints/parse/file_types.py`.

Do not add:
- local fixture fallback
- local file-path fallback
- alternate non-GCS happy-path fixture mode

## Change Rules
Patch narrowly.
Preserve the existing `/parse` baseline.
Do not refactor, redesign, generalize, or reorganize the suite unless explicitly asked.
Do not broaden scope beyond API regression automation.

Favor minimal diffs over cleanup work.
Do not change working behavior just to make the code look more abstract or more "complete."
Use `httpx` for HTTP client work.

## Multi-Agent Workflow
- Keep one patch per branch.
- Start each branch from `main`.
- Do not edit the same branch as another agent at the same time.
- Keep diffs narrow and avoid opportunistic cleanup.
- Before handoff or merge, validate with the protected baseline command.
- The `/parse` matrix is opt-in and hard-gated in code; direct module execution without `RUN_PARSE_MATRIX=1` is an error.

## Safe Git Workflow
Review the diff first. `python tools/safe_git_commit.py` is the guarded mechanical step after review, not the code-review step itself.

Preferred usage:
- Baseline commit only: `python tools/safe_git_commit.py --message "Describe the reviewed change"`
- Baseline commit only with auto message: `python tools/safe_git_commit.py --auto-message`
- Baseline commit + push: `python tools/safe_git_commit.py --message "Describe the reviewed change" --push`
- Full regression commit + push: `python tools/safe_git_commit.py --message "Describe the reviewed change" --validation full --push`
- Full regression commit + push with auto message: `python tools/safe_git_commit.py --auto-message --validation full --push`
- Stage specific files first: `python tools/safe_git_commit.py --message "Describe the reviewed change" --stage AGENTS.md tests/endpoints/parse/test_parse.py`
- Stage all changed files first: `python tools/safe_git_commit.py --message "Describe the reviewed change" --stage-all`
- Dry run preview: `python tools/safe_git_commit.py --auto-message --stage-all --push --dry-run`

Guardrails:
- Default validation is the protected baseline.
- `--push` is explicit and only pushes `HEAD` to the current branch's matching upstream.
- The script refuses to continue if there are no staged changes.
- The script refuses to continue if unstaged or untracked files remain after optional staging.
- `--auto-message` is explicit and generates a short message from the staged file paths.
- The script does not auto-push on ordinary file changes.

## Response Format
When reporting work, return results in this order:
1. diagnosis
2. file-by-file changes
3. exact rerun command

Default rerun command for the protected baseline:
`pytest tests/endpoints/parse/ -v`

If a requested change would risk the protected baseline or broaden repo scope, call that out explicitly.
