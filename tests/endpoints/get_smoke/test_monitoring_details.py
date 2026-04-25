from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import (
    GetSmokeCase,
    assert_get_smoke_200,
    first_mapping_value,
    get_smoke_json,
    require_setup_list,
)


_REQUESTS_CASE = GetSmokeCase("monitoring-requests", "/monitoring/api/v1/requests")
_GOLDEN_DATASET_CASE = GetSmokeCase("monitoring-golden-dataset", "/monitoring/api/v1/golden-dataset")
_GROUND_TRUTH_DOC_TYPES_CASE = GetSmokeCase(
    "monitoring-ground-truth-document-types", "/monitoring/api/v1/ground-truth/document-types"
)
_GCS_TYPES_CASE = GetSmokeCase("monitoring-gcs-types", "/monitoring/api/v1/golden-dataset/gcs/types")


@pytest.fixture(scope="module")
def monitoring_correlation_id(client) -> str:
    body = get_smoke_json(client, _REQUESTS_CASE)
    items = require_setup_list(
        body,
        _REQUESTS_CASE,
        fields=("items",),
        prerequisite="monitoring correlation_id",
        item_label="request",
    )
    return first_mapping_value(
        items,
        keys=("correlation_id",),
        source_case=_REQUESTS_CASE,
        prerequisite="monitoring correlation_id",
        item_label="request",
    )


@pytest.fixture(scope="module")
def monitoring_golden_doc_id(client) -> str:
    body = get_smoke_json(client, _GOLDEN_DATASET_CASE)
    docs = require_setup_list(
        body,
        _GOLDEN_DATASET_CASE,
        fields=("items", "documents", "data"),
        prerequisite="monitoring golden-dataset document id",
        item_label="golden-dataset document",
    )
    return first_mapping_value(
        docs,
        keys=("doc_id", "document_id", "id"),
        source_case=_GOLDEN_DATASET_CASE,
        prerequisite="monitoring golden-dataset document id",
        item_label="golden-dataset document",
    )


@pytest.fixture(scope="module")
def monitoring_document_type(client) -> str:
    body = get_smoke_json(client, _GROUND_TRUTH_DOC_TYPES_CASE)
    if not isinstance(body, dict):
        pytest.fail("Ground-truth document-types response was not an object.")
    if not body:
        pytest.skip(
            "Skipping setup-backed detail GET smoke: missing prerequisite monitoring document type; "
            f"{_GROUND_TRUTH_DOC_TYPES_CASE.path} returned no categories."
        )

    saw_category_values = False
    for category, values in body.items():
        if not isinstance(values, list):
            pytest.fail(
                "Ground-truth document-types response category "
                f"{category!r} was not a list; cannot derive monitoring document type."
            )
        if not values:
            continue
        saw_category_values = True
        for entry in values:
            if isinstance(entry, dict):
                for key in ("name", "document_type", "doc_type"):
                    value = str(entry.get(key, "")).strip()
                    if value:
                        return value
                continue
            if isinstance(entry, str) and entry.strip():
                return entry.strip()
            pytest.fail(
                "Ground-truth document-types response contained a non-object, non-string "
                f"entry in category {category!r}; cannot derive monitoring document type."
            )

    if not saw_category_values:
        pytest.skip(
            "Skipping setup-backed detail GET smoke: missing prerequisite monitoring document type; "
            f"{_GROUND_TRUTH_DOC_TYPES_CASE.path} returned empty category lists."
        )
    pytest.skip(
        "Skipping setup-backed detail GET smoke: missing prerequisite monitoring document type; "
        f"{_GROUND_TRUTH_DOC_TYPES_CASE.path} returned no usable document type names."
    )


def _first_string_item(items: list[object], *, source_case: GetSmokeCase, prerequisite: str, item_label: str) -> str:
    for index, item in enumerate(items, start=1):
        if not isinstance(item, str):
            pytest.fail(
                f"{source_case.path} {item_label} entry #{index} was not a string; "
                f"cannot derive {prerequisite}."
            )
        value = item.strip()
        if value:
            return value
    pytest.skip(
        "Skipping setup-backed detail GET smoke: "
        f"missing prerequisite {prerequisite}; {source_case.path} returned no usable {item_label} values."
    )


@pytest.fixture(scope="module")
def monitoring_gcs_category(client) -> str:
    body = get_smoke_json(client, _GCS_TYPES_CASE)
    categories = require_setup_list(
        body,
        _GCS_TYPES_CASE,
        fields=("types",),
        prerequisite="monitoring GCS category",
        item_label="GCS category",
    )
    return _first_string_item(
        categories,
        source_case=_GCS_TYPES_CASE,
        prerequisite="monitoring GCS category",
        item_label="GCS category",
    )


@pytest.fixture(scope="module")
def monitoring_gcs_variant(client, monitoring_gcs_category: str) -> str:
    variants_case = GetSmokeCase(
        "monitoring-gcs-variants",
        f"/monitoring/api/v1/golden-dataset/gcs/types/{monitoring_gcs_category}/variants",
    )
    body = get_smoke_json(client, variants_case)
    variants = require_setup_list(
        body,
        variants_case,
        fields=("variants",),
        prerequisite="monitoring GCS variant",
        item_label="GCS variant",
    )
    return _first_string_item(
        variants,
        source_case=variants_case,
        prerequisite="monitoring GCS variant",
        item_label="GCS variant",
    )


