# VerifyIQ API Regression

Python-first live API regression automation for VerifyIQ, centered on the protected `/parse` baseline.

## Quick Start
1. `python3 -m venv .venv`
2. `./.venv/bin/python -m pip install -r requirements.txt`
3. `./.venv/bin/python -m pytest tests/endpoints/parse/ -v`

## Canonical Commands
- Protected baseline: `./.venv/bin/python -m pytest tests/endpoints/parse/ -v`
- Matrix run + saved summary: `./.venv/bin/python tools/reporting/run_parse_matrix_with_summary.py`
- Full regression: `./.venv/bin/python tools/run_parse_full_regression.py`
- Safe Git commit flow: `./.venv/bin/python tools/safe_git_commit.py --message "Describe the reviewed change"`
- Command registry: `docs/operations/command-registry.md`
- Workflow runbook: `docs/operations/workflow.md`

## Mind Memory Workflow
- Active workflow memory now lives in Mind space `projects/verifyiq-api-regression`, not in repo docs.
- One-time bootstrap:
  1. `curl -fsSL https://raw.githubusercontent.com/GabrielMartinMoran/mind/main/scripts/install.sh | bash`
  2. Ensure `~/.local/bin` is on `PATH`
  3. `mind help`
  4. `mind setup opencode`
- Resume context with:
  - `mind checkpoint list "projects/verifyiq-api-regression" --status active`
  - `mind checkpoint recover "projects/verifyiq-api-regression" --name <checkpoint-name>`
  - `mind search "<keywords>" --space "projects/verifyiq-api-regression" --detail`
- Persist decisions, patterns, and checkpoints with:
  - `mind checkpoint set "projects/verifyiq-api-regression" "Goal" "Pending work" --notes "Current state"`
  - `mind add "projects/verifyiq-api-regression" "memory-name" "What: ... Why: ... Where: ... Learned: ..." --tags "cat:decision"`
- See `docs/operations/workflow.md` for the full Mind-backed operator flow.

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
- The protected baseline remains the default validation gate.
- The matrix remains opt-in and separate from the default baseline.
- The human-facing reporting commands live under `tools/reporting/`.
- `docs/operations/current-handoff.md` is pointer-only; active session continuity now lives in Mind.
