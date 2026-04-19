# /parse Promotion Candidates

Use this file to record reviewed promotion candidates for canonical fixtures that were `unverified` in the registry and later passed in the opt-in `/parse` matrix.

See also: [Fixtures and Promotion](fixtures-and-promotion.md), [Triage Patterns](triage-patterns.md)

Rules:
- This file is the reviewed candidate ledger only.
- The spreadsheet remains the human source of truth.
- Generated YAML remains derived data.
- Pytest execution must stay side-effect free.
- Candidate status does not mean promoted status.
- Use the generated run summary under `reports/parse/matrix/` as draft source material, not as repo truth.
- Do not turn this page into a run-by-run session log.

## Entry Template

### Candidate: `<date> <registry fileType> <fixture name>`
- Candidate status: `pending` | `needs another run` | `rejected`
- Promoted status: `not promoted` | `promoted in spreadsheet`
- Environment:
- Matrix run command:
- Registry fileType:
- Request fileType used:
- Registry row:
- Fixture name:
- GCS URI:
- Result summary:
- Evidence:
  - terminal result:
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

## Entries

Add new candidates below this line.
