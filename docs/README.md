# Docs Guide

Use this folder to keep repo documentation predictable and easy to scan.

## What Goes Where
- `docs/operations/`
  Runbooks, commands, troubleshooting steps, and workflow instructions.
- `docs/knowledge-base/`
  Durable findings about endpoint behavior, fixture decisions, and validated repo knowledge.

## Canonical Rules
- If a document tells contributors how to run or operate something, it belongs in `docs/operations/`.
- If a document records stable findings or curated reference material, it belongs in `docs/knowledge-base/`.
- Repo-owned executable commands should point to `tools/`, not deep internal implementation paths.
- Generated run output belongs in `reports/`, not in `docs/`.

## Current Exceptions
- `docs/knowledge-base/repo-roadmap.md` and `docs/knowledge-base/current-session-context.md` still live under `docs/knowledge-base/` for now.
- Do not add new roadmap or working-note files under `docs/knowledge-base/`; keep that folder focused on durable knowledge while the later cleanup phases are pending.
