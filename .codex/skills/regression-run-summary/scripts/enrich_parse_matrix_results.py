from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.endpoints.parse.file_types import request_file_type_for
from tests.endpoints.parse.registry import load_canonical_fixtures

from parse_pytest_terminal import ParsedTerminalRun

NON_200_STATUS_RE = re.compile(r"\bstatus:\s+(?P<status>\d{3})\b")


@dataclass
class EnrichedParseResult:
    nodeid: str
    pytest_status: str
    failure_class: str
    note: str
    registry_file_type: str
    request_file_type: str
    fixture_name: str | None
    registry_row: int | None
    verification_status: str | None
    gcs_uri: str | None


def _first_note(failure_text: str) -> str:
    for raw_line in failure_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("E   "):
            return line[4:].strip()
        if line.startswith("E "):
            return line[2:].strip()
        if not line.startswith("_"):
            return line
    return ""


def classify_failure(pytest_status: str, failure_text: str) -> tuple[str, str]:
    if pytest_status == "PASSED":
        return "passed", "passed"

    note = _first_note(failure_text) or pytest_status.lower()
    lowered = failure_text.lower()

    if "matrix parse timed out" in lowered:
        return "timeout", note
    if "matrix parse transport error" in lowered:
        return "transport-error", note
    if "non-json 200" in lowered:
        return "non-json-200", note
    if "filetype mismatch" in lowered:
        return "filetype-mismatch", note
    if "missing fields" in lowered:
        return "missing-fields", note
    if "response body is html" in lowered or "references google auth/iap" in lowered:
        return "auth-proxy", note

    status_match = NON_200_STATUS_RE.search(failure_text)
    if status_match and status_match.group("status") != "200":
        return "non-200", note

    return "failed", note


def enrich_parse_matrix_results(parsed_run: ParsedTerminalRun) -> list[EnrichedParseResult]:
    canonical_by_file_type = {
        fixture["file_type"]: fixture for fixture in load_canonical_fixtures()
    }
    enriched: list[EnrichedParseResult] = []

    for result in parsed_run.results:
        fixture = canonical_by_file_type.get(result.test_id, {})
        registry_file_type = result.test_id
        request_file_type = request_file_type_for(registry_file_type)
        failure_class, note = classify_failure(result.status, result.failure_text)
        enriched.append(
            EnrichedParseResult(
                nodeid=result.nodeid,
                pytest_status=result.status,
                failure_class=failure_class,
                note=note,
                registry_file_type=registry_file_type,
                request_file_type=request_file_type,
                fixture_name=fixture.get("name"),
                registry_row=fixture.get("source_row"),
                verification_status=fixture.get("verification_status"),
                gcs_uri=fixture.get("gcs_uri"),
            )
        )

    return enriched
