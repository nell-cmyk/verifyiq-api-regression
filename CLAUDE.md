# VerifyIQ API Regression Suite

## Scope
This repository is only for VerifyIQ API regression automation.

Do not add or mix in:
- manual QA workflow
- ClickUp workflow
- pass sync logic
- bug ticket logic
- ticket analysis logic
- dev comment workflows
- unrelated business-process automation

Keep the repo focused on Python + pytest API regression work.

## Current Baseline
`/parse` is the current prototype endpoint and protected regression baseline.

Use the latest terminal output as the source of truth for status and validation results.
If docs or assumptions conflict with terminal output, trust the terminal output.

Protected baseline:
- Command: `pytest tests/endpoints/parse/ -v`
- Current expected result: `10 passed, 2 warnings`

Additional explicit tier commands:
- Matrix only: `python .codex/skills/regression-run-summary/scripts/run_parse_matrix_with_summary.py`
- Full regression: `python tools/run_parse_full_regression.py`

Preserve already-working behavior.
Do not change passing behavior unless explicitly asked.

## Fixture Rules
GCS-backed fixtures are required for `/parse`.
`PARSE_FIXTURE_FILE` must be a `gs://` URI.
Request `fileType` follows the explicit repo mapping in `tests/endpoints/parse/file_types.py`.

Do not add:
- local fixture fallback
- local file-path fallback
- alternate non-GCS happy-path fixture mode

## Change Rules
- Patch narrowly.
- Do not refactor, redesign, generalize, or reorganize unless explicitly asked.
- Do not modify app logic, test logic, fixtures, auth flow, config behavior, or architecture unless the task requires it.
- Prefer minimal diffs over cleanup work.
- Use `httpx` for HTTP client work.

## Multi-Agent Workflow
- Keep one patch per branch.
- Start each branch from `main`.
- Do not let multiple agents edit the same branch at the same time.
- Keep diffs narrow and avoid opportunistic cleanup.
- Before handoff or merge, use the protected `/parse` baseline command when validation is needed.
- The `/parse` matrix is opt-in and hard-gated in code; direct module execution without `RUN_PARSE_MATRIX=1` is an error.

## Debugging Expectations
- Start triage from the latest terminal output, not from assumptions.
- For matrix failures, inspect the actual response body, status code, headers, fixture metadata, and registry mapping before proposing root cause.
- Under the current repo policy, request `fileType` comes from the explicit repo mapping in `tests/endpoints/parse/file_types.py`.
- Current aliases: `TIN -> TINID`, `ACR -> ACRICard`, `WaterBill -> WaterUtilityBillingStatement`.
- When a matrix case fails on `fileType`, state the registry label, the mapped request label, and the response label that came back.
- Use response-body contract clues to distinguish likely endpoint regression, auth/proxy interception, fixture mismatch, and staging instability.
- If the available evidence does not support a confident conclusion, say what is missing and keep the diagnosis narrow.

## Startup Workflow
- On a resumed session, read the current session context note if it exists, then verify it against the current repo state.
- Re-check Git status, current branch, and latest terminal evidence before acting on saved context.
- If saved context conflicts with code, terminal output, or Git state, trust the live repo state and update the diagnosis accordingly.

## Output Rules
Return results in this order:
1. diagnosis
2. file-by-file changes
3. exact rerun command
