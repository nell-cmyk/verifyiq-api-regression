from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import GetSmokeCase, assert_get_smoke_200


CASES = (
    GetSmokeCase("monitoring-overview", "/monitoring/api/v1/overview"),
    GetSmokeCase("monitoring-requests", "/monitoring/api/v1/requests"),
    GetSmokeCase("monitoring-endpoints", "/monitoring/api/v1/endpoints"),
    GetSmokeCase("monitoring-tenants", "/monitoring/api/v1/tenants"),
    GetSmokeCase("monitoring-document-types", "/monitoring/api/v1/document-types"),
    GetSmokeCase("monitoring-errors", "/monitoring/api/v1/errors"),
    GetSmokeCase("monitoring-fraud", "/monitoring/api/v1/fraud"),
    GetSmokeCase("monitoring-export", "/monitoring/api/v1/export"),
    GetSmokeCase("monitoring-export-preview", "/monitoring/api/v1/export/preview"),
    GetSmokeCase("monitoring-document-types-list", "/monitoring/api/v1/document-types-list"),
    GetSmokeCase("monitoring-golden-dataset", "/monitoring/api/v1/golden-dataset"),
    GetSmokeCase("monitoring-golden-dataset-stats", "/monitoring/api/v1/golden-dataset/stats"),
    GetSmokeCase("monitoring-benchmark-latest", "/monitoring/api/v1/golden-dataset/benchmark/latest"),
    GetSmokeCase("monitoring-benchmark-recent", "/monitoring/api/v1/golden-dataset/benchmark/recent"),
    GetSmokeCase("monitoring-benchmark-stats", "/monitoring/api/v1/golden-dataset/benchmark/stats"),
    GetSmokeCase("monitoring-gcs-types", "/monitoring/api/v1/golden-dataset/gcs/types"),
    GetSmokeCase("monitoring-audit-logs", "/monitoring/api/v1/audit-logs"),
    GetSmokeCase("monitoring-ground-truth-document-types", "/monitoring/api/v1/ground-truth/document-types"),
    GetSmokeCase("monitoring-ground-truth-review-models", "/monitoring/api/v1/ground-truth/review-models"),
    GetSmokeCase("monitoring-drift-overview", "/monitoring/api/v1/drift/overview"),
    GetSmokeCase("monitoring-drift-events", "/monitoring/api/v1/drift/events"),
    GetSmokeCase("monitoring-drift-settings", "/monitoring/api/v1/drift/settings"),
    GetSmokeCase("monitoring-drift-scheduler-status", "/monitoring/api/v1/drift/scheduler-status"),
    GetSmokeCase("monitoring-drift-suppression-rules", "/monitoring/api/v1/drift/suppression-rules"),
)


@pytest.mark.parametrize("case", CASES, ids=[case.test_id for case in CASES])
def test_monitoring_get_smoke_returns_200(client, case: GetSmokeCase):
    assert_get_smoke_200(client, case)
