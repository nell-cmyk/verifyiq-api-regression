from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
import pytest

from tests.diagnostics import diagnose, parse_json_or_fail, request_error_diagnostics, timeout_diagnostics

GET_SMOKE_TIMEOUT_SECS = 30.0


@dataclass(frozen=True)
class GetSmokeCase:
    test_id: str
    path: str
    params: tuple[tuple[str, str], ...] = ()
    timeout_secs: float = GET_SMOKE_TIMEOUT_SECS


def _case_context(case: GetSmokeCase) -> str:
    lines = [
        "",
        "-- get smoke case --",
        f"  id:                {case.test_id!r}",
        f"  path:              {case.path!r}",
    ]
    if case.params:
        lines.append(f"  params:            {dict(case.params)!r}")
    lines.append("---------------------")
    return "\n".join(lines)


def get_smoke_response(client: httpx.Client, case: GetSmokeCase, *, expected_status: int = 200) -> httpx.Response:
    ctx = _case_context(case)
    params = dict(case.params) if case.params else None
    try:
        resp = client.get(case.path, params=params, timeout=case.timeout_secs)
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

    assert resp.status_code == expected_status, (
        f"GET smoke endpoint {case.path!r}: expected {expected_status}, got {resp.status_code}"
        + diagnose(resp)
        + ctx
    )
    return resp


def get_smoke_json(client: httpx.Client, case: GetSmokeCase, *, context: str | None = None) -> Any:
    resp = get_smoke_response(client, case)
    return parse_json_or_fail(
        resp,
        context=context or f"GET smoke JSON response for {case.path}",
        extra_context=_case_context(case),
    )


def _skip_missing_setup_prerequisite(*, case: GetSmokeCase, prerequisite: str, detail: str) -> None:
    pytest.skip(
        "Skipping setup-backed detail GET smoke: "
        f"missing prerequisite {prerequisite}; {case.path} {detail}."
    )


def require_setup_list(
    body: Any,
    case: GetSmokeCase,
    *,
    fields: tuple[str, ...],
    prerequisite: str,
    item_label: str,
) -> list[Any]:
    if not isinstance(body, dict):
        pytest.fail(f"{case.path} response was not a JSON object; cannot derive {prerequisite}.")

    empty_fields: list[str] = []
    for field in fields:
        if field not in body:
            continue
        value = body[field]
        if not isinstance(value, list):
            pytest.fail(
                f"{case.path} field {field!r} was not a list; cannot derive {prerequisite}."
            )
        if value:
            return value
        empty_fields.append(field)

    if empty_fields:
        _skip_missing_setup_prerequisite(
            case=case,
            prerequisite=prerequisite,
            detail=f"returned no {item_label} items in field(s) {', '.join(empty_fields)}",
        )
    pytest.fail(
        f"{case.path} response did not contain expected list field(s) {fields!r}; "
        f"cannot derive {prerequisite}."
    )


def first_mapping_value(
    items: list[Any],
    *,
    keys: tuple[str, ...],
    source_case: GetSmokeCase,
    prerequisite: str,
    item_label: str,
) -> str:
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            pytest.fail(
                f"{source_case.path} {item_label} entry #{index} was not an object; "
                f"cannot derive {prerequisite}."
            )
        for key in keys:
            raw_value = item.get(key)
            if raw_value is None:
                continue
            value = str(raw_value).strip()
            if value:
                return value

    _skip_missing_setup_prerequisite(
        case=source_case,
        prerequisite=prerequisite,
        detail=f"returned no usable {item_label} items with key(s) {', '.join(keys)}",
    )
    raise AssertionError("unreachable")


def assert_get_smoke_200(client: httpx.Client, case: GetSmokeCase) -> None:
    get_smoke_response(client, case)


def assert_get_smoke_status(client: httpx.Client, case: GetSmokeCase, expected_status: int) -> None:
    get_smoke_response(client, case, expected_status=expected_status)
