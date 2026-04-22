# Mind Session

## Purpose
Use this file for the repo-controlled Mind automation flow in OpenCode.

Normal operation is automatic. Manual `mind ...` commands are fallback and troubleshooting only.

## Automatic Flow
- OpenCode loads `.opencode/opencode.json` when this repo is open.
- That repo-local config loads:
  - `.opencode/plugins/verifyiq-mind-session.js`
  - `.opencode/skills/mind-session/SKILL.md`
- The plugin calls `./.venv/bin/python tools/mind_session.py ...` so the repo controls Mind behavior instead of relying on remembered raw commands.

## What Happens Automatically
### Session start
- The plugin runs `tools/mind_session.py start`.
- The wrapper verifies Mind availability, ensures `projects/verifyiq-api-regression` exists, recovers the latest active checkpoint when present, and creates a continuity checkpoint when none exists.
- The plugin injects compact recovered context into the OpenCode system prompt when available.

### Continuity events
- On compaction preparation, the plugin runs `tools/mind_session.py checkpoint` to refresh the active checkpoint before context is compressed.
- After compaction, the plugin reruns `start` so recent checkpoint context can be surfaced again.
- On idle events, the plugin refreshes the checkpoint instead of waiting for a manual command.

### Session finish
- On session end, the plugin runs `tools/mind_session.py finish`.
- The wrapper closes the latest active checkpoint in `projects/verifyiq-api-regression`, which lets Mind create the corresponding session memory in `sessions/verifyiq-api-regression`.

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
- If Mind reports `SQLITE_BUSY_RECOVERY`, rerun the commands sequentially. The wrapper already serializes access and should be preferred.
