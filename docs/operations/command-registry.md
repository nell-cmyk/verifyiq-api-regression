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
- The external Obsidian session helper expects the vault to exist at `/Users/nellvalenzuela/Documents/QA Workbench`.
- The transcript sync automation depends on local Codex transcripts under `~/.codex/sessions/` and local Claude Code transcripts under `~/.claude/projects/`.
- Because this repo and the external vault live under `~/Documents`, macOS background agents may not have reliable permission to read/write them. Use the foreground watcher command for Codex live syncing on this machine.
- Protected `/parse` happy-path coverage still depends on the repo's configured `PARSE_FIXTURE_FILE` and related auth settings.
- `PARSE_FIXTURE_FILE` must remain a `gs://` URI.
- Supported `/parse` runs write one raw JSON artifact per `/v1/documents/parse` call under a per-run folder in `reports/parse/responses/`.
- Supported `/batch` runs write one raw JSON artifact per `/v1/documents/batch` call under a per-run folder in `reports/batch/`.
- Each Python command invocation reuses one raw-response run folder for all `/parse` or `/batch` artifacts it produces.
- The matrix wrapper sets `RUN_PARSE_MATRIX=1` for you. Direct matrix pytest commands require that env var explicitly.
- Structured reporting under `reports/regression/<timestamp>/` is opt-in via `--report` on the wrapper surfaces that support it.
- Fixture-registry regeneration depends on `tools/fixture_registry_source/qa_fixture_registry.xlsx`, `tools/fixture_registry_source/supplemental_fixture_registry.yaml`, and the deps in `tools/requirements.txt`.
- `tools/safe_git_commit.py` expects a reviewed/staged change set and a clean worktree; `--push` also requires a matching upstream branch.

## Canonical Commands
| Command | Normal Use | High-Level Prereqs | Artifacts | Mutation Scope |
| --- | --- | --- | --- | --- |
| `python3 tools/install_session_capture_automation.py` | One-time install of Claude hook automation and any safe local automation helpers | Local Codex/Claude transcript stores exist | user-level Claude settings; optional launch agent only when path permissions allow | external local config only |
| `python3 tools/start_ai_session.py` | One-command daily startup: resolve or open today's canonical note, print concise status, and start the foreground watcher only if it is not already running | External Obsidian vault exists; run from a terminal tab you can leave open if the watcher starts here | external note `Sessions/YYYY-MM-DD - verifyiq-api-regression.md`; same watcher artifacts as the live sync command when it starts the watcher | external vault markdown only when a note is created or opened; otherwise it hands off to the same generated-artifact flow as the watcher |
| `python3 tools/obsidian_session.py --today --open` | Start or resume the canonical external active session note for this project | External Obsidian vault exists at `/Users/nellvalenzuela/Documents/QA Workbench` | external note `Sessions/YYYY-MM-DD - verifyiq-api-regression.md` | external vault markdown only |
| `python3 tools/session_capture_pipeline.py --watch --quiet` | Keep Codex and Claude transcripts normalized into today’s note while you work | Foreground terminal tab; local transcript stores exist | refreshed automated note sections plus `reports/conversation-captures/**/*` | generated artifacts plus external note |
| `pytest tests/endpoints/parse/ -v` | Protected `/parse` baseline validation | Live repo env for `/parse`; no matrix opt-in | `reports/parse/responses/parse_<timestamp>/<test-case-id>__<description>__<timestamp>_<seq>.json` | generated artifacts only under `reports/parse/responses/` |
| `python tools/reporting/run_parse_matrix_with_summary.py` | Default opt-in `/parse` matrix run plus saved summary | Live repo env for `/parse`; wrapper handles `RUN_PARSE_MATRIX=1` | `reports/parse/matrix/latest-terminal.txt`, `reports/parse/matrix/latest-summary.md` | generated artifacts only in draft mode |
| `python tools/run_parse_full_regression.py` | Stronger gate: baseline first, then matrix wrapper | Same env as baseline + matrix | same matrix artifacts; optional structured reports with `--report` | generated artifacts only |
| `python tools/safe_git_commit.py --message "Describe the reviewed change"` | Guarded commit flow after review | Staged changes, clean worktree, branch configured | none | Git state only |

