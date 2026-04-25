from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import (
    GetSmokeCase,
    assert_get_smoke_200,
    first_mapping_value,
    get_smoke_json,
    require_setup_list,
)


_QUEUE_CASE = GetSmokeCase("qa-queue", "/qa/api/v1/queue")


@pytest.fixture(scope="module")
def qa_correlation_id(client) -> str:
    body = get_smoke_json(client, _QUEUE_CASE)
    items = require_setup_list(
        body,
        _QUEUE_CASE,
        fields=("items", "queue", "requests"),
        prerequisite="QA correlation identifier",
        item_label="queue item",
    )
    return first_mapping_value(
        items,
        keys=("correlation_id", "correlationId", "request_id", "id"),
        source_case=_QUEUE_CASE,
        prerequisite="QA correlation identifier",
        item_label="queue item",
    )


@pytest.mark.parametrize(
    ("test_id", "path_template"),
    (
        ("qa-request-detail", "/qa/api/v1/requests/{correlation_id}"),
        ("qa-review-detail", "/qa/api/v1/reviews/{correlation_id}"),
    ),
)
def test_qa_detail_get_smoke_returns_200(client, qa_correlation_id: str, test_id: str, path_template: str):
    assert_get_smoke_200(client, GetSmokeCase(test_id, path_template.format(correlation_id=qa_correlation_id)))
