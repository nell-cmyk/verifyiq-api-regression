"""Parametrized /parse coverage across fileTypes.

One canonical enabled GCS-backed fixture per fileType, selected by
`tests/endpoints/parse/registry.py`. Collection is gated by the sibling
`conftest.py` via the `RUN_PARSE_MATRIX` environment variable so this module
does not appear in the protected baseline run. Opt in explicitly:

  RUN_PARSE_MATRIX=1 pytest tests/endpoints/parse/test_parse_matrix.py -v

Windows (cmd/PowerShell):

  set RUN_PARSE_MATRIX=1
  pytest tests/endpoints/parse/test_parse_matrix.py -v

Generic contract assertions only. No fileType-specific checks - those belong
in dedicated tests if/when a fileType's behavior warrants it.
"""
from __future__ import annotations

import httpx
import pytest

from tests.diagnostics import diagnose
from tests.endpoints.parse.file_types import api_file_type_for
from tests.endpoints.parse.registry import load_canonical_fixtures

ENDPOINT = "/v1/documents/parse"
_EXPECTED_FIELDS = (
    "fileType",
    "documentQuality",
    "summaryOCR",
    "summaryResult",
    "calculatedFields",
)
_PARSE_TIMEOUT_SECS = 300.0


def _matrix_context(fixture: dict, api_file_type: str) -> str:
    """Traceability block for matrix-level failures. Sibling to diagnose()."""
    return (
        "\n-- matrix fixture --\n"
        f"  registry fileType:  {fixture.get('file_type')!r}\n"
        f"  api fileType:       {api_file_type!r}\n"
        f"  source_row:         {fixture.get('source_row')}\n"
        f"  verification_status:{fixture.get('verification_status')!r}\n"
        f"  gcs_uri:            {fixture.get('gcs_uri')!r}\n"
        "--------------------"
    )


_CANONICAL = load_canonical_fixtures()


@pytest.mark.parametrize(
    "fixture",
    _CANONICAL,
    ids=[f["file_type"] for f in _CANONICAL],
)
def test_parse_fixture_contract(client, fixture):
    """Generic /parse contract: 200 JSON, echoed fileType, required fields present."""
    registry_file_type = fixture["file_type"]
    api_file_type = api_file_type_for(registry_file_type)
    payload = {
        "file": fixture["gcs_uri"],
        "fileType": api_file_type,
        "pipeline": {"use_cache": False},
    }
    ctx = _matrix_context(fixture, api_file_type)
    try:
        resp = client.post(ENDPOINT, json=payload, timeout=_PARSE_TIMEOUT_SECS)
    except httpx.TimeoutException as exc:
        pytest.fail(
            f"Matrix parse timed out ({type(exc).__name__}) after "
            f"{_PARSE_TIMEOUT_SECS:.0f}s.\n"
            f"  underlying: {exc!r}"
            + ctx
        )
    except httpx.RequestError as exc:
        # Connect errors, DNS failures, TLS issues, RemoteProtocolError, etc.
        # Classify transport-layer failures instead of raising a raw traceback.
        pytest.fail(
            f"Matrix parse transport error ({type(exc).__name__}).\n"
            f"  underlying: {exc!r}"
            + ctx
        )

    gcs = fixture["gcs_uri"]
    assert resp.status_code == 200, diagnose(resp, fixture_file=gcs) + ctx

    try:
        body = resp.json()
    except ValueError as exc:
        pytest.fail(
            f"Non-JSON 200 for api fileType {api_file_type!r}: {exc}"
            + diagnose(resp, fixture_file=gcs)
            + ctx
        )

    assert body.get("fileType") == api_file_type, (
        f"fileType mismatch: expected {api_file_type!r}, "
        f"got {body.get('fileType')!r}"
        + diagnose(resp, fixture_file=gcs)
        + ctx
    )

    missing = [f for f in _EXPECTED_FIELDS if f not in body]
    assert not missing, (
        f"Missing fields {missing} for api fileType {api_file_type!r}"
        + diagnose(resp, fixture_file=gcs)
        + ctx
    )
