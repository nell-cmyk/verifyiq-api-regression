"""Local collection gate for the /parse fileType matrix.

The matrix runs one live parse per fileType (slow). It is excluded from default
collection so the protected baseline command
`pytest tests/endpoints/parse/ -v` stays visually unchanged. Opt in explicitly
by pointing pytest at the matrix module with `RUN_PARSE_MATRIX=1` set:

  RUN_PARSE_MATRIX=1 pytest tests/endpoints/parse/test_parse_matrix.py -v
"""
import os

collect_ignore: list[str] = []
if not os.getenv("RUN_PARSE_MATRIX"):
    collect_ignore.append("test_parse_matrix.py")
