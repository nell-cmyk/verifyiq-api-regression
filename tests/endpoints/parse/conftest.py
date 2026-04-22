"""Local collection gate for the /parse fileType matrix.

The matrix runs one live parse per fileType (slow). It is excluded from default
collection so the protected baseline command
`pytest tests/endpoints/parse/ -v` stays visually unchanged. Opt in explicitly
by pointing pytest at the matrix module with `RUN_PARSE_MATRIX=1` set:

  RUN_PARSE_MATRIX=1 pytest tests/endpoints/parse/test_parse_matrix.py -v

Direct module execution without `RUN_PARSE_MATRIX=1` also fails inside the
matrix module so accidental live collection is blocked even when `collect_ignore`
does not apply.
"""
from __future__ import annotations

import os

from tests.endpoints.parse.artifacts import clear_current_parse_nodeid, set_current_parse_nodeid

collect_ignore: list[str] = []
if os.getenv("RUN_PARSE_MATRIX") != "1":
    collect_ignore.append("test_parse_matrix.py")


def pytest_runtest_setup(item):
    set_current_parse_nodeid(item.nodeid)


def pytest_runtest_call(item):
    set_current_parse_nodeid(item.nodeid)


def pytest_runtest_teardown(item):
    clear_current_parse_nodeid()
