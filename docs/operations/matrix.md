# Matrix Triage

Use evidence-first triage for opt-in `/parse` matrix failures.

See also: [Repo Roadmap](C:/Users/v_nel/Documents/verifyiq-api-regression/docs/knowledge-base/repo-roadmap.md)

## Decision Flow
1. Start with the latest terminal output.
2. Identify the failing `fileType`, pytest node ID, status code, and fixture metadata.
3. Inspect the actual response body and headers for contract clues before guessing cause.
4. Check whether the failing registry `fileType` matches the API-accepted request label or needs a remap.
5. Map the failing case back to the canonical fixture and registry row.
6. Classify narrowly:
   - endpoint regression
   - auth or proxy interception
   - fixture-selection issue
   - timeout or staging instability
   - unclear, needs more evidence
7. Only propose fixes after the failure class is supported by the evidence.

## FileType Mapping Example
Example: matrix failure for `TIN`

- Read the terminal failure first.
- Confirm the response body and `diagnose(...)` output.
- Check whether the registry label `TIN` matches the API-accepted request label.
- If the API expects `TINID`, treat `TIN -> TINID` as a live remapping check before blaming the endpoint.
- Then map the case back to the canonical registry row and review fixture status.

Interpretation:
- If the response body suggests unsupported or mismatched `fileType` and the registry label differs from the API label, prioritize remapping diagnosis first.
- If the API label is already correct and the failure remains on a stable confirmed canonical fixture, treat endpoint regression as stronger evidence.
