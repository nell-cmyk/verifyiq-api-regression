# Command Registry

## Purpose
Use this file as the single source of truth for classifying runnable command surfaces in the current root checkout.

This is a classification document, not a workflow guide:
- use it to decide which command surface is primary
- use `docs/operations/workflow.md` for the normal end-to-end operator flow
- use `docs/operations/matrix.md` for matrix triage and run flow
- exclude archived `.claude/worktrees/*` snapshots, `.git` metadata, and `__pycache__` residue from command-surface classification

## Classification Legend
- `Canonical`: normal operator-facing command surface
- `Advanced/Internal`: valid and supported, but specialized or narrower than the default workflow
- `Compatibility-only`: still runnable, but intentionally not a primary workflow surface
- `Deprecated/Legacy`: removed, replaced, or explicitly not for current use

## Prerequisites / Environment Notes
- `/parse` baseline, matrix, full-regression, and reporting commands all assume the repo env is configured for live API access.
- Protected `/parse` happy-path coverage still depends on the repo's configured `PARSE_FIXTURE_FILE` and related auth settings.
- `PARSE_FIXTURE_FILE` must remain a `gs://` URI.
- The matrix wrapper sets `RUN_PARSE_MATRIX=1` for you. Direct matrix pytest commands require that env var explicitly.
- Structured reporting under `reports/regression/<timestamp>/` is opt-in via `--report` on the wrapper surfaces that support it.
- Fixture-registry regeneration depends on `tools/fixture_registry_source/qa_fixture_registry.xlsx` plus the deps in `tools/requirements.txt`.
- `tools/safe_git_commit.py` expects a reviewed/staged change set and a clean worktree; `--push` also requires a matching upstream branch.

## Canonical Commands
| Command | Normal Use | High-Level Prereqs | Artifacts | Mutation Scope |
| --- | --- | --- | --- | --- |
| `pytest tests/endpoints/parse/ -v` | Protected `/parse` baseline validation | Live repo env for `/parse`; no matrix opt-in | none by default | no repo mutation |
| `python tools/reporting/run_parse_matrix_with_summary.py` | Default opt-in `/parse` matrix run plus saved summary | Live repo env for `/parse`; wrapper handles `RUN_PARSE_MATRIX=1` | `reports/parse/matrix/latest-terminal.txt`, `reports/parse/matrix/latest-summary.md` | generated artifacts only in draft mode |
| `python tools/run_parse_full_regression.py` | Stronger gate: baseline first, then matrix wrapper | Same env as baseline + matrix | same matrix artifacts; optional structured reports with `--report` | generated artifacts only |
| `python tools/safe_git_commit.py --message "Describe the reviewed change"` | Guarded commit flow after review | Staged changes, clean worktree, branch configured | none | Git state only |

Notes:
- `python tools/reporting/run_parse_matrix_with_summary.py --report` also writes `reports/regression/<timestamp>/report.json`, `report.md`, and `LATEST.txt`.
- `python tools/reporting/run_parse_matrix_with_summary.py --mode apply` additionally appends reviewed promotion candidates to `docs/knowledge-base/parse/promotion-candidates.md`.

## Advanced/Internal Commands
| Command | Why It Is Not Primary | Artifacts | Mutation Scope |
| --- | --- | --- | --- |
| `python tools/reporting/render_regression_summary.py --endpoint parse --input reports/parse/matrix/latest-terminal.txt` | Re-renders from saved terminal output; useful after a completed run, not as the primary run surface | `reports/parse/matrix/latest-summary.md` by default | generated summary only in draft mode |
| `python tools/run_parse_with_report.py --tier baseline|matrix|full ...` | Focused reporter iteration and targeted structured-report inspection, not the normal operator workflow | `reports/regression/<timestamp>/report.json`, `report.md`, `LATEST.txt` | generated artifacts only |
| `python tools/generate_fixture_registry.py` | Maintenance command for fixture-registry refresh, not a normal regression run | `tests/endpoints/parse/fixture_registry.yaml` | mutates tracked generated YAML |
| `pytest tests/endpoints/parse/test_parse_matrix.py -v` with `RUN_PARSE_MATRIX=1` | Valid direct matrix surface for debugging, but the wrapper is the normal path because it captures terminal output and renders the summary | none unless you add your own capture step | no repo mutation by default |

