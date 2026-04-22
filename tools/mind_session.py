#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


PROJECT_SPACE = "projects/verifyiq-api-regression"
SESSION_SPACE = "sessions/verifyiq-api-regression"
REPO_NAME = "verifyiq-api-regression"
PROJECT_DESCRIPTION = "Persistent memory for VerifyIQ API regression automation"
PROJECT_TAGS = "type:project,repo:verifyiq-api-regression"
SUMMARY_TAGS = "cat:discovery,source:mind-session"
LOCK_PATH = Path(tempfile.gettempdir()) / f"{REPO_NAME}-mind-session.lock"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
CHECKPOINT_RE = re.compile(r"(?m)^\s*(checkpoint-[^\s]+)")
LINE_SECRET_RE = re.compile(
    r"(?i)(authorization|bearer\s+[A-Za-z0-9._-]+|api[_-]?key|tenant[_-]?token|secret|password|private key|google_application_credentials)"
)
INLINE_SECRET_RE = re.compile(
    r"(?i)(Bearer\s+[A-Za-z0-9._=-]+|sk-[A-Za-z0-9_-]+|AIza[0-9A-Za-z_-]+)"
)
MAX_BODY_CHARS = 1600
MAX_CONTEXT_CHARS = 1800
MAX_NOTES_CHARS = 500


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = REPO_ROOT / ".opencode" / "plugins" / "verifyiq-mind-session.js"
SKILL_PATH = REPO_ROOT / ".opencode" / "skills" / "mind-session" / "SKILL.md"
LOCAL_CONFIG_PATH = REPO_ROOT / ".opencode" / "opencode.json"
_RESOLVED_MIND_BINARY: str | None = None


@dataclass
class CommandResult:
    binary: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


class MindSessionError(RuntimeError):
    pass


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text or "")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp_slug() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _default_env() -> dict[str, str]:
    env = os.environ.copy()
    extras = [str(Path.home() / ".local" / "bin"), str(Path.home() / ".bun" / "bin")]
    env["PATH"] = os.pathsep.join([*extras, env.get("PATH", "")])
    return env


def _emit(payload: dict[str, object], *, exit_code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=True))
    return exit_code


def _repo_rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _sanitize_text(text: str, *, max_chars: int) -> str:
    cleaned_lines: list[str] = []
    for raw_line in _strip_ansi(text).splitlines():
        line = raw_line.rstrip()
        if not line:
            cleaned_lines.append("")
            continue
        if LINE_SECRET_RE.search(line):
            cleaned_lines.append("[REDACTED SENSITIVE CONTENT]")
            continue
        cleaned_lines.append(INLINE_SECRET_RE.sub("[REDACTED]", line))

    cleaned = "\n".join(cleaned_lines).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "..."


def _sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-._")
    return cleaned or "summary"


def _candidate_mind_binaries() -> list[str]:
    candidates = [
        os.environ.get("MIND_BIN", ""),
        str(Path.home() / ".local" / "share" / "mind" / "mind"),
        str(Path.home() / ".local" / "bin" / "mind"),
        shutil.which("mind") or "",
    ]

    unique: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        if candidate in unique:
            continue
        path = Path(candidate).expanduser()
        if path.is_absolute() and not path.exists():
            continue
        unique.append(str(path) if path.is_absolute() else candidate)
    return unique


def _run(command: Sequence[str], *, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        env=_default_env(),
        capture_output=True,
        text=True,
        check=False,
    )


def _resolve_mind_binary() -> str:
    global _RESOLVED_MIND_BINARY
    if _RESOLVED_MIND_BINARY:
        return _RESOLVED_MIND_BINARY

    for binary in _candidate_mind_binaries():
        probe = _run([binary, "status"])
        if probe.returncode == 0:
            _RESOLVED_MIND_BINARY = binary
            return binary

    raise MindSessionError("mind executable not found or unusable")


def _run_mind(args: Sequence[str], *, allow_failure: bool = False) -> CommandResult:
    binary = _resolve_mind_binary()
    result = _run([binary, *args])
    command_result = CommandResult(
        binary=binary,
        command=[binary, *map(str, args)],
        returncode=result.returncode,
        stdout=_strip_ansi(result.stdout),
        stderr=_strip_ansi(result.stderr),
    )

    if result.returncode == 0:
        return command_result

    if allow_failure:
        return command_result
    raise MindSessionError(command_result.stderr.strip() or command_result.stdout.strip() or "mind command failed")


@contextmanager
def _mind_lock(timeout_secs: float = 10.0):
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w", encoding="utf-8") as handle:
        deadline = time.monotonic() + timeout_secs
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise MindSessionError("timed out waiting for Mind session lock")
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _space_exists(space_name: str) -> bool:
    result = _run_mind(["list", "--hidden"], allow_failure=True)
    haystack = f"{result.stdout}\n{result.stderr}"
    return space_name in haystack


