from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import GetSmokeCase, assert_get_smoke_200, get_smoke_json


_DOC_TYPES_CASE = GetSmokeCase("parser-doc-types-v1", "/parser_studio/api/v1/document-types")
_TENANTS_CASE = GetSmokeCase("parser-tenants-v1", "/parser_studio/api/v1/tenants")


@pytest.fixture(scope="module")
def parser_document_type(client) -> str:
    body = get_smoke_json(client, _DOC_TYPES_CASE)
    document_types = body.get("document_types")
    assert isinstance(document_types, list) and document_types, (
        "Parser Studio document-types response did not contain any document_types entries."
    )

    for entry in document_types:
        if not isinstance(entry, dict):
            continue
        doc_type = str(entry.get("document_type", "")).strip()
        if doc_type and str(entry.get("status", "")).strip().lower() == "active":
            return doc_type

    pytest.fail("Parser Studio document-types response did not contain an active document_type.")


@pytest.fixture(scope="module")
def parser_tenant_api_key(client) -> str:
    body = get_smoke_json(client, _TENANTS_CASE)
    tenants = body.get("tenants")
    assert isinstance(tenants, list) and tenants, "Parser Studio tenants response did not contain any tenants."

    api_key = str(tenants[0].get("api_key", "")).strip() if isinstance(tenants[0], dict) else ""
    assert api_key, "Parser Studio tenants response did not include api_key for the first tenant."
    return api_key


@pytest.mark.parametrize(
    ("test_id", "path_template"),
    (
        ("parser-doc-type-detail", "/parser_studio/api/v1/document-types/{doc_type}"),
        ("parser-doc-type-versions", "/parser_studio/api/v1/document-types/{doc_type}/versions"),
        ("parser-doc-type-prompt-versions", "/parser_studio/api/v1/document-types/{doc_type}/prompt/versions"),
    ),
)
def test_parser_studio_doc_type_detail_get_smoke_returns_200(
    client,
    parser_document_type: str,
    test_id: str,
    path_template: str,
):
    assert_get_smoke_200(client, GetSmokeCase(test_id, path_template.format(doc_type=parser_document_type)))


def test_parser_studio_tenant_detail_get_smoke_returns_200(client, parser_tenant_api_key: str):
    assert_get_smoke_200(
        client,
        GetSmokeCase("parser-tenant-detail", f"/parser_studio/api/v1/tenants/{parser_tenant_api_key}"),
    )
