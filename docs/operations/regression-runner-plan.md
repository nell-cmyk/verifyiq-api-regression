# Regression Runner Consolidation Plan

## Purpose
This document defines the implementation plan for consolidating the repository's current fragmented regression execution surfaces into one canonical runner while preserving useful targeted workflows.

The goal is to introduce one user-facing command surface for normal regression work, keep current protected behavior stable during migration, preserve valuable targeted flows for `/v1/documents/parse` and `/v1/documents/batch`, and create a clean path to later deprecate legacy wrapper commands.

## Scope
This plan covers current regression execution surfaces for:

- `/v1/documents/parse`
- `/v1/documents/batch`
- shared contract assertion helpers
- current CI usage of the protected baseline

This plan does not implement the runner. It documents the current state, proposed canonical interface, migration strategy, and validation gates required before any cutover.

## Roadmap Alignment
This plan advances the roadmap items in `docs/knowledge-base/repo-roadmap.md` that call for:

- repository and runner inventory
- regression taxonomy
- one-runner design
- migration of legacy wrappers into a canonical runner
- CI cutover only after parity is proven

Repo reality note:
The roadmap previously named `scripts/run_regression.py`, but the repository's established command convention is `tools/`. This plan recommends `tools/run_regression.py` and the roadmap should stay aligned with that repo-local convention.

## Current Runner Inventory Matrix

