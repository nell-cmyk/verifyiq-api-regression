# Batch Ground-Truth Unusable Result Triage

## 2026-04-24 Full Export
- Source run: `reports/batch_ground_truth/batch_ground_truth_2026-04-24-T092636_087780Z`.
- Related recovery run: `reports/batch_ground_truth/recovery_2026-04-24-T114901_567153Z`; that recovery selected prior `503` rows and did not modify the original full-run workbooks.
- The full run had 131 `unusable_result` rows. All were HTTP `200` row results with `ok=true`, `error_type=ValueError`, and the exporter error `successful batch result is missing a usable summaryResult[0] payload`.
- Every affected workbook `_meta` row had a matching raw batch artifact by `correlation_id`.

## Raw Response Pattern
- All 131 rows used the same `data` key set: `authenticityScore`, `calculatedFields`, `completenessBreakdown`, `completenessScore`, `documentQuality`, `extractionStatus`, `fileType`, `fraudReport`, `fraudScore`, `mathematicalFraudReport`, `metadataFraudReport`, `qualityCheck`, `qualityScore`, `summaryOCR`, `summaryResult`, `timings`, and `transactionsOCR`.
- The parsed-payload containers were empty for every affected row: `summaryOCR=[]`, `summaryResult=[]`, `calculatedFields=[]`, and `transactionsOCR=[]`.
- `extractionStatus` was `not_attempted` for every affected row.
- `data.fileType` matched the requested fileType for every affected row, including current aliases such as `ACR -> ACRICard`, `TIN -> TINID`, and `WaterBill -> WaterUtilityBillingStatement`.
- No raw response contained reliable parsed fields outside `summaryResult[0]` that could be safely mapped into the ground-truth workbook.

## Quality-Gate Reasons
- `failed document_classification`: 85 rows.
- Low contrast or overall quality score below threshold: 38 rows.
- `failed blankness`: 5 rows.
- Skew below threshold / overall quality score below threshold: 2 rows.
- `failed resolution`: 1 row.

## Handling Guidance
- Do not bulk-mark these fixtures invalid from the exporter result alone.
- Treat these rows as quality-gated no-extraction responses, not as recoverable alternate success shapes.
- A safe exporter success-mapping change is not available unless a future raw response includes reliable parsed fields outside `summaryResult[0]`.
- The exporter now preserves these rows in the full/audit workbook and triages them as `http_200_no_payload_quality_gate` when the HTTP `200` / `ok=true` response has empty parsed containers, `extractionStatus=not_attempted`, and a quality-gate failure in `documentQuality` or `qualityCheck.issueDescription`.
- These rows remain excluded from clean ground-truth candidate workbooks until a fixture correction, replacement, API/model change, or targeted rerun produces a usable parsed payload.
