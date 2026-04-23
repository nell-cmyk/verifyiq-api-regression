from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import GetSmokeCase, assert_get_smoke_status


CASES = (
    (GetSmokeCase("health-database-pools", "/api/v1/health/database-pools"), 401),
    (GetSmokeCase("health-database-pools-metrics", "/api/v1/health/database-pools/metrics"), 401),
    (GetSmokeCase("admin-cache-health", "/v1/admin/cache/health"), 403),
    (GetSmokeCase("monitoring-gcs-structure", "/monitoring/api/v1/golden-dataset/gcs/structure"), 502),
)


@pytest.mark.parametrize(
    ("case", "expected_status"),
    CASES,
    ids=[case.test_id for case, _ in CASES],
)
def test_expected_status_get_surfaces_return_documented_status(client, case: GetSmokeCase, expected_status: int):
    assert_get_smoke_status(client, case, expected_status)