| Surface | Endpoint(s) | Test type | Current purpose | Requirements | Inputs | Outputs | Execution mode | Future role | Recommendation | Overlap / risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `./.venv/bin/python -m pytest tests/endpoints/parse/ -v` | `/v1/documents/parse` | Protected baseline: live happy-path, auth-negative, validation, plus local registry-selection tests collected from the parse package | Default protected gate used in docs and CI | `BASE_URL`, `TENANT_TOKEN`, `API_KEY`, `IAP_CLIENT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`, `PARSE_FIXTURE_FILE`, `PARSE_FIXTURE_FILE_TYPE` | Env-backed happy-path fixture; parse package collection; `test_parse_matrix.py` excluded unless `RUN_PARSE_MATRIX=1` | Raw parse response artifacts under `reports/parse/responses/parse_<timestamp>/...` | Live API via `httpx` with GCS-backed fixtures; no mocks in the normal path | Canonical default suite backing | Keep exactly; wrap first as `--suite protected` and default no-arg behavior | Highest regression-safety surface; must not silently broaden or narrow |
| `./.venv/bin/python -m pytest tests/endpoints/parse/test_parse.py -v` | `/v1/documents/parse` | Direct parse module: happy path, auth-negative, validation | Underlying live parse module for the protected suite | Same as protected parse baseline | Env-backed `PARSE_REQUEST_BASE` and happy-path fixture | Raw parse response artifacts | Live API via `httpx` with GCS-backed fixture | Internal module mapping for parse categories | Keep as direct debug path; migrate into runner metadata, not the primary operator command | Subset of the protected baseline command; exposing it as primary would be confusing |
| `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py` | `/v1/documents/parse` | Opt-in matrix breadth across canonical file types | Runs matrix, captures terminal output, renders summary, optionally emits structured report | Core parse env above; wrapper sets `RUN_PARSE_MATRIX=1`; optional `PARSE_MATRIX_FIXTURES_JSON`; optional `REGRESSION_REPORT` / `REGRESSION_REPORT_TIER` | Canonical registry fixtures or explicit fixtures JSON; supports `--file-types`, `--fixtures-json`, `--k`, optional custom command | `reports/parse/matrix/latest-terminal.txt`, `reports/parse/matrix/latest-summary.md`, parse response artifacts, optional `reports/regression/<timestamp>/...`; `--mode apply` can update promotion-candidate docs | Live API via `httpx` with GCS-backed fixtures | Matrix engine for the canonical runner | Wrap first as `--endpoint parse --category matrix`; later deprecate as a direct operator command | Slow breadth surface; tied to summary-rendering behavior and optional doc-mutation mode |
| `RUN_PARSE_MATRIX=1 ./.venv/bin/python -m pytest tests/endpoints/parse/test_parse_matrix.py -v` | `/v1/documents/parse` | Direct matrix module | Debug-level direct entry point for matrix contract coverage | Core parse env; `RUN_PARSE_MATRIX=1`; optional `PARSE_MATRIX_FIXTURES_JSON` | Canonical one-fixture-per-fileType selection from registry, or explicit fixture selection JSON | Raw parse response artifacts only; no wrapper-generated summary | Live API via `httpx` with GCS-backed fixtures | Internal/debug surface only | Keep as a debug path only; do not document as the primary operator path | Easy to misuse without summary output; collection must stay gated |
| `./.venv/bin/python tools/run_parse_full_regression.py` | `/v1/documents/parse` | Orchestrated protected baseline plus matrix | Stronger explicit gate that runs baseline first, then matrix | Core parse env; optional `REGRESSION_REPORT`; forwards `--file-types` and `--k` to the matrix wrapper | Baseline command plus matrix wrapper; shared parse artifact run directory | Parse response artifacts, matrix terminal and summary outputs, optional structured regression report | Live API via delegated commands | Initial implementation backing for `--suite full` | Wrap first; later replace direct use with the canonical runner | Must preserve current sequencing and shared parse artifact run directory behavior |
| `./.venv/bin/python tools/run_parse_with_report.py` | `/v1/documents/parse` | Advanced/internal targeted reporting surface | Generates structured JSON + Markdown reports for baseline, matrix, or full flows, including targeted nodeids | Core parse env; baseline tier sets `REGRESSION_REPORT`; matrix/full delegate to other wrappers | `--tier baseline|matrix|full`, optional repeated `--case`, `--file-types`, `--k` | `reports/regression/<timestamp>/report.json`, `report.md`, `LATEST.txt` | Live API via direct baseline pytest or delegated wrappers | Capability source for `--report` and targeted selection | Migrate features into the canonical runner, then deprecate direct use | Very high command-surface duplication; already documented as advanced/internal |
| `./.venv/bin/python -m pytest tests/endpoints/batch/ -v` and `./.venv/bin/python -m pytest tests/endpoints/batch/test_batch.py -v` | `/v1/documents/batch` | Direct batch suite: happy path, validation, negative, limit handling, partial-failure behavior | Current direct batch validation path | `BASE_URL`, `TENANT_TOKEN`, `API_KEY`, `IAP_CLIENT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`; optional `BATCH_FIXTURES_JSON` for selection | Default registry-backed batch fixture set or explicit selection through env; safe item limit is `4` | Raw batch response artifacts under `reports/batch/batch_<timestamp>/...` | Live API via `httpx` with GCS-backed registry fixtures | Canonical runner `--endpoint batch` backing | Keep as a direct debug path; wrap for normal operator use | Not currently part of protected CI; broader runtime and fixture-risk profile than protected parse |
| `./.venv/bin/python tools/run_batch_with_fixtures.py --fixtures-json ...` | `/v1/documents/batch` | Wrapper for selected-fixture and chunked batch execution | Runs selected-fixture batch flows, validates JSON input, surfaces registry warnings, chunks selections over safe limit, supports custom command passthrough | Core batch env above; wrapper sets `BATCH_FIXTURES_JSON` internally when needed | Fixture selection JSON, registry lookup, optional custom pytest command, optional `--k` | Raw batch response artifacts; chunked runs reuse one batch run-dir name | Live API via delegated pytest commands | Batch-targeting engine for the canonical runner | Wrap first as `--endpoint batch --fixtures-json`; keep compatibility during migration; deprecate later as a direct operator path | Chunking and warning behavior are meaningful repo logic and must be preserved exactly |
| `tests/endpoints/document_contracts.py` | `/v1/documents/parse`, `/v1/documents/batch` | Shared assertion helper, not a runner | Provides reusable required-field, fileType, calculated-field, and HTTP validation shape assertions | None directly | Response objects and parsed JSON bodies from parse and batch tests | None directly | Local helper only; does not call APIs itself | Reusable contract-helper module behind runner metadata | Keep | Current contract coverage is manual and selective, not full OpenAPI validation |
| `.github/workflows/protected-baseline.yml` | `/v1/documents/parse` | CI protected gate | Runs the protected baseline on `push`, `pull_request`, and `workflow_dispatch`, but skips cleanly when secrets are missing | GitHub secrets: `BASE_URL`, `TENANT_TOKEN`, `API_KEY`, `IAP_CLIENT_ID`, `GOOGLE_APPLICATION_CREDENTIALS_JSON`, `PARSE_FIXTURE_FILE`, `PARSE_FIXTURE_FILE_TYPE` | Protected baseline via `python tools/run_regression.py --suite protected` using the `setup-python` interpreter | GitHub step summary; any local pytest artifacts are ephemeral unless later uploaded | Live API in CI | Caller of the canonical protected suite | Keep current workflow logic and setup-python interpreter strategy; change only when broader runner parity is proven | CI stability risk if the canonical runner changes env handling, secret handling, or default behavior |

