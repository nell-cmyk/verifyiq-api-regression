from __future__ import annotations

import pytest

from tests.endpoints.get_smoke.helpers import (
    GetSmokeCase,
    assert_get_smoke_200,
    first_mapping_value,
    get_smoke_json,
    require_setup_list,
)


_DOC_TYPES_CASE = GetSmokeCase("parser-doc-types-v1", "/parser_studio/api/v1/document-types")
_TENANTS_CASE = GetSmokeCase("parser-tenants-v1", "/parser_studio/api/v1/tenants")


@pytest.fixture(scope="module")
def parser_document_type(client) -> str:
    body = get_smoke_json(client, _DOC_TYPES_CASE)
    document_types = require_setup_list(
        body,
        _DOC_TYPES_CASE,
        fields=("document_types",),
        prerequisite="Parser Studio active document_type",
        item_label="document-type",
    )

    for index, entry in enumerate(document_types, start=1):
        if not isinstance(entry, dict):
            pytest.fail(
                "Parser Studio document-types entry "
                f"#{index} was not an object; cannot derive active document_type."
            )
        doc_type = str(entry.get("document_type", "")).strip()
        if doc_type and str(entry.get("status", "")).strip().lower() == "active":
            return doc_type

    pytest.skip(
        "Skipping setup-backed detail GET smoke: missing prerequisite Parser Studio active document_type; "
        f"{_DOC_TYPES_CASE.path} returned no active document-type items."
    )


@pytest.fixture(scope="module")
def parser_prompt_version_ref(client) -> tuple[str, str]:
    body = get_smoke_json(client, _DOC_TYPES_CASE)
    document_types = require_setup_list(
        body,
        _DOC_TYPES_CASE,
        fields=("document_types",),
        prerequisite="Parser Studio prompt version reference",
        item_label="document-type",
    )

    saw_document_type = False
    for index, entry in enumerate(document_types, start=1):
        if not isinstance(entry, dict):
            pytest.fail(
                "Parser Studio document-types entry "
                f"#{index} was not an object; cannot derive prompt version reference."
            )
        doc_type = str(entry.get("document_type", "")).strip()
        if not doc_type:
            continue
        saw_document_type = True
        versions_body = get_smoke_json(
            client,
            GetSmokeCase(
                f"parser-prompt-versions-scan-{doc_type}",
                f"/parser_studio/api/v1/document-types/{doc_type}/prompt/versions",
            ),
        )
        if not isinstance(versions_body, dict):
            pytest.fail(
                "Parser Studio prompt-version inventory response was not an object "
                f"for document_type {doc_type!r}."
            )
        versions = versions_body.get("versions")
        if not isinstance(versions, list):
            pytest.fail(
                "Parser Studio prompt-version inventory response did not contain a versions list "
                f"for document_type {doc_type!r}."
            )
        if not versions:
            continue
        for version_index, entry in enumerate(versions, start=1):
            if not isinstance(entry, dict):
                pytest.fail(
                    "Parser Studio prompt-version entry "
                    f"#{version_index} for document_type {doc_type!r} was not an object."
                )
            version_id = str(entry.get("version_id", "")).strip()
            if version_id:
                return doc_type, version_id

    if not saw_document_type:
        pytest.skip(
            "Skipping setup-backed detail GET smoke: missing prerequisite Parser Studio prompt version reference; "
            f"{_DOC_TYPES_CASE.path} returned no usable document_type values."
        )
    pytest.skip(
        "Skipping setup-backed detail GET smoke: missing prerequisite Parser Studio prompt version reference; "
        "prompt-version list endpoints returned no usable version_id entries."
    )


@pytest.fixture(scope="module")
def parser_tenant_api_key(client) -> str:
    body = get_smoke_json(client, _TENANTS_CASE)
    tenants = require_setup_list(
        body,
        _TENANTS_CASE,
        fields=("tenants",),
        prerequisite="Parser Studio tenant api_key",
        item_label="tenant",
    )
    return first_mapping_value(
        tenants,
        keys=("api_key",),
        source_case=_TENANTS_CASE,
        prerequisite="Parser Studio tenant api_key",
        item_label="tenant",
    )


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


def test_parser_studio_prompt_version_content_get_smoke_returns_200(
    client,
    parser_prompt_version_ref: tuple[str, str],
):
    doc_type, version_id = parser_prompt_version_ref
    assert_get_smoke_200(
        client,
        GetSmokeCase(
            "parser-doc-type-prompt-version-content",
            f"/parser_studio/api/v1/document-types/{doc_type}/prompt/versions/{version_id}",
        ),
    )
