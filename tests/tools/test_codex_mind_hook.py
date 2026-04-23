from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "tools" / "codex_mind_hook.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("codex_mind_hook", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_handle_session_start_returns_additional_context():
    module = _load_module()
    module._run_wrapper = lambda command, payload: {"context": "Recovered context"}

    result = module.handle_hook(
        {
            "hook_event_name": "SessionStart",
            "session_id": "session-123",
            "source": "startup",
        }
    )

    assert result["continue"] is True
    assert result["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert result["hookSpecificOutput"]["additionalContext"] == "Recovered context"


def test_handle_checkpoint_failure_returns_warning_without_blocking():
    module = _load_module()

    def _boom(command, payload):
        raise RuntimeError("checkpoint unavailable")

    module._run_wrapper = _boom

    result = module.handle_hook(
        {
            "hook_event_name": "Stop",
            "session_id": "session-123",
        }
    )

    assert result["continue"] is True
    assert "checkpoint refresh failed" in result["systemMessage"]


def test_event_name_includes_session_start_source():
    module = _load_module()

    assert module._event_name({"hook_event_name": "SessionStart", "source": "resume"}) == (
        "codex.session_start.resume"
    )
