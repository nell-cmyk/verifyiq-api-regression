# Docs Guide

Use this folder to keep repo documentation predictable and easy to scan.

## What Goes Where
- `docs/operations/`
  Runbooks, commands, troubleshooting steps, and workflow instructions.
  Active task-state handoff notes do not live here; the external Obsidian vault holds active session state.
- `docs/knowledge-base/`
  Durable findings about endpoint behavior, fixture decisions, and validated repo knowledge.

## Canonical Rules
- If a document tells contributors how to run or operate something, it belongs in `docs/operations/`.
- If a document records stable findings or curated reference material, it belongs in `docs/knowledge-base/`.
- Repo-owned executable commands should point to `tools/`, not deep internal implementation paths.
- Generated run output belongs in `reports/`, not in `docs/`.

## Current Exceptions
- `docs/knowledge-base/repo-roadmap.md` still lives under `docs/knowledge-base/` for now.
- Do not add active handoff or other working-note files under `docs/knowledge-base/`; use the external Obsidian vault at `/Users/nellvalenzuela/Documents/QA Workbench/` for active task state.
- `docs/operations/current-handoff.md` remains in the repo only as a deprecation pointer to the external vault.
