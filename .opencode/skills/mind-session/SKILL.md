---
name: mind-session
description: >
  VerifyIQ repo-local Mind session protocol. Use this when the automatic
  OpenCode session plugin did not recover or save the right context, or when
  you need an explicit durable summary before handoff or commit.
---

# Mind Session

- Normal path: trust the repo-local OpenCode plugin. It automatically runs `tools/mind_session.py start`, refreshes checkpoints during continuity events, and closes the session checkpoint on session end.
- If startup context is missing or stale, run `./.venv/bin/python tools/mind_session.py start`.
- Before risky or long-running work, run `./.venv/bin/python tools/mind_session.py checkpoint`.
- If the task reveals durable repo truth, update the matching tracked docs in the same pass instead of leaving it only in Mind. Use `docs/knowledge-base/repo-roadmap.md` for status and next-step changes, `docs/operations/*` for command/workflow changes, `docs/knowledge-base/*` for durable findings, and `AGENTS.md` only for stable repo-wide rules.
- After a durable decision, bug fix, or validated change, run `./.venv/bin/python tools/mind_session.py save-summary --title "..." --body "..."`.
- Before handoff or commit, run `./.venv/bin/python tools/mind_session.py finish` or `save-summary` so Mind records the task, files changed, validation result, commit hash, and remaining risks.
- The wrapper always uses `projects/verifyiq-api-regression` and serializes Mind access to avoid SQLite concurrency problems.
- Never store secrets, credentials, `.env` content, raw API payloads, raw logs, or large transcript dumps in Mind.
- Save durable summaries only:
  - task
  - decision
  - files changed
  - validation commands/results
  - commit hash
  - remaining risks
