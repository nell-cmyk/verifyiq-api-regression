# Current Handoff

This file is no longer the canonical active handoff system for this project.

## Canonical Active State
- External Obsidian vault: `/Users/nellvalenzuela/Documents/QA Workbench`
- Canonical active session note location: `/Users/nellvalenzuela/Documents/QA Workbench/Sessions/YYYY-MM-DD - verifyiq-api-regression.md`

## Use Instead
- Normal daily startup: `./.venv/bin/python tools/start_ai_session.py`
- Resolve or open today’s active note only: `./.venv/bin/python tools/obsidian_session.py --today --open`
- Find the latest active context: `./.venv/bin/python tools/obsidian_session.py --latest`

## Repo Boundary
- Keep active task state, working context, and handoff notes in the external Obsidian vault only.
- Keep durable runbooks in `docs/operations/*`.
- Keep validated long-term findings in `docs/knowledge-base/*`.

Do not record live handoff state in this file anymore.
