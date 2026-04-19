# Matrix Triage

Use evidence-first triage for opt-in `/parse` matrix failures.

See also: [Repo Roadmap](C:/Users/v_nel/Documents/verifyiq-api-regression/docs/knowledge-base/repo-roadmap.md)

The matrix is hard-gated in code. Running `pytest tests/endpoints/parse/test_parse_matrix.py -v`
without `RUN_PARSE_MATRIX=1` raises a collection error.

## Post-Run Summary
Preferred wrapper:

```powershell
python tools/reporting/run_parse_matrix_with_summary.py
```

This wrapper:
- runs the opt-in `/parse` matrix
- saves terminal output to `reports/parse/matrix/latest-terminal.txt`
- generates `reports/parse/matrix/latest-summary.md`

Full regression wrapper:

```powershell
python tools/run_parse_full_regression.py
```

This runs:
- protected baseline: `pytest tests/endpoints/parse/ -v`
- matrix wrapper: `python tools/reporting/run_parse_matrix_with_summary.py`

Direct manual flow if you need to separate the steps:

PowerShell example:

```powershell
$env:RUN_PARSE_MATRIX='1'
pytest tests/endpoints/parse/test_parse_matrix.py -v 2>&1 | Tee-Object -FilePath reports/parse/matrix/latest-terminal.txt
python tools/reporting/render_regression_summary.py --endpoint parse --input reports/parse/matrix/latest-terminal.txt
```

Use `--mode apply` only after reviewing the generated draft summary.

Legacy compatibility note:
- The older `.codex/skills/regression-run-summary/scripts/...` paths still work during the transition, but `tools/reporting/` is the canonical repo-facing home for reporting commands.

## Decision Flow
1. Start with the latest terminal output.
2. Identify the failing `fileType`, pytest node ID, status code, and fixture metadata.
3. Inspect the actual response body and headers for contract clues before guessing cause.
4. Under the current repo policy, request `fileType` comes from the explicit mapping in `tests/endpoints/parse/file_types.py`.
5. Map the failing case back to the canonical fixture and registry row.
6. Classify narrowly:
   - endpoint regression
   - auth or proxy interception
   - fixture-selection issue
   - timeout or staging instability
   - unclear, needs more evidence
7. Only propose fixes after the failure class is supported by the evidence.

## FileType Policy
- Request `fileType` comes from the explicit repo mapping in `tests/endpoints/parse/file_types.py`.
- Current aliases: `TIN -> TINID`, `ACR -> ACRICard`, `WaterBill -> WaterUtilityBillingStatement`.
- If the response reports a different `fileType` than the mapped request, treat that as live endpoint evidence and diagnose from the registry label, mapped request label, and response pair.
