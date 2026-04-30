"""Approved live executor for narrow Automation Hub nodes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping

import httpx

from tools.automation_hub.manifest import APPROVED_LIVE_NODE_IDS
from tools.automation_hub.report_writer import HubReportPaths, write_live_report


HEALTH_CORE_NODE_ID = "get-smoke.health.core"
HEALTH_READY_NODE_ID = "get-smoke.health.ready"
APPROVED_HEALTH_NODE_IDS = (HEALTH_CORE_NODE_ID, HEALTH_READY_NODE_ID)
HEALTH_METHOD = "GET"
HEALTH_TIMEOUT_SECS = 30.0
EXPECTED_HEALTH_STATUS_CODE = 200


@dataclass(frozen=True)
class HealthEndpointSpec:
    node_id: str
    path: str
    endpoint_label: str
    expected_status_code: int = EXPECTED_HEALTH_STATUS_CODE


HEALTH_ENDPOINTS: Mapping[str, HealthEndpointSpec] = {
    HEALTH_CORE_NODE_ID: HealthEndpointSpec(
        node_id=HEALTH_CORE_NODE_ID,
        path="/health",
        endpoint_label="GET /health",
    ),
    HEALTH_READY_NODE_ID: HealthEndpointSpec(
        node_id=HEALTH_READY_NODE_ID,
        path="/health/ready",
        endpoint_label="GET /health/ready",
    ),
}


@dataclass(frozen=True)
class HubLiveExecutionResult:
    node_id: str
    endpoint_result: Mapping[str, Any]
    report_paths: HubReportPaths
    exit_code: int


def execute_approved_live_node(
    *,
    node_id: str,
    output_root: Path,
    client_factory: Callable[[], Any] | None = None,
    run_id: str | None = None,
) -> HubLiveExecutionResult:
    """Execute one approved live hub node and write its metadata-only report."""

    if node_id not in APPROVED_LIVE_NODE_IDS:
        raise ValueError(f"Hub node is not approved for live execution: {node_id}")
    spec = HEALTH_ENDPOINTS.get(node_id)
    if spec is None:
        raise ValueError(f"No executor is implemented for approved hub node: {node_id}")

    client = client_factory() if client_factory is not None else _default_client_factory()
    try:
        endpoint_result = _execute_health_node(client, spec)
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()

    paths = write_live_report(
        output_root=output_root,
        endpoint_result=endpoint_result,
        run_id=run_id,
    )
    return HubLiveExecutionResult(
        node_id=node_id,
        endpoint_result=endpoint_result,
        report_paths=paths,
        exit_code=0 if endpoint_result["outcome"] == "passed" else 1,
    )


def _default_client_factory() -> Any:
    from tests.client import make_client

    return make_client(timeout=HEALTH_TIMEOUT_SECS)


def _execute_health_node(client: Any, spec: HealthEndpointSpec) -> dict[str, Any]:
    started_at = _utc_now()
    start = perf_counter()
    status_code: int | None = None
    safe_response_headers: dict[str, str] = {}
    outcome = "error"
    failure_type = "request_error"
    error_type = ""

    try:
        response = client.get(spec.path, timeout=HEALTH_TIMEOUT_SECS)
    except httpx.RequestError as exc:
        error_type = type(exc).__name__
    else:
        status_code = response.status_code
        safe_response_headers = _allowlisted_response_headers(response.headers)
        if status_code == spec.expected_status_code:
            outcome = "passed"
            failure_type = ""
        else:
            outcome = "failed"
            failure_type = "unexpected_status_code"

    duration_ms = round((perf_counter() - start) * 1000, 3)
    return {
        "node_id": spec.node_id,
        "endpoint_label": spec.endpoint_label,
        "method": HEALTH_METHOD,
        "path": spec.path,
        "status_code": status_code,
        "expected_status_code": spec.expected_status_code,
        "duration_ms": duration_ms,
        "outcome": outcome,
        "safe_response_headers": safe_response_headers,
        "failure_type": failure_type,
        "error_type": error_type,
        "started_at": started_at,
        "completed_at": _utc_now(),
    }


def _allowlisted_response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    content_type = headers.get("content-type") or headers.get("Content-Type")
    if content_type is None:
        return {}
    return {"content-type": str(content_type)}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
