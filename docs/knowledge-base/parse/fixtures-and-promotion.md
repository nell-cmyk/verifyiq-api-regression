# /parse Fixtures and Promotion

This page records how `/parse` fixtures move from human curation into automated coverage, and how matrix passes can become promotion candidates. It is intentionally about state and meaning, not run commands.

See also: [Promotion Candidates](promotion-candidates.md), [Matrix Triage](../../operations/matrix.md)

## Fixture Lifecycle
1. The human-maintained fixture source lives in `tools/fixture_registry_source/qa_fixture_registry.xlsx`.
2. JSON-driven onboarding can add supplemental fixtures into `tools/fixture_registry_source/supplemental_fixture_registry.yaml`.
3. `tools/generate_fixture_registry.py` materializes the curated sources into the shared generated registry at `tests/fixtures/fixture_registry.yaml`.
4. The generator also writes `tests/endpoints/parse/fixture_registry.yaml` as a generated `/parse` compatibility copy.
5. Pytest reads the shared generated YAML through `tests/endpoints/parse/registry.py` and `tests/fixtures/registry.py`.
6. Happy-path `/parse` requests use remote `gs://` fixtures because the API fetches files server-side.

## Registry Normalization
- Rows without a `gs://` path do not enter the generated registry.
- Composite spreadsheet labels such as `A || B` are split into one generated record per individual `file_type`, while preserving the original source label and row for traceability.
- `No fileType` and `Fraud - Skipped` stay in the generated registry as `excluded` records instead of canonical coverage.
- Source fileType status, assignee, workflow status, unsupported-format annotations, and known batch warning/error metadata are preserved in the generated registry for shared endpoint tooling.
- JSON-driven onboarding and selected-fixture execution normalize imported `gs://` paths before they touch the supplemental registry or the opt-in selected run.
- Unsupported JSON-imported formats are skipped explicitly instead of being added to the supplemental registry or selected for execution. Current supported `/parse` extensions are `pdf`, `png`, `jpg`, `jpeg`, `tiff`, `tif`, `heic`, and `heif`.

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
- `--fixtures-json` is a separate opt-in execution mode for exact selected fixtures; it does not change the default canonical-only selection policy.

## Promotion Candidate Meaning
- A promotion candidate starts when an `unverified` canonical fixture passes the opt-in matrix.
- The matrix summary artifact can draft candidate blocks, but those drafts are review input only.
- [promotion-candidates.md](promotion-candidates.md) is the durable repo ledger for reviewed candidates; it is not the promotion action itself.
- The spreadsheet remains the human source of truth for actual promotion decisions.
- Candidate status records review state such as `pending`, `needs another run`, or `rejected`; it does not change pytest behavior on its own.

## Durable Boundary
- Updating the spreadsheet or supplemental YAML and regenerating YAML changes fixture status for `/parse`, `/documents/batch`, and future registry-backed endpoint tooling.
- `./.venv/bin/python tools/onboard_fixture_json.py --json /path/to/fixtures.json` is the reusable path for JSON-driven additions; it writes only missing supported fixtures into the supplemental YAML, reports skipped unsupported entries, and regenerates the tracked registry when needed.
- Adding or editing a promotion-candidate entry preserves context for humans; it does not mutate the registry.
