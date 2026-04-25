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
- Codex now loads repo-controlled Mind automation from trusted project config in `.codex/` plus the repo skill in `.agents/skills/`.
- Normal path: OpenCode automatically recovers context, refreshes continuity checkpoints, and closes the active checkpoint when the session ends. Codex automatically recovers context and refreshes checkpoints around each turn, but still requires an explicit `finish` before handoff or commit.
- Durable repo truth should be promoted automatically by the agent into the correct tracked docs; Mind keeps active state and summaries, while repo docs keep verified long-lived guidance.
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
- `.agents/`
  Repo-local shared skills, including the Codex-facing Mind session fallback skill.
- `.codex/`
  Repo-local Codex configuration and hooks for Mind MCP plus checkpoint continuity.
- `.claude/`
  Repo-local Claude configuration.
- `reports/`
  Generated run output only. Treat it as disposable local output, not durable repo truth.

## Notes
- The protected parse-only suite remains the default live validation gate.
- `tools/run_regression.py` is the canonical operator path for the default protected live suite.
- The matrix remains opt-in and separate from the default baseline.
- `smoke` is a real opt-in GET suite, not a broader current default.
- The human-facing reporting commands live under `tools/reporting/`.
- `docs/operations/current-handoff.md` is pointer-only; active session continuity now lives in Mind.
