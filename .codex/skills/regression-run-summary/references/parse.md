# /parse Run Summary

Use this reference when summarizing completed `/parse` runs.

## Inputs
- Saved pytest terminal output from a completed run.
- Live repo state for canonical fixture metadata and the current registry-to-request fileType mapping.

## Triage Rules
- Treat terminal output as the run record.
- For matrix runs, include both registry `fileType` and request `fileType`.
- Under the current repo policy, request `fileType` comes from the explicit repo mapping in `tests/endpoints/parse/file_types.py`.
- Current aliases: `TIN -> TINID`, `ACR -> ACRICard`, `WaterBill -> WaterUtilityBillingStatement`.
- Treat passed `unverified` canonical fixtures as promotion candidates, not promoted facts.

## Draft Mode
- Write generated summary output under `reports/parse/matrix/`.
- Include copy-ready promotion-candidate blocks.
- Do not update tracked knowledge-base files.
- Preferred command: `python tools/reporting/run_parse_matrix_with_summary.py`

## Apply Mode
- Generate the same summary artifact first.
- Update only `docs/knowledge-base/parse/promotion-candidates.md`.
- Keep candidate status separate from promoted status.
- Preferred command: `python tools/reporting/run_parse_matrix_with_summary.py --mode apply`

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
