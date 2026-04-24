#!/usr/bin/env python3
"""Onboard fixture JSON into the /parse registry flow."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.endpoints.parse.fixture_json import normalize_fixture_json_entries
from tests.endpoints.parse.registry import load_registry

SHARED_OUTPUT_YAML = REPO_ROOT / "tests" / "fixtures" / "fixture_registry.yaml"
PARSE_COMPAT_OUTPUT_YAML = REPO_ROOT / "tests" / "endpoints" / "parse" / "fixture_registry.yaml"
OUTPUT_YAML = SHARED_OUTPUT_YAML
SUPPLEMENTAL_YAML = (
    REPO_ROOT / "tools" / "fixture_registry_source" / "supplemental_fixture_registry.yaml"
)
SUPPLEMENTAL_SCHEMA_VERSION = 1
VALID_VERIFICATION_STATUSES = {"confirmed", "unverified", "excluded", "unknown"}


def _folder_file_type_map(fixtures: list[dict]) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for fixture in fixtures:
        folder = fixture.get("source_folder")
        file_type = fixture.get("file_type")
        if not folder or not file_type:
            continue
        mapping.setdefault(str(folder), set()).add(str(file_type))
    return mapping


def _entry_exists(entry: dict, fixtures: list[dict]) -> bool:
    gcs_uri = entry["gcs_uri"]
    explicit_file_type = entry.get("file_type")
    for fixture in fixtures:
        if fixture.get("gcs_uri") != gcs_uri:
            continue
        if explicit_file_type and fixture.get("file_type") != explicit_file_type:
            continue
        return True
    return False


def _resolve_file_type(entry: dict, *, folder_map: dict[str, set[str]]) -> str:
    explicit_file_type = entry.get("file_type")
    if explicit_file_type:
        return str(explicit_file_type).strip()

    source_folder = str(entry["source_folder"]).strip()
    mapped = {value for value in folder_map.get(source_folder, set()) if value}
    if len(mapped) == 1:
        return next(iter(mapped))
    if len(mapped) > 1:
        raise SystemExit(
            "Ambiguous file_type inference for source folder "
            f"{source_folder!r}; provide explicit file_type values in the JSON input."
        )
    raise SystemExit(
        "Could not infer file_type for source folder "
        f"{source_folder!r}; provide explicit file_type values in the JSON input."
    )


def _manifest_entry(entry: dict, *, folder_map: dict[str, set[str]]) -> dict[str, object]:
    file_type = _resolve_file_type(entry, folder_map=folder_map)
    source_folder = str(entry["source_folder"]).strip()
    source_file_type = str(entry.get("source_file_type") or file_type).strip()
    verification_status = str(entry.get("verification_status", "unverified")).strip()
    if verification_status not in VALID_VERIFICATION_STATUSES:
        raise SystemExit(
            f"Invalid verification_status for {entry['gcs_uri']}: {verification_status!r}"
        )
    enabled = entry.get("enabled", True)
    if not isinstance(enabled, bool):
        raise SystemExit(f"Invalid enabled flag for {entry['gcs_uri']}: {enabled!r}")

    manifest_entry: dict[str, object] = {
        "gcs_uri": entry["gcs_uri"],
        "file_type": file_type,
        "source_folder": source_folder,
        "source_file_type": source_file_type,
        "verification_status": verification_status,
        "enabled": enabled,
    }
    if entry.get("name"):
        manifest_entry["name"] = str(entry["name"]).strip()
    return manifest_entry


def _write_supplemental_doc(doc: dict) -> None:
    SUPPLEMENTAL_YAML.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Supplemental /parse fixtures for JSON-driven onboarding.\n"
        "# Edit this file directly or rerun tools/onboard_fixture_json.py.\n"
    )
    with SUPPLEMENTAL_YAML.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(header)
        yaml.safe_dump(doc, handle, allow_unicode=True, sort_keys=False, width=160)


def _load_supplemental_doc() -> dict:
    if not SUPPLEMENTAL_YAML.exists():
        return {
            "schema_version": SUPPLEMENTAL_SCHEMA_VERSION,
            "fixtures": [],
        }

    try:
        doc = yaml.safe_load(SUPPLEMENTAL_YAML.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SystemExit(f"Invalid supplemental fixture registry at {SUPPLEMENTAL_YAML}: {exc}") from exc
    if doc is None:
        doc = {}
    if not isinstance(doc, dict):
        raise SystemExit(
            f"Invalid supplemental fixture registry at {SUPPLEMENTAL_YAML}: "
            f"top-level document must be a mapping, got {type(doc).__name__}"
        )
    fixtures = doc.get("fixtures", [])
    if not isinstance(fixtures, list):
        raise SystemExit(
            f"Invalid supplemental fixture registry at {SUPPLEMENTAL_YAML}: "
            f"'fixtures' must be a list, got {type(fixtures).__name__}"
        )
    return {
        "schema_version": doc.get("schema_version", SUPPLEMENTAL_SCHEMA_VERSION),
        "fixtures": fixtures,
    }


def _regenerate_registry_or_exit() -> None:
    try:
        from generate_fixture_registry import build_registry_document, write_registry_document
    except ModuleNotFoundError as exc:
        if exc.name == "openpyxl":
            raise SystemExit(
                "Fixture onboarding needs the tool dependencies to regenerate "
                "the generated fixture registries. Install them with "
                "`./.venv/bin/python -m pip install -r tools/requirements.txt` and rerun the command."
            ) from exc
        raise

    write_registry_document(build_registry_document())


def _registry_pairs(fixtures: list[dict]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for fixture in fixtures:
        gcs_uri = fixture.get("gcs_uri")
        file_type = fixture.get("file_type")
        if isinstance(gcs_uri, str) and isinstance(file_type, str) and file_type.strip():
            pairs.add((gcs_uri, file_type))
    return pairs


def _supplemental_out_of_sync(
    *,
    current_fixtures: list[dict],
    supplemental_fixtures: list[dict],
) -> bool:
    current_pairs = _registry_pairs(current_fixtures)
    for item in supplemental_fixtures:
        if not isinstance(item, dict):
            continue
        gcs_uri = item.get("gcs_uri")
        file_type = item.get("file_type")
        if not isinstance(gcs_uri, str) or not isinstance(file_type, str) or not file_type.strip():
            continue
        if (gcs_uri, file_type) not in current_pairs:
            return True
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Onboard a fixture JSON file into the /parse registry flow.",
    )
    parser.add_argument("--json", required=True, help="Path to the fixture JSON input.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    json_path = Path(args.json).expanduser().resolve()
    if not json_path.exists():
        raise SystemExit(f"Fixture JSON not found: {json_path}")

    try:
        normalization = normalize_fixture_json_entries(json_path)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    entries = normalization.entries
    skipped = normalization.skipped
    processed_count = len(entries) + len(skipped)
    try:
        current_doc = load_registry()
    except RuntimeError:
        _regenerate_registry_or_exit()
        current_doc = load_registry()
    current_fixtures = list(current_doc["fixtures"])

    supplemental_doc = _load_supplemental_doc()
    supplemental_fixtures = list(supplemental_doc["fixtures"])
    if _supplemental_out_of_sync(
        current_fixtures=current_fixtures,
        supplemental_fixtures=supplemental_fixtures,
    ):
        _regenerate_registry_or_exit()
        current_doc = load_registry()
        current_fixtures = list(current_doc["fixtures"])

    if not entries:
        print(f"Input JSON: {json_path}")
        print(f"Entries processed: {processed_count}")
        print(f"Skipped unsupported entries: {len(skipped)}")
        for item in skipped:
            print(f"  - {item.gcs_uri}: {item.reason}")
        print("No supported fixture entries remained after normalization.")
        print("No source-of-truth changes were required.")
        return 0

    folder_map = _folder_file_type_map(current_fixtures)
    existing_pairs = {
        (str(item.get("gcs_uri")), str(item.get("file_type")))
        for item in supplemental_fixtures
        if isinstance(item, dict) and item.get("gcs_uri") and item.get("file_type")
    }

    already_present = 0
    added = 0
    for entry in entries:
        if _entry_exists(entry, current_fixtures):
            already_present += 1
            continue

        manifest_entry = _manifest_entry(entry, folder_map=folder_map)
        key = (str(manifest_entry["gcs_uri"]), str(manifest_entry["file_type"]))
        if key in existing_pairs:
            already_present += 1
            continue

        supplemental_fixtures.append(manifest_entry)
        existing_pairs.add(key)
        folder_map.setdefault(str(manifest_entry["source_folder"]), set()).add(
            str(manifest_entry["file_type"])
        )
        current_fixtures.append({
            "gcs_uri": manifest_entry["gcs_uri"],
            "file_type": manifest_entry["file_type"],
            "source_folder": manifest_entry["source_folder"],
        })
        added += 1

    if added:
        supplemental_fixtures.sort(
            key=lambda item: (
                str(item.get("source_folder") or ""),
                str(item.get("file_type") or ""),
                str(item.get("gcs_uri") or ""),
            )
        )
        updated_doc = {
            "schema_version": supplemental_doc.get("schema_version", SUPPLEMENTAL_SCHEMA_VERSION),
            "fixtures": supplemental_fixtures,
        }
        _write_supplemental_doc(updated_doc)
        _regenerate_registry_or_exit()
    elif not OUTPUT_YAML.exists():
        _regenerate_registry_or_exit()

    print(f"Input JSON: {json_path}")
    print(f"Entries processed: {processed_count}")
    print(f"Skipped unsupported entries: {len(skipped)}")
    for item in skipped:
        print(f"  - {item.gcs_uri}: {item.reason}")
    print(f"Already present in registry flow: {already_present}")
    print(f"Added to supplemental registry: {added}")
    if added:
        print(f"Updated supplemental source: {SUPPLEMENTAL_YAML}")
        print(f"Regenerated derived registry: {SHARED_OUTPUT_YAML}")
        print(f"Regenerated /parse compatibility registry: {PARSE_COMPAT_OUTPUT_YAML}")
    else:
        print("No source-of-truth changes were required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
