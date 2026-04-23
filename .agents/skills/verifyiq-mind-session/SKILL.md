---
name: verifyiq-mind-session
description: >
  VerifyIQ Codex Mind session workflow. Use this when repo-local Codex hooks did
  not recover or refresh the right context, or when you need to explicitly save
  or finish the active Mind session before handoff or commit.
---

# VerifyIQ Mind Session

- Normal Codex path: trust the repo-local `.codex/config.toml` and `.codex/hooks.json`. In a trusted repo, Codex starts the Mind MCP server automatically, recovers context on session start, and refreshes checkpoints around each turn.
- If startup context is missing or stale, run `./.venv/bin/python tools/mind_session.py doctor` and then `./.venv/bin/python tools/mind_session.py start`.
- Before risky or long-running work, run `./.venv/bin/python tools/mind_session.py checkpoint`.
- If the task reveals durable repo truth, update the matching tracked docs in the same pass instead of leaving it only in Mind. Use `docs/knowledge-base/repo-roadmap.md` for status and next-step changes, `docs/operations/*` for command/workflow changes, `docs/knowledge-base/*` for durable findings, and `AGENTS.md` only for stable repo-wide rules.
- Before handoff or commit, run `./.venv/bin/python tools/mind_session.py finish`.
- If you need a durable summary without closing the checkpoint yet, run `./.venv/bin/python tools/mind_session.py save-summary --title "..." --body "..."`.
- Codex does not expose a true session-end hook here, so `finish` remains explicit even though startup recovery and checkpoint refresh are automatic. The agent should handle that bookkeeping before handoff or commit; the user should not need to remember it.
- Never store secrets, credentials, `.env` content, raw API payloads, raw logs, or transcript dumps in Mind.
