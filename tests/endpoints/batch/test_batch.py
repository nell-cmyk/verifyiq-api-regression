"""
Regression tests for POST /v1/documents/batch.

Contract reference: official-openapi.json → BatchRequest / BatchItem / HTTPValidationError
For exact-fixture opt-in runs, set `BATCH_FIXTURES_JSON` to a JSON file of
`gs://` paths or use `python tools/run_batch_with_fixtures.py --fixtures-json ...`.
Observed live behavior:
- empty items => 400 with a batch-level detail string
- 5 items => 429 batch_timeout_risk with safeItemLimit = 4
- unsupported item fileType => 200 with ok=false on the failed result item
- registry-tagged page-limit fixtures may return 200 with per-item
  DocumentSizeGuardError warning results instead of parsed data
"""
from __future__ import annotations

import warnings

import httpx
import pytest

from tests.diagnostics import (
    diagnose,
    parse_json_or_fail,
    request_error_diagnostics,
    timeout_diagnostics,
)
from tests.endpoints.batch.fixtures import (
    BATCH_SAFE_ITEM_LIMIT,
    batch_fixture_context,
    build_batch_request,
    load_batch_fixtures,
)
from tests.endpoints.document_contracts import (
    assert_document_result_calculated_fields_not_stub,
    assert_document_result_file_type,
    assert_document_result_has_required_fields,
    assert_http_validation_error_shape,
)

ENDPOINT = "/v1/documents/batch"
BATCH_HAPPY_TIMEOUT_SECS = 300.0


def _batch_expected_warning_message(fixture: dict[str, object]) -> str | None:
    value = fixture.get("batch_expected_warning")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _batch_expected_error_type(fixture: dict[str, object]) -> str | None:
    value = fixture.get("batch_expected_error_type")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _batch_expected_error(fixture: dict[str, object]) -> str | None:
    value = fixture.get("batch_expected_error")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _clone_request_items(batch_request_payload: dict[str, object]) -> list[dict[str, str]]:
    items = batch_request_payload.get("items")
    assert isinstance(items, list) and items, "Batch request payload must contain at least one item."
    return [dict(item) for item in items]


def _request_items_with_min_count(
    batch_request_payload: dict[str, object],
    *,
    min_count: int,
) -> list[dict[str, str]]:
    items = _clone_request_items(batch_request_payload)
    source_items = [dict(item) for item in items]
    cursor = 0
    while len(items) < min_count:
        items.append(dict(source_items[cursor % len(source_items)]))
        cursor += 1
    return items


@pytest.fixture(scope="session")
def batch_fixtures():
    return load_batch_fixtures()


@pytest.fixture(scope="session")
def batch_context(batch_fixtures):
    return batch_fixture_context(batch_fixtures)


@pytest.fixture(scope="session")
def batch_request_payload(batch_fixtures):
    return build_batch_request(batch_fixtures)


@pytest.fixture(scope="session")
def batch_warning_fixtures(batch_fixtures):
    warning_fixtures: list[dict[str, object]] = []
    for fixture in batch_fixtures:
        warning_message = _batch_expected_warning_message(fixture)
        if warning_message is None:
            continue
        warnings.warn(
            (
                "/documents/batch fixture warning for "
                f"{fixture.get('name')}: {warning_message} "
                f"(expected error_type={_batch_expected_error_type(fixture)!r}, "
                f"expected error={_batch_expected_error(fixture)!r})"
            ),
            UserWarning,
        )
        warning_fixtures.append(fixture)
    return warning_fixtures


@pytest.fixture(scope="session")
def batch_response(client, batch_request_payload, batch_context):
    try:
        return client.post(
            ENDPOINT,
            json=batch_request_payload,
            timeout=BATCH_HAPPY_TIMEOUT_SECS,
        )
    except httpx.TimeoutException as exc:
        pytest.fail(
            timeout_diagnostics(
                exc,
                context="Batch happy-path request",
                timeout_secs=BATCH_HAPPY_TIMEOUT_SECS,
                extra_context=batch_context,
            )
        )
    except httpx.RequestError as exc:
        pytest.fail(
            request_error_diagnostics(
                exc,
                context="Batch happy-path request",
                extra_context=batch_context,
            )
        )


