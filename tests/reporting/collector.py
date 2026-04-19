"""In-memory collector for per-test regression evidence.

Not thread-safe across processes; pytest-xdist support is out of scope.
"""
from __future__ import annotations

import contextvars
import time
from dataclasses import dataclass, field
from typing import Any

CURRENT_NODEID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "regression_report_nodeid", default=None
)


@dataclass
class RequestRecord:
    method: str = ""
    url: str = ""
    path: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    body_text: str | None = None
    body_truncated: bool = False
    sent_at: float | None = None


@dataclass
class ResponseRecord:
    status: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    body_text: str | None = None
    body_truncated: bool = False
    elapsed_ms: float | None = None
    received_at: float | None = None


@dataclass
class CaseRecord:
    nodeid: str
    module: str = ""
    test: str = ""
    start_ts: float = field(default_factory=time.time)
    end_ts: float | None = None
    outcome: str = ""  # PASSED | FAILED | SKIPPED | ERROR
    longrepr: str = ""
    fixture: dict[str, Any] = field(default_factory=dict)
    endpoint: str = ""
    file_type: dict[str, Any] = field(default_factory=dict)
    requests: list[RequestRecord] = field(default_factory=list)
    responses: list[ResponseRecord] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)


class Collector:
    def __init__(self) -> None:
        self._cases: dict[str, CaseRecord] = {}
        self._run_started_at: float = time.time()

    @property
    def run_started_at(self) -> float:
        return self._run_started_at

    def start_case(self, nodeid: str, *, module: str = "", test: str = "") -> CaseRecord:
        case = self._cases.get(nodeid)
        if case is None:
            case = CaseRecord(nodeid=nodeid, module=module, test=test)
            self._cases[nodeid] = case
        return case

    def get_case(self, nodeid: str) -> CaseRecord | None:
        return self._cases.get(nodeid)

    def cases(self) -> list[CaseRecord]:
        return sorted(self._cases.values(), key=lambda c: c.nodeid)

    def add_request(self, nodeid: str, req: RequestRecord) -> None:
        case = self.start_case(nodeid)
        case.requests.append(req)

    def add_response(self, nodeid: str, resp: ResponseRecord) -> None:
        case = self.start_case(nodeid)
        case.responses.append(resp)


_collector: Collector | None = None


def get_collector() -> Collector:
    global _collector
    if _collector is None:
        _collector = Collector()
    return _collector


def reset_collector() -> None:
    global _collector
    _collector = None
