from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import GetSmokeCase, assert_get_smoke_200


CASES = (
    GetSmokeCase("health", "/health"),
    GetSmokeCase("health-live", "/health/live"),
    GetSmokeCase("health-ready", "/health/ready"),
    GetSmokeCase("health-detailed", "/health/detailed"),
    GetSmokeCase("health-startup", "/health/startup"),
    GetSmokeCase("bls-applications-health", "/api/v1/applications/health"),
    GetSmokeCase("bls-admin-health", "/api/v1/admin/health"),
    GetSmokeCase("gateway-circuit-breakers-health", "/ai-gateway/health/gateway-circuit-breakers"),
)


@pytest.mark.parametrize("case", CASES, ids=[case.test_id for case in CASES])
def test_health_get_smoke_returns_200(client, case: GetSmokeCase):
    assert_get_smoke_200(client, case)
