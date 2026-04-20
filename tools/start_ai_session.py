#!/usr/bin/env python3
"""Start the daily Obsidian + Codex transcript workflow for this repo."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from obsidian_session import ensure_today_session, open_path

REPO_ROOT = Path(__file__).resolve().parent.parent
SYNC_SCRIPT = REPO_ROOT / "tools" / "session_capture_pipeline.py"
CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


@dataclass
class RunningWatcher:
    pid: int
    command: str


def _iter_processes() -> Iterable[tuple[int, str]]:
    try:
        result = subprocess.run(
            ["ps", "-ax", "-o", "pid=,command="],
            capture_output=True,
            check=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    processes: list[tuple[int, str]] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        pid_text, command = parts
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        processes.append((pid, command))
    return processes


def _process_cwd(pid: int) -> Path | None:
    try:
        result = subprocess.run(
            ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
            capture_output=True,
            check=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    for line in result.stdout.splitlines():
        if line.startswith("n"):
            return Path(line[1:]).resolve()
    return None


def _find_running_watcher() -> RunningWatcher | None:
    expected_script = str(SYNC_SCRIPT)
    current_pid = os.getpid()

    for pid, command in _iter_processes():
        if pid == current_pid:
            continue
        if "session_capture_pipeline.py" not in command or "--watch" not in command:
            continue
        if expected_script in command:
            return RunningWatcher(pid=pid, command=command)

        cwd = _process_cwd(pid)
        if cwd == REPO_ROOT:
            return RunningWatcher(pid=pid, command=command)

    return None


def _claude_hooks_configured() -> bool:
    if not CLAUDE_SETTINGS_PATH.exists():
        return False

    try:
        payload = json.loads(CLAUDE_SETTINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False

    hooks = payload.get("hooks")
    if not isinstance(hooks, dict):
        return False

    for event_name in ("Stop", "StopFailure", "SessionEnd"):
        event_hooks = hooks.get(event_name)
        if not isinstance(event_hooks, list):
            continue
        for item in event_hooks:
            if not isinstance(item, dict):
                continue
            for hook in item.get("hooks", []):
                if not isinstance(hook, dict):
                    continue
                command = hook.get("command")
                if not isinstance(command, str):
                    continue
                if "session_capture_pipeline.py" in command and "--claude-hook-stdin" in command:
                    return True
    return False


def _print_status(
    note_path: Path,
    *,
    note_opened: bool,
    open_error: str | None,
    watcher: RunningWatcher | None,
    claude_hooks_configured: bool,
    interval: int,
) -> None:
    print(f"Session note: {note_path}")
    if note_opened:
        print("Obsidian: opened today's canonical note.")
    elif open_error:
        print(f"Obsidian: note resolved, but opening it failed ({open_error}).")
    else:
        print("Obsidian: note resolved.")

    if watcher is not None:
        print(f"Watcher: already running in PID {watcher.pid}; leaving the existing foreground sync in place.")
    else:
        print(f"Watcher: starting the foreground Codex sync in this tab (poll interval: {interval}s).")
        print("Watcher help: leave this tab open while you work; press Ctrl-C here to stop live Codex syncing.")

    if claude_hooks_configured:
        print("Claude hooks: detected and unchanged; Claude stop-event capture continues separately.")
    else:
        print("Claude hooks: not detected here; this startup command does not modify Claude capture settings.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Resolve today's note without asking macOS to open it.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        help="Polling interval in seconds when starting the foreground watcher.",
    )
    args = parser.parse_args()

    try:
        note_path = ensure_today_session()
    except Exception as exc:
        print(f"start_ai_session.py: {exc}", file=sys.stderr)
        return 1

    note_opened = False
    open_error: str | None = None
    if not args.no_open:
        try:
            open_path(note_path)
            note_opened = True
        except Exception as exc:
            open_error = str(exc)

    watcher = _find_running_watcher()
    hooks_ready = _claude_hooks_configured()
    interval = max(args.interval, 5)
    _print_status(
        note_path,
        note_opened=note_opened,
        open_error=open_error,
        watcher=watcher,
        claude_hooks_configured=hooks_ready,
        interval=interval,
    )

    if watcher is not None:
        return 0

    python_executable = sys.executable or "/usr/bin/python3"
    os.execv(
        python_executable,
        [
            python_executable,
            str(SYNC_SCRIPT),
            "--watch",
            "--quiet",
            "--interval",
            str(interval),
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
