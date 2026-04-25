from __future__ import annotations

import httpx
import pytest

from tests.endpoints.get_smoke.helpers import (
    GetSmokeCase,
    first_mapping_value,
    get_smoke_json,
    require_setup_list,
)


class FakeClient:
    def __init__(self, response: httpx.Response):
        self.response = response

    def get(self, path, params=None, timeout=None):
        return self.response


def _response(status_code: int, body: dict) -> httpx.Response:
    request = httpx.Request("GET", "https://verifyiq.example.test/list")
    return httpx.Response(status_code, json=body, request=request)


def test_setup_list_skips_when_successful_list_is_empty():
    case = GetSmokeCase("empty-list", "/example/list")

    with pytest.raises(pytest.skip.Exception, match="missing prerequisite example id"):
        require_setup_list(
            {"items": []},
            case,
            fields=("items",),
            prerequisite="example id",
            item_label="example",
        )


def test_setup_list_malformed_payload_fails_instead_of_skipping():
    case = GetSmokeCase("malformed-list", "/example/list")

    with pytest.raises(pytest.fail.Exception, match="field 'items' was not a list"):
        require_setup_list(
            {"items": {"id": "one"}},
            case,
            fields=("items",),
            prerequisite="example id",
            item_label="example",
        )


def test_first_mapping_value_skips_when_no_usable_identifier_exists():
    case = GetSmokeCase("missing-id", "/example/list")

    with pytest.raises(pytest.skip.Exception, match="returned no usable example items"):
        first_mapping_value(
            [{"id": ""}, {"id": None}, {"name": "missing-id"}],
            keys=("id",),
            source_case=case,
            prerequisite="example id",
            item_label="example",
        )


def test_first_mapping_value_malformed_item_fails_instead_of_skipping():
    case = GetSmokeCase("bad-item", "/example/list")

    with pytest.raises(pytest.fail.Exception, match="entry #1 was not an object"):
        first_mapping_value(
            ["not-an-object"],
            keys=("id",),
            source_case=case,
            prerequisite="example id",
            item_label="example",
        )


def test_get_smoke_json_bad_status_fails_instead_of_skipping():
    client = FakeClient(_response(500, {"detail": "bad"}))
    case = GetSmokeCase("bad-status", "/example/list")

    with pytest.raises(AssertionError, match="expected 200, got 500"):
        get_smoke_json(client, case)
