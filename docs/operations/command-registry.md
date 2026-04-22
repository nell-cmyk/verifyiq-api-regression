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
- Mind is the canonical local memory/context layer. Install it with `curl -fsSL https://raw.githubusercontent.com/GabrielMartinMoran/mind/main/scripts/install.sh | bash`, then ensure `~/.local/bin` is on `PATH` for interactive `mind` usage.
- `mind setup opencode` writes managed OpenCode config under `~/.config/opencode/` and uses the local Mind store.
- The current machine defaults to `~/.local/share/data/mind.db` for Mind storage.
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
| `mind setup opencode` | One-time OpenCode memory/MCP setup | Mind installed locally | `~/.config/opencode/opencode.json`, managed instructions, managed plugin | external/local state |
| `mind checkpoint list "projects/verifyiq-api-regression" --status active` | Resume active workflow context | Mind installed; project space exists | none | reads local Mind DB only |
| `mind search "<query>" --space "projects/verifyiq-api-regression" --detail` | Recover durable decisions, bugs, and patterns for the current task | Mind installed; project space exists | none | reads local Mind DB only |
| `mind checkpoint set "projects/verifyiq-api-regression" "Goal" "Pending work" --notes "Current state"` | Persist current goal, pending work, and continuity state | Mind installed; project space exists | local Mind checkpoint entry | external/local state |

## Advanced/Internal Commands
| Command | Why It Is Not Primary | Primary Artifacts | Mutation Scope |
| --- | --- | --- | --- |
| `./.venv/bin/python -m pytest tests/endpoints/batch/ -v` | Direct live `/documents/batch` validation when batch-specific coverage is needed | `reports/batch/batch_<timestamp>/...` | generated artifacts only |
| `./.venv/bin/python tools/run_batch_with_fixtures.py --fixtures-json /path/to/fixtures.json` | Selected-fixture `/documents/batch` run | `reports/batch/batch_<timestamp>/...` | generated artifacts only |
| `RUN_PARSE_MATRIX=1 ./.venv/bin/python -m pytest tests/endpoints/parse/test_parse_matrix.py -v` | Valid direct matrix surface for debugging, but the wrapper is the normal path | none unless you capture output separately | no repo mutation by default |
| `./.venv/bin/python tools/reporting/render_regression_summary.py --endpoint parse --input reports/parse/matrix/latest-terminal.txt` | Re-renders from saved terminal output; not the primary run surface | `reports/parse/matrix/latest-summary.md` by default | generated summary only in draft mode |
| `./.venv/bin/python tools/run_parse_with_report.py --tier baseline|matrix|full ...` | Focused structured-report iteration, not the default operator flow | `reports/regression/<timestamp>/...` | generated artifacts only |
| `mind create "projects/verifyiq-api-regression" "Persistent memory for VerifyIQ API regression automation" --tags "type:project"` | Space creation is one-time bootstrap, not a normal repeated command | local Mind space metadata | external/local state |
| `mind add "projects/verifyiq-api-regression" "memory-name" "What: ... Why: ... Where: ... Learned: ..." --tags "cat:decision"` | Durable memory capture happens during work, but the exact content is task-specific | local Mind memory entry | external/local state |
| `mind checkpoint recover "projects/verifyiq-api-regression" --name <checkpoint-name>` | Specific recovery step after listing checkpoints | recovered checkpoint payload in terminal output | reads local Mind DB only |
| `mind checkpoint complete "projects/verifyiq-api-regression" "<checkpoint-name>" "Completed work summary"` | Closes a known active checkpoint after work finishes | completed checkpoint entry in Mind history | external/local state |
| `mind serve start --detached` | Optional local web UI + HTTP API access; not required for everyday repo work | local web service on `http://localhost:30303` | external/local state |
| `mind mcp start --http --detached` | Optional local HTTP MCP endpoint; OpenCode uses local command transport by default | local MCP service on `http://localhost:7438/mcp` | external/local state |
| `mind server-status` | Status/debug surface for optional Mind services | none | reads local Mind runtime state |

## Mutating Commands
| Command | What It Can Mutate |
| --- | --- |
| `./.venv/bin/python tools/generate_fixture_registry.py` | tracked `tests/endpoints/parse/fixture_registry.yaml` |
| `./.venv/bin/python tools/onboard_fixture_json.py --json /path/to/fixtures.json` | tracked `tools/fixture_registry_source/supplemental_fixture_registry.yaml` and, when needed, tracked `tests/endpoints/parse/fixture_registry.yaml` |
| `./.venv/bin/python tools/reporting/render_regression_summary.py --mode apply ...` | summary output plus tracked `docs/knowledge-base/parse/promotion-candidates.md` |
| `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py --mode apply` | generated matrix outputs plus tracked `docs/knowledge-base/parse/promotion-candidates.md` |
| `mind setup opencode` | `~/.config/opencode/opencode.json`, `~/.config/opencode/instructions/*`, `~/.config/opencode/plugins/*`, and Mind-installed skills |
| `mind create "projects/verifyiq-api-regression" ...` | local Mind space metadata in `mind.db` |
| `mind add "projects/verifyiq-api-regression" ...` | local Mind memory entries in `mind.db` |
| `mind checkpoint set "projects/verifyiq-api-regression" ...` | local Mind checkpoint entries in `mind.db` |
| `mind checkpoint complete "projects/verifyiq-api-regression" ...` | checkpoint lifecycle state in `mind.db` |
| `mind serve start --detached` | local Mind web server process state |
| `mind mcp start --http --detached` | local Mind MCP server process state |
| `./.venv/bin/python tools/safe_git_commit.py ...` | Git index, commit history, and optional upstream push state |

## Notes
- The matrix wrapper sets `RUN_PARSE_MATRIX=1` for you.
- Structured reporting under `reports/regression/<timestamp>/` is opt-in via `--report`.
- `tools/generate_fixture_registry.py` and `tools/onboard_fixture_json.py` are maintenance surfaces, not ordinary validation steps.
- `mind checkpoint list|recover|search` are the normal resume surfaces for active context.
- `mind setup opencode` installs local protocol instructions plus a non-blocking automation plugin for session and compaction continuity.
- Mind uses a local SQLite store; avoid running multiple `mind` commands in parallel against the same database or you may hit `SQLITE_BUSY_RECOVERY`.
- Historical Obsidian session helpers are removed. Use Mind directly for workflow memory and continuity.
- Historical `.codex/skills/regression-run-summary/scripts/...` reporting entrypoints are removed. Translate any old reference to the canonical `tools/reporting/*` commands.

## Update Rules
- Add new repo-owned executable surfaces here when they become user-visible.
- Update this file in the same pass as any canonical command or workflow change.
- Keep command strings exact and repo-root-relative.
- Record artifact paths and mutation scope concisely.