Notes:
- `python tools/reporting/render_regression_summary.py --mode apply` also mutates `docs/knowledge-base/parse/promotion-candidates.md`.
- `python tools/run_parse_with_report.py` preserves the same underlying tier behavior as the chosen baseline, matrix, or full-regression run.

## Compatibility-only Commands
None in the current root checkout.

After the reporting cleanup, there are no live compatibility wrappers for the old `.codex/skills/regression-run-summary/scripts/...` reporting entrypoints.

## Deprecated/Legacy Commands
None in the current root checkout.

Removed historical reporting paths:
- The old `.codex/skills/regression-run-summary/scripts/...` reporting commands are no longer present in the root repo.
- If they appear in old notes, old artifacts, or archived worktree snapshots, translate them to the canonical `tools/reporting/*` commands instead.

## Artifact-producing Commands
| Command | Primary Outputs |
| --- | --- |
| `python tools/reporting/run_parse_matrix_with_summary.py` | `reports/parse/matrix/latest-terminal.txt`, `reports/parse/matrix/latest-summary.md` |
| `python tools/reporting/run_parse_matrix_with_summary.py --report` | matrix outputs above plus `reports/regression/<timestamp>/report.json`, `report.md`, `LATEST.txt` |
| `python tools/run_parse_full_regression.py --report` | matrix outputs above plus `reports/regression/<timestamp>/report.json`, `report.md`, `LATEST.txt` |
| `python tools/reporting/render_regression_summary.py --endpoint parse --input ...` | `reports/parse/matrix/latest-summary.md` by default, or the explicit `--output` target |
| `python tools/run_parse_with_report.py --tier baseline|matrix|full ...` | `reports/regression/<timestamp>/report.json`, `report.md`, `LATEST.txt` |
| `python tools/generate_fixture_registry.py` | `tests/endpoints/parse/fixture_registry.yaml` |

## Mutating Commands
| Command | What It Can Mutate |
| --- | --- |
| `python tools/reporting/run_parse_matrix_with_summary.py` | generated files under `reports/parse/matrix/` |
| `python tools/reporting/run_parse_matrix_with_summary.py --report` | generated files under `reports/parse/matrix/` and `reports/regression/` |
| `python tools/reporting/run_parse_matrix_with_summary.py --mode apply` | generated files under `reports/parse/matrix/` and tracked KB file `docs/knowledge-base/parse/promotion-candidates.md` |
| `python tools/reporting/render_regression_summary.py --endpoint parse --input ...` | summary output file only |
| `python tools/reporting/render_regression_summary.py --mode apply ...` | summary output file and tracked KB file `docs/knowledge-base/parse/promotion-candidates.md` |
| `python tools/run_parse_with_report.py --tier ...` | generated files under `reports/regression/` |
| `python tools/generate_fixture_registry.py` | tracked generated file `tests/endpoints/parse/fixture_registry.yaml` |
| `python tools/safe_git_commit.py ...` | Git index/history/upstream push state depending on flags |

## Update Rules For New/Changed Commands
- Add every new repo-owned executable or newly recommended pytest command surface here when it becomes user-visible.
- If a command becomes canonical, update this file in the same pass that changes the wrapper ownership or operator guidance.
- Record artifact paths and mutation scope concisely; do not duplicate full runbook steps here.
- Do not list `.codex` agent-packaging paths as live command surfaces unless the root repo intentionally restores them as runnable entrypoints.
- When a command is removed, move it to `Deprecated/Legacy` or remove it entirely if no one should see it anymore.
