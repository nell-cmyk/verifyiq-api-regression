# Command Registry

Canonical, tier-classified catalog of operator- and agent-facing commands for this repo.

See also: [Repo Roadmap](../knowledge-base/repo-roadmap.md), [Matrix Triage](matrix.md)

## Purpose & Scope
This file is the source of truth for command classification. Other docs (`README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/operations/matrix.md`, and the agent skill under `.codex/skills/`) reference commands by name; this registry owns the authoritative definition of what each command is, which tier it belongs to, its gates, expected result, and output location.

Scope is limited to VerifyIQ API regression automation. Out-of-scope tooling (manual QA, ClickUp, ticket workflows) is not listed here and must not be added.

## Tiers
- `baseline` — protected `/parse` regression. Must stay green. Runs by default.
- `matrix` — opt-in `/parse` fileType matrix. Hard-gated by `RUN_PARSE_MATRIX=1`.
- `full-regression` — wrapper that runs `baseline` then `matrix` under one command.
- `reporting` — summary/render utilities on existing terminal output. No live endpoint traffic.
- `support` — fixture-registry generation and guarded git workflow. Not part of any test run.

## Canonical Commands

| Tier | Command | Wrapper path | Gate / env | Expected result | Output location |
| --- | --- | --- | --- | --- | --- |
| baseline | `pytest tests/endpoints/parse/ -v` | pytest direct (no wrapper) | none | `10 passed, 2 warnings` | terminal only |
| matrix | `python tools/reporting/run_parse_matrix_with_summary.py` | `tools/reporting/run_parse_matrix_with_summary.py` | sets `RUN_PARSE_MATRIX=1`; `--report` opts into `REGRESSION_REPORT=1` | full fileType matrix (slow, live) | `reports/parse/matrix/latest-terminal.txt`, `reports/parse/matrix/latest-summary.md`; with `--report` also `reports/regression/<timestamp>/` |
| full-regression | `python tools/run_parse_full_regression.py` | `tools/run_parse_full_regression.py` | runs baseline (stops on failure) then delegates to matrix wrapper; `--report` opts into `REGRESSION_REPORT=1`; forwards `--file-types`, `--k` | baseline green then matrix wrapper result | same as baseline + matrix rows above |
| reporting | `python tools/reporting/render_regression_summary.py --endpoint parse --input reports/parse/matrix/latest-terminal.txt` | `tools/reporting/render_regression_summary.py` | reads saved terminal output only; `--mode apply` gated behind explicit review | Markdown summary rendered from saved run | `reports/parse/matrix/latest-summary.md` (draft) |
| reporting (advanced, internal) | `python tools/run_parse_with_report.py --tier {baseline\|matrix\|full}` | `tools/run_parse_with_report.py` | sets `REGRESSION_REPORT=1`; supports `--case`, `--file-types`, `--k` | targeted per-case JSON + Markdown report | `reports/regression/<timestamp>/report.json`, `report.md`, `LATEST.txt` |
| support | `python tools/safe_git_commit.py --message "..."` (see `AGENTS.md` for full flag set) | `tools/safe_git_commit.py` | default validation is protected baseline; `--validation full` switches to full regression; `--push` explicit | reviewed commit (and optional push) after validation passes | git history |
| support | `python tools/generate_fixture_registry.py` | `tools/generate_fixture_registry.py` | reads `tools/fixture_registry_source/qa_fixture_registry.xlsx` | regenerated YAML | `tests/endpoints/parse/fixture_registry.yaml` |

## Legacy / Compatibility-Only
The following internal implementation scripts still exist during the transition and are invoked indirectly by the canonical `tools/reporting/` wrappers. **Do not invoke these paths directly** in operator workflows, handoffs, or docs:

- `.codex/skills/regression-run-summary/scripts/run_parse_matrix_with_summary.py`
- `.codex/skills/regression-run-summary/scripts/render_regression_summary.py`

Use the canonical `tools/reporting/` entries above instead. These legacy paths may be relocated or removed without notice once the transition is complete.

## Gates & Invariants
- **Baseline must stay green.** The protected `/parse` baseline command is `pytest tests/endpoints/parse/ -v` and the current expected result is `10 passed, 2 warnings`. Any change that breaks this is a regression.
- **Matrix requires `RUN_PARSE_MATRIX=1`.** The gate is enforced in code at `tests/endpoints/parse/conftest.py` (collection is ignored unless the env var is set) with a defensive second check inside `tests/endpoints/parse/test_parse_matrix.py`. Running the matrix module directly without the env var is an error, not a silent skip.
- **`REGRESSION_REPORT=1` is opt-in.** Structured per-case artifacts under `reports/regression/<timestamp>/` are emitted only when the flag is set (via `--report` on the full-regression wrapper, always on `tools/run_parse_with_report.py`, or manually in the environment). Default runs do not write to this lane.
- **`reports/` is generated output.** It is not durable repo truth and must not be promoted into tracked docs without an explicit curated summary step.

## Change Policy
- Updating a command string, flag, env var, or output path **requires updating this file** in the same change.
- Adding a new operator- or agent-facing entrypoint **requires adding a row** to the canonical-commands table in this file. A new entrypoint that is not in this registry is not canonical.
- Removing or renaming a wrapper **requires updating this file first**; downstream docs (`README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/operations/matrix.md`) follow.
- The legacy / compatibility-only section may shrink as `.codex/...` paths are retired; it must not grow.
