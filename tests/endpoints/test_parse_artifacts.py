from __future__ import annotations

import json
import re

import httpx

from tests.endpoints.parse.artifacts import (
    PARSE_ENDPOINT,
    PARSE_RESPONSE_ARTIFACT_DIR_ENV_VAR,
    attach,
    clear_current_parse_nodeid,
    set_current_parse_nodeid,
    write_parse_response_artifact,
)


def _response(*, path: str, body: dict[str, object]) -> tuple[httpx.Response, str]:
    raw = json.dumps(body)
    request = httpx.Request("POST", f"https://example.test{path}")
    response = httpx.Response(
        200,
        request=request,
        content=raw.encode("utf-8"),
        headers={"content-type": "application/json"},
    )
    return response, raw


def test_write_parse_response_artifact_writes_raw_json_body(monkeypatch, tmp_path):
    monkeypatch.setenv(PARSE_RESPONSE_ARTIFACT_DIR_ENV_VAR, str(tmp_path))
    set_current_parse_nodeid("tests/endpoints/parse/test_parse.py::TestParseHappyPath::test_returns_200")
    body = {"fileType": "BankStatement", "summaryResult": [], "calculatedFields": {"pageNumber": 2}}
    response, raw = _response(path=PARSE_ENDPOINT, body=body)

    out_path = write_parse_response_artifact(response)
    clear_current_parse_nodeid()

    assert out_path is not None
    assert out_path.parent == tmp_path.resolve()
    assert re.fullmatch(
        r"test_parse__TestParseHappyPath__test_returns_200__\d{8}T\d{6}_\d{6}Z_\d{4}\.json",
        out_path.name,
    )
    assert out_path.read_text(encoding="utf-8") == raw
    assert json.loads(out_path.read_text(encoding="utf-8")) == body


def test_attach_writes_one_artifact_per_parse_response(monkeypatch, tmp_path):
    monkeypatch.setenv(PARSE_RESPONSE_ARTIFACT_DIR_ENV_VAR, str(tmp_path))
    parse_counter = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == PARSE_ENDPOINT:
            parse_counter["value"] += 1
            return httpx.Response(
                200,
                request=request,
                json={"fileType": "TINID", "call": parse_counter["value"]},
            )
        return httpx.Response(200, request=request, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    attach(client)
    set_current_parse_nodeid("tests/endpoints/parse/test_parse.py::TestParseValidation::test_missing_file_returns_422")
    try:
        client.post(f"https://example.test{PARSE_ENDPOINT}", json={"file": "a"})
        client.post("https://example.test/v1/documents/batch", json={"items": []})
        client.post(f"https://example.test{PARSE_ENDPOINT}", json={"file": "b"})
    finally:
        clear_current_parse_nodeid()
        client.close()

    artifacts = sorted(tmp_path.glob("*.json"))
    assert len(artifacts) == 2
    assert [json.loads(path.read_text(encoding="utf-8"))["call"] for path in artifacts] == [1, 2]