def _ensure_project_space() -> bool:
    if _space_exists(PROJECT_SPACE):
        return False
    _run_mind(["create", PROJECT_SPACE, PROJECT_DESCRIPTION, "--tags", PROJECT_TAGS])
    return True


def _extract_checkpoint_names(text: str) -> list[str]:
    return CHECKPOINT_RE.findall(_strip_ansi(text))


def _list_active_checkpoints() -> list[str]:
    result = _run_mind(["checkpoint", "list", PROJECT_SPACE, "--status", "active"], allow_failure=True)
    return _extract_checkpoint_names(result.stdout or result.stderr)


def _recover_checkpoint(name: str) -> dict[str, object] | None:
    result = _run_mind(["checkpoint", "recover", PROJECT_SPACE, "--name", name], allow_failure=True)
    payload = (result.stdout or result.stderr).strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _recover_latest_active_checkpoint() -> tuple[str | None, dict[str, object] | None]:
    checkpoints = _list_active_checkpoints()
    if not checkpoints:
        return None, None
    latest = checkpoints[0]
    return latest, _recover_checkpoint(latest)


def _recent_project_memories() -> str:
    result = _run_mind(["list", PROJECT_SPACE], allow_failure=True)
    return _sanitize_text(result.stdout or result.stderr, max_chars=700)


def _recent_session_activity() -> str:
    result = _run_mind(["query", "--space", SESSION_SPACE, "--limit", "3", "--offset", "0"], allow_failure=True)
    return _sanitize_text(result.stdout or result.stderr, max_chars=500)


def _format_context(
    *,
    checkpoint_name: str | None,
    checkpoint_payload: dict[str, object] | None,
    recent_memories: str,
    recent_sessions: str,
    space_created: bool,
) -> str:
    sections: list[str] = []
    if space_created:
        sections.append("Created project space for verifyiq-api-regression.")

    if checkpoint_name and checkpoint_payload:
        sections.append(f"Active checkpoint: {checkpoint_name}")
        sections.append(
            _sanitize_text(json.dumps(checkpoint_payload, ensure_ascii=True), max_chars=700)
        )
    elif checkpoint_name:
        sections.append(f"Active checkpoint: {checkpoint_name}")
    else:
        sections.append("No active checkpoint was found. A continuity checkpoint was created for this session.")

    if recent_memories:
        sections.append("Recent project memories:\n" + recent_memories)
    if recent_sessions:
        sections.append("Recent session activity:\n" + recent_sessions)

    return _sanitize_text("\n\n".join(sections), max_chars=MAX_CONTEXT_CHARS)


def _git_stdout(args: Sequence[str]) -> str:
    result = _run(["git", *args])
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _current_branch() -> str:
    return _git_stdout(["branch", "--show-current"])


def _current_commit() -> str:
    return _git_stdout(["rev-parse", "HEAD"])


def _changed_files() -> list[str]:
    entries: list[str] = []
    for args in (
        ["diff", "--name-only"],
        ["diff", "--cached", "--name-only"],
        ["ls-files", "--others", "--exclude-standard"],
    ):
        stdout = _git_stdout(args)
        if not stdout:
            continue
        entries.extend(line.strip() for line in stdout.splitlines() if line.strip())
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in entries:
        if entry in seen:
            continue
        seen.add(entry)
        ordered.append(entry)
    return ordered


def _default_goal(existing: dict[str, object] | None) -> str:
    content = existing.get("content") if isinstance(existing, dict) else None
    if isinstance(content, dict) and isinstance(content.get("goal"), str) and content["goal"].strip():
        return str(content["goal"]).strip()
    return "Maintain verifyiq-api-regression session continuity"


def _default_pending(existing: dict[str, object] | None) -> str:
    content = existing.get("content") if isinstance(existing, dict) else None
    if isinstance(content, dict) and isinstance(content.get("pending"), str) and content["pending"].strip():
        return str(content["pending"]).strip()
    return "Continue the current task, keep the checkpoint current, and save a durable summary before handoff or commit."


def _build_notes(*, existing: dict[str, object] | None, session_id: str | None, event: str | None) -> str:
    branch = _current_branch() or "main"
    content = existing.get("content") if isinstance(existing, dict) else None
    base = ""
    if isinstance(content, dict) and isinstance(content.get("notes"), str):
        base = content["notes"].strip()

    details = [
        f"repo={REPO_NAME}",
        f"branch={branch}",
        f"event={event or 'manual'}",
        f"session={session_id or 'manual'}",
        f"updated={_utc_now().isoformat()}",
    ]
    joined = " | ".join(details)
    note = joined if not base else f"{base}\n{joined}"
    return _sanitize_text(note, max_chars=MAX_NOTES_CHARS)


