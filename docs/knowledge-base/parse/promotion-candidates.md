# /parse Promotion Candidates

Use this file to record manual promotion candidates for canonical fixtures that were `unverified` in the registry and later passed in the opt-in `/parse` matrix.

Rules:
- This file is a knowledge-base record only.
- The spreadsheet remains the human source of truth.
- Generated YAML remains derived data.
- Pytest execution must stay side-effect free.
- Candidate status does not mean promoted status.

## Entry Template

### Candidate: `<date> <registry fileType> <fixture name>`
- Candidate status: `pending` | `needs another run` | `rejected`
- Promoted status: `not promoted` | `promoted in spreadsheet`
- Environment:
- Matrix run command:
- Registry fileType:
- API fileType used:
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
