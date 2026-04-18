from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from enrich_parse_matrix_results import EnrichedParseResult, enrich_parse_matrix_results
from parse_pytest_terminal import parse_pytest_terminal_output

DEFAULT_INPUT = REPO_ROOT / "reports" / "parse" / "matrix" / "latest-terminal.txt"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "parse" / "matrix" / "latest-summary.md"
DEFAULT_PROMOTION_CANDIDATES = (
    REPO_ROOT / "docs" / "knowledge-base" / "parse" / "promotion-candidates.md"
)


def _markdown_table(rows: list[EnrichedParseResult]) -> str:
    header = (
        "| Result | Failure Class | Registry fileType | API fileType | "
        "Verification | Row | Fixture | Note |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    lines = [header]
    for row in rows:
        note = row.note.replace("\n", " ").replace("|", "\\|")
        fixture_name = (row.fixture_name or "").replace("|", "\\|")
        lines.append(
            "| {result} | {failure} | {registry_ft} | {api_ft} | {verification} | "
            "{rownum} | {fixture} | {note} |".format(
                result=row.pytest_status,
                failure=row.failure_class,
                registry_ft=row.registry_file_type,
                api_ft=row.api_file_type,
                verification=row.verification_status or "",
                rownum=row.registry_row or "",
                fixture=fixture_name,
                note=note,
            )
        )
    return "\n".join(lines)


def _candidate_block(result: EnrichedParseResult, today: str, command: str) -> str:
    return "\n".join(
        [
            f"### Candidate: `{today} {result.registry_file_type} {result.fixture_name or 'fixture'}`",
            "- Candidate status: `pending`",
            "- Promoted status: `not promoted`",
            "- Environment:",
            f"- Matrix run command: `{command}`",
            f"- Registry fileType: `{result.registry_file_type}`",
            f"- API fileType used: `{result.api_file_type}`",
            f"- Registry row: `{result.registry_row}`",
            f"- Fixture name: `{result.fixture_name or ''}`",
            f"- GCS URI: `{result.gcs_uri or ''}`",
            "- Result summary: passed in the matrix summary artifact",
            "- Evidence:",
            "  - terminal result: passed",
            "  - response-body clue summary:",
            "  - diagnose() clue summary:",
            "- Follow-up note:",
            "",
        ]
    )


def _promotion_candidates(
    rows: list[EnrichedParseResult], today: str, command: str
) -> list[str]:
    candidates: list[str] = []
    for row in rows:
        if row.pytest_status != "PASSED":
            continue
        if row.verification_status != "unverified":
            continue
        candidates.append(_candidate_block(row, today=today, command=command))
    return candidates


def _highlights(rows: list[EnrichedParseResult]) -> list[str]:
    highlights: list[str] = []
    remapped = [
        row for row in rows if row.registry_file_type != row.api_file_type
    ]
    if remapped:
        joined = ", ".join(
            f"{row.registry_file_type}->{row.api_file_type}" for row in remapped
        )
        highlights.append(f"Remapped fileTypes exercised: {joined}.")

    passed_unverified = [
        row.registry_file_type
        for row in rows
        if row.pytest_status == "PASSED" and row.verification_status == "unverified"
    ]
    if passed_unverified:
        joined = ", ".join(passed_unverified)
        highlights.append(f"Passed unverified canonicals: {joined}.")

    failure_classes = sorted(
        {
            row.failure_class
            for row in rows
            if row.failure_class != "passed"
        }
    )
    if failure_classes:
        joined = ", ".join(failure_classes)
        highlights.append(f"Failure classes observed: {joined}.")

    if not highlights:
        highlights.append("No notable current-run highlights beyond the recorded pass set.")

    return highlights


def render_summary(
    *,
    endpoint: str,
    input_path: Path,
    command: str,
    rows: list[EnrichedParseResult],
    duration_text: str | None,
    mode: str,
    generated_at: str,
) -> str:
    counts = Counter(row.failure_class for row in rows)
    promotion_candidates = _promotion_candidates(
        rows, today=generated_at[:10], command=command
    )

    lines = [
        f"# {endpoint} Regression Run Summary",
        "",
        "## Run Metadata",
        f"- Generated at: `{generated_at}`",
        f"- Mode: `{mode}`",
        f"- Input: `{input_path.as_posix()}`",
        f"- Command: `{command}`",
        f"- Duration: `{duration_text or 'unknown'}`",
        "",
        "## Counts",
    ]

    for key in (
        "passed",
        "timeout",
        "transport-error",
        "auth-proxy",
        "non-200",
        "non-json-200",
        "filetype-mismatch",
        "missing-fields",
        "failed",
    ):
        lines.append(f"- `{key}`: {counts.get(key, 0)}")

    lines.extend(
        [
            "",
            "## Per-fileType Results",
            _markdown_table(rows),
            "",
            "## What Looks New In This Run",
        ]
    )
    lines.extend(f"- {item}" for item in _highlights(rows))

    lines.extend(["", "## Promotion Candidates"])
    if promotion_candidates:
        lines.append(
            "Copy the reviewed entries below into "
            "`docs/knowledge-base/parse/promotion-candidates.md` if they should be tracked."
        )
        lines.append("")
        lines.extend(promotion_candidates)
    else:
        lines.append("No passed unverified canonical fixtures were detected in this run.")

    return "\n".join(lines).rstrip() + "\n"


def apply_promotion_candidates(target_path: Path, candidate_blocks: list[str]) -> int:
    if not candidate_blocks:
        return 0

    existing_text = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
    appended = 0
    new_chunks: list[str] = []
    for block in candidate_blocks:
        first_line = block.splitlines()[0]
        if first_line in existing_text:
            continue
        new_chunks.append(block)
        appended += 1

    if not new_chunks:
        return 0

    if existing_text and not existing_text.endswith("\n"):
        existing_text += "\n"
    updated_text = existing_text + "\n" + "\n".join(new_chunks)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(updated_text.lstrip("\n"), encoding="utf-8", newline="\n")
    return appended


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a post-run regression summary artifact."
    )
    parser.add_argument("--endpoint", required=True, choices=["parse"])
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--mode", choices=["draft", "apply"], default="draft")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--promotion-candidates-path",
        default=str(DEFAULT_PROMOTION_CANDIDATES),
    )
    parser.add_argument(
        "--command",
        default="pytest tests/endpoints/parse/test_parse_matrix.py -v",
    )
    parser.add_argument("--generated-at")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    promotion_candidates_path = Path(args.promotion_candidates_path).resolve()
    generated_at = args.generated_at or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    if not input_path.exists():
        raise SystemExit(f"Input terminal output not found: {input_path}")

    parsed_run = parse_pytest_terminal_output(input_path.read_text(encoding="utf-8"))
    if not parsed_run.results:
        raise SystemExit("No pytest result lines were parsed from the input terminal output.")

    if args.endpoint != "parse":
        raise SystemExit(f"Unsupported endpoint: {args.endpoint}")

    rows = enrich_parse_matrix_results(parsed_run)
    summary_text = render_summary(
        endpoint=args.endpoint,
        input_path=input_path,
        command=args.command,
        rows=rows,
        duration_text=parsed_run.duration_text,
        mode=args.mode,
        generated_at=generated_at,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary_text, encoding="utf-8", newline="\n")

    candidate_blocks = _promotion_candidates(
        rows, today=generated_at[:10], command=args.command
    )

    appended = 0
    if args.mode == "apply":
        appended = apply_promotion_candidates(
            promotion_candidates_path,
            candidate_blocks,
        )

    print(f"Wrote summary: {output_path}")
    if args.mode == "apply":
        print(
            f"Applied {appended} promotion candidate entr"
            f"{'y' if appended == 1 else 'ies'} to {promotion_candidates_path}"
        )
    else:
        print("Draft mode only: no tracked knowledge-base files were modified.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
