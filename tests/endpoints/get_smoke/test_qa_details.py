from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import GetSmokeCase, assert_get_smoke_200, get_smoke_json


_QUEUE_CASE = GetSmokeCase("qa-queue", "/qa/api/v1/queue")


@pytest.fixture(scope="module")
def qa_correlation_id(client) -> str:
    body = get_smoke_json(client, _QUEUE_CASE)
    items = body.get("items") or body.get("queue") or body.get("requests")
    assert isinstance(items, list) and items, "QA queue response did not contain any queue items."
    first = items[0]
    assert isinstance(first, dict), "QA queue first item was not an object."

    for key in ("correlation_id", "correlationId", "request_id", "id"):
        value = str(first.get(key, "")).strip()
        if value:
            return value

    pytest.fail("QA queue response did not include a correlation identifier for the first item.")


@pytest.mark.parametrize(
    ("test_id", "path_template"),
    (
        ("qa-request-detail", "/qa/api/v1/requests/{correlation_id}"),
        ("qa-review-detail", "/qa/api/v1/reviews/{correlation_id}"),
    ),
)
def test_qa_detail_get_smoke_returns_200(client, qa_correlation_id: str, test_id: str, path_template: str):
    assert_get_smoke_200(client, GetSmokeCase(test_id, path_template.format(correlation_id=qa_correlation_id)))
