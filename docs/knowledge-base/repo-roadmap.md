# Repo Roadmap

## Purpose
Preserve the working roadmap for this repository as durable reference material.

This repo should grow into a maintainable API regression suite and a pragmatic operating model for long-term agent-assisted development, without changing the protected `/parse` baseline by default and without introducing process clutter.

## Current Priorities
- Keep the current `docs/operations/` runbooks and command-surface guidance aligned with the live wrapper/validation surfaces.
- Extend the curated `/parse` knowledge base only when new stable findings are validated and worth preserving.
- Keep command-surface documentation current as wrappers or operator-facing commands change.
- Resolve the remaining roadmap/docs-placement exception without turning planning notes into durable knowledge.
- Preserve the current simple test-suite split of config, client, diagnostics, endpoint tests, registry tooling, and reporting hooks.
- Improve UTF-8 / doc hygiene incrementally without changing protected `/parse` behavior.

## Later Priorities
- Add CI in two tiers: protected baseline on normal changes, matrix on opt-in or scheduled runs.
- Add richer run-history or trend reporting only when the suite is large enough to justify it.
- Introduce a minimal endpoint expansion template after more endpoints exist beyond `/parse`.
- Expand shared assertion layers or endpoint conventions only when multiple endpoints need the same pattern.

## Sequencing
1. Keep the operations docs aligned with the existing command surface as it changes.
2. Extend curated `/parse` knowledge-base pages only when new durable findings appear.
3. Clean up the remaining docs-placement boundary around roadmap/planning notes without turning them into durable knowledge.
4. Add CI tiers for protected baseline and opt-in matrix flows if still justified.
5. Introduce endpoint templates only after 2-3 endpoints exist.
6. Add richer history/trend automation only after sustained matrix usage.

## Anti-Patterns To Avoid
- Do not change the protected baseline behavior by default.
- Do not turn the matrix into part of the default `/parse` baseline run.
- Do not add local fixture fallback or invent a second fixture source of truth.
- Do not build a generic endpoint test framework before multiple endpoints need it.
- Do not store every run log in Git.
- Do not mix regression knowledge with manual QA workflow, ticket workflow, or business-process tooling.
- Do not let multiple agents share one branch or opportunistically refactor unrelated code.
- Do not promote unstable terminal output into durable repo truth without a curated summary.

## Status Tracker
- Done:
  - Root instruction files exist: `AGENTS.md`, `CLAUDE.md`
  - Protected `/parse` baseline is documented
  - Opt-in matrix path exists
  - Matrix triage doc exists at `docs/operations/matrix.md`
  - Command registry exists at `docs/operations/command-registry.md`
  - Workflow runbook exists at `docs/operations/workflow.md`
  - Mind is the canonical active session/handoff layer
  - `docs/operations/current-handoff.md` is pointer-only
  - Reporting surface lives under `tools/reporting/`
  - `/parse` durable knowledge-base pages exist under `docs/knowledge-base/parse/`
  - Legacy root `.codex` reporting scripts are removed
  - Full regression wrapper exists at `./.venv/bin/python tools/run_parse_full_regression.py`
  - Checked-in protected-baseline CI exists at `.github/workflows/protected-baseline.yml`
  - Fixture lifecycle rules are explicit: spreadsheet is the human source of truth, generated YAML is the automation source of truth
  - Multi-agent Git/governance guidance is materially present
- Next:
  - Keep command-surface and operations docs aligned as wrappers or operator guidance change
  - Add new durable `/parse` knowledge-base entries only when validated findings justify them
  - Clean up the remaining docs-placement exception under `docs/knowledge-base/`
- Later:
  - Expand CI beyond the protected baseline if stronger automated coverage is still desired
  - Add endpoint expansion template after more endpoints exist
  - Add run-history/trend support when justified by suite size
