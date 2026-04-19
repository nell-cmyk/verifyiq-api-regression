#!/usr/bin/env python3
"""Canonical repo entrypoint for regression summary rendering."""
from __future__ import annotations

import runpy
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / ".codex"
    / "skills"
    / "regression-run-summary"
    / "scripts"
    / "render_regression_summary.py"
)


def main() -> int:
    try:
        runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
    except SystemExit as exc:
        if exc.code is None:
            return 0
        if isinstance(exc.code, int):
            return exc.code
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
