from __future__ import annotations

import importlib.util
import sys
from types import SimpleNamespace
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "tools" / "mind_session.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("mind_session", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_checkpoint_names_parses_active_entries():
    module = _load_module()
    text = """
Checkpoints for \"projects/verifyiq-api-regression\":
   checkpoint-2026-04-22T11-40-37-729Z [active]
       Updated: 2026-04-22 11:40:37
   checkpoint-older [active]
"""

    assert module._extract_checkpoint_names(text) == [
        "checkpoint-2026-04-22T11-40-37-729Z",
        "checkpoint-older",
    ]


def test_build_summary_body_redacts_sensitive_lines_and_includes_metadata():
    module = _load_module()

    summary = module._build_summary_body(
        title="automation validation",
        body="Authorization: Bearer super-secret\nValidated repo-controlled Mind session automation.",
        changed_files=["tools/mind_session.py", ".opencode/plugins/verifyiq-mind-session.js"],
        validations=["./.venv/bin/python tools/mind_session.py start (passed)"],
        commit_hash="49dc671",
        risks=["Mind SQLite access must stay sequential."],
    )

    assert "Authorization:" not in summary
    assert "[REDACTED SENSITIVE CONTENT]" in summary
    assert "Files changed:" in summary
    assert "Commit: 49dc671" in summary
    assert "Remaining risks:" in summary


def test_format_context_mentions_created_checkpoint_when_missing():
    module = _load_module()

    context = module._format_context(
        checkpoint_name=None,
        checkpoint_payload=None,
        recent_memories="recent memory output",
        recent_sessions="recent session output",
        space_created=True,
    )

    assert "Created project space" in context
    assert "No active checkpoint was found" in context
    assert "Recent project memories:" in context
    assert "Recent session activity:" in context


def test_doctor_reports_codex_automation_surfaces():
    module = _load_module()
    payloads: list[dict] = []

    class _Lock:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    module._mind_lock = lambda: _Lock()
    module._run_mind = lambda args, allow_failure=False: module.CommandResult(
        binary="/tmp/mind",
        command=["/tmp/mind", *args],
        returncode=0,
        stdout="ok",
        stderr="",
    )
    module._space_exists = lambda space: True
    module._emit = lambda payload, exit_code=0: payloads.append(payload) or exit_code

    rc = module.cmd_doctor(SimpleNamespace(command="doctor"))

    assert rc == 0
    assert payloads
    assert payloads[0]["local_codex_config"] == ".codex/config.toml"
    assert payloads[0]["local_codex_hooks"] == ".codex/hooks.json"
    assert payloads[0]["local_codex_skill"] == ".agents/skills/verifyiq-mind-session/SKILL.md"
