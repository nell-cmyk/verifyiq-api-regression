#!/usr/bin/env python3
"""Inventory-backed canonical regression runner.

This slice supports:
- `--list`
- `--dry-run`
- live execution for the protected baseline only

All other live execution paths remain intentionally disabled.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
FULL_WRAPPER = REPO_ROOT / "tools" / "run_parse_full_regression.py"
PARSE_MATRIX_WRAPPER = REPO_ROOT / "tools" / "reporting" / "run_parse_matrix_with_summary.py"
BATCH_WRAPPER = REPO_ROOT / "tools" / "run_batch_with_fixtures.py"

PROTECTED_ENV_VARS = (
    "BASE_URL",
    "TENANT_TOKEN",
    "API_KEY",
    "IAP_CLIENT_ID",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "PARSE_FIXTURE_FILE",
    "PARSE_FIXTURE_FILE_TYPE",
)

BATCH_ENV_VARS = (
    "BASE_URL",
    "TENANT_TOKEN",
    "API_KEY",
    "IAP_CLIENT_ID",
    "GOOGLE_APPLICATION_CREDENTIALS",
)

IMPLEMENTED_SUITES = ("protected", "full")
PLANNED_SUITES = ("smoke", "extended")
IMPLEMENTED_ENDPOINTS = ("parse", "batch")
IMPLEMENTED_CATEGORIES = ("matrix",)
PLANNED_CATEGORIES = ("contract", "auth", "negative", "legacy")


@dataclass(frozen=True)
class InventoryItem:
    selector: str
    description: str
    required_env: tuple[str, ...]
    supported_flags: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedPlan:
    selector: str
    description: str
    commands: tuple[tuple[str, ...], ...]
    required_env: tuple[str, ...]
    notes: tuple[str, ...]
    defaulted_to_protected: bool = False


INVENTORY: tuple[InventoryItem, ...] = (
    InventoryItem(
        selector="suite=protected",
        description="Current protected /parse baseline.",
        required_env=PROTECTED_ENV_VARS,
        supported_flags=("--k", "--report"),
        notes=(
            "Maps to the current protected pytest baseline.",
            "This is the current default live runner target and the only live execution path implemented so far.",
        ),
    ),
    InventoryItem(
        selector="suite=full",
        description="Protected /parse baseline followed by the parse matrix wrapper.",
        required_env=PROTECTED_ENV_VARS,
        supported_flags=("--file-types", "--k", "--report"),
        notes=(
            "Delegates to the existing full-regression wrapper.",
            "Preserves current wrapper sequencing rather than expanding it inline.",
        ),
    ),
    InventoryItem(
        selector="endpoint=parse category=matrix",
        description="Opt-in /parse matrix wrapper with saved summary output.",
        required_env=PROTECTED_ENV_VARS,
        supported_flags=("--file-types", "--fixtures-json", "--k", "--report"),
        notes=(
            "Wrapper manages RUN_PARSE_MATRIX=1 internally.",
            "--file-types and --fixtures-json are mutually exclusive, matching current wrapper behavior.",
        ),
    ),
    InventoryItem(
        selector="endpoint=batch",
        description="Direct /documents/batch pytest validation path.",
        required_env=BATCH_ENV_VARS,
        supported_flags=("--k",),
        notes=(
            "Uses direct pytest for the default batch mapping.",
            "Keeps the existing direct batch suite available for debugging.",
        ),
    ),
    InventoryItem(
        selector="endpoint=batch --fixtures-json <path>",
        description="Fixture-selection /documents/batch wrapper path.",
        required_env=BATCH_ENV_VARS,
        supported_flags=("--fixtures-json", "--k"),
        notes=(
            "Delegates to the existing batch wrapper so chunking and warning semantics stay intact.",
            "Fixture JSON paths are not validated in dry-run mode.",
        ),
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", default="", help="Planned suite selection (e.g. protected, full).")
    parser.add_argument("--endpoint", default="", help="Endpoint group selection (e.g. parse, batch).")
    parser.add_argument("--category", default="", help="Behavior category selection (e.g. matrix).")
    parser.add_argument("--file-types", default="", help="Comma-separated fileType subset for parse matrix/full mappings.")
    parser.add_argument("--fixtures-json", default="", help="Selection JSON path used by parse matrix or batch wrapper mappings.")
    parser.add_argument("--k", dest="k_expr", default="", help="pytest -k expression passed through when supported.")
    parser.add_argument("--report", action="store_true", help="Include report-mode behavior where the selected mapping supports it.")
    parser.add_argument("--list", action="store_true", help="Print available suites, endpoints, categories, and command mappings.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve the selected mapping and print the exact command(s) that would run.")
    return parser


def _format_command(command: tuple[str, ...] | list[str]) -> str:
    return subprocess.list2cmdline([str(part) for part in command])


def _usage_error(parser: argparse.ArgumentParser, message: str) -> int:
    parser.print_usage(sys.stderr)
    print(f"{parser.prog}: error: {message}", file=sys.stderr)
    return 2


def _base_pytest_command(target: str, *, k_expr: str = "") -> tuple[str, ...]:
    command = [sys.executable, "-m", "pytest", target, "-v"]
    if k_expr:
        command.extend(["-k", k_expr])
    return tuple(command)


def _protected_command(*, k_expr: str = "") -> tuple[str, ...]:
    return _base_pytest_command("tests/endpoints/parse/", k_expr=k_expr)


def _full_command(*, report: bool = False, file_types: str = "", k_expr: str = "") -> tuple[str, ...]:
    command = [sys.executable, str(FULL_WRAPPER)]
    if report:
        command.append("--report")
    if file_types:
        command.extend(["--file-types", file_types])
    if k_expr:
        command.extend(["--k", k_expr])
    return tuple(command)


def _parse_matrix_command(
    *,
    report: bool = False,
    file_types: str = "",
    fixtures_json: str = "",
    k_expr: str = "",
) -> tuple[str, ...]:
    command = [sys.executable, str(PARSE_MATRIX_WRAPPER)]
    if report:
        command.append("--report")
    if file_types:
        command.extend(["--file-types", file_types])
    if fixtures_json:
        command.extend(["--fixtures-json", fixtures_json])
    if k_expr:
        command.extend(["--k", k_expr])
    return tuple(command)


def _batch_command(*, k_expr: str = "") -> tuple[str, ...]:
    return _base_pytest_command("tests/endpoints/batch/", k_expr=k_expr)


def _batch_wrapper_command(*, fixtures_json: str, k_expr: str = "") -> tuple[str, ...]:
    command = [sys.executable, str(BATCH_WRAPPER), "--fixtures-json", fixtures_json]
    if k_expr:
        command.extend(["--k", k_expr])
    return tuple(command)


def _normalize(value: str) -> str:
    return value.strip().lower()


def resolve_plan(args: argparse.Namespace, parser: argparse.ArgumentParser) -> ResolvedPlan | int:
    suite = _normalize(args.suite)
    endpoint = _normalize(args.endpoint)
    category = _normalize(args.category)

    if args.list and args.dry_run:
        return _usage_error(parser, "--list and --dry-run are mutually exclusive.")

    if suite and (endpoint or category):
        return _usage_error(parser, "--suite cannot be combined with --endpoint or --category.")

    if category and not endpoint:
        return _usage_error(parser, "--category currently requires --endpoint.")

    defaulted_to_protected = False
    if not suite and not endpoint and not category:
        suite = "protected"
        defaulted_to_protected = True

    if suite:
        if suite not in IMPLEMENTED_SUITES and suite not in PLANNED_SUITES:
            return _usage_error(parser, f"Unknown suite: {suite!r}.")
        if suite in PLANNED_SUITES:
            return _usage_error(parser, f"Suite {suite!r} is planned but not mapped in this first slice.")
        if suite == "protected":
            if args.file_types:
                return _usage_error(parser, "--file-types is not supported for --suite protected.")
            if args.fixtures_json:
                return _usage_error(parser, "--fixtures-json is not supported for --suite protected.")
            notes = [
                "Dry-run prints the exact protected baseline command without executing it.",
                "The protected suite is the current default dry-run mapping and the only live execution path implemented so far.",
            ]
            if args.report:
                notes.append(
                    "Structured reporting would rely on REGRESSION_REPORT=1 and REGRESSION_REPORT_TIER=baseline when execution is added."
                )
            return ResolvedPlan(
                selector="suite=protected",
                description="Current protected /parse baseline.",
                commands=(_protected_command(k_expr=args.k_expr),),
                required_env=PROTECTED_ENV_VARS,
                notes=tuple(notes),
                defaulted_to_protected=defaulted_to_protected,
            )
        if args.fixtures_json:
            return _usage_error(parser, "--fixtures-json is not supported for --suite full.")
        return ResolvedPlan(
            selector="suite=full",
            description="Protected /parse baseline followed by the existing full-regression wrapper.",
            commands=(_full_command(report=args.report, file_types=args.file_types, k_expr=args.k_expr),),
            required_env=PROTECTED_ENV_VARS,
            notes=(
                "Live execution remains disabled in this first slice.",
                "The full suite delegates to the existing full-regression wrapper.",
            ),
            defaulted_to_protected=defaulted_to_protected,
        )

    if endpoint not in IMPLEMENTED_ENDPOINTS:
        return _usage_error(parser, f"Unknown endpoint: {endpoint!r}.")

    if endpoint == "parse":
        if not category:
            return _usage_error(
                parser,
                "--endpoint parse currently requires --category matrix, or use --suite protected/full.",
            )
        if category not in IMPLEMENTED_CATEGORIES and category not in PLANNED_CATEGORIES:
            return _usage_error(parser, f"Unknown category: {category!r}.")
        if category in PLANNED_CATEGORIES:
            return _usage_error(
                parser,
                f"Category {category!r} is planned for --endpoint parse but not yet mapped in this first slice.",
            )
        if args.fixtures_json and args.file_types:
            return _usage_error(parser, "--fixtures-json and --file-types are mutually exclusive for parse matrix dry-runs.")
        return ResolvedPlan(
            selector="endpoint=parse category=matrix",
            description="Opt-in /parse matrix wrapper with saved summary output.",
            commands=(
                _parse_matrix_command(
                    report=args.report,
                    file_types=args.file_types,
                    fixtures_json=args.fixtures_json,
                    k_expr=args.k_expr,
                ),
            ),
            required_env=PROTECTED_ENV_VARS,
            notes=(
                "Live execution remains disabled in this first slice.",
                "The wrapper manages RUN_PARSE_MATRIX=1 internally when execution is added.",
            ),
        )

    if category:
        if category not in IMPLEMENTED_CATEGORIES and category not in PLANNED_CATEGORIES:
            return _usage_error(parser, f"Unknown category: {category!r}.")
        return _usage_error(
            parser,
            f"Category {category!r} is not mapped for --endpoint batch in this first slice.",
        )
    if args.file_types:
        return _usage_error(parser, "--file-types is not supported for --endpoint batch.")
    if args.report:
        return _usage_error(parser, "--report is not yet supported for --endpoint batch dry-runs.")

    if args.fixtures_json:
        return ResolvedPlan(
            selector="endpoint=batch --fixtures-json",
            description="Fixture-selection /documents/batch wrapper path.",
            commands=(_batch_wrapper_command(fixtures_json=args.fixtures_json, k_expr=args.k_expr),),
            required_env=BATCH_ENV_VARS,
            notes=(
                "Live execution remains disabled in this first slice.",
                "The batch wrapper would manage BATCH_FIXTURES_JSON and chunking when execution is added.",
                "Fixture JSON paths are not validated in dry-run mode.",
            ),
        )

    return ResolvedPlan(
        selector="endpoint=batch",
        description="Direct /documents/batch pytest validation path.",
        commands=(_batch_command(k_expr=args.k_expr),),
        required_env=BATCH_ENV_VARS,
        notes=(
            "Live execution remains disabled in this first slice.",
            "This keeps the existing direct batch pytest mapping visible without executing it.",
        ),
    )


def render_list() -> str:
    lines: list[str] = []
    lines.append("Canonical regression runner inventory (first slice)")
    lines.append("")
    lines.append("Implemented suites:")
    for suite in IMPLEMENTED_SUITES:
        lines.append(f"- {suite}")
    lines.append("")
    lines.append("Planned suites not yet mapped:")
    for suite in PLANNED_SUITES:
        lines.append(f"- {suite}")
    lines.append("")
    lines.append("Endpoints:")
    for endpoint in IMPLEMENTED_ENDPOINTS:
        lines.append(f"- {endpoint}")
    lines.append("")
    lines.append("Implemented categories:")
    for category in IMPLEMENTED_CATEGORIES:
        lines.append(f"- {category}")
    lines.append("")
    lines.append("Planned categories not yet mapped:")
    for category in PLANNED_CATEGORIES:
        lines.append(f"- {category}")
    lines.append("")
    lines.append("Planned command mappings:")
    for item in INVENTORY:
        lines.append(f"- {item.selector}")
        lines.append(f"  description: {item.description}")
        lines.append(f"  supported flags: {', '.join(item.supported_flags)}")
        if item.selector == "suite=protected":
            command = _protected_command()
        elif item.selector == "suite=full":
            command = _full_command()
        elif item.selector == "endpoint=parse category=matrix":
            command = _parse_matrix_command()
        elif item.selector == "endpoint=batch":
            command = _batch_command()
        else:
            command = _batch_wrapper_command(fixtures_json="<path-to-fixtures.json>")
        lines.append(f"  command: {_format_command(command)}")
        lines.append("  required env:")
        for name in item.required_env:
            lines.append(f"    - {name}")
        if item.notes:
            lines.append("  notes:")
            for note in item.notes:
                lines.append(f"    - {note}")
    lines.append("")
    lines.append(
        "Only the protected suite supports live execution in this slice. "
        "Use --dry-run to inspect every other mapping."
    )
    return "\n".join(lines) + "\n"


def render_dry_run(plan: ResolvedPlan) -> str:
    lines: list[str] = []
    lines.append(f"Selection: {plan.selector}")
    if plan.defaulted_to_protected:
        lines.append("Default selection: suite=protected")
    lines.append(f"Description: {plan.description}")
    lines.append("")
    lines.append("Commands that would run:")
    for index, command in enumerate(plan.commands, start=1):
        lines.append(f"{index}. {_format_command(command)}")
    lines.append("")
    lines.append("Required env expectations:")
    for name in plan.required_env:
        lines.append(f"- {name}")
    if plan.notes:
        lines.append("")
        lines.append("Notes:")
        for note in plan.notes:
            lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def _run_command(command: tuple[str, ...]) -> int:
    completed = subprocess.run([str(part) for part in command], cwd=REPO_ROOT)
    return completed.returncode


def execute_live(args: argparse.Namespace, plan: ResolvedPlan) -> int:
    if plan.selector != "suite=protected":
        print(
            "Only protected live execution is implemented so far. "
            "Use --dry-run for full, parse matrix, batch, and other selections.",
            file=sys.stderr,
        )
        return 2

    if args.file_types or args.fixtures_json or args.k_expr or args.report:
        print(
            "Live protected execution currently supports only the exact protected baseline command with no additional flags. "
            "Use --dry-run to inspect extended mappings.",
            file=sys.stderr,
        )
        return 2

    command = plan.commands[0]
    print(f"Executing command: {_format_command(command)}")
    return _run_command(command)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        return code

    if args.list and args.dry_run:
        return _usage_error(parser, "--list and --dry-run are mutually exclusive.")

    if args.list:
        print(render_list(), end="")
        return 0

    resolution = resolve_plan(args, parser)
    if isinstance(resolution, int):
        return resolution

    if not args.dry_run:
        return execute_live(args, resolution)

    print(render_dry_run(resolution), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
