# /parse Run Summary

Use this reference when summarizing completed `/parse` runs.

## Inputs
- Saved pytest terminal output from a completed run.
- Live repo state for canonical fixture metadata and current registry-to-API fileType remaps.

## Triage Rules
- Treat terminal output as the run record.
- For matrix runs, include both registry `fileType` and API `fileType`.
- Check registry-to-API fileType remaps before concluding endpoint failure.
- Treat passed `unverified` canonical fixtures as promotion candidates, not promoted facts.

## Draft Mode
- Write generated summary output under `reports/parse/matrix/`.
- Include copy-ready promotion-candidate blocks.
- Do not update tracked knowledge-base files.
- Preferred command: `python .codex/skills/regression-run-summary/scripts/run_parse_matrix_with_summary.py`

## Apply Mode
- Generate the same summary artifact first.
- Update only `docs/knowledge-base/parse/promotion-candidates.md`.
- Keep candidate status separate from promoted status.
- Preferred command: `python .codex/skills/regression-run-summary/scripts/run_parse_matrix_with_summary.py --mode apply`

## Failure Classes
- `passed`
- `timeout`
- `transport-error`
- `auth-proxy`
- `non-200`
- `non-json-200`
- `filetype-mismatch`
- `missing-fields`
- `failed`
