# /parse Fixtures and Promotion

This page records how `/parse` fixtures move from human curation into automated coverage, and how matrix passes can become promotion candidates. It is intentionally about state and meaning, not run commands.

See also: [Promotion Candidates](promotion-candidates.md), [Matrix Triage](../../operations/matrix.md)

## Fixture Lifecycle
1. The human-maintained fixture source lives in `tools/fixture_registry_source/qa_fixture_registry.xlsx`.
2. `tools/generate_fixture_registry.py` materializes that spreadsheet into `tests/endpoints/parse/fixture_registry.yaml`.
3. Pytest reads the generated YAML through `tests/endpoints/parse/registry.py`.
4. Happy-path `/parse` requests use remote `gs://` fixtures because the API fetches files server-side.

## Registry Normalization
- Rows without a `gs://` path do not enter the generated registry.
- Composite spreadsheet labels such as `A || B` are split into one generated record per individual `file_type`, while preserving the original source label and row for traceability.
- `No fileType` and `Fraud - Skipped` stay in the generated registry as `excluded` records instead of canonical coverage.

## Registry Status Meanings
- `confirmed`: enabled and already spreadsheet-verified.
- `unverified`: enabled and still eligible for matrix coverage and promotion review.
- `excluded`: kept for traceability, but not enabled for canonical coverage.
- `unknown`: disabled until the spreadsheet status is clarified.

## Canonical Matrix Selection
- The matrix does not run every enabled registry row.
- `load_canonical_fixtures()` takes the first enabled record for each distinct registry `file_type`.
- "First" is deterministic because the generator sorts records by `(source_folder, file_type, name)` before writing YAML.
- The result is one canonical fixture per fileType, not exhaustive per-file coverage.

## Promotion Candidate Meaning
- A promotion candidate starts when an `unverified` canonical fixture passes the opt-in matrix.
- The matrix summary artifact can draft candidate blocks, but those drafts are review input only.
- [promotion-candidates.md](promotion-candidates.md) is the durable repo ledger for reviewed candidates; it is not the promotion action itself.
- The spreadsheet remains the human source of truth for actual promotion decisions.
- Candidate status records review state such as `pending`, `needs another run`, or `rejected`; it does not change pytest behavior on its own.

## Durable Boundary
- Updating the spreadsheet and regenerating YAML changes fixture status.
- Adding or editing a promotion-candidate entry preserves context for humans; it does not mutate the registry.