class TestBatchHappyPath:
    def test_returns_200(self, batch_response, batch_context):
        assert batch_response.status_code == 200, diagnose(batch_response) + batch_context

    def test_response_has_expected_batch_structure(
        self,
        batch_response,
        batch_fixtures,
        batch_warning_fixtures,
        batch_request_payload,
        batch_context,
    ):
        assert batch_response.status_code == 200, diagnose(batch_response) + batch_context
        body = parse_json_or_fail(
            batch_response,
            context="Batch happy-path response",
            extra_context=batch_context,
        )

        for key in ("summary", "results", "cacheStatistics", "crosscheckResults"):
            assert key in body, (
                f"Missing top-level batch response key: {key!r}"
                + diagnose(batch_response)
                + batch_context
            )

        assert isinstance(body["summary"], dict), (
            "Batch response 'summary' must be an object"
            + diagnose(batch_response)
            + batch_context
        )
        assert isinstance(body["results"], list), (
            "Batch response 'results' must be a list"
            + diagnose(batch_response)
            + batch_context
        )
        assert isinstance(body["cacheStatistics"], dict), (
            "Batch response 'cacheStatistics' must be an object"
            + diagnose(batch_response)
            + batch_context
        )
        assert isinstance(body["crosscheckResults"], list), (
            "Batch response 'crosscheckResults' must be a list"
            + diagnose(batch_response)
            + batch_context
        )
        assert "aggregated_gshare_fields" in body, (
            "Batch response must include the aggregated_gshare_fields key"
            + diagnose(batch_response)
            + batch_context
        )

        summary = body["summary"]
        expected_warning_count = len(batch_warning_fixtures)
        expected_success_count = len(batch_request_payload["items"]) - expected_warning_count
        assert summary.get("items") == len(batch_request_payload["items"]), (
            "Batch summary item count did not match the request item count"
            + diagnose(batch_response)
            + batch_context
        )
        assert summary.get("ok") == expected_success_count, (
            "Batch summary ok count did not match the number of returned results"
            + diagnose(batch_response)
            + batch_context
        )
        assert summary.get("failed") == expected_warning_count, (
            "Batch summary failed count did not match the number of expected warning fixtures"
            + diagnose(batch_response)
            + batch_context
        )

    def test_results_preserve_request_order_and_item_contract(
        self,
        batch_response,
        batch_fixtures,
        batch_warning_fixtures,
        batch_request_payload,
        batch_context,
    ):
        assert batch_response.status_code == 200, diagnose(batch_response) + batch_context
        body = parse_json_or_fail(
            batch_response,
            context="Batch happy-path response",
            extra_context=batch_context,
        )

        results = body["results"]
        assert len(results) == len(batch_request_payload["items"]), (
            "Batch response result count did not match the request item count"
            + diagnose(batch_response)
            + batch_context
        )

        for index, (fixture, request_item, result) in enumerate(
            zip(batch_fixtures, batch_request_payload["items"], results)
        ):
            fixture_file = request_item["file"]
            item_context = batch_context + f"\n  current_result_index: {index}\n"

            assert result.get("index") == index, (
                f"Batch result index mismatch at position {index}"
                + diagnose(batch_response, fixture_file=fixture_file)
                + item_context
            )
            warning_message = _batch_expected_warning_message(fixture)
            if warning_message is not None:
                assert result.get("ok") is False, (
                    f"Batch warning fixture at index {index} did not return an expected failure"
                    + diagnose(batch_response, fixture_file=fixture_file)
                    + item_context
                )
                assert result.get("error_type") == _batch_expected_error_type(fixture), (
                    f"Batch warning fixture at index {index} returned the wrong error type"
                    + diagnose(batch_response, fixture_file=fixture_file)
                    + item_context
                )
                assert _batch_expected_error(fixture) in str(result.get("error", "")), (
                    f"Batch warning fixture at index {index} returned the wrong error message"
                    + diagnose(batch_response, fixture_file=fixture_file)
                    + item_context
                )
                continue

            assert result.get("ok") is True, (
                f"Batch happy-path result at index {index} was not successful"
                + diagnose(batch_response, fixture_file=fixture_file)
                + item_context
            )
            assert "data" in result and isinstance(result["data"], dict), (
                f"Batch happy-path result at index {index} is missing parsed data"
                + diagnose(batch_response, fixture_file=fixture_file)
                + item_context
            )

            parsed_item = result["data"]
            assert_document_result_has_required_fields(
                parsed_item,
                context=f"batch result #{index}",
                response=batch_response,
                fixture_file=fixture_file,
                extra_context=item_context,
            )
            assert_document_result_file_type(
                parsed_item,
                expected_file_type=request_item["fileType"],
                context=f"batch result #{index}",
                response=batch_response,
                fixture_file=fixture_file,
                extra_context=item_context,
            )
            assert_document_result_calculated_fields_not_stub(
                parsed_item,
                context=f"batch result #{index}",
                response=batch_response,
                fixture_file=fixture_file,
                extra_context=item_context,
            )


