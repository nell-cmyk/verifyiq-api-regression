from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import GetSmokeCase, assert_get_smoke_200


CASES = (
    GetSmokeCase("qa-queue", "/qa/api/v1/queue"),
    GetSmokeCase("qa-stats", "/qa/api/v1/stats"),
    GetSmokeCase("qa-document-types", "/qa/api/v1/document-types"),
    GetSmokeCase("qa-tenants", "/qa/api/v1/tenants"),
    GetSmokeCase("qa-report-summary", "/qa/api/v1/reports/summary"),
    GetSmokeCase("qa-field-errors", "/qa/api/v1/reports/field-errors"),
    GetSmokeCase("qa-thresholds", "/qa/api/v1/thresholds"),
    GetSmokeCase("qa-export", "/qa/api/v1/export"),
    GetSmokeCase("qa-export-preview", "/qa/api/v1/export/preview"),
)


@pytest.mark.parametrize("case", CASES, ids=[case.test_id for case in CASES])
def test_qa_get_smoke_returns_200(client, case: GetSmokeCase):
    assert_get_smoke_200(client, case)
