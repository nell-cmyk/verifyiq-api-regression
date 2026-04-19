# Repo Roadmap

## Purpose
Preserve the working roadmap for this repository as durable reference material.

This repo should grow into a maintainable API regression suite and a pragmatic operating model for long-term agent-assisted development, without changing the protected `/parse` baseline by default and without introducing process clutter.

## Current Priorities
- Add a small `docs/operations/` spine for baseline runs, matrix runs, fixture-registry flow, auth troubleshooting, and multi-agent workflow.
- Build a curated `docs/knowledge-base/` for stable findings: known endpoint behaviors, flaky patterns, canonical fixture decisions, environment-specific findings, and triage notes.
- Add a few high-ROI support utilities under `tools/`, such as env checks, registry reports, and run-summary helpers.
- Keep test-suite architecture simple: preserve the current split of config, client, diagnostics, endpoint tests, and registry tooling.
- Make the multi-agent Git workflow explicit: one patch per branch, narrow diffs, clear handoff, Git as checkpoint truth.
- Improve developer experience with Python-first command wrappers and better UTF-8 / doc hygiene.
- Make fixture lifecycle rules explicit: spreadsheet is the human source of truth, generated YAML is the automation source of truth.

## Later Priorities
- Add CI in two tiers: protected baseline on normal changes, matrix on opt-in or scheduled runs.
- Add lightweight reporting and stored artifacts for broader matrix coverage once usage grows.
- Introduce a minimal endpoint expansion template after more endpoints exist beyond `/parse`.
- Add structured run metadata and trend reporting only when the suite is large enough to justify it.
- Expand shared assertion layers or endpoint conventions only when multiple endpoints need the same pattern.

## Sequencing
1. Stabilize repo instructions and operations docs.
2. Build the curated knowledge base structure.
3. Add small support utilities for repeatable agent work.
4. Lock in multi-agent handoff and checkpoint norms.
5. Add CI/reporting for protected baseline and opt-in matrix flows.
6. Introduce endpoint templates only after 2-3 endpoints exist.
7. Add richer history/trend automation only after sustained matrix usage.

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
- Next:
  - Add the remaining `docs/operations/` pages (`command-registry.md` landed; `workflow.md`, `session-handoff-template.md` outstanding)
  - Add endpoint-first knowledge-base pages for `/parse`
  - Add small reporting/support utilities under `tools/`
- Later:
  - Add CI/reporting tiers
  - Add endpoint expansion template after more endpoints exist
  - Add structured run-history/trend support when justified by suite size
