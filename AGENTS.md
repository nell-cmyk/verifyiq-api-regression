# AGENTS.md

## Repository Purpose
- VerifyIQ API regression automation only.
- Scope: Python + pytest live regression coverage and maintenance for `/parse` and supported `/documents/batch` validation helpers.
- Out of scope: manual QA workflow, ClickUp, ticketing, pass-sync logic, and unrelated process automation.

## Project Structure
- `tests/`: endpoint coverage plus shared validation, fixture, and reporting helpers.
- `tools/`: repo-owned CLIs.
- `tools/reporting/`: matrix and reporting wrappers.
- `docs/operations/`: canonical runbooks and command registry.
- `docs/knowledge-base/`: durable findings only.
- `reports/`: generated local artifacts only.
- External session notes: `/Users/nellvalenzuela/Documents/QA Workbench/Sessions/`.

## Runtime/Tooling
- Run repo-local commands from the repo root.
- Prefer `./.venv/bin/python` for repo-local Python and pytest commands.
- One-time local bootstrap:
  - `python3 -m venv .venv`
  - `./.venv/bin/python -m pip install -r requirements.txt`
  - Optional tool deps: `./.venv/bin/python -m pip install -r tools/requirements.txt`
- Operator command source of truth: `docs/operations/command-registry.md`.

## Canonical Validation Commands
- Protected baseline: `./.venv/bin/python -m pytest tests/endpoints/parse/ -v`
- Matrix wrapper: `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py`
- Full regression: `./.venv/bin/python tools/run_parse_full_regression.py`
- Batch suite: `./.venv/bin/python -m pytest tests/endpoints/batch/ -v`
- Tooling/reporting suites:
  - `./.venv/bin/python -m pytest tests/tools/ -v`
  - `./.venv/bin/python -m pytest tests/skills/ -v`
  - `./.venv/bin/python -m pytest tests/reporting/ -v`

## Test Tiers And When To Run Each
- Protected baseline: default gate for ordinary repo changes and before handoff or merge.
- Matrix: when touching fileType mapping, registry selection, reporting, or matrix triage.
- Full regression: when a stronger `/parse` gate is intentionally required.
- Batch suite: when touching `/documents/batch` tests, fixtures, or wrappers.
- Tooling/reporting suites: when editing `tools/`, reporting helpers, or agent/reporting surfaces.
- Trust live terminal output over hardcoded test counts.

## Safe/Unsafe Commands
- Safe discovery and validation:
  - `--help` on repo-owned tools
  - protected baseline
  - matrix wrapper
  - batch suite
  - repo-local pytest suites
- Mutating repo commands:
  - `./.venv/bin/python tools/generate_fixture_registry.py`
  - `./.venv/bin/python tools/onboard_fixture_json.py --json ...`
  - `./.venv/bin/python tools/reporting/render_regression_summary.py --mode apply ...`
  - `./.venv/bin/python tools/safe_git_commit.py ...`
- Mutating external/local-state commands:
  - `./.venv/bin/python tools/install_session_capture_automation.py`
  - `./.venv/bin/python tools/start_ai_session.py`
  - `./.venv/bin/python tools/obsidian_session.py ...`
  - `./.venv/bin/python tools/session_capture_pipeline.py --sync|--watch ...`
- Never run deployment, publish, destructive Git, or data-deleting commands unless explicitly requested.

## Development Rules
- Patch narrowly. Preserve passing behavior unless the task explicitly requires a change.
- Do not refactor, redesign, reorganize, or broaden repo scope unless explicitly asked.
- Use evidence-first debugging: start from the latest terminal output, response body, status code, headers, and fixture metadata.
- `fileType` request mapping lives in `tests/endpoints/parse/file_types.py`.
- Current aliases: `TIN -> TINID`, `ACR -> ACRICard`, `WaterBill -> WaterUtilityBillingStatement`.
- GCS-backed fixtures are required for `/parse`; do not add local fixture fallback or local file-path fallback.
- Use `httpx` for HTTP client work.
- When a canonical command or workflow changes, update the corresponding docs in the same pass.

## Reporting Expectations
- Return results in this order:
  1. diagnosis
  2. file-by-file changes
  3. exact rerun command
- If validation is blocked by missing secrets, external services, or environment prerequisites, say so plainly.
- If terminal output conflicts with saved notes or docs, trust the terminal output.

## External Dependencies/Secrets
- Required live env: `BASE_URL`, `TENANT_TOKEN`, `API_KEY`, `IAP_CLIENT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`, `PARSE_FIXTURE_FILE`, `PARSE_FIXTURE_FILE_TYPE`
- `PARSE_FIXTURE_FILE` must be a `gs://` URI.
- `/parse` and `/documents/batch` rely on live API access and Google IAP credentials.
- Active session automation depends on the external Obsidian vault at `/Users/nellvalenzuela/Documents/QA Workbench`.
- Checked-in CI baseline uses the same live inputs and skips clearly when the required secrets are not configured.

## Artifact/Report Handling
- Treat `reports/` as disposable generated output, not durable truth.
- Protected baseline writes raw `/parse` response artifacts under `reports/parse/responses/`.
- `/documents/batch` runs write raw artifacts under `reports/batch/`.
- Matrix wrapper writes `reports/parse/matrix/latest-terminal.txt` and `reports/parse/matrix/latest-summary.md`.
- Structured reports under `reports/regression/` are opt-in via `--report`.

## Known Gotchas
- The `/parse` matrix is opt-in; direct matrix pytest requires `RUN_PARSE_MATRIX=1`.
- Auth-negative `/parse` tests may warn on timeout and still pass by design.
- The `python` shell alias is not assumed on this machine; use `./.venv/bin/python` or `python3` only when bootstrapping `.venv`.
- `docs/operations/current-handoff.md` is pointer-only; live session state lives in the external Obsidian note.
- Historical `.codex` reporting entrypoints are removed; use `tools/reporting/*`.
