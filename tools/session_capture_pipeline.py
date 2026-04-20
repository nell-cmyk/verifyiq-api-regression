#!/usr/bin/env python3
"""Sync Codex and Claude transcripts into project artifacts and Obsidian."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from obsidian_session import (
    AUTO_ACTIVE_STATE_MARKER,
    AUTO_SESSION_LOG_MARKER,
    ensure_today_session,
    upsert_generated_section,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECT_SLUG = "verifyiq-api-regression"
ARTIFACT_ROOT = REPO_ROOT / "reports" / "conversation-captures"
RAW_ROOT = ARTIFACT_ROOT / "raw"
NORMALIZED_ROOT = ARTIFACT_ROOT / "normalized"
STATE_PATH = ARTIFACT_ROOT / "state" / "sync-state.json"
CODEX_SOURCE_ROOT = Path.home() / ".codex" / "sessions"
CLAUDE_SOURCE_ROOT = Path.home() / ".claude" / "projects"
DEFAULT_EMPTY_LIST = ["None recorded."]
AUTO_STATE_INTRO = "_Automatically updated from Codex and Claude Code transcripts._"


@dataclass
class SessionSummary:
    tool: str
    session_id: str
    title: str
    started_at: str
    updated_at: str
    cwd: str
    canonical_root: str
    source_path: str
    raw_copy_path: str
    normalized_path: str
    objective: str
    work_completed: list[str]
    key_findings: list[str]
    decisions_made: list[str]
    files_changed: list[str]
    validation: list[str]
    blockers_risks: list[str]
    next_step: str
    promotion_targets: list[str]


def _utc_now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _slugify(text: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-._")
    return cleaned or fallback


def _session_title(objective: str, fallback: str) -> str:
    clean = " ".join(objective.split()).strip()
    if not clean or clean == "No objective extracted from transcript.":
        clean = fallback
    return clean[:80]


def _dedupe_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        clean = " ".join(str(item).split()).strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
    return result


def _canonical_project_root(path_str: str) -> Path:
    path = Path(path_str).expanduser().resolve()
    marker = f"{os.sep}.claude{os.sep}worktrees{os.sep}"
    as_text = str(path)
    if marker in as_text:
        return Path(as_text.split(marker, 1)[0]).resolve()
    return path


def _extract_text_blocks(content: Any, text_key: str) -> list[str]:
    if isinstance(content, str):
        return [content]
    blocks: list[str] = []
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") in {"input_text", "output_text", "text"}:
                text = block.get(text_key) or block.get("text")
                if isinstance(text, str):
                    blocks.append(text)
    return blocks


def _extract_objective(user_texts: list[str]) -> str:
    for text in user_texts:
        match = re.search(
            r"(?ims)^Task:\s*(.+?)(?:\n\s*\n|\n[A-Z][A-Za-z /_-]+:|\Z)",
            text,
        )
        if match:
            return " ".join(match.group(1).split())

    ignored_prefixes = (
        "# AGENTS.md",
        "You are working in the",
        "Do not restart planning",
        "Context:",
        "<INSTRUCTIONS>",
        "Important:",
    )
    for text in user_texts:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if re.fullmatch(r"[A-Z][A-Za-z /_-]+:", stripped):
                continue
            if stripped.startswith("<") and stripped.endswith(">"):
                continue
            if stripped.startswith(ignored_prefixes):
                continue
            return stripped

    return "No objective extracted from transcript."


def _normalize_heading_name(name: str) -> str:
    normalized = " ".join(name.lower().split()).strip(" :-")
    normalized = re.sub(r"^\d+(?:\.\d+)*[.)]?\s*", "", normalized)
    return normalized


def _assistant_text_is_summary(text: str) -> bool:
    lowered = text.lower()
    if re.search(
        r"(?im)^(?:#{1,6}\s+|\*\*)?(?:\d+\.\s*)?"
        r"(?:final report|diagnosis|key findings|findings|work completed|"
        r"implementation|files changed|file-by-file changes|exact files changed|"
        r"validation(?: results)?|next step|blockers(?: / risks)?|decisions made)\b",
        text,
    ):
        return True
    return any(
        token in lowered
        for token in (
            "**diagnosis**",
            "final report",
            "validation results",
            "files changed",
            "file-by-file changes",
            "exact files changed",
            "next step",
        )
    )


def _select_latest_summary(assistant_texts: list[str]) -> str:
    meaningful = [text for text in assistant_texts if len(text.strip()) >= 40]
    for text in reversed(meaningful):
        if _assistant_text_is_summary(text):
            return text
    return meaningful[-1] if meaningful else ""


def _markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "body"
    sections[current] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        heading_match = re.match(r"^\*\*(.+?)\*\*\s*$", line) or re.match(
            r"^#{1,6}\s+(.+?)\s*$",
            line,
        )
        if heading_match:
            current = _normalize_heading_name(heading_match.group(1))
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)

    return {
        name: "\n".join(lines).strip()
        for name, lines in sections.items()
        if "\n".join(lines).strip()
    }


def _section_text(sections: dict[str, str], aliases: Iterable[str]) -> str:
    alias_set = {alias.lower() for alias in aliases}
    for name, body in sections.items():
        if name in alias_set:
            return body
    return ""


def _extract_list_items(text: str) -> list[str]:
    items: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if re.match(r"^[-*]\s+", stripped):
            items.append(re.sub(r"^[-*]\s+", "", stripped))
        elif re.match(r"^\d+\.\s+", stripped):
            items.append(re.sub(r"^\d+\.\s+", "", stripped))
    if items:
        return _dedupe_preserve(items)
    compact = " ".join(text.split()).strip()
    return [compact] if compact else []


def _extract_paths(text: str) -> list[str]:
    found: list[str] = []
    for match in re.finditer(r"\]\((/[^):\s]+)", text):
        found.append(match.group(1))
    for match in re.finditer(r"`([^`\n]*\.[A-Za-z0-9]+)`", text):
        found.append(match.group(1))
    return _dedupe_preserve(found)


def _extract_promotion_targets(text: str) -> list[str]:
    targets: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("- ["):
            continue
        target = re.sub(r"^- \[[ xX]\]\s*", "", stripped)
        if target:
            targets.append(target)
    return _dedupe_preserve(targets)


def _parse_patch_paths(patch_text: str) -> list[str]:
    paths: list[str] = []
    for raw_line in patch_text.splitlines():
        if raw_line.startswith("*** Add File: "):
            paths.append(raw_line.removeprefix("*** Add File: ").strip())
        elif raw_line.startswith("*** Update File: "):
            paths.append(raw_line.removeprefix("*** Update File: ").strip())
        elif raw_line.startswith("*** Delete File: "):
            paths.append(raw_line.removeprefix("*** Delete File: ").strip())
    return _dedupe_preserve(paths)


def _display_command(command: str) -> str:
    cleaned = " ".join(command.split()).strip()
    wrapper_match = re.match(r"^/(?:bin|usr/bin)/(?:zsh|bash) -lc (.+)$", cleaned)
    if wrapper_match:
        wrapped = wrapper_match.group(1).strip()
        if (wrapped.startswith("'") and wrapped.endswith("'")) or (
            wrapped.startswith('"') and wrapped.endswith('"')
        ):
            wrapped = wrapped[1:-1]
        cleaned = wrapped
    return cleaned


def _display_path(path_text: str) -> str:
    raw = str(path_text).strip()
    if not raw:
        return raw
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        return raw
    try:
        return str(candidate.resolve().relative_to(REPO_ROOT))
    except Exception:
        return raw


def _extract_validation_command(command: str) -> str | None:
    cleaned = _display_command(command)
    trimmed_prefixes = (
        "python tools/session_capture_pipeline.py",
        "python3 tools/session_capture_pipeline.py",
        "./.venv/bin/python tools/session_capture_pipeline.py",
        "python tools/obsidian_session.py",
        "python3 tools/obsidian_session.py",
        "./.venv/bin/python tools/obsidian_session.py",
        "python tools/install_session_capture_automation.py",
        "python3 tools/install_session_capture_automation.py",
        "./.venv/bin/python tools/install_session_capture_automation.py",
    )
    if cleaned.lower().startswith(trimmed_prefixes):
        for separator in (" && ", " || ", " ; "):
            if separator in cleaned:
                cleaned = cleaned.split(separator, 1)[0].strip()
                break
    lowered = cleaned.lower()
    prefixes = (
        "pytest ",
        "./.venv/bin/pytest ",
        ".venv/bin/pytest ",
        "run_parse_matrix=1 pytest ",
        "run_parse_matrix=1 ./.venv/bin/pytest ",
        "python -m compileall ",
        "python3 -m compileall ",
        "./.venv/bin/python -m compileall ",
        "python tools/obsidian_session.py",
        "python3 tools/obsidian_session.py",
        "./.venv/bin/python tools/obsidian_session.py",
        "python tools/session_capture_pipeline.py",
        "python3 tools/session_capture_pipeline.py",
        "./.venv/bin/python tools/session_capture_pipeline.py",
        "python tools/install_session_capture_automation.py",
        "python3 tools/install_session_capture_automation.py",
        "./.venv/bin/python tools/install_session_capture_automation.py",
        "launchctl ",
        "open -ra obsidian",
        "command -v brew",
        "brew --version",
        "brew doctor",
    )
    return cleaned if lowered.startswith(prefixes) else None


def _render_validation_line(command: str, status: str | None) -> str:
    command = _extract_validation_command(command)
    if not command:
        return ""
    suffix = f" ({status})" if status else ""
    return f"`{command}`{suffix}"


def _normalized_lists_or_default(items: list[str]) -> list[str]:
    clean = _dedupe_preserve(items)
    return clean if clean else DEFAULT_EMPTY_LIST[:]


def _looks_like_heading_only(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    normalized = _normalize_heading_name(re.sub(r"[*#`]", "", stripped))
    return normalized in {
        "diagnosis",
        "key findings",
        "findings",
        "work completed",
        "implementation",
        "files changed",
        "validation",
        "validation results",
        "blockers / risks",
        "blockers",
        "decisions made",
        "next step",
    }


def _fallback_work_completed(
    final_text: str,
    objective: str,
    changed_files: list[str],
    validation_lines: list[str],
) -> list[str]:
    items: list[str] = []
    first_paragraph = re.split(r"\n\s*\n", final_text.strip(), maxsplit=1)[0] if final_text else ""
    compact = " ".join(first_paragraph.split()).strip()
    if compact and compact != objective and not _looks_like_heading_only(compact):
        items.append(compact)
    if changed_files:
        items.append(f"Updated {len(changed_files)} file(s).")
    if validation_lines:
        items.append(f"Ran {len(validation_lines)} validation command(s).")
    return _dedupe_preserve(items)


def _normalize_from_sections(
    final_text: str,
    objective: str,
    changed_files: list[str],
    validation_lines: list[str],
) -> dict[str, Any]:
    sections = _markdown_sections(final_text)
    work_completed = _extract_list_items(
        _section_text(sections, ("work completed", "implementation", "change summary"))
    )
    key_findings = _extract_list_items(
        _section_text(sections, ("diagnosis", "findings", "key findings", "root cause"))
    )
    decisions = _extract_list_items(
        _section_text(sections, ("decisions", "decisions made"))
    )
    files_from_sections = _extract_paths(
        _section_text(sections, ("files changed", "file-by-file changes", "exact files changed"))
    )
    validation_from_sections = _extract_list_items(
        _section_text(sections, ("validation", "validation results", "commands run", "exact rerun command"))
    )
    blockers = _extract_list_items(
        _section_text(
            sections,
            (
                "blockers",
                "blockers / risks",
                "remaining risks",
                "risks",
                "remaining risks / follow-ups",
            ),
        )
    )
    next_step_text = _section_text(
        sections,
        ("next step", "recommended next step", "recommended next steps", "follow-up"),
    )
    promotion = _extract_promotion_targets(
        _section_text(sections, ("promotion targets", "promote to repo"))
    )

    if not work_completed and final_text:
        work_completed = _fallback_work_completed(
            final_text,
            objective,
            changed_files,
            validation_lines,
        )

    if not key_findings and final_text:
        for paragraph in re.split(r"\n\s*\n", final_text.strip()):
            compact = " ".join(paragraph.split()).strip()
            if compact and not _looks_like_heading_only(compact):
                key_findings = [compact]
                break

    return {
        "objective": objective,
        "work_completed": _normalized_lists_or_default(work_completed),
        "key_findings": _normalized_lists_or_default(key_findings),
        "decisions_made": _normalized_lists_or_default(decisions),
        "files_changed": _normalized_lists_or_default(
            [_display_path(path) for path in files_from_sections + changed_files]
        ),
        "validation": _normalized_lists_or_default(validation_from_sections + validation_lines),
        "blockers_risks": _normalized_lists_or_default(blockers),
        "next_step": " ".join(next_step_text.split()) if next_step_text else "No next step extracted.",
        "promotion_targets": _normalized_lists_or_default(promotion),
    }


def _latest_codex_segment(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    start_index = 0
    prompt_text = ""
    for index, row in enumerate(rows):
        if row.get("type") != "event_msg":
            continue
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if payload.get("type") != "user_message":
            continue
        message = str(payload.get("message") or "").strip()
        if not message:
            continue
        start_index = index
        prompt_text = message
    return rows[start_index:], prompt_text


def _latest_claude_segment(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    start_index = 0
    prompt_text = ""
    for index, row in enumerate(rows):
        if row.get("type") != "user":
            continue
        message = row.get("message") if isinstance(row.get("message"), dict) else {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            start_index = index
            prompt_text = content.strip()
    if prompt_text:
        return rows[start_index:], prompt_text

    for row in reversed(rows):
        if row.get("type") != "last-prompt":
            continue
        prompt = str(row.get("lastPrompt") or "").strip()
        if prompt:
            return rows, prompt
    return rows, ""


def _copy_raw_file(path: Path, tool: str, session_id: str, updated_at: str) -> Path:
    day = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).date().isoformat()
    filename = f"{tool}-{_slugify(session_id, tool)}.jsonl"
    dest = RAW_ROOT / tool / day / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    return dest


def _write_normalized_json(summary: SessionSummary) -> Path:
    day = datetime.fromisoformat(summary.updated_at.replace("Z", "+00:00")).date().isoformat()
    filename = f"{summary.tool}-{_slugify(summary.session_id, summary.tool)}.json"
    dest = NORMALIZED_ROOT / summary.tool / day / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(asdict(summary), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return dest


def _codex_summary_from_path(path: Path) -> SessionSummary | None:
    rows = _read_jsonl(path)
    if not rows:
        return None

    meta = next((row.get("payload", {}) for row in rows if row.get("type") == "session_meta"), {})
    cwd = str(meta.get("cwd") or "")
    if not cwd:
        return None
    canonical_root = _canonical_project_root(cwd)
    if canonical_root != REPO_ROOT.resolve():
        return None

    session_id = str(meta.get("id") or path.stem)
    started_at = str(meta.get("timestamp") or rows[0].get("timestamp") or "")
    updated_at = str(rows[-1].get("timestamp") or started_at)
    title = session_id
    segment_rows, latest_prompt = _latest_codex_segment(rows)
    user_texts: list[str] = [latest_prompt] if latest_prompt else []
    final_assistant_texts: list[str] = []
    progress_assistant_texts: list[str] = []
    changed_files: list[str] = []
    validation_lines: list[str] = []

    for row in segment_rows:
        row_type = row.get("type")
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}

        if row_type == "event_msg" and payload.get("type") == "thread_name_updated":
            title = str(payload.get("thread_name") or title)

        if row_type == "response_item" and payload.get("type") == "message":
            blocks = _extract_text_blocks(payload.get("content"), "text")
            text = "\n".join(blocks).strip()
            if not text:
                continue
            role = payload.get("role")
            if role == "user":
                user_texts.append(text)
            elif role == "assistant":
                if payload.get("phase") == "final_answer":
                    final_assistant_texts.append(text)
                else:
                    progress_assistant_texts.append(text)

        if row_type == "response_item" and payload.get("type") == "function_call":
            name = payload.get("name")
            arguments = payload.get("arguments") or ""
            if name == "apply_patch":
                changed_files.extend(_parse_patch_paths(str(arguments)))
                continue
            if name == "exec_command":
                try:
                    args = json.loads(arguments)
                except json.JSONDecodeError:
                    args = {}
                command = str(args.get("cmd") or "").strip()
                rendered = _render_validation_line(command, None)
                if rendered:
                    validation_lines.append(rendered)

        if row_type == "event_msg" and payload.get("type") == "exec_command_end":
            command_parts = payload.get("command") or []
            if isinstance(command_parts, list) and command_parts:
                command = " ".join(str(part) for part in command_parts)
                status = "passed" if payload.get("exit_code") == 0 else "failed"
                rendered = _render_validation_line(command, status)
                if rendered:
                    validation_lines.append(rendered)

    objective = _extract_objective(user_texts)
    title = _session_title(objective, title)
    final_text = _select_latest_summary(final_assistant_texts or progress_assistant_texts)
    normalized = _normalize_from_sections(final_text, objective, changed_files, validation_lines)
    raw_copy = _copy_raw_file(path, "codex", session_id, updated_at)

    summary = SessionSummary(
        tool="codex",
        session_id=session_id,
        title=title,
        started_at=started_at,
        updated_at=updated_at,
        cwd=cwd,
        canonical_root=str(canonical_root),
        source_path=str(path),
        raw_copy_path=str(raw_copy),
        normalized_path="",
        objective=normalized["objective"],
        work_completed=normalized["work_completed"],
        key_findings=normalized["key_findings"],
        decisions_made=normalized["decisions_made"],
        files_changed=normalized["files_changed"],
        validation=normalized["validation"],
        blockers_risks=normalized["blockers_risks"],
        next_step=normalized["next_step"],
        promotion_targets=normalized["promotion_targets"],
    )
    normalized_path = _write_normalized_json(summary)
    summary.normalized_path = str(normalized_path)
    _write_normalized_json(summary)
    return summary


def _claude_message_text(message: Any) -> list[str]:
    if not isinstance(message, dict):
        return []
    return _extract_text_blocks(message.get("content"), "text")


def _claude_summary_from_path(path: Path) -> SessionSummary | None:
    rows = _read_jsonl(path)
    if not rows:
        return None

    cwd = ""
    session_id = ""
    started_at = str(rows[0].get("timestamp") or "")
    updated_at = str(rows[-1].get("timestamp") or started_at)
    segment_rows, latest_prompt = _latest_claude_segment(rows)
    user_texts: list[str] = [latest_prompt] if latest_prompt else []
    assistant_texts: list[str] = []
    changed_files: list[str] = []
    validation_lines: list[str] = []

    for row in segment_rows:
        cwd = cwd or str(row.get("cwd") or "")
        session_id = session_id or str(row.get("sessionId") or "")
        row_type = row.get("type")

        if row_type == "user":
            texts = _claude_message_text(row.get("message"))
            if texts:
                user_texts.append("\n".join(texts).strip())

        if row_type == "assistant":
            message = row.get("message") if isinstance(row.get("message"), dict) else {}
            content = message.get("content")
            blocks = content if isinstance(content, list) else []
            text_parts = []
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type")
                if block_type == "text":
                    text = block.get("text")
                    if isinstance(text, str):
                        text_parts.append(text)
                elif block_type == "tool_use":
                    name = str(block.get("name") or "")
                    tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
                    if name in {"Write", "Edit", "MultiEdit"}:
                        file_path = tool_input.get("file_path")
                        if isinstance(file_path, str):
                            changed_files.append(file_path)
                    if name == "Bash":
                        command = str(tool_input.get("command") or "").strip()
                        rendered = _render_validation_line(command, None)
                        if rendered:
                            validation_lines.append(rendered)
            if text_parts:
                assistant_texts.append("\n".join(text_parts).strip())

    if not cwd:
        return None

    canonical_root = _canonical_project_root(cwd)
    if canonical_root != REPO_ROOT.resolve():
        return None

    session_id = session_id or path.stem
    objective = _extract_objective(user_texts)
    title = _session_title(objective, session_id)
    final_text = _select_latest_summary(assistant_texts)
    normalized = _normalize_from_sections(final_text, objective, changed_files, validation_lines)
    raw_copy = _copy_raw_file(path, "claude", session_id, updated_at)

    summary = SessionSummary(
        tool="claude",
        session_id=session_id,
        title=title,
        started_at=started_at,
        updated_at=updated_at,
        cwd=cwd,
        canonical_root=str(canonical_root),
        source_path=str(path),
        raw_copy_path=str(raw_copy),
        normalized_path="",
        objective=normalized["objective"],
        work_completed=normalized["work_completed"],
        key_findings=normalized["key_findings"],
        decisions_made=normalized["decisions_made"],
        files_changed=normalized["files_changed"],
        validation=normalized["validation"],
        blockers_risks=normalized["blockers_risks"],
        next_step=normalized["next_step"],
        promotion_targets=normalized["promotion_targets"],
    )
    normalized_path = _write_normalized_json(summary)
    summary.normalized_path = str(normalized_path)
    _write_normalized_json(summary)
    return summary


def _iter_codex_sources() -> list[Path]:
    return sorted(CODEX_SOURCE_ROOT.glob("**/*.jsonl"))


def _iter_claude_sources() -> list[Path]:
    return sorted(CLAUDE_SOURCE_ROOT.glob("**/*.jsonl"))


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"sessions": {}, "last_sync_at": ""}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"sessions": {}, "last_sync_at": ""}


def _write_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _session_state_key(summary: SessionSummary) -> str:
    return f"{summary.tool}:{summary.session_id}"


def _session_updated(summary: SessionSummary, source_hash: str, state: dict[str, Any]) -> bool:
    sessions = state.setdefault("sessions", {})
    current = sessions.get(_session_state_key(summary)) or sessions.get(summary.session_id)
    if not current:
        return True
    return current.get("source_hash") != source_hash


def _remember_session(summary: SessionSummary, source_hash: str, state: dict[str, Any]) -> None:
    state.setdefault("sessions", {})[_session_state_key(summary)] = {
        "tool": summary.tool,
        "updated_at": summary.updated_at,
        "source_hash": source_hash,
        "source_path": summary.source_path,
        "normalized_path": summary.normalized_path,
    }


def _render_list_block(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _render_active_state(summary: SessionSummary) -> str:
    return "\n".join(
        [
            AUTO_STATE_INTRO,
            "",
            f"Last automated update: `{summary.updated_at}` from **{summary.tool.title()}** - {summary.title}",
            "",
            f"Objective: {summary.objective}",
            "",
            "Key findings:",
            _render_list_block(summary.key_findings),
            "",
            "Blockers / risks:",
            _render_list_block(summary.blockers_risks),
            "",
            f"Next step: {summary.next_step}",
            "",
            "Validation:",
            _render_list_block(summary.validation),
            "",
            "Promotion targets:",
            _render_list_block(summary.promotion_targets),
        ]
    ).strip()


def _render_session_entry(summary: SessionSummary) -> str:
    return "\n".join(
        [
            f"### {summary.updated_at} - {summary.tool.title()} - {summary.title}",
            f"<!-- verifyiq:auto:entry:{summary.tool}:{summary.session_id} -->",
            f"Source: `{summary.session_id}`",
            f"Raw artifact: `{Path(summary.raw_copy_path).relative_to(REPO_ROOT)}`",
            f"Normalized artifact: `{Path(summary.normalized_path).relative_to(REPO_ROOT)}`",
            "",
            f"Objective: {summary.objective}",
            "",
            "Work completed:",
            _render_list_block(summary.work_completed),
            "",
            "Key findings:",
            _render_list_block(summary.key_findings),
            "",
            "Decisions made:",
            _render_list_block(summary.decisions_made),
            "",
            "Files changed:",
            _render_list_block(summary.files_changed),
            "",
            "Validation:",
            _render_list_block(summary.validation),
            "",
            "Blockers / risks:",
            _render_list_block(summary.blockers_risks),
            "",
            f"Next step: {summary.next_step}",
            "",
            "Promotion targets:",
            _render_list_block(summary.promotion_targets),
        ]
    ).strip()


def _render_session_log(summaries: list[SessionSummary]) -> str:
    body = [AUTO_STATE_INTRO, ""]
    for summary in summaries:
        body.append(_render_session_entry(summary))
        body.append("")
    return "\n".join(body).strip()


def _today_local_date() -> str:
    return datetime.now().astimezone().date().isoformat()


def _updated_today(summary: SessionSummary) -> bool:
    try:
        local_date = datetime.fromisoformat(summary.updated_at.replace("Z", "+00:00")).astimezone().date().isoformat()
    except ValueError:
        return False
    return local_date == _today_local_date()


def _sync_note(summaries: list[SessionSummary]) -> Path:
    note_path = ensure_today_session()
    today_summaries = [summary for summary in summaries if _updated_today(summary)]
    if not today_summaries:
        upsert_generated_section(note_path, AUTO_ACTIVE_STATE_MARKER, AUTO_STATE_INTRO)
        upsert_generated_section(note_path, AUTO_SESSION_LOG_MARKER, AUTO_STATE_INTRO)
        return note_path

    ordered = sorted(today_summaries, key=lambda item: item.updated_at, reverse=True)
    upsert_generated_section(note_path, AUTO_ACTIVE_STATE_MARKER, _render_active_state(ordered[0]))
    upsert_generated_section(note_path, AUTO_SESSION_LOG_MARKER, _render_session_log(ordered))
    return note_path


def _process_path(tool: str, path: Path) -> SessionSummary | None:
    if tool == "codex":
        return _codex_summary_from_path(path)
    return _claude_summary_from_path(path)


def _scan_all_sources() -> list[tuple[str, Path]]:
    sources: list[tuple[str, Path]] = []
    sources.extend(("codex", path) for path in _iter_codex_sources())
    sources.extend(("claude", path) for path in _iter_claude_sources())
    return sources


def _hook_transcript_from_stdin() -> tuple[str | None, Path | None]:
    raw = sys.stdin.read().strip()
    if not raw:
        return None, None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None, None
    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str) or not transcript_path:
        return None, None
    hook_event = payload.get("hook_event_name")
    if not isinstance(hook_event, str):
        hook_event = None
    return hook_event, Path(transcript_path).expanduser()


def _sync_sources(sources: list[tuple[str, Path]], quiet: bool) -> dict[str, Any]:
    state = _load_state()
    summaries: list[SessionSummary] = []
    synced: list[SessionSummary] = []

    for tool, path in sources:
        if not path.exists():
            continue
        summary = _process_path(tool, path)
        if summary is None:
            continue
        summaries.append(summary)
        source_hash = _file_digest(path)
        if _session_updated(summary, source_hash, state):
            synced.append(summary)
            _remember_session(summary, source_hash, state)

    _write_state({**state, "last_sync_at": _utc_now_iso()})
    note_path = _sync_note(summaries)

    result = {
        "synced": [asdict(item) for item in sorted(synced, key=lambda item: item.updated_at, reverse=True)],
        "all_project_sessions": [asdict(item) for item in sorted(summaries, key=lambda item: item.updated_at, reverse=True)],
        "note_path": str(note_path),
        "last_sync_at": _utc_now_iso(),
    }
    if not quiet:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true", help="Scan both local transcript stores and sync any project sessions.")
    parser.add_argument("--watch", action="store_true", help="Keep polling both transcript stores and refresh artifacts continuously.")
    parser.add_argument(
        "--claude-hook-stdin",
        action="store_true",
        help="Read Claude hook JSON from stdin and sync only the referenced transcript.",
    )
    parser.add_argument(
        "--tool",
        choices=("codex", "claude"),
        help="Sync a single explicit transcript for one tool.",
    )
    parser.add_argument(
        "--transcript",
        help="Explicit transcript path to sync.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        help="Polling interval in seconds for --watch mode.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress JSON output.")
    args = parser.parse_args()

    if not args.sync and not args.watch and not args.claude_hook_stdin and not args.transcript:
        parser.error("choose --sync, --watch, --claude-hook-stdin, or --transcript")

    if args.claude_hook_stdin:
        _, transcript = _hook_transcript_from_stdin()
        if transcript is None:
            if not args.quiet:
                print(json.dumps({"synced": [], "all_project_sessions": [], "note_path": str(ensure_today_session())}, indent=2))
            return 0
        return 0 if _sync_sources([("claude", transcript)], args.quiet) else 1

    if args.transcript:
        if not args.tool:
            parser.error("--tool is required with --transcript")
        return 0 if _sync_sources([(args.tool, Path(args.transcript).expanduser())], args.quiet) else 1

    if args.watch:
        try:
            while True:
                _sync_sources(_scan_all_sources(), args.quiet)
                time.sleep(max(args.interval, 5))
        except KeyboardInterrupt:
            return 0

    return 0 if _sync_sources(_scan_all_sources(), args.quiet) else 1


if __name__ == "__main__":
    raise SystemExit(main())
