# /batch Auth-Negative Blocker

## Purpose
This document records the current blocker for representative tenant-token auth-negative coverage on `/v1/documents/batch`.

It intentionally separates four things:
- the safe main-branch state
- the exact opt-in reproduction path
- the current observed outcomes for the two representative cases
- what must change before the auth gap can be considered closed

## Evidence Used In This Pass
- `tests/endpoints/batch/test_batch.py`
- `tests/endpoints/batch/test_batch_auth_characterization.py`
- `tests/endpoints/batch/conftest.py`
- `docs/operations/workflow.md`
- terminal output from:

```bash
./.venv/bin/python -m pytest tests/endpoints/batch/ -v
RUN_BATCH_AUTH_CHARACTERIZATION=1 ./.venv/bin/python -m pytest tests/endpoints/batch/test_batch_auth_characterization.py -v
```

Current blocker:
- verified rejection semantics are still not established for the representative `/documents/batch` tenant-token auth-negative cases
- the default batch suite intentionally excludes the blocked characterization so the main branch stays green

## Safe Main-Branch State
- `./.venv/bin/python -m pytest tests/endpoints/batch/ -v` stays green
- `tests/endpoints/batch/test_batch_auth_characterization.py` is opt-in behind `RUN_BATCH_AUTH_CHARACTERIZATION=1`
- timeout, transport failure, or `200` do not count as passing auth coverage

## Opt-In Reproduction Path

```bash
RUN_BATCH_AUTH_CHARACTERIZATION=1 ./.venv/bin/python -m pytest tests/endpoints/batch/test_batch_auth_characterization.py -v
```

This command re-runs both representative cases against the live endpoint:
- missing `X-Tenant-Token`
- invalid `X-Tenant-Token`

## Current Observed Outcomes

### 1. Missing `X-Tenant-Token`
Status: blocker confirmed from the latest opt-in run

Evidence:
- the request kept platform auth headers and omitted only `X-Tenant-Token`
- `POST /v1/documents/batch` failed with `ReadTimeout` after 30 seconds
- no HTTP response was received, so there is no confirmed `401` or `403` rejection semantics for this case

Current action:
- keep this case as opt-in characterization only
- do not treat timeout or hang as acceptable auth-negative coverage

### 2. Invalid `X-Tenant-Token`
Status: blocker confirmed from the latest opt-in run

Evidence:
- the request kept platform auth headers and sent `X-Tenant-Token: invalid-token-xyz`
- `POST /v1/documents/batch` returned `HTTP 200`
- the response was success-shaped rather than rejection-shaped; the latest diagnostic excerpt showed `summary.items = 4`, `summary.ok = 4`, and `summary.failed = 0`

Current action:
- keep this case as opt-in characterization only
- do not treat this as auth rejection; the invalid token case is currently being accepted by the live path

## What Is Still Unresolved
- whether the missing-token case should reject at the gateway, app, or some downstream auth layer
- whether the invalid-token case should reject as `401` or `403`
- whether any broader batch auth matrix is worth adding before these two representative cases reject correctly

## Safe Next Step
When auth-layer or staging behavior changes, rerun:

```bash
RUN_BATCH_AUTH_CHARACTERIZATION=1 ./.venv/bin/python -m pytest tests/endpoints/batch/test_batch_auth_characterization.py -v
```

Then verify:
- missing `X-Tenant-Token` returns confirmed `401` or `403`
- invalid `X-Tenant-Token` returns confirmed `401` or `403`

## Decision Boundary
- do not move these cases back into the default batch suite until both representative cases return confirmed rejection semantics
- do not declare the batch auth gap closed while one case times out and the other returns `200`
