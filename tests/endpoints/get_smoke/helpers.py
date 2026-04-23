from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest

from tests.diagnostics import diagnose, request_error_diagnostics, timeout_diagnostics

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


def assert_get_smoke_200(client: httpx.Client, case: GetSmokeCase) -> None:
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

    assert resp.status_code == 200, (
        f"GET smoke endpoint {case.path!r}: expected 200, got {resp.status_code}"
        + diagnose(resp)
        + ctx
    )
