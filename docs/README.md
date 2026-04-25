# Docs Guide

Use this folder to keep repo documentation predictable and easy to scan.

## What Goes Where
- `docs/operations/`
  Runbooks, commands, troubleshooting steps, and workflow instructions.
  Active task-state handoff notes do not live here; Mind holds active session state in `projects/verifyiq-api-regression`.
- `docs/knowledge-base/`
  Durable findings about endpoint behavior, fixture decisions, and validated repo knowledge.
  `docs/knowledge-base/repo-roadmap.md` is the canonical planning source for project progression and future-development decisions.

## Canonical Rules
- If a document tells contributors how to run or operate something, it belongs in `docs/operations/`.
- If a document records stable findings or curated reference material, it belongs in `docs/knowledge-base/`.
- Repo-owned executable commands should point to `tools/`, not deep internal implementation paths.
- Generated run output belongs in `reports/`, not in `docs/`.

## Planning And Handoff
- Do not add separate roadmap, plan, audit, future-work, or active-handoff files under `docs/`.
- Use `docs/knowledge-base/repo-roadmap.md` for planning/progression truth.
- Use Mind checkpoints and memories for active task state.
- `docs/operations/current-handoff.md` remains in the repo only as a pointer to the canonical Mind workflow.
