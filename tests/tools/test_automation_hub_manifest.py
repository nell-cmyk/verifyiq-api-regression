from __future__ import annotations

import pytest

from tools.automation_hub import manifest
from tools.automation_hub.reporting import metadata_only_policy


def _node(
    node_id: str,
    *,
    endpoint_group: str = "test-group",
    dependencies: tuple[str, ...] = (),
    produces: tuple[manifest.NamedOutput, ...] = (),
    consumes: tuple[manifest.NamedInput, ...] = (),
) -> manifest.HubNode:
    return manifest.HubNode(
        node_id=node_id,
        endpoint_group=endpoint_group,
        endpoint_label=f"{node_id} label",
        status=manifest.STATUS_SAFE_CANDIDATE,
        dependencies=dependencies,
        produces=produces,
        consumes=consumes,
        artifact_policy=metadata_only_policy(),
        execution_availability=manifest.EXECUTION_DRY_RUN_ONLY,
        rerun_selector="dry-run-only",
    )


def test_default_manifest_orders_producer_before_dependency_consumer() -> None:
    ordered = manifest.DEFAULT_HUB_MANIFEST.ordered_nodes()
    node_ids = [node.node_id for node in ordered]

    assert node_ids.index("document-processing.fraud-status.producer") < node_ids.index(
        "document-processing.fraud-status.consumer"
    )
    assert all(node.status in manifest.HUB_PLANNING_STATUSES for node in ordered)
    assert any(node.endpoint_group == "parse" for node in ordered)
    assert any(node.endpoint_group == "batch" for node in ordered)


def test_extended_dry_run_text_documents_dependency_and_reporting_contract() -> None:
    text = manifest.render_extended_dry_run()

    assert "Selection: suite=extended" in text
    assert "Hub selector:" not in text
    assert (
        "Live execution: approved only for --hub-node get-smoke.health.core "
        "or --hub-node get-smoke.health.ready"
    ) in text
    assert "Dependency order:" in text
    assert "fraud_status.job_reference from document-processing.fraud-status.producer" in text
    assert "failed producer -> dependent consumers skipped as dependency failed" in text
    assert "successful producer with no safe usable value -> dependent consumers skipped as missing prerequisite" in text
    assert "required sections: run_metadata, selected_nodes" in text
    assert "Raw response bodies are not automatically persisted" in text
    assert "get-smoke.health.core and get-smoke.health.ready are the only approved live hub nodes" in text


def test_default_manifest_marks_only_split_health_nodes_live_capable() -> None:
    live_nodes = manifest.live_capable_nodes()

    assert [node.node_id for node in live_nodes] == [
        "get-smoke.health.core",
        "get-smoke.health.ready",
    ]
    assert live_nodes[0].endpoint_label == "GET /health"
    assert live_nodes[1].endpoint_label == "GET /health/ready"
    assert all(node.execution_availability == manifest.EXECUTION_LIVE_APPROVED for node in live_nodes)
    assert manifest.live_capable_node_ids() == frozenset(
        ("get-smoke.health.core", "get-smoke.health.ready")
    )
    assert not manifest.is_live_capable_node("get-smoke.safe-read-only")
    assert not manifest.is_live_capable_node("get-smoke.health.live")


def test_node_selector_filters_to_selected_node_without_dependencies() -> None:
    selection = manifest.DEFAULT_HUB_MANIFEST.select_nodes(hub_node="get-smoke.safe-read-only")

    assert [node.node_id for node in selection.nodes] == ["get-smoke.safe-read-only"]
    assert selection.selected_node_ids == frozenset(("get-smoke.safe-read-only",))
    assert selection.prerequisite_node_ids == frozenset()


def test_node_selector_includes_prerequisite_closure_for_dependency_consumer() -> None:
    selection = manifest.DEFAULT_HUB_MANIFEST.select_nodes(
        hub_node="document-processing.fraud-status.consumer"
    )

    assert [node.node_id for node in selection.nodes] == [
        "document-processing.fraud-status.producer",
        "document-processing.fraud-status.consumer",
    ]
    assert selection.selected_node_ids == frozenset(("document-processing.fraud-status.consumer",))
    assert selection.prerequisite_node_ids == frozenset(("document-processing.fraud-status.producer",))


def test_group_selector_filters_to_matching_endpoint_group_nodes() -> None:
    selection = manifest.DEFAULT_HUB_MANIFEST.select_nodes(hub_group="get-smoke")

    assert [node.node_id for node in selection.nodes] == [
        "get-smoke.health.core",
        "get-smoke.health.ready",
        "get-smoke.safe-read-only",
    ]
    assert selection.selected_node_ids == frozenset(
        ("get-smoke.health.core", "get-smoke.health.ready", "get-smoke.safe-read-only")
    )
    assert selection.prerequisite_node_ids == frozenset()


def test_group_selector_includes_required_prerequisites_from_other_groups() -> None:
    nodes = (
        _node(
            "shared.producer",
            endpoint_group="shared",
            produces=(manifest.NamedOutput(name="shared.output", description="Shared output"),),
        ),
        _node(
            "selected.consumer",
            endpoint_group="selected",
            dependencies=("shared.producer",),
            consumes=(manifest.NamedInput(name="shared.output", source_node_id="shared.producer"),),
        ),
    )

    selection = manifest.select_nodes(nodes, hub_group="selected")

    assert [node.node_id for node in selection.nodes] == ["shared.producer", "selected.consumer"]
    assert selection.selected_node_ids == frozenset(("selected.consumer",))
    assert selection.prerequisite_node_ids == frozenset(("shared.producer",))


def test_filtered_dry_run_text_labels_selected_and_prerequisite_nodes() -> None:
    text = manifest.render_extended_dry_run(hub_node="document-processing.fraud-status.consumer")

    assert "Hub selector: --hub-node document-processing.fraud-status.consumer" in text
    assert "Selection scope: selected node plus required prerequisite closure." in text
    assert "1. document-processing.fraud-status.producer" in text
    assert "   inclusion: prerequisite for selected node" in text
    assert "2. document-processing.fraud-status.consumer" in text
    assert "   inclusion: selected node" in text
    assert "parse.protected" not in text


def test_unknown_node_selector_is_rejected() -> None:
    with pytest.raises(manifest.ManifestSelectionError, match="Unknown hub node id"):
        manifest.DEFAULT_HUB_MANIFEST.select_nodes(hub_node="missing.node")


def test_unknown_group_selector_is_rejected() -> None:
    with pytest.raises(manifest.ManifestSelectionError, match="Unknown hub endpoint group"):
        manifest.DEFAULT_HUB_MANIFEST.select_nodes(hub_group="missing-group")


def test_node_and_group_selectors_are_mutually_exclusive() -> None:
    with pytest.raises(manifest.ManifestSelectionError, match="mutually exclusive"):
        manifest.DEFAULT_HUB_MANIFEST.select_nodes(
            hub_node="get-smoke.safe-read-only",
            hub_group="get-smoke",
        )


def test_unknown_dependency_is_rejected() -> None:
    with pytest.raises(manifest.ManifestValidationError, match="Unknown dependency"):
        manifest.order_nodes((_node("consumer", dependencies=("missing.producer",)),))


def test_dependency_cycles_are_rejected() -> None:
    nodes = (
        _node("producer", dependencies=("consumer",)),
        _node("consumer", dependencies=("producer",)),
    )

    with pytest.raises(manifest.ManifestValidationError, match="Cycle detected"):
        manifest.order_nodes(nodes)


def test_consumed_output_must_be_produced_by_declared_prerequisite() -> None:
    nodes = (
        _node(
            "producer",
            produces=(manifest.NamedOutput(name="known.output", description="Known output"),),
        ),
        _node(
            "consumer",
            dependencies=("producer",),
            consumes=(manifest.NamedInput(name="missing.output", source_node_id="producer"),),
        ),
    )

    with pytest.raises(manifest.ManifestValidationError, match="consumes unknown named output"):
        manifest.order_nodes(nodes)


def test_consumed_output_source_must_be_a_prerequisite() -> None:
    nodes = (
        _node(
            "producer",
            produces=(manifest.NamedOutput(name="known.output", description="Known output"),),
        ),
        _node(
            "consumer",
            consumes=(manifest.NamedInput(name="known.output", source_node_id="producer"),),
        ),
    )

    with pytest.raises(manifest.ManifestValidationError, match="without declaring it as a prerequisite"):
        manifest.order_nodes(nodes)
