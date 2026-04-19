# VerifyIQ API Regression

Python-first API regression automation for VerifyIQ, currently centered on the protected `/parse` baseline.

## Quick Start
- Protected baseline: `pytest tests/endpoints/parse/ -v`
- Matrix run + saved summary: `python tools/reporting/run_parse_matrix_with_summary.py`
- Full regression: `python tools/run_parse_full_regression.py`
- Safe Git commit flow: `python tools/safe_git_commit.py --message "Describe the reviewed change"`

## Reporting Outputs
- Matrix summary lane: `reports/parse/matrix/latest-terminal.txt` and `reports/parse/matrix/latest-summary.md`
- Structured per-run lane: `reports/regression/<timestamp>/report.json`, `report.md`, and `LATEST.txt` when `--report` is enabled

## Repo Map
- `tests/`
  Endpoint coverage plus test infrastructure for the regression suite. `/parse` remains the protected baseline.
- `tools/`
  Repo-owned executable commands. This is the canonical home for Git helpers, full-regression wrappers, and human-facing reporting entrypoints.
- `docs/operations/`
  Runbooks and exact operational commands.
- `docs/knowledge-base/`
  Durable repo and endpoint findings.
- `.codex/`
  Repo-local Codex packaging and adapters. Keep agent-specific wiring here, but prefer `tools/` for shared repo utilities.
- `.claude/`
  Repo-local Claude configuration.
- `reports/`
  Generated run output only. Treat it as disposable local output, not durable repo truth.

## Canonical Home Rules
- Use `tools/` for repo-owned executables.
- Use `.codex/skills/` for agent packaging, adapters, and agent-specific guidance.
- Use `docs/operations/` for repeatable runbooks.
- Use `docs/knowledge-base/` for durable findings, not active working notes or roadmap planning.
- Prefer top-level wrapper commands over deep internal paths when documenting workflows.

## Notes
- The protected baseline behavior must stay unchanged: `pytest tests/endpoints/parse/ -v`
- The matrix remains opt-in and separate from the default baseline.
- The human-facing reporting commands now live under `tools/reporting/`. The older `.codex/.../scripts/...` paths remain compatible during the transition.
