from __future__ import annotations

import httpx
import pytest

from tests.diagnostics import diagnose, request_error_diagnostics, timeout_diagnostics
from tests.endpoints.get_smoke.helpers import (
    GetSmokeCase,
    assert_get_smoke_200,
    get_smoke_json,
    require_setup_list,
)


_QUEUE_CASE = GetSmokeCase("qa-queue", "/qa/api/v1/queue")
_QUEUE_CORRELATION_KEYS = ("correlation_id", "correlationId", "request_id", "id")


def _case_context(case: GetSmokeCase) -> str:
    return "\n".join(
        (
            "",
            "-- get smoke case --",
            f"  id:                {case.test_id!r}",
            f"  path:              {case.path!r}",
            "---------------------",
        )
    )


@pytest.fixture(scope="module")
def qa_queue_items(client) -> list[object]:
    body = get_smoke_json(client, _QUEUE_CASE)
    return require_setup_list(
        body,
        _QUEUE_CASE,
        fields=("items", "queue", "requests"),
        prerequisite="QA queue data",
        item_label="queue item",
    )


def _correlation_ids_from_queue_items(items: list[object]) -> list[str]:
    correlation_ids: list[str] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            pytest.fail(
                f"{_QUEUE_CASE.path} queue item entry #{index} was not an object; "
                "cannot derive QA correlation identifier."
            )
        for key in _QUEUE_CORRELATION_KEYS:
            raw_value = item.get(key)
            if raw_value is None:
                continue
            value = str(raw_value).strip()
            if value:
                correlation_ids.append(value)
                break
    return correlation_ids


@pytest.fixture(scope="module")
def qa_request_correlation_id(qa_queue_items: list[object]) -> str:
    correlation_ids = _correlation_ids_from_queue_items(qa_queue_items)
    if not correlation_ids:
        pytest.skip(
            "Skipping setup-backed detail GET smoke: missing prerequisite QA correlation identifier; "
            f"{_QUEUE_CASE.path} returned queue items but none had a usable "
            f"{', '.join(_QUEUE_CORRELATION_KEYS)} value."
        )
    return correlation_ids[0]


@pytest.fixture(scope="module")
def qa_review_correlation_id(client, qa_queue_items: list[object]) -> str:
    correlation_ids = _correlation_ids_from_queue_items(qa_queue_items)
    if not correlation_ids:
        pytest.skip(
            "Skipping setup-backed detail GET smoke: missing prerequisite QA review correlation identifier; "
            f"{_QUEUE_CASE.path} returned queue items but none had a usable "
            f"{', '.join(_QUEUE_CORRELATION_KEYS)} value."
        )

    for correlation_id in correlation_ids:
        case = GetSmokeCase("qa-review-detail", f"/qa/api/v1/reviews/{correlation_id}")
        ctx = _case_context(case)
        try:
            response = client.get(case.path, timeout=case.timeout_secs)
        except httpx.TimeoutException as exc:
            pytest.fail(
                timeout_diagnostics(
                    exc,
                    context=f"GET smoke request for {case.path}",
                    timeout_secs=case.timeout_secs,
                    extra_context=ctx,
                )
            )
        except httpx.RequestError as exc:
            pytest.fail(
                request_error_diagnostics(
                    exc,
                    context=f"GET smoke request for {case.path}",
                    extra_context=ctx,
                )
            )

        if response.status_code == 200:
            return correlation_id
        if response.status_code == 404:
            continue
        pytest.fail(
            "QA review detail candidate returned unexpected status "
            f"{response.status_code}; expected 200 or candidate-level 404."
            + diagnose(response)
            + ctx
        )

    pytest.skip(
        "Skipping setup-backed detail GET smoke: missing prerequisite QA review correlation identifier; "
        "all queue-derived correlation IDs returned 404 from /qa/api/v1/reviews/{correlation_id}."
    )


def test_qa_request_detail_get_smoke_returns_200(client, qa_request_correlation_id: str):
    assert_get_smoke_200(
        client,
        GetSmokeCase("qa-request-detail", f"/qa/api/v1/requests/{qa_request_correlation_id}"),
    )


def test_qa_review_detail_get_smoke_returns_200(client, qa_review_correlation_id: str):
    assert_get_smoke_200(
        client,
        GetSmokeCase("qa-review-detail", f"/qa/api/v1/reviews/{qa_review_correlation_id}"),
    )