Notes:
- `python3 tools/start_ai_session.py` is the recommended day-to-day startup command on this Mac. It preserves the existing architecture by calling the same note helper and foreground watcher underneath, and it leaves Claude hook-based capture untouched.
- If `python3 tools/start_ai_session.py` finds an existing foreground watcher for this repo, it only resolves or opens today's note, prints status, and exits without starting a duplicate watcher.
- `python3 tools/obsidian_session.py --latest` returns the most recently modified session note for this project, and `--open` prefers opening the resolved note in Obsidian on macOS before falling back to the default app.
- `python3 tools/install_session_capture_automation.py` installs Claude hooks and prints the foreground watch command. It skips the launch agent by default when the repo lives under a macOS-protected folder such as `~/Documents`.
- `python3 tools/session_capture_pipeline.py --sync` is the manual catch-up command behind the live automation; it syncs Codex and Claude transcripts into `reports/conversation-captures/` and refreshes today's automated note sections.
- `python tools/reporting/run_parse_matrix_with_summary.py --report` also writes `reports/regression/<timestamp>/report.json`, `report.md`, and `LATEST.txt`.
- `python tools/reporting/run_parse_matrix_with_summary.py --mode apply` additionally appends reviewed promotion candidates to `docs/knowledge-base/parse/promotion-candidates.md`.
- `python tools/reporting/run_parse_matrix_with_summary.py --fixtures-json /path/to/fixtures.json` keeps the default matrix wrapper flow but replaces canonical selection with the exact registry fixtures resolved from that JSON input after skipping unsupported file formats.
- `python tools/run_batch_with_fixtures.py --fixtures-json /path/to/fixtures.json` reuses the same fixture JSON normalization rules as `/parse`; when the selection resolves to more than four supported registry fixtures, it runs the full live `/documents/batch` suite once on the first legal chunk, then replays the happy-path checks across the remaining chunks. It also surfaces registry-annotated batch warning fixtures, such as known `DocumentSizeGuardError` page-count limits, instead of silently treating them as ordinary happy-path items.

## Advanced/Internal Commands
| Command | Why It Is Not Primary | Artifacts | Mutation Scope |
| --- | --- | --- | --- |
| `python3 tools/session_capture_pipeline.py --sync` | Useful for manual backfill and debugging because the watcher or Claude hooks usually keep things current for you | `reports/conversation-captures/raw/**/*`, `reports/conversation-captures/normalized/**/*`, state JSON, and refreshed external note sections | generated artifacts plus external Obsidian note |
| `python tools/reporting/render_regression_summary.py --endpoint parse --input reports/parse/matrix/latest-terminal.txt` | Re-renders from saved terminal output; useful after a completed run, not as the primary run surface | `reports/parse/matrix/latest-summary.md` by default | generated summary only in draft mode |
| `python tools/run_parse_with_report.py --tier baseline|matrix|full ...` | Focused reporter iteration and targeted structured-report inspection, not the normal operator workflow | `reports/regression/<timestamp>/report.json`, `report.md`, `LATEST.txt` | generated artifacts only |
| `pytest tests/endpoints/batch/test_batch.py -v` | Direct live `/documents/batch` validation | Live repo env for `/documents/batch` | `reports/batch/batch_<timestamp>/batch_<timestamp>_<seq>.json` | generated artifacts only under `reports/batch/` |
| `python tools/run_batch_with_fixtures.py --fixtures-json /path/to/fixtures.json` | Opt-in `/documents/batch` selected-fixture run; useful when you want batch coverage against an exact JSON-provided fixture list, including larger JSON inputs that need to be chunked into multiple legal 4-item batch requests and registry-annotated warning fixtures that should be treated as expected page-limit warnings instead of hard failures | `reports/batch/batch_<timestamp>/batch_<timestamp>_<seq>.json` | generated artifacts only under `reports/batch/` |
| `python tools/generate_fixture_registry.py` | Maintenance command for fixture-registry refresh, not a normal regression run | `tests/endpoints/parse/fixture_registry.yaml` | mutates tracked generated YAML |
| `python tools/onboard_fixture_json.py --json /path/to/fixtures.json` | Maintenance helper for JSON-driven fixture onboarding before an opt-in selected-fixture run | `tools/fixture_registry_source/supplemental_fixture_registry.yaml`, `tests/endpoints/parse/fixture_registry.yaml` when new supported fixtures are added; skipped unsupported entries are reported only in CLI output | mutates tracked YAML sources only when missing supported fixtures are discovered |
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
| `python3 tools/install_session_capture_automation.py` | user-level Claude settings; optional launch-agent plist only when allowed |
| `python3 tools/start_ai_session.py` | external note `Sessions/YYYY-MM-DD - verifyiq-api-regression.md`, plus the same live-sync outputs as the watcher when it starts the watcher |
| `python3 tools/obsidian_session.py --today --open` | external note `Sessions/YYYY-MM-DD - verifyiq-api-regression.md` |
| `python3 tools/session_capture_pipeline.py --watch --quiet` | refreshed automated note sections plus `reports/conversation-captures/raw/**/*`, `reports/conversation-captures/normalized/**/*`, and sync state |
| `python3 tools/session_capture_pipeline.py --sync` | `reports/conversation-captures/raw/**/*`, `reports/conversation-captures/normalized/**/*`, and refreshed automated note sections |
| `python tools/reporting/run_parse_matrix_with_summary.py` | `reports/parse/matrix/latest-terminal.txt`, `reports/parse/matrix/latest-summary.md` |
| `pytest tests/endpoints/parse/ -v` | `reports/parse/responses/parse_<timestamp>/<test-case-id>__<description>__<timestamp>_<seq>.json` |
| `pytest tests/endpoints/batch/test_batch.py -v` | `reports/batch/batch_<timestamp>/batch_<timestamp>_<seq>.json` |
| `python tools/run_batch_with_fixtures.py --fixtures-json /path/to/fixtures.json` | `reports/batch/batch_<timestamp>/batch_<timestamp>_<seq>.json` |
| `python tools/reporting/run_parse_matrix_with_summary.py --report` | matrix outputs above plus `reports/regression/<timestamp>/report.json`, `report.md`, `LATEST.txt` |
| `python tools/run_parse_full_regression.py --report` | matrix outputs above plus `reports/regression/<timestamp>/report.json`, `report.md`, `LATEST.txt` |
| `python tools/reporting/render_regression_summary.py --endpoint parse --input ...` | `reports/parse/matrix/latest-summary.md` by default, or the explicit `--output` target |
| `python tools/run_parse_with_report.py --tier baseline|matrix|full ...` | `reports/regression/<timestamp>/report.json`, `report.md`, `LATEST.txt` |
| `python tools/generate_fixture_registry.py` | `tests/endpoints/parse/fixture_registry.yaml` |
| `python tools/onboard_fixture_json.py --json /path/to/fixtures.json` | `tools/fixture_registry_source/supplemental_fixture_registry.yaml` and, when supported additions exist, `tests/endpoints/parse/fixture_registry.yaml` |

