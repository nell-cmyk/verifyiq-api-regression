# Command Registry

## Purpose
Use this file as the source of truth for runnable command surfaces in the current root checkout.

Use it to answer:
- which commands are canonical
- which commands are advanced or mutating
- which artifact paths and prerequisites matter

Use `docs/operations/workflow.md` for the operator run sequence and `docs/operations/matrix.md` for matrix-specific triage.

## Runtime Notes
- Run repo-local commands from the repo root.
- Repo-local Python and pytest commands assume `.venv`; bootstrap with `python3 -m venv .venv`, then install deps with `./.venv/bin/python -m pip install -r requirements.txt`.
- Tool-only deps are needed only for fixture-registry maintenance: `./.venv/bin/python -m pip install -r tools/requirements.txt`.
- `/parse` baseline, matrix, full regression, and `/documents/batch` validation all require the live repo env.
- `PARSE_FIXTURE_FILE` must remain a `gs://` URI.
- The external Obsidian session helper expects the vault at `/Users/nellvalenzuela/Documents/QA Workbench`.
- Because this repo lives under `~/Documents`, foreground watcher commands are preferred over background macOS agents on this machine.
- Checked-in CI lives at `.github/workflows/protected-baseline.yml`. It runs the protected baseline when these GitHub secrets are configured: `BASE_URL`, `TENANT_TOKEN`, `API_KEY`, `IAP_CLIENT_ID`, `GOOGLE_APPLICATION_CREDENTIALS_JSON`, `PARSE_FIXTURE_FILE`, `PARSE_FIXTURE_FILE_TYPE`. When any are missing, the workflow skips the live baseline with a clear summary.

## Classification Legend
- `Canonical`: normal operator-facing command surface
- `Advanced/Internal`: supported, but narrower or more specialized than the default flow
- `Mutating`: changes tracked files, Git state, or external local state

## Canonical Commands
| Command | Normal Use | High-Level Prereqs | Primary Artifacts | Mutation Scope |
| --- | --- | --- | --- | --- |
| `./.venv/bin/python -m pytest tests/endpoints/parse/ -v` | Protected `/parse` baseline validation | Live `/parse` env | `reports/parse/responses/parse_<timestamp>/...` | generated artifacts only |
| `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py` | Default opt-in `/parse` matrix run plus saved summary | Live `/parse` env | `reports/parse/matrix/latest-terminal.txt`, `reports/parse/matrix/latest-summary.md` | generated artifacts only in draft mode |
| `./.venv/bin/python tools/run_parse_full_regression.py` | Stronger gate: protected baseline, then matrix wrapper | Same env as baseline + matrix | same matrix artifacts; optional `reports/regression/<timestamp>/...` with `--report` | generated artifacts only |
| `./.venv/bin/python tools/safe_git_commit.py --message "Describe the reviewed change"` | Guarded commit flow after review | Reviewed diff, staged changes, clean worktree | none | Git state only |
| `./.venv/bin/python tools/start_ai_session.py` | Normal daily startup for external Obsidian + foreground transcript sync | External Obsidian vault exists | external session note; same live-sync artifacts as watcher when started here | external/local state |

## Advanced/Internal Commands
| Command | Why It Is Not Primary | Primary Artifacts | Mutation Scope |
| --- | --- | --- | --- |
| `./.venv/bin/python -m pytest tests/endpoints/batch/ -v` | Direct live `/documents/batch` validation when batch-specific coverage is needed | `reports/batch/batch_<timestamp>/...` | generated artifacts only |
| `./.venv/bin/python tools/run_batch_with_fixtures.py --fixtures-json /path/to/fixtures.json` | Selected-fixture `/documents/batch` run | `reports/batch/batch_<timestamp>/...` | generated artifacts only |
| `RUN_PARSE_MATRIX=1 ./.venv/bin/python -m pytest tests/endpoints/parse/test_parse_matrix.py -v` | Valid direct matrix surface for debugging, but the wrapper is the normal path | none unless you capture output separately | no repo mutation by default |
| `./.venv/bin/python tools/reporting/render_regression_summary.py --endpoint parse --input reports/parse/matrix/latest-terminal.txt` | Re-renders from saved terminal output; not the primary run surface | `reports/parse/matrix/latest-summary.md` by default | generated summary only in draft mode |
| `./.venv/bin/python tools/run_parse_with_report.py --tier baseline|matrix|full ...` | Focused structured-report iteration, not the default operator flow | `reports/regression/<timestamp>/...` | generated artifacts only |
| `./.venv/bin/python tools/obsidian_session.py --today --open` | Resolve or open the external active note without the startup wrapper | external session note | external/local state |
| `./.venv/bin/python tools/session_capture_pipeline.py --sync` | Manual transcript catch-up outside the normal watcher flow | `reports/conversation-captures/**/*` plus refreshed external note sections | generated artifacts plus external note |

## Mutating Commands
| Command | What It Can Mutate |
| --- | --- |
| `./.venv/bin/python tools/generate_fixture_registry.py` | tracked `tests/endpoints/parse/fixture_registry.yaml` |
| `./.venv/bin/python tools/onboard_fixture_json.py --json /path/to/fixtures.json` | tracked `tools/fixture_registry_source/supplemental_fixture_registry.yaml` and, when needed, tracked `tests/endpoints/parse/fixture_registry.yaml` |
| `./.venv/bin/python tools/reporting/render_regression_summary.py --mode apply ...` | summary output plus tracked `docs/knowledge-base/parse/promotion-candidates.md` |
| `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py --mode apply` | generated matrix outputs plus tracked `docs/knowledge-base/parse/promotion-candidates.md` |
| `./.venv/bin/python tools/install_session_capture_automation.py` | `~/.claude/settings.json`; optional launch-agent plist and launchctl state |
| `./.venv/bin/python tools/start_ai_session.py` | external note; if it starts the watcher, the same generated files and automated note sections as the sync pipeline |
| `./.venv/bin/python tools/obsidian_session.py --today --open` | external note under `/Users/nellvalenzuela/Documents/QA Workbench/Sessions/` |
| `./.venv/bin/python tools/session_capture_pipeline.py --watch --quiet` | `reports/conversation-captures/**/*` and automated sections in the external session note while running |
| `./.venv/bin/python tools/safe_git_commit.py ...` | Git index, commit history, and optional upstream push state |

## Notes
- The matrix wrapper sets `RUN_PARSE_MATRIX=1` for you.
- Structured reporting under `reports/regression/<timestamp>/` is opt-in via `--report`.
- `tools/generate_fixture_registry.py` and `tools/onboard_fixture_json.py` are maintenance surfaces, not ordinary validation steps.
- Historical `.codex/skills/regression-run-summary/scripts/...` reporting entrypoints are removed. Translate any old reference to the canonical `tools/reporting/*` commands.

## Update Rules
- Add new repo-owned executable surfaces here when they become user-visible.
- Update this file in the same pass as any canonical command or workflow change.
- Keep command strings exact and repo-root-relative.
- Record artifact paths and mutation scope concisely.
