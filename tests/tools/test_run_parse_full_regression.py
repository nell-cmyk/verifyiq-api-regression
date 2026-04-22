from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "run_parse_full_regression.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("run_parse_full_regression", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_regression_reuses_one_parse_run_dir_name(monkeypatch):
    module = _load_module()
    calls: list[tuple[str, list[str], dict[str, str] | None]] = []

    def fake_run_step(label: str, command: list[str], env: dict[str, str] | None = None) -> int:
        calls.append((label, command, env))
        return 0

    monkeypatch.setattr(module, "_run_step", fake_run_step)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH)])

    assert module.main() == 0
    assert [label for label, _, _ in calls] == ["Protected baseline", "Parse matrix"]

    baseline_env = calls[0][2]
    matrix_env = calls[1][2]
    assert baseline_env is not None
    assert matrix_env is not None

    baseline_run_dir = baseline_env.get(module.PARSE_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR, "")
    matrix_run_dir = matrix_env.get(module.PARSE_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR, "")
    assert re.fullmatch(r"parse_\d{4}-\d{2}-\d{2}-T\d{6}_\d{6}Z", baseline_run_dir)
    assert matrix_run_dir == baseline_run_dir