class TestBatchValidation:
    def test_missing_items_returns_422(self, client):
        resp = client.post(ENDPOINT, json={})
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}" + diagnose(resp)

        body = assert_http_validation_error_shape(
            resp,
            context="Batch validation response for missing items",
        )

        assert body["detail"][0]["loc"] == ["body", "items"], (
            "Batch validation error loc did not point at the missing items field"
            + diagnose(resp)
        )

    def test_empty_items_returns_400(self, client):
        resp = client.post(ENDPOINT, json={"items": []})
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}" + diagnose(resp)

        body = parse_json_or_fail(resp, context="Batch empty-items response")
        assert body.get("detail") == "Provide non-empty 'items' list.", (
            "Batch empty-items response did not return the expected detail message"
            + diagnose(resp)
        )

    def test_more_than_safe_item_limit_returns_429(self, client, batch_request_payload, batch_context):
        over_limit_payload = {
            "items": _request_items_with_min_count(
                batch_request_payload,
                min_count=BATCH_SAFE_ITEM_LIMIT + 1,
            ),
        }

        resp = client.post(ENDPOINT, json=over_limit_payload)
        assert resp.status_code == 429, (
            f"Expected 429, got {resp.status_code}" + diagnose(resp) + batch_context
        )

        body = parse_json_or_fail(
            resp,
            context="Batch over-limit response",
            extra_context=batch_context,
        )
        assert body.get("code") == "batch_timeout_risk", (
            "Batch over-limit response did not return batch_timeout_risk"
            + diagnose(resp)
            + batch_context
        )
        assert body.get("retryable") is True, (
            "Batch over-limit response should be retryable"
            + diagnose(resp)
            + batch_context
        )
        assert body.get("details", {}).get("requestItemCount") == len(over_limit_payload["items"]), (
            "Batch over-limit response did not echo the request item count"
            + diagnose(resp)
            + batch_context
        )
        assert body.get("details", {}).get("safeItemLimit") == BATCH_SAFE_ITEM_LIMIT, (
            "Batch over-limit response did not return the expected safe item limit"
            + diagnose(resp)
            + batch_context
        )

    def test_missing_file_type_in_item_returns_422(self, client, batch_request_payload, batch_context):
        item_index = 0
        items = _request_items_with_min_count(batch_request_payload, min_count=1)
        del items[item_index]["fileType"]

        resp = client.post(ENDPOINT, json={"items": items})
        assert resp.status_code == 422, (
            f"Expected 422, got {resp.status_code}" + diagnose(resp) + batch_context
        )

        body = assert_http_validation_error_shape(
            resp,
            context="Batch validation response for missing item fileType",
            extra_context=batch_context,
        )
        assert body["detail"][0]["loc"] == ["body", "items", item_index, "fileType"], (
            "Batch validation error loc did not point at the missing item fileType"
            + diagnose(resp)
            + batch_context
        )

    def test_missing_file_in_item_returns_422(self, client, batch_request_payload, batch_context):
        item_index = 0
        items = _request_items_with_min_count(batch_request_payload, min_count=1)
        del items[item_index]["file"]

        resp = client.post(ENDPOINT, json={"items": items})
        assert resp.status_code == 422, (
            f"Expected 422, got {resp.status_code}" + diagnose(resp) + batch_context
        )

        body = assert_http_validation_error_shape(
            resp,
            context="Batch validation response for missing item file",
            extra_context=batch_context,
        )
        assert body["detail"][0]["loc"] == ["body", "items", item_index, "file"], (
            "Batch validation error loc did not point at the missing item file"
            + diagnose(resp)
            + batch_context
        )

    def test_unsupported_file_type_returns_partial_failure(
        self,
        client,
        batch_request_payload,
        batch_context,
    ):
        failure_index = 1
        items = _request_items_with_min_count(batch_request_payload, min_count=2)
        items[failure_index]["fileType"] = "NotARealFileType"

        resp = client.post(ENDPOINT, json={"items": items})
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}" + diagnose(resp) + batch_context
        )

        body = parse_json_or_fail(
            resp,
            context="Batch partial-failure response",
            extra_context=batch_context,
        )
        results = body["results"]
        failed_results = [result for result in results if result.get("ok") is False]
        assert len(results) == len(items), (
            "Batch partial-failure response did not preserve the request item count"
            + diagnose(resp)
            + batch_context
        )
        assert body["summary"].get("ok") == len(items) - 1, (
            "Batch partial-failure response reported an unexpected ok count"
            + diagnose(resp)
            + batch_context
        )
        assert body["summary"].get("failed") == 1, (
            "Batch partial-failure response reported an unexpected failed count"
            + diagnose(resp)
            + batch_context
        )
        assert len(failed_results) == 1, (
            "Batch partial-failure response should contain exactly one failed result"
            + diagnose(resp)
            + batch_context
        )

        failed_result = failed_results[0]
        assert failed_result.get("index") == failure_index, (
            "Batch partial-failure response did not keep the failing item index"
            + diagnose(resp)
            + batch_context
        )
        assert isinstance(failed_result.get("error"), str) and "not supported" in failed_result["error"], (
            "Batch partial-failure response did not return the expected unsupported-fileType error"
            + diagnose(resp)
            + batch_context
        )