## Current-State Conclusions
- The protected baseline is the only current default gate and must remain the default until parity is proven.
- The repo already has orchestration logic worth reusing. This is especially true for:
  - `tools/run_parse_full_regression.py`
  - `tools/reporting/run_parse_matrix_with_summary.py`
  - `tools/run_batch_with_fixtures.py`
- The direct pytest surfaces should remain valid for debugging, but they should stop being the primary operator story after consolidation.
- `tools/run_parse_with_report.py` is the clearest direct-command candidate for later deprecation because it overlaps other surfaces and is already documented as advanced/internal.
- Current contract validation is shared-assertion based, not full OpenAPI validation. The future runner must not blur that distinction.

## Canonical Runner Path Recommendation
Recommended canonical path:

    ./.venv/bin/python tools/run_regression.py

Reasoning:
- `tools/` is the repository's existing canonical home for repo-owned executable commands.
- The current docs, tests, and operator surfaces already point there.
- Introducing `scripts/` would add a convention change without a strong repo-local need.
- Existing tests import runner modules from `tools/` by exact path, so `tools/run_regression.py` fits current maintenance patterns better than `scripts/run_regression.py`.

## Proposed CLI
Recommended initial user-facing interface:

    ./.venv/bin/python tools/run_regression.py
    ./.venv/bin/python tools/run_regression.py --suite protected
    ./.venv/bin/python tools/run_regression.py --suite full
    ./.venv/bin/python tools/run_regression.py --suite extended
    ./.venv/bin/python tools/run_regression.py --endpoint parse
    ./.venv/bin/python tools/run_regression.py --endpoint batch
    ./.venv/bin/python tools/run_regression.py --category contract
    ./.venv/bin/python tools/run_regression.py --category auth
    ./.venv/bin/python tools/run_regression.py --category negative
    ./.venv/bin/python tools/run_regression.py --category matrix
    ./.venv/bin/python tools/run_regression.py --file-types Payslip,TIN
    ./.venv/bin/python tools/run_regression.py --fixtures-json path/to/fixtures.json
    ./.venv/bin/python tools/run_regression.py --k "expr"
    ./.venv/bin/python tools/run_regression.py --report
    ./.venv/bin/python tools/run_regression.py --list
    ./.venv/bin/python tools/run_regression.py --dry-run

CLI design notes:
- Keep `--endpoint parse|batch` for endpoint selection.
- Reserve `--category` for behavior lenses such as `contract`, `auth`, `negative`, `matrix`, and `legacy`.
- Do not duplicate endpoint selection by also introducing `--category parse|batch`.
- `--file-types` and `--fixtures-json` should stay because they already correspond to real wrapper behavior.
- `--k` should remain a supported pass-through because it already exists on multiple surfaces.
- `--report` should unify structured-report behavior instead of preserving a separate reporting-only command long term.
- `--list` and `--dry-run` should be implemented before broad execution mapping so the new runner is transparent from day one.

## Default No-Argument Behavior
Recommended default:

    ./.venv/bin/python tools/run_regression.py

should be equivalent to:

    ./.venv/bin/python tools/run_regression.py --suite protected

and should map exactly to today's protected baseline command:

    ./.venv/bin/python -m pytest tests/endpoints/parse/ -v

Why this is the right default now:
- It preserves the repo's current protected gate.
- It matches current CI.
- It keeps runtime and scope predictable.
- It avoids silently adding `/documents/batch` or matrix breadth to the default path.
- It preserves the current assumption that matrix and stronger gates are opt-in.

Tradeoff:
- This default is narrower than an eventual cross-endpoint smoke suite.
- That tradeoff is correct today because the repo does not yet have a proven, documented, stable cross-endpoint smoke suite.

Future note:
- A future `smoke` suite can exist once a deliberate cross-endpoint smoke composition is defined.
- Until that exists, `protected` is the concrete default suite and should not be replaced by an undefined or aspirational `smoke` label.

