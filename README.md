# VerifyIQ API Regression

Python-first live API regression automation for VerifyIQ, centered on the protected `/parse` baseline.

## Quick Start
1. `python3 -m venv .venv`
2. `./.venv/bin/python -m pip install -r requirements.txt`
3. Non-live validation: `VERIFYIQ_SKIP_DOTENV=1 ./.venv/bin/python -m pytest tests/tools/ tests/reporting/ tests/skills/ -v`
4. Live protected default after configuring `.env`: `./.venv/bin/python tools/run_regression.py`

## Canonical Commands
- Protected default runner: `./.venv/bin/python tools/run_regression.py`
- Stronger live gate: `./.venv/bin/python tools/run_regression.py --suite full`
- Matrix run + saved summary: `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py`
- Non-live tooling/reporting validation: `VERIFYIQ_SKIP_DOTENV=1 ./.venv/bin/python -m pytest tests/tools/ tests/reporting/ tests/skills/ -v`
- Safe Git commit flow: `./.venv/bin/python tools/safe_git_commit.py --message "Describe the reviewed change"`
- Command registry: `docs/operations/command-registry.md`
- Workflow runbook: `docs/operations/workflow.md`

## Mind Memory Workflow
- Active workflow memory lives in Mind space `projects/verifyiq-api-regression`, not in repo docs.
- OpenCode now loads repo-controlled Mind automation from `.opencode/` when this repo is open.
- Normal path: the repo plugin automatically recovers context, refreshes continuity checkpoints, and closes the active checkpoint when the session ends.
- Fallback/debug path: use `./.venv/bin/python tools/mind_session.py doctor|start|checkpoint|save-summary|finish`.
- See `docs/operations/mind-session.md` for the automatic flow and troubleshooting.

## Reporting Outputs
- Matrix summary lane: `reports/parse/matrix/latest-terminal.txt` and `reports/parse/matrix/latest-summary.md`
- Structured per-run lane: `reports/regression/<timestamp>/report.json`, `report.md`, and `LATEST.txt` when `--report` is enabled

## Repo Map
- `tests/`
  Endpoint coverage plus shared test infrastructure. `/parse` remains the protected baseline.
- `tools/`
  Repo-owned executable commands. This is the canonical home for Git helpers, full-regression wrappers, and human-facing reporting entrypoints.
- `docs/operations/`
  Runbooks and exact operational commands.
- `docs/knowledge-base/`
  Durable repo and endpoint findings.
- `.codex/`
  Repo-local agent packaging and adapters. Keep agent-specific wiring here, but prefer `tools/` for shared repo utilities.
- `.claude/`
  Repo-local Claude configuration.
- `reports/`
  Generated run output only. Treat it as disposable local output, not durable repo truth.

## Notes
- The protected parse-only suite remains the default live validation gate.
- `tools/run_regression.py` is the canonical operator path for the default protected live suite.
- The matrix remains opt-in and separate from the default baseline.
- `smoke` remains planned terminology, not a broader current default.
- The human-facing reporting commands live under `tools/reporting/`.
- `docs/operations/current-handoff.md` is pointer-only; active session continuity now lives in Mind.
