# /parse Knowledge Base

This folder is the durable reference layer for `/parse`. Keep workflow steps and commands in `docs/operations/`; keep this folder focused on stable behavior boundaries, fixture knowledge, and recurring triage context that should survive beyond any single session.

See also: [Matrix Triage](../../operations/matrix.md), [Fixtures and Promotion](fixtures-and-promotion.md), [Triage Patterns](triage-patterns.md), [OpenAPI Drift Pilot](openapi-drift-pilot.md), [Promotion Candidates](promotion-candidates.md)

## Coverage Boundaries

### Protected baseline
- The protected baseline is the default `/parse` regression gate for this repo.
- It covers one happy-path parse request plus auth-negative and request-validation behavior.
- It intentionally excludes matrix collection so the default baseline signal stays stable and easy to compare across changes.

### Matrix
- The matrix is opt-in live coverage across one canonical enabled fixture per registry `file_type`.
- It answers broad contract questions across fileTypes and surfaces promotion candidates and recurring failure classes.
- Its assertions stay generic on purpose; fileType-specific assertions belong in dedicated coverage when a fileType needs them.

### Full regression
- Full regression is the stronger confidence tier: baseline first, matrix second.
- It is the right mental model when a change needs both the protected contract signal and broader fileType coverage.

## Pages In This Folder
- [Fixtures and Promotion](fixtures-and-promotion.md): how spreadsheet fixtures become canonical matrix inputs and what promotion-candidate status means.
- [Triage Patterns](triage-patterns.md): explicit fileType remap policy plus durable endpoint and failure signals.
- [OpenAPI Drift Pilot](openapi-drift-pilot.md): current safe contract-vs-repo comparison for `/v1/documents/parse`.
- [Promotion Candidates](promotion-candidates.md): reviewed candidate ledger only.

## What Does Not Belong Here
- Operator commands, run sequences, or troubleshooting flowcharts.
- Session-by-session run status or transcript-style notes.
- Repo-wide governance already defined in `AGENTS.md`.
