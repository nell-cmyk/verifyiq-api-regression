from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import GetSmokeCase, assert_get_smoke_200


CASES = (
    GetSmokeCase("parser-auth-status", "/parser_studio/auth/status"),
    GetSmokeCase("parser-doc-types-v1", "/parser_studio/api/v1/document-types"),
    GetSmokeCase("parser-pipeline-defaults-v1", "/parser_studio/api/v1/pipeline-defaults"),
    GetSmokeCase("parser-categories-v1", "/parser_studio/api/v1/categories"),
    GetSmokeCase("parser-field-types-v1", "/parser_studio/api/v1/field-types"),
    GetSmokeCase("parser-audit-log-v1", "/parser_studio/api/v1/audit-log"),
    GetSmokeCase("parser-categories-legacy", "/parser_studio/api/categories"),
    GetSmokeCase("parser-field-types-legacy", "/parser_studio/api/field-types"),
    GetSmokeCase("parser-tenants-v1", "/parser_studio/api/v1/tenants"),
    GetSmokeCase("parser-fraud-thresholds-v1", "/parser_studio/api/v1/fraud-thresholds"),
)


@pytest.mark.parametrize("case", CASES, ids=[case.test_id for case in CASES])
def test_parser_studio_get_smoke_returns_200(client, case: GetSmokeCase):
    assert_get_smoke_200(client, case)
