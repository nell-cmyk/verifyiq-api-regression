from __future__ import annotations

import json

import httpx
import pytest

from tools.automation_hub import executor


class FakeHealthClient:
    def __init__(self, response: httpx.Response):
        self.response = response
        self.calls: list[tuple[str, float]] = []
        self.closed = False

    def get(self, path: str, *, timeout: float) -> httpx.Response:
        self.calls.append((path, timeout))
        return self.response

    def close(self) -> None:
        self.closed = True


def _response(status_code: int = 200) -> httpx.Response:
    request = httpx.Request("GET", "https://verifyiq.example.test/health")
    return httpx.Response(
        status_code,
        headers={
            "content-type": "application/json",
            "set-cookie": "secret-cookie",
            "x-request-id": "raw-id",
        },
        text='{"raw":"body should not be persisted"}',
        request=request,
    )


def test_health_core_executor_calls_only_get_health_and_writes_metadata_report(tmp_path) -> None:
    client = FakeHealthClient(_response())

    result = executor.execute_approved_live_node(
        node_id="get-smoke.health.core",
        output_root=tmp_path,
        client_factory=lambda: client,
        run_id="unit-executor",
    )

    assert result.exit_code == 0
    assert client.calls == [("/health", executor.HEALTH_TIMEOUT_SECS)]
    assert client.closed is True
    payload = json.loads(result.report_paths.json_path.read_text(encoding="utf-8"))
    assert payload["run_metadata"]["report_kind"] == "automation_hub_live"
    assert payload["selected_nodes"] == ["get-smoke.health.core"]
    assert payload["node_result_summaries"][0]["node_id"] == "get-smoke.health.core"
    assert payload["node_result_summaries"][0]["endpoint_label"] == "GET /health"
    assert payload["node_result_summaries"][0]["method"] == "GET"
    assert payload["node_result_summaries"][0]["path"] == "/health"
    assert payload["node_result_summaries"][0]["status_code"] == 200
    assert payload["node_result_summaries"][0]["outcome"] == "passed"
    assert payload["node_result_summaries"][0]["duration_ms"] >= 0
    assert payload["safe_response_metadata"][0]["headers"] == {"content-type": "application/json"}
    assert payload["rerun_selectors"] == {
        "get-smoke.health.core": "./.venv/bin/python tools/run_regression.py --suite extended --hub-node get-smoke.health.core"
    }
    raw_json = result.report_paths.json_path.read_text(encoding="utf-8")
    assert "body should not be persisted" not in raw_json
    assert "secret-cookie" not in raw_json
    assert "raw-id" not in raw_json


def test_health_core_executor_records_unexpected_status_without_body(tmp_path) -> None:
    client = FakeHealthClient(_response(status_code=503))

    result = executor.execute_approved_live_node(
        node_id="get-smoke.health.core",
        output_root=tmp_path,
        client_factory=lambda: client,
        run_id="unit-failure",
    )

    assert result.exit_code == 1
    payload = json.loads(result.report_paths.json_path.read_text(encoding="utf-8"))
    assert payload["node_result_summaries"][0]["status_code"] == 503
    assert payload["node_result_summaries"][0]["outcome"] == "failed"
    assert payload["failures"] == [
        {
            "node_id": "get-smoke.health.core",
            "type": "unexpected_status_code",
            "outcome": "failed",
            "status_code": 503,
            "expected_status_code": 200,
        }
    ]
    assert "body should not be persisted" not in result.report_paths.json_path.read_text(encoding="utf-8")


def test_executor_rejects_unapproved_live_nodes(tmp_path) -> None:
    with pytest.raises(ValueError, match="not approved for live execution"):
        executor.execute_approved_live_node(
            node_id="get-smoke.safe-read-only",
            output_root=tmp_path,
            client_factory=lambda: FakeHealthClient(_response()),
            run_id="unit-rejected",
        )
