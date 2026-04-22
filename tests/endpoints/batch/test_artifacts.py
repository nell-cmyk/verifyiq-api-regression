from __future__ import annotations

import json
import re

import httpx

from tests.endpoints.batch.artifacts import (
    BATCH_RESPONSE_ARTIFACT_DIR_ENV_VAR,
    BATCH_ENDPOINT,
    attach,
    write_batch_response_artifact,
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


def test_write_batch_response_artifact_writes_raw_json_body(monkeypatch, tmp_path):
    monkeypatch.setenv(BATCH_RESPONSE_ARTIFACT_DIR_ENV_VAR, str(tmp_path))
    body = {"summary": {"items": 1, "ok": 1, "failed": 0}, "results": [{"index": 0, "ok": True}]}
    response, raw = _response(path=BATCH_ENDPOINT, body=body)

    out_path = write_batch_response_artifact(response)
    run_dirs = sorted(path for path in tmp_path.iterdir() if path.is_dir())

    assert out_path is not None
    assert len(run_dirs) == 1
    assert out_path.parent == run_dirs[0]
    assert out_path.parent.parent == tmp_path.resolve()
    assert re.fullmatch(r"batch_\d{4}-\d{2}-\d{2}-T\d{6}_\d{6}Z", run_dirs[0].name)
    assert re.fullmatch(r"batch_\d{4}-\d{2}-\d{2}-T\d{6}_\d{6}Z_\d{4}\.json", out_path.name)
    assert out_path.read_text(encoding="utf-8") == raw
    assert json.loads(out_path.read_text(encoding="utf-8")) == body


def test_attach_writes_one_artifact_per_batch_response(monkeypatch, tmp_path):
    monkeypatch.setenv(BATCH_RESPONSE_ARTIFACT_DIR_ENV_VAR, str(tmp_path))
    batch_counter = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == BATCH_ENDPOINT:
            batch_counter["value"] += 1
            return httpx.Response(
                200,
                request=request,
                json={"summary": {"items": batch_counter["value"]}, "results": []},
            )
        return httpx.Response(200, request=request, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    attach(client)
    try:
        client.post("https://example.test/v1/documents/parse", json={"file": "ignored"})
        client.post(f"https://example.test{BATCH_ENDPOINT}", json={"items": []})
        client.post(f"https://example.test{BATCH_ENDPOINT}", json={"items": []})
    finally:
        client.close()

    run_dirs = sorted(path for path in tmp_path.iterdir() if path.is_dir())
    assert len(run_dirs) == 1
    assert re.fullmatch(r"batch_\d{4}-\d{2}-\d{2}-T\d{6}_\d{6}Z", run_dirs[0].name)

    artifacts = sorted(run_dirs[0].glob("batch_*.json"))
    assert len(artifacts) == 2
    assert all(path.parent == run_dirs[0] for path in artifacts)
    assert [json.loads(path.read_text(encoding="utf-8"))["summary"]["items"] for path in artifacts] == [1, 2]
