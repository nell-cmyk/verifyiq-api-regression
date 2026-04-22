#!/usr/bin/env python3
"""Run /documents/batch live tests with optional JSON-driven fixture selection."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.endpoints.batch.fixtures import (
    BATCH_FIXTURES_JSON_ENV_VAR,
    BATCH_SAFE_ITEM_LIMIT,
)
from tests.endpoints.batch.artifacts import BATCH_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR
from tests.endpoints.artifact_runs import ensure_run_folder_name
from tests.endpoints.parse.fixture_json import normalize_fixture_json_entries
from tests.endpoints.parse.registry import load_registry, resolve_selected_registry_fixtures


def default_pytest_command(
    *,
    k_expr: str | None = None,
    extra: list[str] | None = None,
    happy_path_only: bool = False,
) -> list[str]:
    target = "tests/endpoints/batch/test_batch.py"
    if happy_path_only:
        target = "tests/endpoints/batch/test_batch.py::TestBatchHappyPath"
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        target,
        "-v",
    ]
    if k_expr:
        cmd.extend(["-k", k_expr])
    if extra:
        cmd.extend(extra)
    return cmd


def normalize_remainder(remainder: list[str]) -> list[str]:
    if remainder and remainder[0] == "--":
        return remainder[1:]
    return remainder


def command_display(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def print_skipped_fixture_entries(*, fixtures_json: Path, skipped) -> None:
    print(f"Skipped unsupported entries: {len(skipped)}", flush=True)
    for item in skipped:
        print(f"  - {item.gcs_uri}: {item.reason}", flush=True)
    print(f"Filtered JSON input: {fixtures_json}", flush=True)


def _batch_selection_error(message: str) -> RuntimeError:
    return RuntimeError(f"Invalid /batch fixture selection: {message}")


def resolve_batch_selection(selection_json_path: Path) -> list[dict[str, Any]]:
    return resolve_selected_registry_fixtures(
        load_registry().get("fixtures", []),
        selection_json_path,
        error_factory=_batch_selection_error,
    )


def batch_warning_fixtures(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [fixture for fixture in fixtures if fixture.get("batch_expected_warning")]


def chunk_fixtures(
    fixtures: list[dict[str, Any]],
    *,
    chunk_size: int = BATCH_SAFE_ITEM_LIMIT,
) -> list[list[dict[str, Any]]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    return [
        fixtures[index : index + chunk_size]
        for index in range(0, len(fixtures), chunk_size)
    ]


def write_chunk_selection_json(
    chunk_path: Path,
    fixtures: list[dict[str, Any]],
) -> Path:
    payload = {
        "fixtures": [
            {
                "gcs_uri": fixture["gcs_uri"],
                "file_type": fixture.get("file_type"),
            }
            for fixture in fixtures
        ]
    }
    chunk_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return chunk_path


def print_batch_selection_registry_warnings(fixtures: list[dict[str, Any]]) -> None:
    print(f"Registry-annotated batch fixture warnings: {len(fixtures)}", flush=True)
    for fixture in fixtures:
        print(
            "  - "
            f"{fixture.get('gcs_uri')}: {fixture.get('batch_expected_warning')} "
            f"[expected_error_type={fixture.get('batch_expected_error_type')!r}, "
            f"expected_error={fixture.get('batch_expected_error')!r}]",
            flush=True,
        )


@dataclass(frozen=True)
class BatchCommandStep:
    label: str
    command: list[str]
    fixtures_json: Path | None


def build_chunked_default_steps(
    *,
    chunk_paths: list[Path],
    k_expr: str | None = None,
) -> list[BatchCommandStep]:
    assert chunk_paths, "chunk_paths must not be empty"
    steps = [
        BatchCommandStep(
            label=f"Full batch validation [chunk 1/{len(chunk_paths)}]",
            command=default_pytest_command(k_expr=k_expr),
            fixtures_json=chunk_paths[0],
        )
    ]
    for index, chunk_path in enumerate(chunk_paths[1:], start=2):
        steps.append(
            BatchCommandStep(
                label=f"Batch happy path [chunk {index}/{len(chunk_paths)}]",
                command=default_pytest_command(k_expr=k_expr, happy_path_only=True),
                fixtures_json=chunk_path,
            )
        )
    return steps


def run_batch_step(step: BatchCommandStep) -> int:
    env = os.environ.copy()
    ensure_run_folder_name(
        env,
        prefix="batch",
        env_var=BATCH_RESPONSE_ARTIFACT_RUN_DIR_ENV_VAR,
    )
    if step.fixtures_json is not None:
        env[BATCH_FIXTURES_JSON_ENV_VAR] = str(step.fixtures_json)
    else:
        env.pop(BATCH_FIXTURES_JSON_ENV_VAR, None)

    print(f"== {step.label} ==", flush=True)
    if step.fixtures_json is not None:
        print(f"Using batch fixture selection: {step.fixtures_json}", flush=True)
    print(f"Running batch command: {command_display(step.command)}", flush=True)
    return subprocess.run(step.command, cwd=REPO_ROOT, env=env).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run /documents/batch tests with optional JSON-selected fixtures.",
    )
    parser.add_argument(
        "--fixtures-json",
        default="",
        help="JSON file of gs:// paths to run through /documents/batch instead of the default fixture set.",
    )
    parser.add_argument(
        "--k",
        dest="k_expr",
        default="",
        help="Extra pytest -k expression applied to the default batch command.",
    )
    parser.add_argument(
        "pytest_cmd",
        nargs=argparse.REMAINDER,
        help="Optional custom command to run instead of the default batch pytest command.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    custom_command = normalize_remainder(args.pytest_cmd)
    fixtures_json = Path(args.fixtures_json).resolve() if args.fixtures_json else None
    if fixtures_json is not None and not fixtures_json.exists():
        raise SystemExit(f"Fixture JSON not found: {fixtures_json}")
    if fixtures_json is not None:
        try:
            normalization = normalize_fixture_json_entries(fixtures_json)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if normalization.skipped:
            print_skipped_fixture_entries(fixtures_json=fixtures_json, skipped=normalization.skipped)
        if not normalization.entries:
            raise SystemExit(
                "No supported fixture entries remained after filtering unsupported formats "
                f"from {fixtures_json}."
            )

    if fixtures_json is None:
        command = custom_command or default_pytest_command(k_expr=args.k_expr or None)
        return run_batch_step(
            BatchCommandStep(
                label="Batch validation",
                command=command,
                fixtures_json=None,
            )
        )

    try:
        selected_fixtures = resolve_batch_selection(fixtures_json)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    registry_warnings = batch_warning_fixtures(selected_fixtures)
    if registry_warnings:
        print_batch_selection_registry_warnings(registry_warnings)

    if len(selected_fixtures) <= BATCH_SAFE_ITEM_LIMIT:
        command = custom_command or default_pytest_command(k_expr=args.k_expr or None)
        return run_batch_step(
            BatchCommandStep(
                label="Batch validation",
                command=command,
                fixtures_json=fixtures_json,
            )
        )

    chunks = chunk_fixtures(selected_fixtures, chunk_size=BATCH_SAFE_ITEM_LIMIT)
    print(
        "Resolved "
        f"{len(selected_fixtures)} supported registry fixtures from {fixtures_json}; "
        f"running {len(chunks)} /documents/batch chunks of up to {BATCH_SAFE_ITEM_LIMIT} items.",
        flush=True,
    )

    with tempfile.TemporaryDirectory(prefix="batch-fixtures-") as tmpdir:
        chunk_paths = [
            write_chunk_selection_json(
                Path(tmpdir) / f"batch-selection-chunk-{index:02d}.json",
                chunk,
            )
            for index, chunk in enumerate(chunks, start=1)
        ]

        if custom_command:
            steps = [
                BatchCommandStep(
                    label=f"Batch chunk [{index}/{len(chunk_paths)}]",
                    command=custom_command,
                    fixtures_json=chunk_path,
                )
                for index, chunk_path in enumerate(chunk_paths, start=1)
            ]
        else:
            steps = build_chunked_default_steps(
                chunk_paths=chunk_paths,
                k_expr=args.k_expr or None,
            )

        for step in steps:
            return_code = run_batch_step(step)
            if return_code != 0:
                return return_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
