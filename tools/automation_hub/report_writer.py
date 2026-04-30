"""Report writers for Automation Hub dry-run plans and approved live nodes."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from tools.automation_hub.manifest import (
    APPROVED_LIVE_NODE_IDS,
    DEFAULT_HUB_MANIFEST,
    HubNode,
    HubNodeSelection,
)
from tools.automation_hub.reporting import (
    EXCLUDED_BY_POLICY,
    default_evidence_contract,
    redact_evidence_metadata,
)


NO_ENDPOINTS_EXECUTED = "No endpoints were executed; this is a synthetic non-live hub dry-run report."

SKIP_SEMANTICS = (
    "failed producer -> dependent consumers skipped as dependency failed",
    "successful producer with no safe usable value -> dependent consumers skipped as missing prerequisite",
    "unrelated independent nodes may continue",
)


@dataclass(frozen=True)
class HubReportPaths:
    run_dir: Path
    json_path: Path
    markdown_path: Path
    latest_path: Path


def write_synthetic_report(
    *,
    output_root: Path,
    hub_node: str = "",
    hub_group: str = "",
    run_id: str | None = None,
    extra_metadata: Mapping[str, Any] | None = None,
) -> HubReportPaths:
    """Write a synthetic report for the selected non-live hub plan."""

    selection = DEFAULT_HUB_MANIFEST.select_nodes(hub_node=hub_node, hub_group=hub_group)
    resolved_run_id = run_id or _default_run_id()
    run_dir = output_root / resolved_run_id
    payload = build_synthetic_report_payload(
        selection=selection,
        run_id=resolved_run_id,
        hub_node=hub_node,
        hub_group=hub_group,
        extra_metadata=extra_metadata,
    )

    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "run.json"
    markdown_path = run_dir / "run.md"
    latest_path = output_root / "LATEST.txt"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    latest_path.write_text(resolved_run_id + "\n", encoding="utf-8")
    return HubReportPaths(
        run_dir=run_dir,
        json_path=json_path,
        markdown_path=markdown_path,
        latest_path=latest_path,
    )


def write_live_report(
    *,
    output_root: Path,
    endpoint_result: Mapping[str, Any],
    run_id: str | None = None,
    extra_metadata: Mapping[str, Any] | None = None,
) -> HubReportPaths:
    """Write a metadata-only live report for one approved hub endpoint result."""

    resolved_run_id = run_id or _default_run_id()
    run_dir = output_root / resolved_run_id
    payload = build_live_report_payload(
        endpoint_result=endpoint_result,
        run_id=resolved_run_id,
        extra_metadata=extra_metadata,
    )

    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "run.json"
    markdown_path = run_dir / "run.md"
    latest_path = output_root / "LATEST.txt"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_live_markdown(payload), encoding="utf-8")
    latest_path.write_text(resolved_run_id + "\n", encoding="utf-8")
    return HubReportPaths(
        run_dir=run_dir,
        json_path=json_path,
        markdown_path=markdown_path,
        latest_path=latest_path,
    )


def build_synthetic_report_payload(
    *,
    selection: HubNodeSelection,
    run_id: str,
    hub_node: str = "",
    hub_group: str = "",
    extra_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the JSON payload for a synthetic non-live hub report."""

    contract = default_evidence_contract()
    selector = _selector_metadata(hub_node=hub_node, hub_group=hub_group)
    node_plans = [_node_payload(node, selection) for node in selection.nodes]
    selected_nodes = [node.node_id for node in selection.nodes if node.node_id in selection.selected_node_ids]
    dependency_order = [node.node_id for node in selection.nodes]
    dependency_inputs = {
        node.node_id: [
            {"name": item.name, "source_node_id": item.source_node_id, "required": item.required}
            for item in node.consumes
        ]
        for node in selection.nodes
    }
    dependency_outputs = {
        node.node_id: [
            {
                "name": output.name,
                "description": output.description,
                "sensitivity": output.sensitivity,
            }
            for output in node.produces
        ]
        for node in selection.nodes
    }

    return {
        "run_metadata": {
            "run_id": run_id,
            "generated_at": _utc_now(),
            "report_kind": "automation_hub_synthetic_dry_run",
            "selected_suite": "extended",
            "dry_run": True,
            "endpoints_executed": False,
            "endpoint_call_count": 0,
            "live_execution": "not implemented",
            "notice": NO_ENDPOINTS_EXECUTED,
        },
        "selector": selector,
        "selected_nodes": selected_nodes,
        "dependency_order": dependency_order,
        "prerequisite_closure": sorted(selection.prerequisite_node_ids),
        "node_plans": node_plans,
        "node_result_summaries": [],
        "request_metadata": [],
        "safe_response_metadata": [],
        "response_body_policy": {
            "raw_response_bodies_present": False,
            "raw_response_body_persistence": "absent",
            "policy": contract.raw_response_body_policy,
        },
        "timing": {
            "synthetic_report_generated_at": _utc_now(),
            "endpoint_durations_ms": [],
        },
        "dependency_inputs": dependency_inputs,
        "dependency_outputs": dependency_outputs,
        "skip_semantics": list(SKIP_SEMANTICS),
        "skips": [],
        "failures": [],
        "rerun_selectors": {
            node.node_id: node.rerun_selector
            for node in selection.nodes
        },
        "reporting_contract": {
            "required_sections": list(contract.required_sections),
            "redaction_exclusions": list(contract.redaction_exclusions),
            "raw_response_body_policy": contract.raw_response_body_policy,
        },
        "sanitized_metadata": _sanitize_report_metadata(dict(extra_metadata or {})),
    }


