# Matrix Triage

Use evidence-first triage for opt-in `/parse` matrix failures.

See also: [Repo Roadmap](../knowledge-base/repo-roadmap.md)
See also: [Command Registry](command-registry.md)
See also: [Workflow](workflow.md)

The matrix is hard-gated in code. Running `./.venv/bin/python -m pytest tests/endpoints/parse/test_parse_matrix.py -v`
without `RUN_PARSE_MATRIX=1` raises a collection error.

## Post-Run Summary
Use these commands in this order:

1. Canonical runner matrix selection and summary:

```bash
./.venv/bin/python tools/run_regression.py --endpoint parse --category matrix
```

This canonical operator path:
- runs the opt-in `/parse` matrix
- delegates to `tools/reporting/run_parse_matrix_with_summary.py`
- saves terminal output to `reports/parse/matrix/latest-terminal.txt`
- generates `reports/parse/matrix/latest-summary.md`
- accepts `--report` to also emit structured per-run artifacts under `reports/regression/<timestamp>/`
- accepts `--fixtures-json /path/to/fixtures.json` to run the exact registry fixtures resolved from that JSON input instead of the default canonical-only selection
- normalizes JSON-imported `gs://` paths first, skips unsupported file formats with an explicit CLI report, and fails fast if no supported entries remain

2. Canonical re-render from existing saved terminal output:

```bash
./.venv/bin/python tools/reporting/render_regression_summary.py --endpoint parse --input reports/parse/matrix/latest-terminal.txt
```

Use `--mode apply` only after reviewing the generated draft summary.

3. Full regression wrapper when you want the stronger gate:

```bash
./.venv/bin/python tools/run_regression.py --suite full
```

This runs:
- protected baseline: `./.venv/bin/python -m pytest tests/endpoints/parse/ -v`
- matrix wrapper: `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py`
- add `--report` to also emit structured per-run artifacts under `reports/regression/<timestamp>/`

4. Advanced/manual flow if you need to separate the steps for debugging:

Shell example:

```bash
RUN_PARSE_MATRIX=1 ./.venv/bin/python -m pytest tests/endpoints/parse/test_parse_matrix.py -v 2>&1 | tee reports/parse/matrix/latest-terminal.txt
./.venv/bin/python tools/reporting/render_regression_summary.py --endpoint parse --input reports/parse/matrix/latest-terminal.txt
```

5. Reporting surfaces:
- Use `./.venv/bin/python tools/run_regression.py --endpoint parse --category matrix` for normal matrix runs and saved summaries.
- Use `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py` as the delegated engine and compatibility/debug path.
- Use `./.venv/bin/python tools/reporting/render_regression_summary.py ...` for rerendering from saved terminal output.
- Do not document or rely on `.codex/.../scripts/...` reporting entrypoints.

## Decision Flow
1. Start with the latest terminal output.
2. Identify the failing `fileType`, pytest node ID, status code, and fixture metadata.
3. Inspect the actual response body and headers for contract clues before guessing cause.
4. Under the current repo policy, request `fileType` comes from the explicit mapping in `tests/endpoints/parse/file_types.py`.
5. Map the failing case back to the canonical fixture and registry row, or to the explicitly selected fixture when `--fixtures-json` was used.
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
