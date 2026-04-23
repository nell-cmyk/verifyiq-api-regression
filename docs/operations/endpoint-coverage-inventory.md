# Endpoint Coverage Inventory

## Purpose
Use this inventory to track practical API automation coverage at the endpoint-group level.

This is intentionally not a path-by-path busywork matrix. The current repo covers a small, high-value subset of the OpenAPI inventory, so the maintainable unit is the endpoint group plus its minimum required categories.

## Current Default-Suite Rule
- Canonical operator path: `./.venv/bin/python tools/run_regression.py`
- Current default live suite: parse-only `protected`
- Current stronger live gate: `./.venv/bin/python tools/run_regression.py --suite full`
- `smoke` remains planned terminology, not a broader current default

## Group Inventory

| Endpoint group | Approx. OpenAPI paths | Current automated coverage | Current categories covered | Minimum required categories | Priority | Onboarding status | Notes / blockers |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `parse` | 1 | Yes | protected live default, happy-path, auth-negative, request validation, selective contract, extended matrix | protected/smoke, contract, auth, negative | Critical | Covered | Current default suite. Success schema in `official-openapi.json` is still too generic; see `docs/knowledge-base/parse/openapi-drift-pilot.md`. |
| `batch` | 1 | Yes | happy-path, auth-negative, selective contract, validation, negative, partial-failure, safe-limit handling | smoke/protected candidate, contract, auth, negative | High | Partially covered | Representative tenant-token auth-negative coverage now exists. Batch still remains an opt-in lane, and default live selection is capped at 4 items. |
| `document-processing-adjacent` | 4 | No | none | smoke, contract, negative | High | Not onboarded | `/v1/documents/check-cache`, `/v1/documents/cache`, `/v1/documents/crosscheck`, `/v1/documents/fraud-status/{job_id}` are the most natural next expansion candidates if repo scope grows beyond parse/batch. |
| `health` | 5 | No | none | smoke, basic contract | Medium | Not onboarded | Good future candidate only after the repo decides whether a broader cross-endpoint smoke suite should exist. |
| `applications-api` | 35 | No | none | smoke, contract, auth, negative | Medium | Scope-blocked | Large surface under `/api/v1/applications/*`; requires an explicit repo-scope decision before onboarding. |
| `monitoring` | 69 | No | none | smoke, contract, auth, negative | Medium | Scope-blocked | Operational/reporting surface with unclear value for this repo's current charter. |
| `parser-studio` | 43 | No | none | smoke, contract, auth, negative | Medium | Scope-blocked | Configuration and admin-adjacent surface; do not onboard casually. |
| `qa` | 15 | No | none | smoke, contract, auth, negative | Medium | Scope-blocked | QA/review surface is outside the current repo's primary parse/batch regression focus. |
| `admin` | 8 | No | none | isolated smoke only, negative, safety review | Low | Safety-blocked | Contains admin-style and destructive-looking paths. Never add to the default suite. |
| `other-service-surfaces` | 37 | No | none | explicit scope review first | Low | Scope-blocked | Mixed legacy, gateway, benchmark, and service-specific paths. Treat as out of scope until product ownership and value are clear. |

## Current Coverage Notes
- `official-openapi.json` currently exposes 218 paths.
- The current repo's meaningful live coverage is intentionally concentrated on `/v1/documents/parse` and `/v1/documents/batch`.
- Parse matrix breadth is opt-in and intentionally limited to one canonical enabled fixture per registry file type.
- Batch coverage reuses registry-backed fixtures and enforces a safe default request size of 4 items.

## Onboarding Rule For New Endpoint Groups
Before a new endpoint group is added here as "in progress" or "covered", define:

1. Why the endpoint belongs in this repo's scope.
2. Whether the endpoint is safe for live automation.
3. The minimum categories required for first onboarding.
4. Whether the endpoint belongs in the default `protected` suite, a future `smoke` suite, or an opt-in lane only.
5. Which fixtures or live prerequisites the endpoint needs.

## Immediate Follow-ups
- Decide whether `batch` should remain opt-in or join a future curated smoke lane now that representative auth-negative coverage exists.
- Extend the parse OpenAPI drift pilot with safe observed artifacts from a future protected run.
- Do not broaden the default suite until a deliberate cross-endpoint smoke composition exists.
