#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER_PATH = REPO_ROOT / "tools" / "mind_session.py"


def _parse_last_json(stdout: str) -> dict[str, Any] | None:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _event_name(payload: dict[str, Any]) -> str:
    hook_name = str(payload.get("hook_event_name") or "").strip().lower()
    if hook_name == "sessionstart":
        source = str(payload.get("source") or "startup").strip().lower() or "startup"
        return f"codex.session_start.{source}"
    if hook_name == "userpromptsubmit":
        return "codex.user_prompt_submit"
    if hook_name == "stop":
        return "codex.stop"
    return f"codex.{hook_name or 'unknown'}"


def _run_wrapper(command: str, payload: dict[str, Any]) -> dict[str, Any]:
    args = [sys.executable, str(WRAPPER_PATH), command]
    session_id = payload.get("session_id")
    if isinstance(session_id, str) and session_id:
        args.extend(["--session-id", session_id])
    args.extend(["--event", _event_name(payload)])

    completed = subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    parsed = _parse_last_json(completed.stdout)
    if completed.returncode == 0 and parsed and parsed.get("status") == "ok":
        return parsed

    if parsed and parsed.get("error"):
        raise RuntimeError(str(parsed["error"]))
    error = (completed.stderr or completed.stdout or "wrapper call failed").strip()
    raise RuntimeError(error)


def _warning(message: str) -> dict[str, Any]:
    return {"continue": True, "systemMessage": message}


def handle_hook(payload: dict[str, Any]) -> dict[str, Any]:
    hook_name = str(payload.get("hook_event_name") or "").strip()

    if hook_name == "SessionStart":
        try:
            response = _run_wrapper("start", payload)
        except RuntimeError as exc:
            return _warning(
                "VerifyIQ Mind session recovery failed: "
                f"{exc}. Run ./.venv/bin/python tools/mind_session.py doctor."
            )

        output: dict[str, Any] = {"continue": True}
        context = str(response.get("context") or "").strip()
        if context:
            output["hookSpecificOutput"] = {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        return output

    if hook_name in {"UserPromptSubmit", "Stop"}:
        try:
            _run_wrapper("checkpoint", payload)
        except RuntimeError as exc:
            return _warning(
                "VerifyIQ Mind checkpoint refresh failed: "
                f"{exc}. Run ./.venv/bin/python tools/mind_session.py checkpoint."
            )
        return {"continue": True}

    return {"continue": True}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps(_warning(f"Invalid Codex hook payload: {exc}"), ensure_ascii=True))
        return 0

    print(json.dumps(handle_hook(payload), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