def build_live_report_payload(
    *,
    endpoint_result: Mapping[str, Any],
    run_id: str,
    extra_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a metadata-only JSON payload for an approved live hub run."""

    node_id = str(endpoint_result["node_id"])
    selection = DEFAULT_HUB_MANIFEST.select_nodes(hub_node=node_id)
    node_by_id = {node.node_id: node for node in selection.nodes}
    node = node_by_id[node_id]
    if node.node_id not in APPROVED_LIVE_NODE_IDS:
        raise ValueError(f"Hub node is not approved for live reporting: {node.node_id}")
    contract = default_evidence_contract()
    status_code = endpoint_result.get("status_code")
    duration_ms = endpoint_result.get("duration_ms")
    outcome = str(endpoint_result.get("outcome", "unknown"))
    expected_status_code = endpoint_result.get("expected_status_code")
    safe_response_headers = _safe_response_headers(endpoint_result.get("safe_response_headers", {}))
    result_summary = {
        "node_id": node.node_id,
        "endpoint_label": str(endpoint_result.get("endpoint_label") or node.endpoint_label),
        "method": str(endpoint_result.get("method", "GET")),
        "path": str(endpoint_result.get("path", "")),
        "status_code": status_code,
        "expected_status_code": expected_status_code,
        "duration_ms": duration_ms,
        "outcome": outcome,
        "rerun_selector": node.rerun_selector,
    }
    failure = _failure_payload(endpoint_result, result_summary) if outcome != "passed" else None

    return {
        "run_metadata": {
            "run_id": run_id,
            "generated_at": _utc_now(),
            "report_kind": "automation_hub_live",
            "selected_suite": "extended",
            "dry_run": False,
            "endpoints_executed": True,
            "endpoint_call_count": 1,
            "live_execution": "approved_health_node",
            "approved_node_id": node.node_id,
            "notice": "Live Automation Hub execution for approved health node only.",
        },
        "selector": {"type": "hub-node", "value": node.node_id},
        "selected_nodes": [node.node_id],
        "dependency_order": [item.node_id for item in selection.nodes],
        "prerequisite_closure": sorted(selection.prerequisite_node_ids),
        "node_plans": [_node_payload(item, selection) for item in selection.nodes],
        "node_result_summaries": [result_summary],
        "request_metadata": [
            {
                "node_id": node.node_id,
                "endpoint_label": result_summary["endpoint_label"],
                "method": result_summary["method"],
                "path": result_summary["path"],
                "body_present": False,
                "request_body_persisted": False,
                "request_headers_persisted": False,
            }
        ],
        "safe_response_metadata": [
            {
                "node_id": node.node_id,
                "status_code": status_code,
                "headers": safe_response_headers,
                "body_persisted": False,
            }
        ],
        "response_body_policy": {
            "raw_response_bodies_present": False,
            "raw_response_body_persistence": "absent",
            "policy": "metadata_only; raw response bodies are not persisted for approved health-node live reports.",
        },
        "timing": {
            "started_at": endpoint_result.get("started_at"),
            "completed_at": endpoint_result.get("completed_at"),
            "duration_ms": duration_ms,
            "endpoint_durations_ms": [
                {
                    "node_id": node.node_id,
                    "duration_ms": duration_ms,
                }
            ],
        },
        "dependency_inputs": {node.node_id: []},
        "dependency_outputs": {
            node.node_id: [
                {
                    "name": output.name,
                    "description": output.description,
                    "sensitivity": output.sensitivity,
                }
                for output in node.produces
            ]
        },
        "skip_semantics": list(SKIP_SEMANTICS),
        "skips": [],
        "failures": [] if failure is None else [failure],
        "rerun_selectors": {node.node_id: node.rerun_selector},
        "reporting_contract": {
            "required_sections": list(contract.required_sections),
            "redaction_exclusions": list(contract.redaction_exclusions),
            "raw_response_body_policy": contract.raw_response_body_policy,
        },
        "sanitized_metadata": _sanitize_report_metadata(dict(extra_metadata or {})),
    }


def render_markdown(payload: Mapping[str, Any]) -> str:
    run = payload["run_metadata"]
    selector = payload["selector"]
    lines: list[str] = []
    lines.append("# Automation Hub Synthetic Dry-Run Report")
    lines.append("")
    lines.append(f"- Run ID: `{run['run_id']}`")
    lines.append(f"- Generated: `{run['generated_at']}`")
    lines.append("- Suite: `extended`")
    lines.append(f"- Selector: `{selector['type']}`")
    if selector["value"]:
        lines.append(f"- Selector value: `{selector['value']}`")
    lines.append(f"- Endpoint calls: `{run['endpoint_call_count']}`")
    lines.append(f"- Notice: {run['notice']}")
    lines.append("")
    lines.append("## Dependency Order")
    lines.append("")
    for index, node in enumerate(payload["node_plans"], start=1):
        lines.append(
            f"{index}. `{node['node_id']}` - {node['inclusion']} - "
            f"{node['status']} - {node['execution_availability']}"
        )
    lines.append("")
    lines.append("## Nodes")
    lines.append("")
    lines.append("| node | group | inputs | outputs | artifact policy | rerun selector |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for node in payload["node_plans"]:
        inputs = _format_names(node["consumes"])
        outputs = _format_names(node["produces"])
        artifact_policy = (
            f"response_body={node['artifact_policy']['response_body_policy']}; "
            f"raw_body_persistence={node['artifact_policy']['raw_body_persistence']}"
        )
        lines.append(
            f"| `{node['node_id']}` | `{node['endpoint_group']}` | {inputs} | {outputs} | "
            f"`{artifact_policy}` | `{node['rerun_selector']}` |"
        )
    lines.append("")
    lines.append("## Dependency Semantics")
    lines.append("")
    for item in payload["skip_semantics"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Reporting Contract")
    lines.append("")
    contract = payload["reporting_contract"]
    lines.append(f"- Required sections: {', '.join(contract['required_sections'])}")
    lines.append(f"- Redaction/exclusion: {', '.join(contract['redaction_exclusions'])}")
    lines.append(f"- Raw response bodies: {contract['raw_response_body_policy']}")
    lines.append("")
    lines.append("## Runtime Evidence")
    lines.append("")
    lines.append("- No endpoints were executed.")
    lines.append("- No request bodies, response bodies, document identifiers, GCS object names, fraud results, or artifact/export payloads are present.")
    lines.append("- `node_result_summaries`, `request_metadata`, and `safe_response_metadata` are intentionally empty for this synthetic report.")
    lines.append("")
    return "\n".join(lines)


def render_live_markdown(payload: Mapping[str, Any]) -> str:
    run = payload["run_metadata"]
    selector = payload["selector"]
    result = payload["node_result_summaries"][0]
    lines: list[str] = []
    lines.append("# Automation Hub Live Report")
    lines.append("")
    lines.append(f"- Run ID: `{run['run_id']}`")
    lines.append(f"- Generated: `{run['generated_at']}`")
    lines.append("- Suite: `extended`")
    lines.append(f"- Selector: `{selector['type']}`")
    lines.append(f"- Selector value: `{selector['value']}`")
    lines.append(f"- Endpoint calls: `{run['endpoint_call_count']}`")
    lines.append(f"- Notice: {run['notice']}")
    lines.append("")
    lines.append("## Result")
    lines.append("")
    lines.append("| node | method | path | status | duration ms | outcome | rerun selector |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    lines.append(
        f"| `{result['node_id']}` | `{result['method']}` | `{result['path']}` | "
        f"`{result['status_code']}` | `{result['duration_ms']}` | `{result['outcome']}` | "
        f"`{result['rerun_selector']}` |"
    )
    lines.append("")
    lines.append("## Metadata Policy")
    lines.append("")
    lines.append("- Raw request bodies and raw response bodies are not persisted.")
    lines.append("- Request headers, auth material, cookies, tenant/API keys, document identifiers, GCS object names, fraud details, and artifact/export payloads are excluded.")
    lines.append("- Safe response metadata is limited to status code and allowlisted headers such as content-type.")
    lines.append("")
    return "\n".join(lines)


def _selector_metadata(*, hub_node: str, hub_group: str) -> dict[str, str | None]:
    node_selector = hub_node.strip()
    group_selector = hub_group.strip()
    if node_selector:
        return {"type": "hub-node", "value": node_selector}
    if group_selector:
        return {"type": "hub-group", "value": group_selector}
    return {"type": "full", "value": None}


def _node_payload(node: HubNode, selection: HubNodeSelection) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "inclusion": _inclusion_label(node, selection),
        "endpoint_group": node.endpoint_group,
        "endpoint_label": node.endpoint_label,
        "status": node.status,
        "execution_availability": node.execution_availability,
        "dependencies": list(node.dependencies),
        "consumes": [
            {"name": item.name, "source_node_id": item.source_node_id, "required": item.required}
            for item in node.consumes
        ],
        "produces": [
            {
                "name": output.name,
                "description": output.description,
                "sensitivity": output.sensitivity,
            }
            for output in node.produces
        ],
        "artifact_policy": {
            "response_body_policy": node.artifact_policy.response_body_policy,
            "raw_body_persistence": node.artifact_policy.raw_body_persistence,
            "raw_body_allowed": node.artifact_policy.raw_body_allowed,
            "notes": list(node.artifact_policy.notes),
        },
        "rerun_selector": node.rerun_selector,
        "notes": list(node.notes),
    }


def _inclusion_label(node: HubNode, selection: HubNodeSelection) -> str:
    if not selection.is_filtered:
        return "selected manifest node"
    if node.node_id in selection.prerequisite_node_ids:
        if selection.selector_label.startswith("--hub-group "):
            return "prerequisite for selected endpoint group"
        return "prerequisite for selected node"
    if selection.selector_label.startswith("--hub-group "):
        return "selected endpoint-group node"
    return "selected node"


def _format_names(items: list[Mapping[str, Any]]) -> str:
    if not items:
        return "`none`"
    return ", ".join(f"`{item['name']}`" for item in items)


def _safe_response_headers(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    content_type = value.get("content-type") or value.get("Content-Type")
    if content_type is None:
        return {}
    return {"content-type": str(content_type)}


def _sanitize_report_metadata(value: Any) -> Any:
    return _exclude_report_only_fields(redact_evidence_metadata(value))


def _exclude_report_only_fields(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            if _normalize_key(str(key)).startswith("fraud"):
                sanitized[str(key)] = EXCLUDED_BY_POLICY
            else:
                sanitized[str(key)] = _exclude_report_only_fields(child)
        return sanitized
    if isinstance(value, list):
        return [_exclude_report_only_fields(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_exclude_report_only_fields(item) for item in value)
    return value


def _normalize_key(key: str) -> str:
    return "".join(char for char in key.lower() if char.isalnum())


def _failure_payload(endpoint_result: Mapping[str, Any], result_summary: Mapping[str, Any]) -> dict[str, Any]:
    status_code = result_summary["status_code"]
    expected_status_code = result_summary["expected_status_code"]
    failure_type = "unexpected_status_code" if status_code is not None else "request_error"
    payload: dict[str, Any] = {
        "node_id": result_summary["node_id"],
        "type": str(endpoint_result.get("failure_type") or failure_type),
        "outcome": result_summary["outcome"],
        "status_code": status_code,
        "expected_status_code": expected_status_code,
    }
    if endpoint_result.get("error_type"):
        payload["error_type"] = str(endpoint_result["error_type"])
    return payload


def _default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
