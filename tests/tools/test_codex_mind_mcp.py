from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "tools" / "codex_mind_mcp.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("codex_mind_mcp", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_command_uses_resolved_mind_binary():
    module = _load_module()
    module.mind_session._resolve_mind_binary = lambda: "/tmp/mind-bin"

    binary, command = module.build_command()

    assert binary == "/tmp/mind-bin"
    assert command == ["/tmp/mind-bin", "mcp"]
