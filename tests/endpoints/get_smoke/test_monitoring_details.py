from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import GetSmokeCase, assert_get_smoke_200, get_smoke_json


_REQUESTS_CASE = GetSmokeCase("monitoring-requests", "/monitoring/api/v1/requests")
_GOLDEN_DATASET_CASE = GetSmokeCase("monitoring-golden-dataset", "/monitoring/api/v1/golden-dataset")
_GROUND_TRUTH_DOC_TYPES_CASE = GetSmokeCase(
    "monitoring-ground-truth-document-types", "/monitoring/api/v1/ground-truth/document-types"
)
_GCS_TYPES_CASE = GetSmokeCase("monitoring-gcs-types", "/monitoring/api/v1/golden-dataset/gcs/types")


@pytest.fixture(scope="module")
def monitoring_correlation_id(client) -> str:
    body = get_smoke_json(client, _REQUESTS_CASE)
    items = body.get("items")
    assert isinstance(items, list) and items, "Monitoring requests response did not contain any items."
    correlation_id = str(items[0].get("correlation_id", "")).strip() if isinstance(items[0], dict) else ""
    assert correlation_id, "Monitoring requests response did not include correlation_id for the first item."
    return correlation_id


@pytest.fixture(scope="module")
def monitoring_golden_doc_id(client) -> str:
    body = get_smoke_json(client, _GOLDEN_DATASET_CASE)
    docs = body.get("items") or body.get("documents") or body.get("data")
    assert isinstance(docs, list) and docs, "Monitoring golden-dataset response did not contain any documents."
    first = docs[0]
    assert isinstance(first, dict), "Monitoring golden-dataset first document was not an object."
    for key in ("doc_id", "document_id", "id"):
        value = str(first.get(key, "")).strip()
        if value:
            return value
    pytest.fail("Monitoring golden-dataset response did not include a document id for the first document.")


@pytest.fixture(scope="module")
def monitoring_document_type(client) -> str:
    body = get_smoke_json(client, _GROUND_TRUTH_DOC_TYPES_CASE)
    assert isinstance(body, dict) and body, "Ground-truth document-types response did not contain any categories."

    for values in body.values():
        if not isinstance(values, list) or not values:
            continue
        first = values[0]
        if isinstance(first, dict):
            for key in ("name", "document_type", "doc_type"):
                value = str(first.get(key, "")).strip()
                if value:
                    return value
        elif isinstance(first, str) and first.strip():
            return first.strip()

    pytest.fail("Ground-truth document-types response did not contain any usable document type names.")


@pytest.fixture(scope="module")
def monitoring_gcs_category(client) -> str:
    body = get_smoke_json(client, _GCS_TYPES_CASE)
    categories = body.get("types")
    assert isinstance(categories, list) and categories, "Monitoring GCS types response did not contain any types."
    category = str(categories[0]).strip()
    assert category, "Monitoring GCS types response returned an empty category value."
    return category


@pytest.fixture(scope="module")
def monitoring_gcs_variant(client, monitoring_gcs_category: str) -> str:
    body = get_smoke_json(
        client,
        GetSmokeCase(
            "monitoring-gcs-variants",
            f"/monitoring/api/v1/golden-dataset/gcs/types/{monitoring_gcs_category}/variants",
        ),
    )
    variants = body.get("variants")
    assert isinstance(variants, list) and variants, "Monitoring GCS variants response did not contain any variants."
    variant = str(variants[0]).strip()
    assert variant, "Monitoring GCS variants response returned an empty variant value."
    return variant


@pytest.fixture(scope="module")
def monitoring_gcs_document_id(client, monitoring_gcs_category: str, monitoring_gcs_variant: str) -> str:
    body = get_smoke_json(
        client,
        GetSmokeCase(
            "monitoring-gcs-variant-documents",
            (
                f"/monitoring/api/v1/golden-dataset/gcs/types/{monitoring_gcs_category}"
                f"/variants/{monitoring_gcs_variant}/documents"
            ),
        ),
    )
    documents = body.get("documents")
    assert isinstance(documents, list) and documents, "Monitoring GCS documents response did not contain any documents."
    first = documents[0]
    assert isinstance(first, dict), "Monitoring GCS documents response first entry was not an object."
    for key in ("document_id", "id", "name"):
        value = str(first.get(key, "")).strip()
        if value:
            return value
    pytest.fail("Monitoring GCS documents response did not include a document id for the first document.")


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
