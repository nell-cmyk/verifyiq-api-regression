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

Use the latest terminal output as the source of truth for status, regressions, and validation results.
If terminal output conflicts with assumptions or docs, trust the terminal output.

Preserve already-working behavior.
Do not change passing behavior unless explicitly asked.

## Fixture Rules
GCS-backed fixtures are required for `/parse`.
`PARSE_FIXTURE_FILE` must be a `gs://` URI.

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

## Response Format
When reporting work, return results in this order:
1. diagnosis
2. file-by-file changes
3. exact rerun command

Default rerun command for the protected baseline:
`pytest tests/endpoints/parse/ -v`

If a requested change would risk the protected baseline or broaden repo scope, call that out explicitly.
