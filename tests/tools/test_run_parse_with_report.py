from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "run_parse_with_report.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("run_parse_with_report", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_matrix_tier_uses_canonical_reporting_wrapper():
    module = _load_module()
    args = SimpleNamespace(file_types="Payslip,TIN", k_expr="smoke")

    cmd = module._matrix_cmd(args)

    expected_wrapper = (
        module.REPO_ROOT
        / "tools"
        / "reporting"
        / "run_parse_matrix_with_summary.py"
    )
    assert cmd[:3] == [sys.executable, str(expected_wrapper), "--report"]
    assert ".codex" not in " ".join(cmd)