@pytest.fixture(scope="module")
def monitoring_gcs_document_id(client, monitoring_gcs_category: str, monitoring_gcs_variant: str) -> str:
    documents_case = GetSmokeCase(
        "monitoring-gcs-variant-documents",
        (
            f"/monitoring/api/v1/golden-dataset/gcs/types/{monitoring_gcs_category}"
            f"/variants/{monitoring_gcs_variant}/documents"
        ),
    )
    body = get_smoke_json(client, documents_case)
    documents = require_setup_list(
        body,
        documents_case,
        fields=("documents",),
        prerequisite="monitoring GCS document id",
        item_label="GCS document",
    )
    return first_mapping_value(
        documents,
        keys=("document_id", "id", "name"),
        source_case=documents_case,
        prerequisite="monitoring GCS document id",
        item_label="GCS document",
    )


@pytest.mark.parametrize(
    ("test_id", "path_template"),
    (
        ("monitoring-request-detail", "/monitoring/api/v1/requests/{correlation_id}"),
        ("monitoring-request-retests", "/monitoring/api/v1/requests/{correlation_id}/retests"),
        ("monitoring-request-document", "/monitoring/api/v1/requests/{correlation_id}/document"),
        ("monitoring-request-file", "/monitoring/api/v1/requests/{correlation_id}/file"),
        ("monitoring-request-qa-review", "/monitoring/api/v1/requests/{correlation_id}/qa-review"),
        ("monitoring-request-fields", "/monitoring/api/v1/requests/{correlation_id}/fields"),
        ("monitoring-request-golden-status", "/monitoring/api/v1/requests/{correlation_id}/golden-status"),
    ),
)
def test_monitoring_request_detail_get_smoke_returns_200(
    client,
    monitoring_correlation_id: str,
    test_id: str,
    path_template: str,
):
    assert_get_smoke_200(client, GetSmokeCase(test_id, path_template.format(correlation_id=monitoring_correlation_id)))


@pytest.mark.parametrize(
    ("test_id", "path_template"),
    (
        ("monitoring-golden-doc-detail", "/monitoring/api/v1/golden-dataset/{doc_id}"),
        ("monitoring-golden-doc-file", "/monitoring/api/v1/golden-dataset/{doc_id}/file"),
    ),
)
def test_monitoring_golden_dataset_detail_get_smoke_returns_200(
    client,
    monitoring_golden_doc_id: str,
    test_id: str,
    path_template: str,
):
    assert_get_smoke_200(client, GetSmokeCase(test_id, path_template.format(doc_id=monitoring_golden_doc_id)))


@pytest.mark.parametrize(
    ("test_id", "path_template"),
    (
        ("monitoring-ground-truth-schema", "/monitoring/api/v1/ground-truth/document-schema/{document_type}"),
        ("monitoring-drift-trends", "/monitoring/api/v1/drift/trends/{document_type}"),
    ),
)
def test_monitoring_document_type_detail_get_smoke_returns_200(
    client,
    monitoring_document_type: str,
    test_id: str,
    path_template: str,
):
    assert_get_smoke_200(client, GetSmokeCase(test_id, path_template.format(document_type=monitoring_document_type)))


def test_monitoring_gcs_variants_get_smoke_returns_200(client, monitoring_gcs_category: str):
    assert_get_smoke_200(
        client,
        GetSmokeCase(
            "monitoring-gcs-variants",
            f"/monitoring/api/v1/golden-dataset/gcs/types/{monitoring_gcs_category}/variants",
        ),
    )


def test_monitoring_gcs_variant_documents_get_smoke_returns_200(
    client,
    monitoring_gcs_category: str,
    monitoring_gcs_variant: str,
):
    assert_get_smoke_200(
        client,
        GetSmokeCase(
            "monitoring-gcs-variant-documents",
            (
                f"/monitoring/api/v1/golden-dataset/gcs/types/{monitoring_gcs_category}"
                f"/variants/{monitoring_gcs_variant}/documents"
            ),
        ),
    )


def test_monitoring_gcs_preview_get_smoke_returns_200(
    client,
    monitoring_gcs_category: str,
    monitoring_gcs_variant: str,
    monitoring_gcs_document_id: str,
):
    assert_get_smoke_200(
        client,
        GetSmokeCase(
            "monitoring-gcs-preview",
            (
                f"/monitoring/api/v1/golden-dataset/gcs/preview/{monitoring_gcs_category}"
                f"/{monitoring_gcs_variant}/{monitoring_gcs_document_id}"
            ),
        ),
    )


@pytest.mark.parametrize(
    "metric",
    ("requests", "errors", "latency", "latency_p95"),
)
def test_monitoring_timeseries_get_smoke_returns_200(client, metric: str):
    assert_get_smoke_200(
        client,
        GetSmokeCase(
            f"monitoring-timeseries-{metric}",
            f"/monitoring/api/v1/timeseries/{metric}",
        ),
    )
