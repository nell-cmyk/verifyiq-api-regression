#!/usr/bin/env python3
"""Create or locate the external Obsidian session note for this project.

This helper keeps active handoff/session state outside the repo in the
configured QA Workbench vault.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VAULT_ROOT = Path("/Users/nellvalenzuela/Documents/QA Workbench")
SESSIONS_DIR = VAULT_ROOT / "Sessions"
TEMPLATE_PATH = VAULT_ROOT / "Templates" / "Session Template.md"
PROJECT_SLUG = "verifyiq-api-regression"
DEFAULT_TEMPLATE = """# Session: {{project}} - {{date}}

## Status
- State:
- Owner:
- Branch:

## Goal

## Current context

## Active work
- Task:
- Files in scope:

## Findings

## Decisions

## Blockers / risks

## Validation state
- Commands:
- Last result:
- Follow-up needed:

## Next step

## Promotion targets
- [ ] AGENTS.md
- [ ] docs/operations/*
- [ ] docs/knowledge-base/*
- [ ] No promotion needed

## Automated active state
<!-- verifyiq:auto:active-state:start -->
_Automatically updated from Codex and Claude Code transcripts._
<!-- verifyiq:auto:active-state:end -->

## Automated session log
<!-- verifyiq:auto:session-log:start -->
_Automatically updated from Codex and Claude Code transcripts._
<!-- verifyiq:auto:session-log:end -->
"""

AUTO_ACTIVE_STATE_MARKER = "verifyiq:auto:active-state"
AUTO_SESSION_LOG_MARKER = "verifyiq:auto:session-log"


def _session_name(day: datetime) -> str:
    return f"{day.date().isoformat()} - {PROJECT_SLUG}.md"


def _session_path(day: datetime) -> Path:
    return SESSIONS_DIR / _session_name(day)


def _render_template(day: datetime) -> str:
    if TEMPLATE_PATH.exists():
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
    else:
        template = DEFAULT_TEMPLATE

    replacements = {
        "{{project}}": PROJECT_SLUG,
        "{{date}}": day.date().isoformat(),
        "{{vault_root}}": str(VAULT_ROOT),
    }
    for old, new in replacements.items():
        template = template.replace(old, new)
    return template


def _ensure_vault_layout() -> None:
    if not VAULT_ROOT.exists():
        raise RuntimeError(f"Obsidian vault not found: {VAULT_ROOT}")
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _ensure_today_session() -> Path:
    now = datetime.now().astimezone()
    path = _session_path(now)
    if not path.exists():
        path.write_text(_render_template(now), encoding="utf-8")
    return path


def _latest_session() -> Path:
    candidates = sorted(
        SESSIONS_DIR.glob(f"* - {PROJECT_SLUG}.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]
    return _ensure_today_session()


def ensure_today_session() -> Path:
    _ensure_vault_layout()
    return _ensure_today_session()


def latest_session() -> Path:
    _ensure_vault_layout()
    return _latest_session()


def _section_marker_block(marker: str, body: str) -> str:
    clean_body = body.strip()
    if clean_body:
        clean_body = f"{clean_body}\n"
    return (
        f"<!-- {marker}:start -->\n"
        f"{clean_body}"
        f"<!-- {marker}:end -->"
    )


def upsert_generated_section(note_path: Path, marker: str, body: str) -> Path:
    text = note_path.read_text(encoding="utf-8")
    replacement = _section_marker_block(marker, body)
    pattern = re.compile(
        rf"<!-- {re.escape(marker)}:start -->.*?<!-- {re.escape(marker)}:end -->",
        re.DOTALL,
    )
    if pattern.search(text):
        updated = pattern.sub(replacement, text, count=1)
    else:
        updated = text.rstrip() + "\n\n" + replacement + "\n"
    note_path.write_text(updated.rstrip() + "\n", encoding="utf-8")
    return note_path


def open_path(path: Path) -> None:
    try:
        subprocess.run(["open", "-a", "Obsidian", str(path)], check=True)
    except FileNotFoundError as exc:
        raise RuntimeError("The macOS 'open' command is not available") from exc
    except subprocess.CalledProcessError as exc:
        try:
            subprocess.run(["open", str(path)], check=True)
        except subprocess.CalledProcessError as fallback_exc:
            raise RuntimeError(f"Failed to open {path}") from fallback_exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or locate the external Obsidian session note.",
    )
    resolution_group = parser.add_mutually_exclusive_group()
    resolution_group.add_argument(
        "--today",
        action="store_true",
        help="Return today's canonical session note for this project.",
    )
    resolution_group.add_argument(
        "--latest",
        action="store_true",
        help="Return the most recently modified session note instead of forcing today's note.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the resolved note in Obsidian on macOS when available, otherwise fall back to the default app.",
    )
    args = parser.parse_args()

    try:
        _ensure_vault_layout()
        path = latest_session() if args.latest else ensure_today_session()
        print(path)
        if args.open:
            open_path(path)
    except Exception as exc:
        print(f"obsidian_session.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
