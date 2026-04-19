# Repo Roadmap

## Purpose
Preserve the working roadmap for this repository as durable reference material.

This repo should grow into a maintainable API regression suite and a pragmatic operating model for long-term agent-assisted development, without changing the protected `/parse` baseline by default and without introducing process clutter.

## Current Priorities
- Finish the remaining `docs/operations/` spine around baseline/auth troubleshooting and fixture-registry flow without duplicating the command registry.
- Build a curated `docs/knowledge-base/` for stable findings: known `/parse` behaviors, canonical fixture decisions, environment-specific findings, and triage notes.
- Keep command-surface documentation current as wrappers or operator-facing commands change.
- Preserve the current simple test-suite split of config, client, diagnostics, endpoint tests, registry tooling, and reporting hooks.
- Improve UTF-8 / doc hygiene incrementally without changing protected `/parse` behavior.

## Later Priorities
- Add CI in two tiers: protected baseline on normal changes, matrix on opt-in or scheduled runs.
- Add richer run-history or trend reporting only when the suite is large enough to justify it.
- Introduce a minimal endpoint expansion template after more endpoints exist beyond `/parse`.
- Expand shared assertion layers or endpoint conventions only when multiple endpoints need the same pattern.

## Sequencing
1. Finish the remaining operations docs around the existing command surface.
2. Build out the curated knowledge-base pages for `/parse`.
3. Clean up the remaining docs-placement boundaries without turning roadmap/planning notes into durable knowledge.
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
  - Reporting surface lives under `tools/reporting/`
  - Legacy root `.codex` reporting scripts are removed
  - Full regression wrapper exists at `python tools/run_parse_full_regression.py`
  - Fixture lifecycle rules are explicit: spreadsheet is the human source of truth, generated YAML is the automation source of truth
  - Multi-agent Git/governance guidance is materially present
  - Active handoff state lives under `docs/operations/current-handoff.md`
- Next:
  - Add the remaining `docs/operations/` pages beyond `command-registry.md`, `workflow.md`, `matrix.md`, and `current-handoff.md`
  - Add endpoint-first durable knowledge-base pages for `/parse`
  - Clean up the remaining docs-placement exception under `docs/knowledge-base/`
- Later:
  - Add CI tiers for protected baseline and opt-in matrix flows if still desired
  - Add endpoint expansion template after more endpoints exist
  - Add run-history/trend support when justified by suite size