def _build_summary_body(
    *,
    title: str,
    body: str,
    changed_files: list[str],
    validations: list[str],
    commit_hash: str,
    risks: list[str],
) -> str:
    sections = [f"Task: {_sanitize_text(title, max_chars=120)}"]

    if body.strip():
        sections.append("Summary:\n" + _sanitize_text(body, max_chars=MAX_BODY_CHARS))
    if changed_files:
        sections.append("Files changed:\n" + "\n".join(f"- {path}" for path in changed_files))
    if validations:
        sections.append(
            "Validation:\n" + "\n".join(f"- {_sanitize_text(item, max_chars=200)}" for item in validations)
        )
    if commit_hash:
        sections.append(f"Commit: {commit_hash}")
    if risks:
        sections.append(
            "Remaining risks:\n" + "\n".join(f"- {_sanitize_text(item, max_chars=160)}" for item in risks)
        )
    return _sanitize_text("\n\n".join(sections), max_chars=MAX_BODY_CHARS)


def _save_summary_memory(*, title: str, body: str, validations: list[str], risks: list[str]) -> dict[str, object]:
    _ensure_project_space()
    commit_hash = _current_commit()
    files = _changed_files()
    memory_name = f"{_sanitize_name(title)}-{_timestamp_slug()}"
    content = _build_summary_body(
        title=title,
        body=body,
        changed_files=files,
        validations=validations,
        commit_hash=commit_hash,
        risks=risks,
    )
    _run_mind(["add", PROJECT_SPACE, memory_name, content, "--tags", SUMMARY_TAGS])
    return {
        "memory_name": memory_name,
        "commit": commit_hash,
        "files_changed": files,
    }


def _complete_latest_checkpoint(*, summary: str) -> str | None:
    checkpoints = _list_active_checkpoints()
    if not checkpoints:
        return None
    latest = checkpoints[0]
    _run_mind(["checkpoint", "complete", PROJECT_SPACE, latest, _sanitize_text(summary, max_chars=180)])
    return latest


def cmd_doctor(args: argparse.Namespace) -> int:
    with _mind_lock():
        status = _run_mind(["status"], allow_failure=True)
        if status.returncode != 0:
            return _emit(
                {
                    "status": "error",
                    "command": "doctor",
                    "error": status.stderr.strip() or status.stdout.strip() or "mind status failed",
                },
                exit_code=1,
            )

        payload = {
            "status": "ok",
            "command": "doctor",
            "mind_bin": status.binary,
            "project_space": PROJECT_SPACE,
            "space_exists": _space_exists(PROJECT_SPACE),
            "local_plugin": _repo_rel(PLUGIN_PATH),
            "local_plugin_exists": PLUGIN_PATH.exists(),
            "local_skill": _repo_rel(SKILL_PATH),
            "local_skill_exists": SKILL_PATH.exists(),
            "local_opencode_config": _repo_rel(LOCAL_CONFIG_PATH),
            "local_opencode_config_exists": LOCAL_CONFIG_PATH.exists(),
        }
        return _emit(payload)


def cmd_start(args: argparse.Namespace) -> int:
    with _mind_lock():
        space_created = _ensure_project_space()
        checkpoint_name, checkpoint_payload = _recover_latest_active_checkpoint()
        checkpoint_created = False

        if checkpoint_name is None:
            goal = args.goal or "Resume verifyiq-api-regression work"
            pending = args.pending or "Recover the active task, keep the checkpoint current, and save a durable summary before handoff or commit."
            notes = _build_notes(existing=None, session_id=args.session_id, event=args.event or "start")
            _run_mind(["checkpoint", "set", PROJECT_SPACE, goal, pending, "--notes", notes])
            checkpoint_created = True
            checkpoint_name, checkpoint_payload = _recover_latest_active_checkpoint()

        recent_memories = _recent_project_memories()
        recent_sessions = _recent_session_activity()
        context = _format_context(
            checkpoint_name=checkpoint_name,
            checkpoint_payload=checkpoint_payload,
            recent_memories=recent_memories,
            recent_sessions=recent_sessions,
            space_created=space_created,
        )
        return _emit(
            {
                "status": "ok",
                "command": "start",
                "space": PROJECT_SPACE,
                "space_created": space_created,
                "checkpoint": checkpoint_name,
                "checkpoint_created": checkpoint_created,
                "context": context,
            }
        )


