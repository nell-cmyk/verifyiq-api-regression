# Current Handoff

This file is no longer the canonical active handoff system for this project.

## Canonical Active State
- Mind project space: `projects/verifyiq-api-regression`
- Canonical active continuity lives in Mind checkpoints, memories, and session summaries.

## Use Instead
- Normal path: rely on the repo-local OpenCode automation described in `docs/operations/mind-session.md`
- Fallback doctor: `./.venv/bin/python tools/mind_session.py doctor`
- Fallback recovery: `./.venv/bin/python tools/mind_session.py start`
- Fallback checkpoint refresh: `./.venv/bin/python tools/mind_session.py checkpoint`

## Repo Boundary
- Keep active task state, working context, and handoff continuity in Mind only.
- Keep durable runbooks in `docs/operations/*`.
- Keep validated long-term findings in `docs/knowledge-base/*`.

Do not record live handoff state in this file anymore.
