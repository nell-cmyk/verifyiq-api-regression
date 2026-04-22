"""Parametrized /parse coverage across fileTypes.

One canonical enabled GCS-backed fixture per fileType, selected by
`tests/endpoints/parse/registry.py`. Collection is gated by the sibling
`conftest.py` via the `RUN_PARSE_MATRIX` environment variable so this module
does not appear in the protected baseline run. Opt in explicitly:

  RUN_PARSE_MATRIX=1 pytest tests/endpoints/parse/test_parse_matrix.py -v

For exact-fixture opt-in runs, set `PARSE_MATRIX_FIXTURES_JSON` to a JSON file
of `gs://` paths (or use the reporting wrapper's `--fixtures-json` flag).

Windows (cmd/PowerShell):

  set RUN_PARSE_MATRIX=1
  pytest tests/endpoints/parse/test_parse_matrix.py -v

Generic contract assertions only. No fileType-specific checks - those belong
in dedicated tests if/when a fileType's behavior warrants it.
"""
from __future__ import annotations

import os

import httpx
import pytest

from tests.diagnostics import (
    diagnose,
    parse_json_or_fail,
    request_error_diagnostics,
    timeout_diagnostics,
)
from tests.endpoints.parse.file_types import request_file_type_for
from tests.endpoints.parse.registry import fixture_test_id, load_matrix_fixtures

ENDPOINT = "/v1/documents/parse"
_EXPECTED_FIELDS = (
    "fileType",
    "documentQuality",
    "summaryOCR",
    "summaryResult",
    "calculatedFields",
)
_PARSE_TIMEOUT_SECS = 300.0


if os.getenv("RUN_PARSE_MATRIX") != "1":
    raise RuntimeError(
        "The /parse matrix is opt-in only. Use "
        "`python tools/reporting/run_parse_matrix_with_summary.py` "
        "or set RUN_PARSE_MATRIX=1 explicitly before running "
        "`tests/endpoints/parse/test_parse_matrix.py`."
    )


def _matrix_context(fixture: dict, request_file_type: str) -> str:
    """Traceability block for matrix-level failures. Sibling to diagnose()."""
    return (
        "\n-- matrix fixture --\n"
        f"  registry fileType:  {fixture.get('file_type')!r}\n"
        f"  request fileType:   {request_file_type!r}\n"
        f"  source_row:         {fixture.get('source_row')}\n"
        f"  verification_status:{fixture.get('verification_status')!r}\n"
        f"  gcs_uri:            {fixture.get('gcs_uri')!r}\n"
        "--------------------"
    )


_SELECTION_JSON = os.getenv("PARSE_MATRIX_FIXTURES_JSON")
_EXPLICIT_SELECTION = bool(_SELECTION_JSON)
_MATRIX_FIXTURES = load_matrix_fixtures(selection_json_path=_SELECTION_JSON)


@pytest.mark.parametrize(
    "fixture",
    _MATRIX_FIXTURES,
    ids=[fixture_test_id(f, explicit_selection=_EXPLICIT_SELECTION) for f in _MATRIX_FIXTURES],
)
def test_parse_fixture_contract(client, fixture):
    """Generic /parse contract: 200 JSON, echoed fileType, required fields present."""
    registry_file_type = fixture["file_type"]
    request_file_type = request_file_type_for(registry_file_type)
    payload = {
        "file": fixture["gcs_uri"],
        "fileType": request_file_type,
        "pipeline": {"use_cache": False},
    }
    ctx = _matrix_context(fixture, request_file_type)
    try:
        resp = client.post(ENDPOINT, json=payload, timeout=_PARSE_TIMEOUT_SECS)
    except httpx.TimeoutException as exc:
        pytest.fail(
            timeout_diagnostics(
                exc,
                context="Matrix parse request",
                timeout_secs=_PARSE_TIMEOUT_SECS,
                fixture_file=fixture["gcs_uri"],
                file_type=request_file_type,
                extra_context=ctx,
            )
        )
    except httpx.RequestError as exc:
        pytest.fail(
            request_error_diagnostics(
                exc,
                context="Matrix parse request",
                fixture_file=fixture["gcs_uri"],
                file_type=request_file_type,
                extra_context=ctx,
            )
        )

    gcs = fixture["gcs_uri"]
    assert resp.status_code == 200, diagnose(resp, fixture_file=gcs) + ctx

    body = parse_json_or_fail(
        resp,
        context=f"Matrix parse response for request fileType {request_file_type!r}",
        fixture_file=gcs,
        extra_context=ctx,
    )

    assert body.get("fileType") == request_file_type, (
        f"fileType mismatch: expected {request_file_type!r}, "
        f"got {body.get('fileType')!r}"
        + diagnose(resp, fixture_file=gcs)
        + ctx
    )

    missing = [f for f in _EXPECTED_FIELDS if f not in body]
    assert not missing, (
        f"Missing fields {missing} for request fileType {request_file_type!r}"
        + diagnose(resp, fixture_file=gcs)
        + ctx
    )