## Mutating Commands
| Command | What It Can Mutate |
| --- | --- |
| `python3 tools/install_session_capture_automation.py` | `~/.claude/settings.json`; optional launch-agent plist and launchctl state when allowed |
| `python3 tools/start_ai_session.py` | external vault markdown under `/Users/nellvalenzuela/Documents/QA Workbench/Sessions/`; if it starts the watcher, the same generated files and automated note sections as `python3 tools/session_capture_pipeline.py --watch --quiet` |
| `python3 tools/obsidian_session.py --today --open` | external vault markdown under `/Users/nellvalenzuela/Documents/QA Workbench/Sessions/` |
| `python3 tools/session_capture_pipeline.py --watch --quiet` | generated files under `reports/conversation-captures/` and automated sections in the external session note while the watcher runs |
| `python3 tools/session_capture_pipeline.py --sync` | generated files under `reports/conversation-captures/` and automated sections in the external session note |
| `pytest tests/endpoints/parse/ -v` | generated per-run raw response folders under `reports/parse/responses/` |
| `pytest tests/endpoints/batch/test_batch.py -v` | generated per-run folders under `reports/batch/` |
| `python tools/run_batch_with_fixtures.py --fixtures-json /path/to/fixtures.json` | generated per-run folders under `reports/batch/` |
| `python tools/reporting/run_parse_matrix_with_summary.py` | generated files under `reports/parse/matrix/` |
| `python tools/reporting/run_parse_matrix_with_summary.py --report` | generated files under `reports/parse/matrix/` and `reports/regression/` |
| `python tools/reporting/run_parse_matrix_with_summary.py --mode apply` | generated files under `reports/parse/matrix/` and tracked KB file `docs/knowledge-base/parse/promotion-candidates.md` |
| `python tools/reporting/render_regression_summary.py --endpoint parse --input ...` | summary output file only |
| `python tools/reporting/render_regression_summary.py --mode apply ...` | summary output file and tracked KB file `docs/knowledge-base/parse/promotion-candidates.md` |
| `python tools/run_parse_with_report.py --tier ...` | generated files under `reports/regression/` |
| `python tools/generate_fixture_registry.py` | tracked generated file `tests/endpoints/parse/fixture_registry.yaml` |
| `python tools/onboard_fixture_json.py --json /path/to/fixtures.json` | tracked YAML under `tools/fixture_registry_source/` and, when supported additions exist, tracked generated file `tests/endpoints/parse/fixture_registry.yaml` |
| `python tools/safe_git_commit.py ...` | Git index/history/upstream push state depending on flags |

## Update Rules For New/Changed Commands
- Add every new repo-owned executable or newly recommended pytest command surface here when it becomes user-visible.
- If a command becomes canonical, update this file in the same pass that changes the wrapper ownership or operator guidance.
- Record artifact paths and mutation scope concisely; do not duplicate full runbook steps here.
- Do not list `.codex` agent-packaging paths as live command surfaces unless the root repo intentionally restores them as runnable entrypoints.
- When a command is removed, move it to `Deprecated/Legacy` or remove it entirely if no one should see it anymore.
