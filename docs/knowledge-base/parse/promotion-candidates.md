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

### Candidate: `2026-04-19 BarangayCertificate 2025_08_05_barangay_certificate_additional_2`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `BarangayCertificate`
- Request fileType used: `BarangayCertificate`
- Registry row: `111`
- Fixture name: `2025_08_05_barangay_certificate_additional_2`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/Brgy Cert/2025_08_05_barangay_certificate_additional_2.jpeg`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 CertificateOfEmployment 2006_Certificate of employment`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `CertificateOfEmployment`
- Request fileType used: `CertificateOfEmployment`
- Registry row: `346`
- Fixture name: `2006_Certificate of employment`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/COE/2006_Certificate of employment.jpg`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 ElectricUtilityBillingStatement TC02a_ElectricityBill_Meralco`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `ElectricUtilityBillingStatement`
- Request fileType used: `ElectricUtilityBillingStatement`
- Registry row: `617`
- Fixture name: `TC02a_ElectricityBill_Meralco`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/Cross match/TC02a_ElectricityBill_Meralco.pdf`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 Payslip TC02a_Payslip_Abuyan`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `Payslip`
- Request fileType used: `Payslip`
- Registry row: `905`
- Fixture name: `TC02a_Payslip_Abuyan`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/Cross match/TC02a_Payslip_Abuyan.pdf`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 PhilippineNationalID TC03a_PhilSysID_JRUA`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `PhilippineNationalID`
- Request fileType used: `PhilippineNationalID`
- Registry row: `1336`
- Fixture name: `TC03a_PhilSysID_JRUA`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/Cross match/TC03a_PhilSysID_JRUA.pdf`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 SSSID TC03e_SSSID_JRUA`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `SSSID`
- Request fileType used: `SSSID`
- Registry row: `1361`
- Fixture name: `TC03e_SSSID_JRUA`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/Cross match/TC03e_SSSID_JRUA.pdf`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 UMID TC03p_UMID_JRUA`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `UMID`
- Request fileType used: `UMID`
- Registry row: `1386`
- Fixture name: `TC03p_UMID_JRUA`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/Cross match/TC03p_UMID_JRUA.png`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 DriversLicense DL ID`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `DriversLicense`
- Request fileType used: `DriversLicense`
- Registry row: `414`
- Fixture name: `DL ID`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/ID/DL ID .png`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 PhilHealthID Philhealth ID`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `PhilHealthID`
- Request fileType used: `PhilHealthID`
- Registry row: `1335`
- Fixture name: `Philhealth ID`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/ID/Philhealth ID.png`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 PostalID Postal ID_56058_2024-11-18 01_07_15 Postal ID - FIRST LAST`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `PostalID`
- Request fileType used: `PostalID`
- Registry row: `1340`
- Fixture name: `Postal ID_56058_2024-11-18 01_07_15 Postal ID - FIRST LAST`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/ID/Postal ID_56058_2024-11-18 01_07_15 Postal ID - FIRST LAST.jpg`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 TIN 462065192_1469876900470951_1855405225948407119_n__2`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `TIN`
- Request fileType used: `TINID`
- Registry row: `1384`
- Fixture name: `462065192_1469876900470951_1855405225948407119_n__2`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/ID/462065192_1469876900470951_1855405225948407119_n.jpeg`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 VotersID 61000_Voter ID__2`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `VotersID`
- Request fileType used: `VotersID`
- Registry row: `1500`
- Fixture name: `61000_Voter ID__2`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/ID/61000_Voter ID.jpg`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 ACR 59002_Heather_ACR ID`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `ACR`
- Request fileType used: `ACRICard`
- Registry row: `5`
- Fixture name: `59002_Heather_ACR ID`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/ID/ACR/59002_Heather_ACR ID.jpg`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note:

### Candidate: `2026-04-19 SECCertificateOfIncorporation 2024_12_04_sec_incorporation_certificate`
- Candidate status: `pending`
- Promoted status: `not promoted`
- Environment:
- Matrix run command: `/Users/nellvalenzuela/Documents/verifyiq-api-regression/.venv/bin/python /Users/nellvalenzuela/Documents/verifyiq-api-regression/tools/reporting/run_parse_matrix_with_summary.py`
- Registry fileType: `SECCertificateOfIncorporation`
- Request fileType used: `SECCertificateOfIncorporation`
- Registry row: `1341`
- Fixture name: `2024_12_04_sec_incorporation_certificate`
- GCS URI: `gs://verifyiq-internal-testing/QA/GroundTruth/SEC COI/2024_12_04_sec_incorporation_certificate.pdf`
- Result summary: passed in the matrix summary artifact
- Evidence:
  - terminal result: passed
  - response-body clue summary:
  - diagnose() clue summary:
- Follow-up note: