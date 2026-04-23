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
- the latest opt-in rerun in this pass kept the missing-token timeout and showed the invalid-token case timing out as well, so the invalid-token behavior is now confirmed unstable rather than consistently rejection-shaped

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
Status: blocker confirmed from repeated opt-in runs

Evidence:
- the request kept platform auth headers and sent `X-Tenant-Token: invalid-token-xyz`
- one recent opt-in characterization returned `HTTP 200`
- that `200` response was success-shaped rather than rejection-shaped; the diagnostic excerpt showed `summary.items = 4`, `summary.ok = 4`, and `summary.failed = 0`
- the latest opt-in rerun in this pass instead failed with `ReadTimeout` after 30 seconds
- this case therefore does not have stable confirmed rejection semantics; it has been observed as both accepted (`200`) and non-responsive (`ReadTimeout`)

Current action:
- keep this case as opt-in characterization only
- do not treat either observed outcome as auth rejection; this case currently lacks stable rejection behavior

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

## Backend Engineering Handoff

### Scope
- endpoint: `/v1/documents/batch`
- auth scope: representative tenant-token auth-negative cases only
- cases in scope:
  - missing `X-Tenant-Token`
  - invalid `X-Tenant-Token`
- safe repo state to preserve:
  - `./.venv/bin/python -m pytest tests/endpoints/batch/ -v` stays green
  - opt-in characterization remains gated behind `RUN_BATCH_AUTH_CHARACTERIZATION=1`

### Exact Reproduction
Prerequisites:
- use the normal live `/documents/batch` environment documented in `AGENTS.md`
- set `RUN_BATCH_AUTH_CHARACTERIZATION=1`

Command:

```bash
RUN_BATCH_AUTH_CHARACTERIZATION=1 ./.venv/bin/python -m pytest tests/endpoints/batch/test_batch_auth_characterization.py -v
```

### Backend Defect Candidates
1. Missing tenant token does not produce confirmed rejection semantics for `/documents/batch`.
   Current evidence: the representative missing-token case times out after 30 seconds instead of returning `401` or `403`.
2. Invalid tenant token does not produce stable confirmed rejection semantics for `/documents/batch`.
   Current evidence: the representative invalid-token case has been observed returning success-shaped `HTTP 200` on one opt-in run and `ReadTimeout` after 30 seconds on a later opt-in rerun.

### Backend/API Follow-Up Requested
- confirm the intended rejection behavior for the two representative tenant-token failures on `/documents/batch`
- correct the live behavior so both cases reject explicitly instead of hanging or being accepted
- keep the decision boundary narrow: repo auth-negative coverage for this tranche can close only when both representative cases return verified `401` or `403`

### Verification After Backend Change
After a backend or auth-layer fix, rerun exactly:

```bash
RUN_BATCH_AUTH_CHARACTERIZATION=1 ./.venv/bin/python -m pytest tests/endpoints/batch/test_batch_auth_characterization.py -v
```

Successful closure criteria for this tranche:
- missing `X-Tenant-Token` returns confirmed `401` or `403`
- invalid `X-Tenant-Token` returns confirmed `401` or `403`
- neither case times out, hangs, or returns `200`

## Decision Boundary
- do not move these cases back into the default batch suite until both representative cases return confirmed rejection semantics
- do not declare the batch auth gap closed while either case times out, hangs, or returns `200`
