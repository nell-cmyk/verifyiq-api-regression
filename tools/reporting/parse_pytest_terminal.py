from __future__ import annotations

import re
from dataclasses import dataclass

RESULT_RE = re.compile(
    r"^(?P<nodeid>\S+::\S+(?:\[[^\]]+\])?)\s+"
    r"(?P<status>PASSED|FAILED|ERROR)\s+\[\s*\d+%\]$"
)
TEST_ID_RE = re.compile(r"\[(?P<test_id>[^\]]+)\]")
FAILURE_HEADER_RE = re.compile(
    r"^_{5,}\s+(?P<name>\S+(?:\[[^\]]+\])?)\s+_{5,}$"
)
SUMMARY_DURATION_RE = re.compile(r"=+\s+.+?\s+in\s+(?P<duration>.+?)\s+=+$")


@dataclass
class ParsedResult:
    nodeid: str
    test_id: str
    status: str
    failure_text: str = ""


@dataclass
class ParsedTerminalRun:
    results: list[ParsedResult]
    duration_text: str | None
    raw_text: str


def _extract_test_id(text: str) -> str | None:
    match = TEST_ID_RE.search(text)
    return match.group("test_id") if match else None


def parse_pytest_terminal_output(text: str) -> ParsedTerminalRun:
    lines = text.splitlines()
    results: list[ParsedResult] = []
    results_by_test_id: dict[str, ParsedResult] = {}
    duration_text: str | None = None

    for line in lines:
        result_match = RESULT_RE.match(line.strip())
        if not result_match:
            duration_match = SUMMARY_DURATION_RE.match(line.strip())
            if duration_match:
                duration_text = duration_match.group("duration")
            continue

        nodeid = result_match.group("nodeid")
        test_id = _extract_test_id(nodeid) or nodeid
        parsed = ParsedResult(
            nodeid=nodeid,
            test_id=test_id,
            status=result_match.group("status"),
        )
        results.append(parsed)
        results_by_test_id[test_id] = parsed

    current_result: ParsedResult | None = None
    current_lines: list[str] = []
    in_failure_details = False

    for line in lines:
        stripped = line.rstrip()
        header_match = FAILURE_HEADER_RE.match(stripped)
        if header_match:
            header_test_id = _extract_test_id(header_match.group("name"))
            if current_result is not None:
                current_result.failure_text = "\n".join(current_lines).strip()
            current_result = results_by_test_id.get(header_test_id or "")
            current_lines = []
            in_failure_details = current_result is not None
            continue

        if not in_failure_details:
            continue

        if stripped.startswith("====") and "short test summary info" in stripped.lower():
            if current_result is not None:
                current_result.failure_text = "\n".join(current_lines).strip()
            current_result = None
            current_lines = []
            in_failure_details = False
            continue

        if current_result is not None:
            current_lines.append(stripped)

    if current_result is not None:
        current_result.failure_text = "\n".join(current_lines).strip()

    return ParsedTerminalRun(results=results, duration_text=duration_text, raw_text=text)
