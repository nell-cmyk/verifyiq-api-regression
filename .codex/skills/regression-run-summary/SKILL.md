---
name: regression-run-summary
description: Summarize completed API regression runs and draft follow-up findings. Use when a pytest-based regression run has already finished and you want a terminal-first summary, failure classification, mapped-fileType /parse matrix triage, or copy-ready promotion-candidate text without mutating suite state during the run.
---

# Regression Run Summary

Generate a post-run summary after a completed regression run. Default to safe draft output under `reports/` and only update tracked knowledge-base files when explicitly asked.

## Workflow
1. Start from saved terminal output, not from memory.
2. Verify the live repo state before trusting prior notes or summaries.
3. Use the repo-owned wrappers in `tools/reporting/` to parse the run, enrich it with endpoint metadata, and render a Markdown summary.
4. In `draft` mode, write only local generated artifacts under `reports/`.
5. In `apply` mode, update only the explicit tracked knowledge-base target after generating the same draft summary first.

## Parse Support
- Read [references/parse.md](references/parse.md) for `/parse`-specific guidance.
- Use `tools/reporting/render_regression_summary.py` as the entrypoint.
- For `/parse`, treat the terminal output as the run record and enrich results with:
  - canonical registry metadata
  - registry `fileType`
  - request `fileType`
  - promotion-candidate eligibility

## Safety Rules
- Do not run during pytest execution.
- Do not mutate the spreadsheet or generated YAML.
- Do not let saved summaries override current code, terminal output, or Git state.
- Do not append to tracked knowledge-base files unless `apply` mode is explicitly requested.

## Commands
Preferred wrapper for a completed `/parse` matrix run:

```bash
./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py
```

Apply promotion-candidate updates after reviewing the generated draft:

```bash
./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py --mode apply
```

Direct summary generation from an existing saved run:

```bash
./.venv/bin/python tools/reporting/render_regression_summary.py --endpoint parse --input reports/parse/matrix/latest-terminal.txt
```
