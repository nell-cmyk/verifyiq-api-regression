#!/usr/bin/env python3
"""Install local automation for transcript-to-Obsidian session syncing."""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SYNC_SCRIPT = REPO_ROOT / "tools" / "session_capture_pipeline.py"
CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
LAUNCH_AGENT_LABEL = "com.verifyiq.obsidian-session-sync"
LAUNCH_AGENT_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_LABEL}.plist"
LAUNCH_AGENT_LOG_DIR = REPO_ROOT / "reports" / "conversation-captures" / "launch-agent"
PROTECTED_MACOS_DIRS = (
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _ensure_claude_hook(config: dict[str, Any], python_executable: str) -> bool:
    command = f"\"{python_executable}\" \"{SYNC_SCRIPT}\" --claude-hook-stdin --quiet"
    hooks = config.setdefault("hooks", {})
    changed = False

    for event_name in ("Stop", "StopFailure", "SessionEnd"):
        event_hooks = hooks.setdefault(event_name, [])
        existing = next(
            (
                item
                for item in event_hooks
                if isinstance(item, dict)
                and any(
                    isinstance(hook, dict) and hook.get("command") == command
                    for hook in item.get("hooks", [])
                )
            ),
            None,
        )
        if existing is not None:
            continue
        event_hooks.append(
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "async": True,
                        "timeout": 120,
                    }
                ],
            }
        )
        changed = True

    return changed


def _write_launch_agent(python_executable: str) -> None:
    LAUNCH_AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": [
            python_executable,
            str(SYNC_SCRIPT),
            "--sync",
            "--quiet",
        ],
        "RunAtLoad": True,
        "StartInterval": 120,
        "WorkingDirectory": str(REPO_ROOT),
        "StandardOutPath": str(LAUNCH_AGENT_LOG_DIR / "stdout.log"),
        "StandardErrorPath": str(LAUNCH_AGENT_LOG_DIR / "stderr.log"),
    }
    LAUNCH_AGENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LAUNCH_AGENT_PATH.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=False)


def _run_launchctl(label: str, path: Path) -> None:
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(path)], check=False, capture_output=True)
    subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True)
    subprocess.run(["launchctl", "enable", f"{domain}/{label}"], check=False, capture_output=True)
    subprocess.run(["launchctl", "kickstart", "-k", f"{domain}/{label}"], check=False, capture_output=True)


def _remove_launch_agent(label: str, path: Path) -> None:
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(path)], check=False, capture_output=True)
    if path.exists():
        path.unlink()


def _path_is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _launch_agent_allowed() -> bool:
    return not any(_path_is_under(REPO_ROOT, protected) for protected in PROTECTED_MACOS_DIRS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python",
        default="/usr/bin/python3",
        help="Python executable used by Claude hooks and the launch agent.",
    )
    parser.add_argument(
        "--force-launch-agent",
        action="store_true",
        help="Install the macOS launch agent even when the repo lives under a protected folder such as ~/Documents.",
    )
    args = parser.parse_args()

    config = _load_json(CLAUDE_SETTINGS_PATH)
    hook_changed = _ensure_claude_hook(config, args.python)
    if hook_changed or not CLAUDE_SETTINGS_PATH.exists():
        _write_json(CLAUDE_SETTINGS_PATH, config)

    launch_agent_installed = False
    launch_agent_reason = ""
    if args.force_launch_agent or _launch_agent_allowed():
        _write_launch_agent(args.python)
        _run_launchctl(LAUNCH_AGENT_LABEL, LAUNCH_AGENT_PATH)
        launch_agent_installed = True
    else:
        _remove_launch_agent(LAUNCH_AGENT_LABEL, LAUNCH_AGENT_PATH)
        launch_agent_reason = (
            "Skipped the background launch agent because this repo lives under a "
            "macOS-protected folder. Use `./.venv/bin/python tools/start_ai_session.py` for the "
            "normal daily startup flow; it will hand off to the same foreground watcher "
            "for Codex live syncing when needed."
        )

    print(
        json.dumps(
            {
                "claude_settings_path": str(CLAUDE_SETTINGS_PATH),
                "launch_agent_path": str(LAUNCH_AGENT_PATH),
                "python": args.python,
                "hook_changed": hook_changed,
                "launch_agent_label": LAUNCH_AGENT_LABEL,
                "launch_agent_installed": launch_agent_installed,
                "launch_agent_reason": launch_agent_reason,
                "startup_command": "./.venv/bin/python tools/start_ai_session.py",
                "watch_command": "./.venv/bin/python tools/session_capture_pipeline.py --watch --quiet",
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