def cmd_checkpoint(args: argparse.Namespace) -> int:
    with _mind_lock():
        _ensure_project_space()
        checkpoint_name, checkpoint_payload = _recover_latest_active_checkpoint()
        goal = args.goal or _default_goal(checkpoint_payload)
        pending = args.pending or _default_pending(checkpoint_payload)
        notes = args.notes or _build_notes(
            existing=checkpoint_payload,
            session_id=args.session_id,
            event=args.event or "checkpoint",
        )
        _run_mind(["checkpoint", "set", PROJECT_SPACE, goal, pending, "--notes", notes])
        active = _list_active_checkpoints()
        return _emit(
            {
                "status": "ok",
                "command": "checkpoint",
                "space": PROJECT_SPACE,
                "checkpoint": active[0] if active else checkpoint_name,
                "goal": goal,
                "pending": pending,
            }
        )


def cmd_save_summary(args: argparse.Namespace) -> int:
    with _mind_lock():
        saved = _save_summary_memory(
            title=args.title,
            body=args.body,
            validations=args.validation or [],
            risks=args.risk or [],
        )
        return _emit(
            {
                "status": "ok",
                "command": "save-summary",
                "space": PROJECT_SPACE,
                **saved,
            }
        )


def cmd_finish(args: argparse.Namespace) -> int:
    with _mind_lock():
        saved: dict[str, object] | None = None
        if args.title or args.body or args.validation or args.risk:
            saved = _save_summary_memory(
                title=args.title or "session-finish",
                body=args.body or "Finished the active verifyiq-api-regression work session.",
                validations=args.validation or [],
                risks=args.risk or [],
            )

        checkpoint_name, checkpoint_payload = _recover_latest_active_checkpoint()
        completion_summary = args.summary or args.body or args.title or _default_goal(checkpoint_payload)
        completed = _complete_latest_checkpoint(summary=completion_summary)

        return _emit(
            {
                "status": "ok",
                "command": "finish",
                "space": PROJECT_SPACE,
                "completed_checkpoint": completed,
                "saved_summary": saved["memory_name"] if saved else None,
                "commit": saved.get("commit") if saved else _current_commit(),
            }
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repo-controlled Mind session automation for verifyiq-api-regression.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Validate Mind availability and local repo automation surfaces.")
    doctor.set_defaults(func=cmd_doctor)

    start = subparsers.add_parser("start", help="Recover or create the active VerifyIQ Mind session context.")
    start.add_argument("--session-id", help=argparse.SUPPRESS)
    start.add_argument("--event", help=argparse.SUPPRESS)
    start.add_argument("--goal", help="Override the default session goal when no active checkpoint exists.")
    start.add_argument("--pending", help="Override the default pending text when no active checkpoint exists.")
    start.set_defaults(func=cmd_start)

    checkpoint = subparsers.add_parser("checkpoint", help="Refresh the active VerifyIQ continuity checkpoint.")
    checkpoint.add_argument("--session-id", help=argparse.SUPPRESS)
    checkpoint.add_argument("--event", help=argparse.SUPPRESS)
    checkpoint.add_argument("--goal", help="Explicit checkpoint goal.")
    checkpoint.add_argument("--pending", help="Explicit pending work summary.")
    checkpoint.add_argument("--notes", help="Explicit checkpoint notes.")
    checkpoint.set_defaults(func=cmd_checkpoint)

    save_summary = subparsers.add_parser("save-summary", help="Persist a durable project summary memory.")
    save_summary.add_argument("--title", required=True, help="Short summary title.")
    save_summary.add_argument("--body", required=True, help="Compact durable summary body.")
    save_summary.add_argument("--validation", action="append", default=[], help="Validation command/result to record.")
    save_summary.add_argument("--risk", action="append", default=[], help="Remaining risk to record.")
    save_summary.set_defaults(func=cmd_save_summary)

    finish = subparsers.add_parser("finish", help="Close the active checkpoint and optionally save a durable summary.")
    finish.add_argument("--session-id", help=argparse.SUPPRESS)
    finish.add_argument("--event", help=argparse.SUPPRESS)
    finish.add_argument("--summary", help="Short completion summary for the checkpoint closure.")
    finish.add_argument("--title", help="Optional durable summary title.")
    finish.add_argument("--body", help="Optional durable summary body.")
    finish.add_argument("--validation", action="append", default=[], help="Validation command/result to record.")
    finish.add_argument("--risk", action="append", default=[], help="Remaining risk to record.")
    finish.set_defaults(func=cmd_finish)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except MindSessionError as exc:
        return _emit({"status": "error", "command": args.command, "error": str(exc)}, exit_code=1)


if __name__ == "__main__":
    raise SystemExit(main())