## Suite And Category Taxonomy
Keep the model small and practical.

### Suites
- `protected`
  - Exact current protected baseline
  - Current default
- `full`
  - Protected baseline plus parse matrix
  - Stronger explicit gate
- `extended`
  - Heavy or selective runs that are useful but not default
  - Examples: matrix subsets, selected-fixture batch runs, report-heavy runs
- `smoke`
  - Reserved for a later curated cross-endpoint minimal suite
  - Do not make it the default until it is deliberately defined

### Endpoints
- `parse`
- `batch`

### Categories
- `contract`
- `auth`
- `negative`
- `matrix`
- `legacy`

Initial mapping:
- `parse` protected module contains:
  - `contract`
  - `auth`
  - `negative`
- `parse` matrix module contains:
  - `matrix`
  - `contract`
- `batch` module contains:
  - `contract`
  - `negative`
- `document_contracts.py` is shared assertion infrastructure and should back the `contract` category, not appear as its own runnable suite.

## OpenAPI And Schema Validation Plan
`official-openapi.json` should be treated as an initial contract source, not automatic ground truth.

The future runner should separate four concerns clearly.

### Contract Validation Against OpenAPI
This means testing behavior against the intended documented contract.

Current repo reality:
- parse tests reference `ParseRequest` and `HTTPValidationError`
- batch tests reference `BatchRequest`, `BatchItem`, and `HTTPValidationError`
- success-response validation is still mostly manual and selective
- `official-openapi.json` uses a generic success schema for parse `200` responses, so current tests are already stronger than the success schema in some ways and looser in others

### Schema Discovery From Current Observed Behavior
This means capturing safe, current request and response shapes from existing trusted regression flows.

Safe sources:
- current parse baseline runs
- current parse matrix runs
- current batch runs
- existing response artifacts under `reports/parse/...` and `reports/batch/...`
- existing structured reporting output when `--report` is used

Unsafe or out-of-scope sources:
- destructive probing
- ad hoc production mutation
- undocumented endpoint exploration

### Drift Documentation
When the spec and observed behavior diverge:
- record the mismatch explicitly
- identify whether the spec is stale, the implementation is wrong, or ownership is unresolved
- keep contract drift out of raw terminal logs and capture it as a durable summary

### Spec And Test Reconciliation
When drift is confirmed:
- update the spec if accepted behavior is not documented correctly
- update the tests if the tests are asserting outdated or incorrect assumptions
- add targeted regression coverage if the mismatch reflects a prior defect

### Pilot Endpoint
Pilot endpoint recommendation:
- `/v1/documents/parse`

Why:
- It is the protected baseline.
- It already has stable live fixtures.
- It already writes raw response artifacts.
- It already has both happy-path and validation coverage.
- It is already the central operational surface in docs and CI.

## Migration And Deprecation Plan

### Phase A: Metadata And Transparency First
1. Add `tools/run_regression.py`.
2. Implement only:
   - `--list`
   - `--dry-run`
   - inventory-backed command mapping
3. Do not change current operator docs or CI yet.
4. Do not remove or rename any wrapper.

### Phase B: Wrap Existing Parse Flows
1. Map `--suite protected` to the exact current protected baseline command.
2. Map `--suite full` to the existing full-regression behavior.
3. Map `--endpoint parse --category matrix` to the matrix wrapper.
4. Support existing parse targeting flags:
   - `--file-types`
   - `--fixtures-json`
   - `--k`
   - `--report`

### Phase C: Wrap Existing Batch Flows
1. Map `--endpoint batch` to the direct batch pytest surface.
2. Map `--endpoint batch --fixtures-json ...` to the batch wrapper behavior.
3. Preserve chunking semantics and warning output from the current batch wrapper.
4. Keep direct batch pytest and batch wrapper available as compatibility/debug surfaces.

### Phase D: Consolidate Reporting Behavior
1. Move user-facing structured reporting to `tools/run_regression.py --report`.
2. Keep report-tier naming internal to the canonical runner.
3. Reduce direct operator dependence on `tools/run_parse_with_report.py`.

### Phase E: Documentation And CI Cutover
1. Update:
   - `README.md`
   - `docs/operations/command-registry.md`
   - `docs/operations/workflow.md`
