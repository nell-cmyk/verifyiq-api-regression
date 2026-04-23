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
- `VERIFYIQ_SKIP_DOTENV=1` disables repo `.env` loading so non-live tooling/reporting suites can prove they do not depend on live env bootstrap.
- Mind is the canonical local memory/context layer. Install it with `curl -fsSL https://raw.githubusercontent.com/GabrielMartinMoran/mind/main/scripts/install.sh | bash`, then ensure `~/.local/bin` is on `PATH` for interactive `mind` usage.
- `mind setup opencode` writes managed OpenCode config under `~/.config/opencode/` and uses the local Mind store.
- Repo-local OpenCode automation lives under `.opencode/` and loads automatically for this repo.
- `./.venv/bin/python tools/mind_session.py ...` is the repo-owned fallback/debug surface. Raw mutating `mind ...` commands are fallback only.
- The current machine defaults to `~/.local/share/data/mind.db` for Mind storage.
- Checked-in CI workflows live under `.github/workflows/`.
- `.github/workflows/non-live-validation.yml` runs the non-live tooling, reporting, and skills suites plus runner discovery checks with `VERIFYIQ_SKIP_DOTENV=1` and no secrets.
- `.github/workflows/protected-baseline.yml` calls `python tools/run_regression.py --suite protected` for the protected live baseline using the `setup-python` interpreter it already bootstraps and installs dependencies into. When these GitHub secrets are configured: `BASE_URL`, `TENANT_TOKEN`, `API_KEY`, `IAP_CLIENT_ID`, `GOOGLE_APPLICATION_CREDENTIALS_JSON`, `PARSE_FIXTURE_FILE`, `PARSE_FIXTURE_FILE_TYPE`, the workflow runs the live baseline. When any are missing, the workflow skips the live baseline with a clear summary.

## Classification Legend
- `Canonical`: normal operator-facing command surface
- `Advanced/Internal`: supported, but narrower or more specialized than the default flow
- `Mutating`: changes tracked files, Git state, or external local state

## Canonical Commands
| Command | Normal Use | High-Level Prereqs | Primary Artifacts | Mutation Scope |
| --- | --- | --- | --- | --- |
| `VERIFYIQ_SKIP_DOTENV=1 ./.venv/bin/python -m pytest tests/tools/ tests/reporting/ tests/skills/ -v` | Canonical non-live validation for runner, reporting, and tooling changes | `.venv` only; no live secrets | none | no repo mutation |
| `./.venv/bin/python tools/run_regression.py` | Canonical live runner entry point; the no-arg default is the parse-only protected suite | Live `/parse` env | `reports/parse/responses/parse_<timestamp>/...` | generated artifacts only |
| `./.venv/bin/python tools/run_regression.py --suite full` | Stronger live gate: protected parse suite followed by delegated full wrapper execution | Live `/parse` env | `reports/parse/responses/parse_<timestamp>/...`, plus the existing matrix/report artifacts when delegation reaches the full wrapper | generated artifacts only |
| `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py` | Default opt-in `/parse` matrix run plus saved summary | Live `/parse` env | `reports/parse/matrix/latest-terminal.txt`, `reports/parse/matrix/latest-summary.md` | generated artifacts only in draft mode |
| `./.venv/bin/python tools/safe_git_commit.py --message "Describe the reviewed change"` | Guarded commit flow after review | Reviewed diff, staged changes, clean worktree | none | Git state only |
| `mind setup opencode` | One-time OpenCode memory/MCP setup | Mind installed locally | `~/.config/opencode/opencode.json`, managed instructions, managed plugin | external/local state |
| `./.venv/bin/python tools/mind_session.py doctor` | Validate the repo-controlled Mind automation surface | Mind installed locally | none | reads local Mind and repo automation state |
| `./.venv/bin/python tools/mind_session.py start` | Force a fresh VerifyIQ context recovery when automatic startup needs verification | Mind installed locally | terminal-only recovered context | external/local state when it creates a checkpoint |

