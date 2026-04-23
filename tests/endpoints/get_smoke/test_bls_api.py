from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import GetSmokeCase, assert_get_smoke_200


CASES = (
    GetSmokeCase("bls-applications-list", "/api/v1/applications/"),
    GetSmokeCase("bls-application-pages-list", "/api/v1/applications/documents/pages"),
    GetSmokeCase("bls-document-pages-list", "/api/v1/documents/pages"),
    GetSmokeCase("bls-document-statistics", "/api/v1/document-statistics"),
    GetSmokeCase("bls-activities-list", "/api/v1/activities/"),
    GetSmokeCase("benchmark-jobs-list", "/api/v1/benchmark/jobs"),
    GetSmokeCase("pii-cleanup-runs-list", "/api/v1/pii-cleanup/runs"),
)


@pytest.mark.parametrize("case", CASES, ids=[case.test_id for case in CASES])
def test_bls_get_smoke_returns_200(client, case: GetSmokeCase):
    assert_get_smoke_200(client, case)