2. Change CI only after command parity is verified.
3. Replace direct CI use of `pytest tests/endpoints/parse/ -v` with:

       python tools/run_regression.py --suite protected

### Phase F: Legacy Deprecation
Deprecate later:
- direct operator use of `tools/run_parse_full_regression.py`
- direct operator use of `tools/run_batch_with_fixtures.py`
- direct operator use of `tools/run_parse_with_report.py`

Remove later only after all conditions hold:
- canonical runner covers the same use cases
- docs point only to canonical paths
- CI is no longer calling legacy commands
- runner tests cover all mappings
- protected baseline behavior is unchanged

## CI Integration Plan
Current CI behavior should remain protected until parity exists.

### Keep Protected
- secret-aware skip logic
- current live-input requirements
- current protected baseline scope

### Default CI Behavior After Parity
Use:

    ./.venv/bin/python tools/run_regression.py --suite protected

### Keep Opt-In Or Later
- parse matrix
- full regression
- extended batch-targeted runs
- report-heavy or artifact-heavy flows beyond the protected gate

### Secret Handling
The canonical runner should not invent a new secret model.
It should continue to rely on the same current repo inputs:

- `BASE_URL`
- `TENANT_TOKEN`
- `API_KEY`
- `IAP_CLIENT_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `PARSE_FIXTURE_FILE`
- `PARSE_FIXTURE_FILE_TYPE`
- optional targeted-run inputs such as `PARSE_MATRIX_FIXTURES_JSON` or `BATCH_FIXTURES_JSON`

### CI Recommendation
- Keep one protected workflow for the default gate.
- Add broader suites only as separate explicit CI lanes once runtime and stability are well understood.
- Do not make `full` or `extended` the default on every push or PR.

## Validation Plan For Future Implementation
The runner implementation is complete only when all of the following are true.

### CLI Transparency
- `--list` shows the inventory-backed suite, endpoint, and category mapping.
- `--dry-run` prints exact underlying commands and required env expectations without executing them.

### Default Behavior
- No-arg runner maps to `--suite protected`.
- `--suite protected` is equivalent to today's protected baseline command.

### Command Parity
- `--suite full` is equivalent to today's full regression behavior.
- parse matrix targeting supports:
  - `--file-types`
  - `--fixtures-json`
  - `--k`
  - `--report`
- batch targeting supports:
  - direct batch execution
  - selected-fixture execution
  - chunking semantics
  - warning output parity

### Reporting And Artifacts
- parse raw response artifacts still exist
- batch raw response artifacts still exist
- existing summary/report artifacts remain available where currently expected
- shared run-directory behavior is preserved where current wrappers depend on it

### Error Handling
- missing secrets fail clearly and early
- `--file-types` and `--fixtures-json` validation remains explicit
- no extended or destructive behavior runs by default

### Test Strategy
Implementation validation should be unit-test heavy before any live validation:
- add `tests/tools/test_run_regression.py`
- use monkeypatch and fake runners in the style of existing runner tests
- assert exact command mapping and env propagation
- assert `--list` and `--dry-run` output
- assert protected/full/batch mapping without needing live API access

### Live Validation After Unit Parity
Only after unit parity:
- run the protected baseline locally
- run one matrix-targeted dry-run, then one real targeted matrix subset if needed
- run one safe batch-targeted dry-run, then one real batch validation if needed
- keep CI cutover until after local parity is demonstrated

## Recommended Implementation Sequence
1. Save this design document.
2. Keep the roadmap aligned to `tools/run_regression.py` rather than `scripts/run_regression.py`.
3. Implement `tools/run_regression.py` with inventory metadata plus `--list` and `--dry-run` only.
4. Add unit tests for command mapping and env propagation.
5. Add protected parse execution mapping.
6. Add full parse execution mapping.
7. Add batch execution mapping.
8. Add reporting and targeted-flag support.
9. Update docs and CI only after parity is confirmed.
10. Deprecate legacy direct-wrapper docs after the canonical runner is proven.

## Roadmap Impact
This plan advances:
- `Phase 0: Repository and runner inventory`
- `Phase 2: One-runner design`

It also partially advances the taxonomy and migration-preparation work needed before implementation.

Next implementation step:
- implement `./.venv/bin/python tools/run_regression.py --list` and `--dry-run` against the documented inventory before adding live execution behavior
