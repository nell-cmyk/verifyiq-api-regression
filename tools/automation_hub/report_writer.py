"""Synthetic report writer for non-live Automation Hub dry-run plans."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from tools.automation_hub.manifest import (
    DEFAULT_HUB_MANIFEST,
    HubNode,
    HubNodeSelection,
)
from tools.automation_hub.reporting import (
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
        "sanitized_metadata": redact_evidence_metadata(dict(extra_metadata or {})),
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


def _default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