## Advanced/Internal Commands
| Command | Why It Is Not Primary | Primary Artifacts | Mutation Scope |
| --- | --- | --- | --- |
| `./.venv/bin/python -m pytest tests/endpoints/parse/ -v` | Exact protected `/parse` implementation and debug surface; the canonical operator path is now `tools/run_regression.py` | `reports/parse/responses/parse_<timestamp>/...` | generated artifacts only |
| `./.venv/bin/python -m pytest tests/endpoints/batch/ -v` | Direct live `/documents/batch` validation when batch-specific coverage is needed | `reports/batch/batch_<timestamp>/...` | generated artifacts only |
| `./.venv/bin/python tools/run_batch_with_fixtures.py --fixtures-json /path/to/fixtures.json` | Selected-fixture `/documents/batch` run | `reports/batch/batch_<timestamp>/...` | generated artifacts only |
| `./.venv/bin/python tools/run_regression.py --list|--dry-run ...` | Non-executing canonical-runner discovery surface for inventory preview and command mapping | none | no repo mutation |
| `RUN_PARSE_MATRIX=1 ./.venv/bin/python -m pytest tests/endpoints/parse/test_parse_matrix.py -v` | Valid direct matrix surface for debugging, but the wrapper is the normal path | none unless you capture output separately | no repo mutation by default |
| `./.venv/bin/python tools/reporting/render_regression_summary.py --endpoint parse --input reports/parse/matrix/latest-terminal.txt` | Re-renders from saved terminal output; not the primary run surface | `reports/parse/matrix/latest-summary.md` by default | generated summary only in draft mode |
| `./.venv/bin/python tools/run_parse_with_report.py --tier baseline|matrix|full ...` | Focused structured-report iteration, not the default operator flow | `reports/regression/<timestamp>/...` | generated artifacts only |
| `./.venv/bin/python tools/run_parse_full_regression.py` | Compatibility/debug wrapper behind `tools/run_regression.py --suite full` | same matrix artifacts; optional `reports/regression/<timestamp>/...` with `--report` | generated artifacts only |
| `./.venv/bin/python tools/mind_session.py checkpoint` | Fallback explicit checkpoint refresh outside the automatic plugin flow | local Mind checkpoint update | external/local state |
| `./.venv/bin/python tools/mind_session.py save-summary --title "..." --body "..."` | Save a durable project memory before handoff or commit | local Mind memory entry | external/local state |
| `./.venv/bin/python tools/mind_session.py finish` | Fallback explicit checkpoint completion outside the automatic plugin flow | completed checkpoint entry in Mind history | external/local state |
| `mind status` | Raw Mind health/status fallback when wrapper debugging is insufficient | none | reads local Mind DB only |
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
| `./.venv/bin/python tools/mind_session.py start` | may create the project space and/or active continuity checkpoint in `mind.db` |
| `./.venv/bin/python tools/mind_session.py checkpoint` | active checkpoint state in `mind.db` |
| `./.venv/bin/python tools/mind_session.py save-summary ...` | durable project summary memories in `mind.db` |
| `./.venv/bin/python tools/mind_session.py finish` | checkpoint lifecycle state plus Mind-generated session summary memory |
| `mind serve start --detached` | local Mind web server process state |
| `mind mcp start --http --detached` | local Mind MCP server process state |
| `./.venv/bin/python tools/safe_git_commit.py ...` | Git index, commit history, and optional upstream push state |

## Notes
- The matrix wrapper sets `RUN_PARSE_MATRIX=1` for you.
- Structured reporting under `reports/regression/<timestamp>/` is opt-in via `--report`.
- `tools/run_regression.py` is the canonical operator path for the default protected live suite and the current delegated `--suite full` path.
- `tools/run_regression.py` currently supports live execution for the protected baseline and `--suite full` only. Direct live parse-matrix, batch, extended, and other selections remain dry-run only.
- `smoke` remains planned terminology, not a broader current default suite.
- `tools/generate_fixture_registry.py` and `tools/onboard_fixture_json.py` are maintenance surfaces, not ordinary validation steps.
- The normal active-context path is automatic through `.opencode/plugins/verifyiq-mind-session.js`.
- `tools/mind_session.py` is the repo-owned fallback surface for explicit recovery, checkpointing, summaries, and finish events.
- `mind setup opencode` installs global Mind wiring, while `.opencode/opencode.json` adds repo-local automation and skills.
- Mind uses a local SQLite store; avoid running multiple raw mutating `mind` commands in parallel against the same database or you may hit `SQLITE_BUSY_RECOVERY`. The wrapper already serializes access.
- Historical Obsidian session helpers are removed. Use Mind directly for workflow memory and continuity.
- Historical `.codex/skills/regression-run-summary/scripts/...` reporting entrypoints are removed. Translate any old reference to the canonical `tools/reporting/*` commands.

## Update Rules
- Add new repo-owned executable surfaces here when they become user-visible.
- Update this file in the same pass as any canonical command or workflow change.
- Keep command strings exact and repo-root-relative.
- Record artifact paths and mutation scope concisely.
