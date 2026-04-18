# Matrix Triage

Use evidence-first triage for opt-in `/parse` matrix failures.

See also: [Repo Roadmap](C:/Users/v_nel/Documents/verifyiq-api-regression/docs/knowledge-base/repo-roadmap.md)

## Decision Flow
1. Start with the latest terminal output.
2. Identify the failing `fileType`, pytest node ID, status code, and fixture metadata.
3. Inspect the actual response body and headers for contract clues before guessing cause.
4. Map the failing case back to the canonical fixture and registry row.
5. Classify narrowly:
   - endpoint regression
   - auth or proxy interception
   - fixture-selection issue
   - timeout or staging instability
   - unclear, needs more evidence
6. Only propose fixes after the failure class is supported by the evidence.

## FileType Mapping Example
Example: matrix failure for `Payslip`

- Read the terminal failure first.
- Confirm the response body and `diagnose(...)` output.
- Map `Payslip` to the canonical registry row selected for the run.
- Check whether that canonical row is `confirmed` or `unverified`, and whether a later confirmed candidate exists in the registry.

Interpretation:
- If the response body shows a contract or parser failure on a stable confirmed canonical fixture, treat it as stronger endpoint-regression evidence.
- If the failing canonical fixture is unverified and a later confirmed candidate exists, treat fixture selection as a live hypothesis before blaming the endpoint.
