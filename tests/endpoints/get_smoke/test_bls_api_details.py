from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import GetSmokeCase, assert_get_smoke_200, get_smoke_json


_BENCHMARK_JOBS_CASE = GetSmokeCase("benchmark-jobs-list", "/api/v1/benchmark/jobs")
_APPLICATIONS_CASE = GetSmokeCase("bls-applications-list", "/api/v1/applications/")


@pytest.fixture(scope="module")
def benchmark_job_id(client) -> str:
    body = get_smoke_json(client, _BENCHMARK_JOBS_CASE)
    jobs = body.get("jobs")
    assert isinstance(jobs, list) and jobs, "Benchmark jobs response did not contain any jobs."
    job_id = str(jobs[0].get("job_id", "")).strip() if isinstance(jobs[0], dict) else ""
    assert job_id, "Benchmark jobs response did not include job_id for the first job."
    return job_id


@pytest.fixture(scope="module")
def application_id(client) -> str:
    body = get_smoke_json(client, _APPLICATIONS_CASE)
    items = body.get("items")
    assert isinstance(items, list) and items, "Applications response did not contain any items."
    first = items[0]
    assert isinstance(first, dict), "Applications response first item was not an object."
    app_id = str(first.get("applicationId", "")).strip()
    assert app_id, "Applications response did not include applicationId for the first item."
    return app_id


@pytest.fixture(scope="module")
def application_document_id(client, application_id: str) -> str:
    body = get_smoke_json(
        client,
        GetSmokeCase("bls-application-documents", f"/api/v1/applications/{application_id}/documents"),
    )
    items = body.get("items") or body.get("documents") or body.get("data")
    assert isinstance(items, list) and items, "Application documents response did not contain any documents."
    first = items[0]
    assert isinstance(first, dict), "Application documents response first item was not an object."

    for key in ("documentId", "document_id", "id"):
        value = str(first.get(key, "")).strip()
        if value:
            return value

    pytest.fail("Application documents response did not include a document identifier for the first document.")


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
