# Mind Session

## Purpose
Use this file for the repo-controlled Mind automation flow in OpenCode and Codex.

Normal operation is automatic. Manual `mind ...` commands are fallback and troubleshooting only.

## Automatic Flow
- OpenCode loads `.opencode/opencode.json` when this repo is open.
- Codex loads trusted project config from `.codex/config.toml` and hooks from `.codex/hooks.json`.
- The repo-controlled automation surfaces call `./.venv/bin/python tools/mind_session.py ...` or the repo MCP shim so the repo controls Mind behavior instead of relying on remembered raw commands.

## What Happens Automatically
### OpenCode session start
- The plugin runs `tools/mind_session.py start`.
- The wrapper verifies Mind availability, ensures `projects/verifyiq-api-regression` exists, recovers the latest active checkpoint when present, and creates a continuity checkpoint when none exists.
- The plugin injects compact recovered context into the OpenCode system prompt when available.

### OpenCode continuity events
- On compaction preparation, the plugin runs `tools/mind_session.py checkpoint` to refresh the active checkpoint before context is compressed.
- After compaction, the plugin reruns `start` so recent checkpoint context can be surfaced again.
- On idle events, the plugin refreshes the checkpoint instead of waiting for a manual command.

### OpenCode session finish
- On session end, the plugin runs `tools/mind_session.py finish`.
- The wrapper closes the latest active checkpoint in `projects/verifyiq-api-regression`, which lets Mind create the corresponding session memory in `sessions/verifyiq-api-regression`.

### Codex session start
- Trusted project config in `.codex/config.toml` starts the repo-local Mind MCP shim at `tools/codex_mind_mcp.py`.
- The `SessionStart` hook in `.codex/hooks.json` runs `tools/codex_mind_hook.py`, which calls `tools/mind_session.py start` and injects compact recovered context back into Codex as additional developer context.

### Codex continuity events
- The `UserPromptSubmit` and `Stop` hooks run `tools/codex_mind_hook.py`.
- The hook refreshes the active checkpoint through `tools/mind_session.py checkpoint` before and after each turn so the latest work survives context loss more reliably.

### Codex limitation
- Codex does not expose a true session-end hook in this repo.
- Because of that, automatic `finish` handling is not available here.
- Before handoff or commit in Codex, explicitly run `./.venv/bin/python tools/mind_session.py finish` or `save-summary`.
- In practice this is agent-owned, not user-owned: the agent should run the repo-local Mind bookkeeping before handoff or commit instead of leaving it to the user.

## Durable Summary Rules
- Never save secrets, credentials, `.env` values, raw API payloads, raw logs, or transcript dumps to Mind.
- Save durable summaries only:
  - task
  - decision
  - files changed
  - validation commands/results
  - commit hash
  - remaining risks
- When an explicit durable project memory is needed before handoff or commit, use:

```bash
./.venv/bin/python tools/mind_session.py save-summary --title "short-title" --body "Durable summary"
```

## Automatic Durable-Truth Promotion
- Mind is the active memory layer, not the only durable record.
- When a task establishes durable repo truth, the agent should update the matching tracked doc in the same pass without waiting for a separate user request.
- Route durable updates by scope:
  - `docs/knowledge-base/repo-roadmap.md` for status, sequencing, blockers, priorities, milestones, and next steps.
  - `docs/operations/*` for canonical commands, workflow steps, setup, and artifact/reporting paths.
  - `docs/knowledge-base/*` for durable findings that should outlive one session.
  - `AGENTS.md` only for stable repo-wide agent rules or safety/workflow policy.
  - `README.md` only for top-level orientation or quick-start changes.
- If a fact belongs both in Mind and in tracked docs, do both: save it durably in Mind and patch the tracked doc in the same pass.

## Fallback Commands
- Validate the repo-local automation surface:

```bash
./.venv/bin/python tools/mind_session.py doctor
```

- Force a fresh recovery if startup context looks stale:

```bash
./.venv/bin/python tools/mind_session.py start
```

- Refresh the active checkpoint explicitly:

```bash
./.venv/bin/python tools/mind_session.py checkpoint
```

- Close the active checkpoint explicitly:

```bash
./.venv/bin/python tools/mind_session.py finish
```

## Troubleshooting
- If the wrapper reports Mind is unavailable, check `PATH` and run `mind status`.
- If OpenCode is not loading the repo plugin, inspect `.opencode/opencode.json` and run `opencode debug config` from the repo root.
- If the repo skill is missing, run `opencode debug skill` from the repo root.
- If the Codex repo skill is missing, inspect `.agents/skills/verifyiq-mind-session/SKILL.md` and restart Codex.
- If Codex is not loading the repo config, trust the project and inspect `.codex/config.toml` plus `.codex/hooks.json`.
- If Codex startup context looks stale, run `./.venv/bin/python tools/mind_session.py doctor` and then `./.venv/bin/python tools/mind_session.py start`.
- If Mind reports `SQLITE_BUSY_RECOVERY`, rerun the commands sequentially. The wrapper already serializes access and should be preferred.
