#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import mind_session


def build_command() -> tuple[str, list[str]]:
    binary = mind_session._resolve_mind_binary()
    return binary, [binary, "mcp"]


def main() -> int:
    binary, command = build_command()
    os.execvp(binary, command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
