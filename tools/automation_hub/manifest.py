"""Dependency-aware manifest for the Automation Hub.

Most hub nodes remain dry-run planning entries. A narrow approved live tranche
is represented explicitly so broad endpoint groups cannot become executable by
accident.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from tools.automation_hub.reporting import (
    ArtifactPolicy,
    default_evidence_contract,
    metadata_only_policy,
    policy_controlled_body_policy,
)


STATUS_CURRENTLY_COVERED = "currently covered"
STATUS_SAFE_CANDIDATE = "safe candidate"
STATUS_DEPENDENCY_PRODUCER = "dependency producer"
STATUS_DEPENDENCY_CONSUMER = "dependency consumer"
STATUS_LEGACY_EXCLUDED = "legacy/excluded"
STATUS_BLOCKED_DEFERRED = "blocked/deferred"
STATUS_UNKNOWN_PENDING_AUDIT = "unknown/pending audit"

HUB_PLANNING_STATUSES = (
    STATUS_CURRENTLY_COVERED,
    STATUS_SAFE_CANDIDATE,
    STATUS_DEPENDENCY_PRODUCER,
    STATUS_DEPENDENCY_CONSUMER,
    STATUS_LEGACY_EXCLUDED,
    STATUS_BLOCKED_DEFERRED,
    STATUS_UNKNOWN_PENDING_AUDIT,
)

EXECUTION_CURRENT_DELEGATED = "current delegated suite; future hub dry-run only"
EXECUTION_DRY_RUN_ONLY = "future hub dry-run only"
EXECUTION_NOT_EXECUTABLE = "not executable pending audit or approval"
EXECUTION_LIVE_APPROVED = "approved live hub execution"

APPROVED_LIVE_NODE_IDS = ("get-smoke.health.core", "get-smoke.health.ready")
APPROVED_LIVE_SELECTOR_HINT = (
    "--hub-node get-smoke.health.core or --hub-node get-smoke.health.ready"
)


class ManifestValidationError(ValueError):
    """Raised when a hub manifest cannot produce a deterministic run plan."""


class ManifestSelectionError(ValueError):
    """Raised when a requested non-live manifest slice cannot be resolved."""


@dataclass(frozen=True)
class NamedOutput:
    name: str
    description: str
    sensitivity: str = "safe_metadata"


@dataclass(frozen=True)
class NamedInput:
    name: str
    source_node_id: str
    required: bool = True


@dataclass(frozen=True)
class HubNode:
    node_id: str
    endpoint_group: str
    endpoint_label: str
    status: str
    dependencies: tuple[str, ...]
    produces: tuple[NamedOutput, ...]
    consumes: tuple[NamedInput, ...]
    artifact_policy: ArtifactPolicy
    execution_availability: str
    rerun_selector: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class HubNodeSelection:
    nodes: tuple[HubNode, ...]
    selected_node_ids: frozenset[str]
    prerequisite_node_ids: frozenset[str]
    selector_label: str = ""
    scope_label: str = "full manifest"

    @property
    def is_filtered(self) -> bool:
        return bool(self.selector_label)


@dataclass(frozen=True)
class HubManifest:
    nodes: tuple[HubNode, ...]

    def validate(self) -> None:
        validate_manifest(self.nodes)

    def ordered_nodes(self) -> tuple[HubNode, ...]:
        return order_nodes(self.nodes)

    def select_nodes(self, *, hub_node: str = "", hub_group: str = "") -> HubNodeSelection:
        return select_nodes(self.nodes, hub_node=hub_node, hub_group=hub_group)


DEFAULT_HUB_MANIFEST = HubManifest(
    nodes=(
        HubNode(
            node_id="parse.protected",
            endpoint_group="parse",
            endpoint_label="POST /v1/documents/parse protected baseline",
            status=STATUS_CURRENTLY_COVERED,
            dependencies=(),
            produces=(
                NamedOutput(
                    name="parse.protected_status_signal",
                    description="Success and validation signal from the current protected parse lane.",
                ),
            ),
            consumes=(),
            artifact_policy=policy_controlled_body_policy(
                "Current parse reporting can write raw artifacts outside the hub; future hub persistence stays policy-controlled."
            ),
            execution_availability=EXECUTION_CURRENT_DELEGATED,
            rerun_selector="./.venv/bin/python tools/run_regression.py",
            notes=("Protected remains the no-argument default and is not broadened by this dry-run plan.",),
        ),
        HubNode(
            node_id="batch.validation",
            endpoint_group="batch",
            endpoint_label="POST /v1/documents/batch validation",
            status=STATUS_CURRENTLY_COVERED,
            dependencies=(),
            produces=(
                NamedOutput(
                    name="batch.validation_status_signal",
                    description="Current opt-in batch validation and contract signal.",
                ),
            ),
            consumes=(),
            artifact_policy=policy_controlled_body_policy(
                "Current batch runs can write raw artifacts outside the hub; future hub persistence stays policy-controlled."
            ),
            execution_availability=EXECUTION_CURRENT_DELEGATED,
            rerun_selector="./.venv/bin/python tools/run_regression.py --endpoint batch",
            notes=("Batch remains opt-in and is not part of the protected default.",),
        ),
        HubNode(
            node_id="get-smoke.health.core",
            endpoint_group="get-smoke",
            endpoint_label="GET /health",
            status=STATUS_CURRENTLY_COVERED,
            dependencies=(),
            produces=(
                NamedOutput(
                    name="health.core_status_signal",
                    description="Status and safe metadata signal from the top-level health endpoint.",
                ),
            ),
            consumes=(),
            artifact_policy=metadata_only_policy(
                "Live health-node reports persist metadata only: status, timing, outcome, and content-type."
            ),
            execution_availability=EXECUTION_LIVE_APPROVED,
            rerun_selector="./.venv/bin/python tools/run_regression.py --suite extended --hub-node get-smoke.health.core",
            notes=(
                "First approved live Automation Hub node; limited to GET /health only.",
                "This node does not include /health/ready, /health/live, /health/detailed, /health/startup, or health-like routes in other groups.",
            ),
        ),
        HubNode(
            node_id="get-smoke.health.ready",
            endpoint_group="get-smoke",
            endpoint_label="GET /health/ready",
            status=STATUS_CURRENTLY_COVERED,
            dependencies=(),
            produces=(
                NamedOutput(
                    name="health.ready_status_signal",
                    description="Status and safe metadata signal from the readiness probe endpoint.",
                ),
            ),
            consumes=(),
            artifact_policy=metadata_only_policy(
                "Live readiness-node reports persist metadata only: status, timing, outcome, and content-type."
            ),
            execution_availability=EXECUTION_LIVE_APPROVED,
            rerun_selector="./.venv/bin/python tools/run_regression.py --suite extended --hub-node get-smoke.health.ready",
            notes=(
                "Second approved live Automation Hub health node; limited to GET /health/ready only.",
                "Readiness is first-party health-tagged, has no path parameters or request body, and response bodies are not persisted.",
                "This node does not include /health/live, /health/detailed, /health/startup, or health-like routes in other groups.",
            ),
        ),
        HubNode(
            node_id="get-smoke.health.live",
            endpoint_group="get-smoke",
            endpoint_label="GET /health/live",
            status=STATUS_SAFE_CANDIDATE,
            dependencies=(),
            produces=(
                NamedOutput(
                    name="health.live_status_signal",
                    description="Candidate-only status and safe metadata signal from the liveness probe endpoint.",
                ),
            ),
            consumes=(),
            artifact_policy=metadata_only_policy(
                "Candidate health-sibling reports must remain metadata-only and must not persist probe response bodies."
            ),
            execution_availability=EXECUTION_DRY_RUN_ONLY,
            rerun_selector="./.venv/bin/python tools/run_regression.py --suite smoke --k live",
            notes=(
                "Candidate-only health sibling; not approved for live Automation Hub execution.",
                "Current live fallback remains the opt-in GET smoke lane until smoke-to-extended gates are complete.",
            ),
        ),
        HubNode(
            node_id="get-smoke.health.detailed",
            endpoint_group="get-smoke",
            endpoint_label="GET /health/detailed",
            status=STATUS_SAFE_CANDIDATE,
            dependencies=(),
            produces=(
                NamedOutput(
                    name="health.detailed_status_signal",
                    description="Candidate-only status and safe metadata signal from the detailed health probe endpoint.",
                ),
            ),
            consumes=(),
            artifact_policy=metadata_only_policy(
                "Candidate health-sibling reports must remain metadata-only and must not persist probe response bodies."
            ),
            execution_availability=EXECUTION_DRY_RUN_ONLY,
            rerun_selector="./.venv/bin/python tools/run_regression.py --suite smoke --k detailed",
            notes=(
                "Candidate-only health sibling; not approved for live Automation Hub execution.",
                "Current live fallback remains the opt-in GET smoke lane until smoke-to-extended gates are complete.",
            ),
        ),
        HubNode(
            node_id="get-smoke.health.startup",
            endpoint_group="get-smoke",
            endpoint_label="GET /health/startup",
            status=STATUS_SAFE_CANDIDATE,
            dependencies=(),
            produces=(
                NamedOutput(
                    name="health.startup_status_signal",
                    description="Candidate-only status and safe metadata signal from the startup health probe endpoint.",
                ),
            ),
            consumes=(),
            artifact_policy=metadata_only_policy(
                "Candidate health-sibling reports must remain metadata-only and must not persist probe response bodies."
            ),
            execution_availability=EXECUTION_DRY_RUN_ONLY,
            rerun_selector="./.venv/bin/python tools/run_regression.py --suite smoke --k startup",
            notes=(
                "Candidate-only health sibling; not approved for live Automation Hub execution.",
                "Current live fallback remains the opt-in GET smoke lane until smoke-to-extended gates are complete.",
            ),
        ),
        HubNode(
            node_id="get-smoke.safe-read-only",
            endpoint_group="get-smoke",
            endpoint_label="Delegated opt-in safe GET smoke groups outside approved health core",
            status=STATUS_CURRENTLY_COVERED,
            dependencies=(),
            produces=(
                NamedOutput(
                    name="get_smoke.delegated_status_signal",
                    description="Status and top-level shape signal from the current opt-in GET smoke lane outside the approved hub health node.",
                ),
            ),
            consumes=(),
            artifact_policy=metadata_only_policy("GET smoke should avoid raw response artifact persistence."),
            execution_availability=EXECUTION_CURRENT_DELEGATED,
            rerun_selector="./.venv/bin/python tools/run_regression.py --suite smoke",
            notes=(
                "The broad GET smoke lane remains delegated and is not a live-executable hub unit.",
                "Other GET smoke groups stay non-live in the hub manifest until split and approved separately.",
            ),
        ),
        HubNode(
            node_id="document-processing.fraud-status.producer",
            endpoint_group="document-processing-adjacent",
            endpoint_label="Fraud-status setup producer through bounded parse setup",
            status=STATUS_DEPENDENCY_PRODUCER,
            dependencies=(),
            produces=(
                NamedOutput(
                    name="fraud_status.job_reference",
                    description="Safe alias for a tenant-scoped fraud-status prerequisite.",
                    sensitivity="sensitive_alias_only",
                ),
            ),
            consumes=(),
            artifact_policy=metadata_only_policy(
                "Producer output must be represented as a named alias, not a raw response value."
            ),
            execution_availability=EXECUTION_DRY_RUN_ONLY,
            rerun_selector="./.venv/bin/python tools/run_regression.py --suite smoke -k fraud_status",
            notes=(
                "This models the current provisional setup-backed smoke pattern without making hub execution live.",
            ),
        ),
        HubNode(
            node_id="document-processing.fraud-status.consumer",
            endpoint_group="document-processing-adjacent",
            endpoint_label="GET /v1/documents/fraud-status/{job_id} top-level status check",
            status=STATUS_DEPENDENCY_CONSUMER,
            dependencies=("document-processing.fraud-status.producer",),
            produces=(
                NamedOutput(
                    name="fraud_status.top_level_status_signal",
                    description="Safe top-level status metadata from the fraud-status consumer.",
                ),
            ),
            consumes=(
                NamedInput(
                    name="fraud_status.job_reference",
                    source_node_id="document-processing.fraud-status.producer",
                ),
            ),
            artifact_policy=metadata_only_policy(
                "Fraud results and deep terminal response bodies are excluded unless separately approved."
            ),
            execution_availability=EXECUTION_DRY_RUN_ONLY,
            rerun_selector="./.venv/bin/python tools/run_regression.py --suite smoke -k fraud_status",
            notes=(
                "If the producer fails, this consumer is skipped as dependency failed.",
                "If the producer succeeds without a safe usable value, this consumer is skipped as missing prerequisite.",
            ),
        ),
    )
)


def live_capable_nodes(manifest: HubManifest = DEFAULT_HUB_MANIFEST) -> tuple[HubNode, ...]:
    """Return the manifest nodes approved for live Automation Hub execution."""

    approved = set(APPROVED_LIVE_NODE_IDS)
    return tuple(node for node in manifest.ordered_nodes() if node.node_id in approved)


def live_capable_node_ids(manifest: HubManifest = DEFAULT_HUB_MANIFEST) -> frozenset[str]:
    return frozenset(node.node_id for node in live_capable_nodes(manifest))


def is_live_capable_node(node_id: str, manifest: HubManifest = DEFAULT_HUB_MANIFEST) -> bool:
    return node_id in live_capable_node_ids(manifest)


def validate_manifest(nodes: Iterable[HubNode]) -> None:
    node_tuple = tuple(nodes)
    by_id = _nodes_by_id(node_tuple)
    _validate_statuses(node_tuple)
    _validate_dependencies(node_tuple, by_id)
    ordered = _order_nodes(node_tuple, by_id)
    _validate_named_inputs(ordered, by_id)


def order_nodes(nodes: Iterable[HubNode]) -> tuple[HubNode, ...]:
    node_tuple = tuple(nodes)
    by_id = _nodes_by_id(node_tuple)
    _validate_statuses(node_tuple)
    _validate_dependencies(node_tuple, by_id)
    ordered = _order_nodes(node_tuple, by_id)
    _validate_named_inputs(ordered, by_id)
    return ordered


def select_nodes(
    nodes: Iterable[HubNode],
    *,
    hub_node: str = "",
    hub_group: str = "",
) -> HubNodeSelection:
    node_selector = hub_node.strip()
    group_selector = hub_group.strip()
    if node_selector and group_selector:
        raise ManifestSelectionError("--hub-node and --hub-group are mutually exclusive.")

    ordered_nodes = order_nodes(nodes)
    by_id = _nodes_by_id(ordered_nodes)

    if node_selector:
        if node_selector not in by_id:
            raise ManifestSelectionError(f"Unknown hub node id for --hub-node: {node_selector}")
        prerequisite_ids = frozenset(_dependency_closure(by_id[node_selector], by_id))
        selected_ids = frozenset((node_selector,))
        included_ids = selected_ids | prerequisite_ids
        return HubNodeSelection(
            nodes=tuple(node for node in ordered_nodes if node.node_id in included_ids),
            selected_node_ids=selected_ids,
            prerequisite_node_ids=prerequisite_ids,
            selector_label=f"--hub-node {node_selector}",
            scope_label="selected node plus required prerequisite closure",
        )

    if group_selector:
        selected_ids = frozenset(
            node.node_id for node in ordered_nodes if node.endpoint_group == group_selector
        )
        if not selected_ids:
            raise ManifestSelectionError(f"Unknown hub endpoint group for --hub-group: {group_selector}")
        prerequisite_ids = frozenset(
            dependency_id
            for node_id in selected_ids
            for dependency_id in _dependency_closure(by_id[node_id], by_id)
            if dependency_id not in selected_ids
        )
        included_ids = selected_ids | prerequisite_ids
        return HubNodeSelection(
            nodes=tuple(node for node in ordered_nodes if node.node_id in included_ids),
            selected_node_ids=selected_ids,
            prerequisite_node_ids=prerequisite_ids,
            selector_label=f"--hub-group {group_selector}",
            scope_label="endpoint-group nodes plus required prerequisite closure",
        )

    return HubNodeSelection(
        nodes=ordered_nodes,
        selected_node_ids=frozenset(node.node_id for node in ordered_nodes),
        prerequisite_node_ids=frozenset(),
    )


def render_extended_dry_run(*, hub_node: str = "", hub_group: str = "") -> str:
    manifest = DEFAULT_HUB_MANIFEST
    selection = manifest.select_nodes(hub_node=hub_node, hub_group=hub_group)
    ordered_nodes = selection.nodes
    contract = default_evidence_contract()

    lines: list[str] = []
    lines.append("Selection: suite=extended")
    if selection.is_filtered:
        lines.append(f"Hub selector: {selection.selector_label}")
        lines.append(f"Selection scope: {selection.scope_label}.")
    lines.append("Description: Planned Automation Hub dependency graph preview.")
    lines.append(
        f"Live execution: approved only for {APPROVED_LIVE_SELECTOR_HINT}; "
        "this dry-run performs no endpoint calls."
    )
    lines.append("")
    lines.append("Dependency order:")
    for index, node in enumerate(ordered_nodes, start=1):
        lines.append(f"{index}. {node.node_id}")
        inclusion = _format_inclusion(node, selection)
        if inclusion:
            lines.append(f"   inclusion: {inclusion}")
        lines.append(f"   endpoint group: {node.endpoint_group}")
        lines.append(f"   label: {node.endpoint_label}")
        lines.append(f"   status: {node.status}")
        lines.append(f"   execution availability: {node.execution_availability}")
        lines.append(f"   depends on: {_format_items(node.dependencies)}")
        lines.append(f"   consumes: {_format_inputs(node.consumes)}")
        lines.append(f"   produces: {_format_outputs(node.produces)}")
        lines.append(
            "   artifact policy: "
            f"response_body={node.artifact_policy.response_body_policy}; "
            f"raw_body_persistence={node.artifact_policy.raw_body_persistence}"
        )
        lines.append(f"   rerun selector: {node.rerun_selector}")
        if node.notes:
            lines.append("   notes:")
            for note in node.notes:
                lines.append(f"     - {note}")
    lines.append("")
    lines.append("Dependency semantics:")
    lines.append("- named outputs are published into a run context; consumers request names, not raw response bodies")
    lines.append("- failed producer -> dependent consumers skipped as dependency failed")
    lines.append("- successful producer with no safe usable value -> dependent consumers skipped as missing prerequisite")
    lines.append("- unrelated independent nodes may continue")
    lines.append("")
    lines.append("Reporting contract scaffold:")
    lines.append(f"- required sections: {', '.join(contract.required_sections)}")
    lines.append(f"- redaction/exclusion: {', '.join(contract.redaction_exclusions)}")
    lines.append(f"- raw response bodies: {contract.raw_response_body_policy}")
    lines.append("")
    lines.append("Notes:")
    lines.append("- this is an endpoint-group oriented plan, not a path-by-path coverage matrix")
    lines.append(
        "- get-smoke.health.core and get-smoke.health.ready are the only approved live hub nodes; "
        "they represent GET /health and GET /health/ready only"
    )
    lines.append("- legacy, unsafe, admin, destructive, internal/debug, storage-risk, artifact-risk, auth-blocked, owner-unconfirmed, setup-dependent, and unknown groups remain outside live hub scope until approved")
    return "\n".join(lines) + "\n"


def _nodes_by_id(nodes: tuple[HubNode, ...]) -> dict[str, HubNode]:
    by_id: dict[str, HubNode] = {}
    for node in nodes:
        if node.node_id in by_id:
            raise ManifestValidationError(f"Duplicate hub node id: {node.node_id}")
        by_id[node.node_id] = node
    return by_id


def _validate_statuses(nodes: tuple[HubNode, ...]) -> None:
    for node in nodes:
        if node.status not in HUB_PLANNING_STATUSES:
            raise ManifestValidationError(f"Unknown hub planning status for {node.node_id}: {node.status}")


def _validate_dependencies(nodes: tuple[HubNode, ...], by_id: dict[str, HubNode]) -> None:
    for node in nodes:
        for dependency in node.dependencies:
            if dependency not in by_id:
                raise ManifestValidationError(f"Unknown dependency for {node.node_id}: {dependency}")


def _order_nodes(nodes: tuple[HubNode, ...], by_id: dict[str, HubNode]) -> tuple[HubNode, ...]:
    ordered: list[HubNode] = []
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(node: HubNode) -> None:
        if node.node_id in permanent:
            return
        if node.node_id in temporary:
            raise ManifestValidationError(f"Cycle detected at hub node: {node.node_id}")
        temporary.add(node.node_id)
        for dependency_id in node.dependencies:
            visit(by_id[dependency_id])
        temporary.remove(node.node_id)
        permanent.add(node.node_id)
        ordered.append(node)

    for node in nodes:
        visit(node)
    return tuple(ordered)


def _validate_named_inputs(nodes: tuple[HubNode, ...], by_id: dict[str, HubNode]) -> None:
    predecessors_by_node = {node.node_id: _dependency_closure(node, by_id) for node in nodes}
    outputs_by_node = {
        node.node_id: {output.name for output in node.produces}
        for node in nodes
    }

    for node in nodes:
        for consumed in node.consumes:
            if consumed.source_node_id not in by_id:
                raise ManifestValidationError(
                    f"{node.node_id} consumes {consumed.name} from unknown node {consumed.source_node_id}"
                )
            if consumed.source_node_id not in predecessors_by_node[node.node_id]:
                raise ManifestValidationError(
                    f"{node.node_id} consumes {consumed.name} from {consumed.source_node_id} "
                    "without declaring it as a prerequisite"
                )
            if consumed.name not in outputs_by_node[consumed.source_node_id]:
                raise ManifestValidationError(
                    f"{node.node_id} consumes unknown named output {consumed.name} "
                    f"from {consumed.source_node_id}"
                )


def _dependency_closure(node: HubNode, by_id: dict[str, HubNode]) -> set[str]:
    seen: set[str] = set()

    def collect(current: HubNode) -> None:
        for dependency_id in current.dependencies:
            if dependency_id in seen:
                continue
            seen.add(dependency_id)
            collect(by_id[dependency_id])

    collect(node)
    return seen


def _format_items(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else "none"


def _format_outputs(outputs: tuple[NamedOutput, ...]) -> str:
    if not outputs:
        return "none"
    return ", ".join(output.name for output in outputs)


def _format_inputs(inputs: tuple[NamedInput, ...]) -> str:
    if not inputs:
        return "none"
    return ", ".join(f"{item.name} from {item.source_node_id}" for item in inputs)


def _format_inclusion(node: HubNode, selection: HubNodeSelection) -> str:
    if not selection.is_filtered:
        return ""
    if node.node_id in selection.prerequisite_node_ids:
        if selection.selector_label.startswith("--hub-group "):
            return "prerequisite for selected endpoint group"
        return "prerequisite for selected node"
    if selection.selector_label.startswith("--hub-group "):
        return "selected endpoint-group node"
    return "selected node"
