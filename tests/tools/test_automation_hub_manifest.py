from __future__ import annotations

import pytest

from tools.automation_hub import manifest
from tools.automation_hub.reporting import metadata_only_policy


def _node(
    node_id: str,
    *,
    dependencies: tuple[str, ...] = (),
    produces: tuple[manifest.NamedOutput, ...] = (),
    consumes: tuple[manifest.NamedInput, ...] = (),
) -> manifest.HubNode:
    return manifest.HubNode(
        node_id=node_id,
        endpoint_group="test-group",
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
    assert "Live execution: not implemented" in text
    assert "Dependency order:" in text
    assert "fraud_status.job_reference from document-processing.fraud-status.producer" in text
    assert "failed producer -> dependent consumers skipped as dependency failed" in text
    assert "successful producer with no safe usable value -> dependent consumers skipped as missing prerequisite" in text
    assert "required sections: run_metadata, selected_nodes" in text
    assert "Raw response bodies are not automatically persisted" in text


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
