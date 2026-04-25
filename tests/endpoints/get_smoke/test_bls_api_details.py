from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import (
    GetSmokeCase,
    assert_get_smoke_200,
    first_mapping_value,
    get_smoke_json,
    require_setup_list,
)


_BENCHMARK_JOBS_CASE = GetSmokeCase("benchmark-jobs-list", "/api/v1/benchmark/jobs")
_APPLICATIONS_CASE = GetSmokeCase("bls-applications-list", "/api/v1/applications/")


@pytest.fixture(scope="module")
def benchmark_job_id(client) -> str:
    body = get_smoke_json(client, _BENCHMARK_JOBS_CASE)
    jobs = require_setup_list(
        body,
        _BENCHMARK_JOBS_CASE,
        fields=("jobs",),
        prerequisite="benchmark job_id",
        item_label="benchmark job",
    )
    return first_mapping_value(
        jobs,
        keys=("job_id",),
        source_case=_BENCHMARK_JOBS_CASE,
        prerequisite="benchmark job_id",
        item_label="benchmark job",
    )


@pytest.fixture(scope="module")
def application_id(client) -> str:
    body = get_smoke_json(client, _APPLICATIONS_CASE)
    items = require_setup_list(
        body,
        _APPLICATIONS_CASE,
        fields=("items",),
        prerequisite="applicationId",
        item_label="application",
    )
    return first_mapping_value(
        items,
        keys=("applicationId",),
        source_case=_APPLICATIONS_CASE,
        prerequisite="applicationId",
        item_label="application",
    )


@pytest.fixture(scope="module")
def application_document_id(client, application_id: str) -> str:
    documents_case = GetSmokeCase("bls-application-documents", f"/api/v1/applications/{application_id}/documents")
    body = get_smoke_json(
        client,
        documents_case,
    )
    items = require_setup_list(
        body,
        documents_case,
        fields=("items", "documents", "data"),
        prerequisite="application document id",
        item_label="application document",
    )
    return first_mapping_value(
        items,
        keys=("documentId", "document_id", "id"),
        source_case=documents_case,
        prerequisite="application document id",
        item_label="application document",
    )


@pytest.mark.parametrize(
    ("test_id", "path_template"),
    (
        ("benchmark-status", "/api/v1/benchmark/{job_id}/status"),
        ("benchmark-result", "/api/v1/benchmark/{job_id}/result"),
        ("benchmark-preview", "/api/v1/benchmark/{job_id}/preview"),
    ),
)
def test_benchmark_detail_get_smoke_returns_200(client, benchmark_job_id: str, test_id: str, path_template: str):
    assert_get_smoke_200(client, GetSmokeCase(test_id, path_template.format(job_id=benchmark_job_id)))


@pytest.mark.parametrize(
    ("test_id", "path_template"),
    (
        ("bls-application-detail", "/api/v1/applications/{application_id}"),
        ("bls-application-documents", "/api/v1/applications/{application_id}/documents"),
    ),
)
def test_application_detail_get_smoke_returns_200(client, application_id: str, test_id: str, path_template: str):
    assert_get_smoke_200(client, GetSmokeCase(test_id, path_template.format(application_id=application_id)))


@pytest.mark.parametrize(
    ("test_id", "path_template"),
    (
        ("bls-application-document-info", "/api/v1/applications/{application_id}/documents/{document_id}/info"),
        ("bls-application-document-pages", "/api/v1/applications/{application_id}/documents/{document_id}/pages"),
        ("bls-application-document-export", "/api/v1/applications/{application_id}/documents/{document_id}/export"),
        ("bls-activities-document", "/api/v1/activities/document/{document_id}"),
    ),
)
def test_application_document_detail_get_smoke_returns_200(
    client,
    application_id: str,
    application_document_id: str,
    test_id: str,
    path_template: str,
):
    assert_get_smoke_200(
        client,
        GetSmokeCase(
            test_id,
            path_template.format(application_id=application_id, document_id=application_document_id),
        ),
    )
