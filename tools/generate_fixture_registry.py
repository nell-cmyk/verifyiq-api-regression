#!/usr/bin/env python3
"""Generate the machine-readable /parse fixture registry from the QA spreadsheet.

Source (human-maintained):
  tools/fixture_registry_source/qa_fixture_registry.xlsx
Output (automation source of truth):
  tests/endpoints/parse/fixture_registry.yaml

Re-run this after editing the spreadsheet. Idempotent.

Usage:
  pip install -r tools/requirements.txt
  python tools/generate_fixture_registry.py

Classification rules (schema_version: 2):
  - Rows with no gs:// path are dropped.
  - fileType == "No fileType" or "Fraud - Skipped"
      → verification_status=excluded, enabled=False (kept for traceability).
  - fileType containing "||" (composite label) is SPLIT into one record per
    individual fileType. Each split record is enabled on its own merit; the
    original composite label is preserved in `source_file_type` and the source
    row number in `source_row`.
  - fileType Status "✓"        → verification_status=confirmed, enabled=True.
  - fileType Status "⚠ Verify" → verification_status=unverified, enabled=True.
    ("Verify" is a human QA tag, not an automation gate — both are valid
    fixture candidates for Phase 2.)
  - anything else              → verification_status=unknown, enabled=False.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import openpyxl
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_XLSX = REPO_ROOT / "tools" / "fixture_registry_source" / "qa_fixture_registry.xlsx"
OUTPUT_YAML = REPO_ROOT / "tests" / "endpoints" / "parse" / "fixture_registry.yaml"
SHEET_NAME = "All"
HEADER_ROW = 4  # Rows 1–2 are title, row 3 blank, row 4 is the header. Data from row 5.
SCHEMA_VERSION = 2

EXCLUDED_FILE_TYPES = {"No fileType", "Fraud - Skipped"}
COMPOSITE_DELIMITER = "||"
CONFIRMED_MARK = "✓"
UNVERIFIED_MARK = "⚠ Verify"


def classify(file_type: str, file_type_status: str) -> tuple[str, bool]:
    """Return (verification_status, enabled) for a (post-split) fileType."""
    if file_type in EXCLUDED_FILE_TYPES:
        return "excluded", False
    if file_type_status == CONFIRMED_MARK:
        return "confirmed", True
    if file_type_status == UNVERIFIED_MARK:
        return "unverified", True
    return "unknown", False


def base_name_from_uri(uri: str) -> str:
    base = uri.rsplit("/", 1)[-1]
    stem = base.rsplit(".", 1)[0] if "." in base else base
    return stem.strip() or "fixture"


def reserve_name(candidate: str, used: set[str]) -> str:
    """Return a name unique within `used`, appending __2, __3, ... on collision."""
    name = candidate
    n = 2
    while name in used:
        name = f"{candidate}__{n}"
        n += 1
    used.add(name)
    return name


def main() -> int:
    if not SOURCE_XLSX.exists():
        print(f"ERROR: source spreadsheet not found at {SOURCE_XLSX}", file=sys.stderr)
        return 2

    wb = openpyxl.load_workbook(SOURCE_XLSX, data_only=True)
    if SHEET_NAME not in wb.sheetnames:
        print(f"ERROR: sheet {SHEET_NAME!r} not found; sheets: {wb.sheetnames}", file=sys.stderr)
        return 2
    ws = wb[SHEET_NAME]

    fixtures: list[dict] = []
    used_names: set[str] = set()
    counts: Counter[str] = Counter()
    split_rows = 0

    for row_idx, row in enumerate(
        ws.iter_rows(min_row=HEADER_ROW + 1, values_only=True),
        start=HEADER_ROW + 1,
    ):
        # Columns: Folder | fileType | gsutil Path | fileType Status | Assignee | Status | (unused)
        folder, file_type, gcs_uri, ft_status, _assignee, _row_status, *_ = row
        gcs_uri = gcs_uri.strip() if isinstance(gcs_uri, str) else gcs_uri
        if not gcs_uri or not str(gcs_uri).startswith("gs://"):
            counts["skipped_no_gcs"] += 1
            continue

        raw_file_type = (file_type or "").strip()
        ft_status_clean = (ft_status or "").strip()
        folder_clean = (folder or "").strip() or None
        base_name = base_name_from_uri(str(gcs_uri))

        # Split composite labels (e.g. "A || B") into one record per fileType.
        is_composite = COMPOSITE_DELIMITER in raw_file_type
        if is_composite:
            split_rows += 1
            parts = [p.strip() for p in raw_file_type.split(COMPOSITE_DELIMITER) if p.strip()]
        else:
            parts = [raw_file_type]

        for part in parts:
            verification_status, enabled = classify(part, ft_status_clean)
            counts[verification_status] += 1
            # Disambiguate split-record names by suffixing the individual fileType.
            candidate = f"{base_name}__{part}" if is_composite and part else base_name
            fixtures.append({
                "name": reserve_name(candidate, used_names),
                "file_type": part or None,
                "gcs_uri": str(gcs_uri),
                "source_folder": folder_clean,
                "source_file_type": raw_file_type or None,
                "source_row": row_idx,
                "verification_status": verification_status,
                "enabled": enabled,
            })

    fixtures.sort(key=lambda f: (f["source_folder"] or "", f["file_type"] or "", f["name"]))

    OUTPUT_YAML.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# AUTO-GENERATED by tools/generate_fixture_registry.py — do not edit by hand.\n"
        f"# Source: {SOURCE_XLSX.relative_to(REPO_ROOT).as_posix()}\n"
        "# Edit the spreadsheet and rerun the generator to update this file.\n"
    )
    doc = {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE_XLSX.relative_to(REPO_ROOT).as_posix(),
        "total": len(fixtures),
        "composite_rows_split": split_rows,
        "counts": dict(sorted(counts.items())),
        "fixtures": fixtures,
    }
    with OUTPUT_YAML.open("w", encoding="utf-8", newline="\n") as f:
        f.write(header)
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, width=160)

    enabled_count = sum(1 for x in fixtures if x["enabled"])
    print(
        f"Wrote {len(fixtures)} fixture records ({enabled_count} enabled; "
        f"{split_rows} source rows split into multiple records) to "
        f"{OUTPUT_YAML.relative_to(REPO_ROOT).as_posix()}",
        file=sys.stderr,
    )
    for k, v in sorted(counts.items()):
        print(f"  {k:14s} {v}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
