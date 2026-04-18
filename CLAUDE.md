# VerifyIQ API Regression Suite

## Scope
This repository is for API regression automation only.

Do not add:
- ClickUp workflows
- ticket analysis logic
- dev comment workflows
- manual QA orchestration
- business-process tooling unrelated to API regression

This repository should:
- send API requests
- validate responses
- support repeatable regression checks
- scale cleanly to more endpoints over time

## Stack
- Language: Python 3.x
- Framework: pytest
- HTTP client: httpx (preferred) or requests

## Environment variables
| Variable                       | Required | Description                                                                   |
|--------------------------------|----------|-------------------------------------------------------------------------------|
| BASE_URL                       | yes      | API base URL (no trailing /) — see known values below                         |
| TENANT_TOKEN                   | yes      | Sent as `X-Tenant-Token` request header                                       |
| API_KEY                        | yes      | App BearerAuth key (e.g. `sk_...`). Sent as `Authorization: Bearer <API_KEY>` |
| IAP_CLIENT_ID                  | yes      | OAuth 2.0 client ID (audience) of the IAP-protected backend                   |
| GOOGLE_APPLICATION_CREDENTIALS | yes      | Path to service account JSON with `roles/iap.httpsResourceAccessor`           |
| PARSE_FIXTURE_FILE             | yes      | `gs://` URI for /parse happy path. API fetches server-side; no client creds   |
| PARSE_FIXTURE_FILE_TYPE        | yes      | Document type string matching the fixture (e.g. `Payslip`)                    |

Known BASE_URL values:
- Dev: `https://parser-dev.boostkh.com`
- Staging: `https://parser-staging.boostkh.com`

Fail fast with a clear error if required variables are missing — do not let tests run against undefined config.

## How to run
```bash
pytest tests/ -v
pytest tests/endpoints/parse/ -v     # single endpoint
pytest -k "test_name" -v             # single test
```

## Directory layout
```
tests/
  conftest.py              # shared fixtures, client setup
  client.py                # thin HTTP client wrapper
  config.py                # env var loading with fail-fast
  endpoints/
    parse/
      test_parse.py        # all /parse tests
      fixtures.py          # parse-specific fixtures/payloads
  fixtures/                # shared fixture data (JSON, etc.)
```

Each new endpoint gets its own folder under `tests/endpoints/`. Follow the parse pattern.

## OpenAPI spec
`official-openapi.json` is the contract reference for all endpoints. Use it for method, path, required fields, and response schema. It is not the driver of test design — tests are based on observed endpoint behavior.

## Endpoint notes

### POST /v1/documents/parse
- Always include `"pipeline": { "use_cache": false }` in every request body.
- Required fields: `file` (GCS/S3/HTTP URL), `fileType` (document type string).
- Primary assertion targets: `fileType`, `documentQuality`, `summaryOCR`, `summaryResult`, `calculatedFields`.
- Known fragile: `calculatedFields` returns only `{"pageNumber": 1}` when the computed_fields config is missing — treat an empty or stub `calculatedFields` as a potential regression signal.
- GCS fixture paths use `gs://` URIs. Fixture accessibility is environment-specific — a path valid on dev may not be accessible on staging.

## Engineering rules
- Keep the architecture pragmatic.
- Avoid overengineering.
- Separate config, client, endpoint logic, assertions, and fixtures clearly.
- Reuse code where it improves clarity or future endpoint expansion.
- Do not add abstractions without a clear payoff.

## Test rules
- Base tests on the real endpoint contract and actual behavior.
- Do not invent requirements.
- Do not add generic low-value tests.
- Prioritize meaningful happy paths, negative cases, boundary checks, response structure validation, and important business assertions.
- Make failures readable and actionable.

## Configuration rules
- Externalize all config via environment variables.
- Do not hardcode secrets or base URLs.
- Fail fast with clear errors if required config is missing.

## Working style
- Be direct.
- Avoid filler.
- Ask questions only if missing information would materially block correct implementation.
- If not blocked, make a brief assumption and proceed.
- Prefer concrete deliverables over long explanations.

## Execution rules
When implementing or changing the suite:
1. Inspect the current workspace.
2. Align with existing patterns unless they are weak.
3. Make the minimum necessary structural changes.
4. Implement.
5. Validate (run the suite or the relevant endpoint tests).
6. Show exact run commands.

## Output rules
- Keep narration compact.
- Show file-by-file changes when relevant.
- State assumptions briefly.
- State what was not validated directly.
