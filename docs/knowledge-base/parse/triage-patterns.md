# /parse Triage Patterns

This page keeps stable `/parse` triage knowledge. For operator steps and command sequences, use [Matrix Triage](../../operations/matrix.md).

## Keep The Three fileType Labels Separate
- Registry `fileType`: the label stored in the fixture registry.
- Request `fileType`: the explicit repo-mapped label sent to the API.
- Response `fileType`: the label echoed back by the live endpoint.
- When a failure involves `fileType`, diagnose those three labels directly instead of collapsing them into one value.

## Current Explicit Request Remaps
- `TIN -> TINID`
- `ACR -> ACRICard`
- `WaterBill -> WaterUtilityBillingStatement`
- Unmapped registry labels are sent unchanged.
- This remap table is intentionally explicit and small. New aliases belong in `tests/endpoints/parse/file_types.py` and should be treated as deliberate compatibility decisions, not ad hoc response-driven guesses.

## Durable Endpoint Signals
- Happy-path `/parse` coverage expects a 200 JSON response containing `fileType`, `documentQuality`, `summaryOCR`, `summaryResult`, and `calculatedFields`.
- `calculatedFields == {"pageNumber": 1}` is treated as the config-missing stub value, not as a valid computed-fields result.
- Auth-negative `/parse` requests do not reliably fast-fail. In the protected baseline, either `401/403` or a short timeout is treated as a valid negative signal because both show the request did not successfully complete the parse path.

## Recurring Failure Classes
- `timeout`: the live parse request exceeded the matrix timeout.
- `transport-error`: the request failed before an HTTP response was received.
- `auth-proxy`: HTML or Google auth/IAP clues suggest upstream interception instead of API behavior.
- `non-200`: an HTTP response arrived, but it was not 200 and was not better explained as `auth-proxy`.
- `non-json-200`: the endpoint returned 200, but the body was not JSON.
- `filetype-mismatch`: the response `fileType` did not echo the mapped request `fileType`.
- `missing-fields`: the 200 JSON body omitted one or more required contract fields.
- `failed`: the failure did not fit a more specific durable class yet.

## Durable Evidence Rule
- Summary artifacts are useful for classification and trend spotting.
- The actual evidence still comes from saved terminal output, response clues, status codes, headers, and fixture metadata.
