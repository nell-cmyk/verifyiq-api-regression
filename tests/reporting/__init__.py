"""Regression reporting package.

Inactive unless the env flag `REGRESSION_REPORT=1` is set. See design plan for
scope and rationale. No module here should import network or auth machinery at
import time, so `pytest --collect-only` remains cheap.
"""
from __future__ import annotations

import os


def is_enabled() -> bool:
    return os.getenv("REGRESSION_REPORT", "").strip() == "1"
