#!/usr/bin/env python3
"""Inventory-backed canonical regression runner.

This slice supports:
- `--list`
- `--dry-run`
- live execution for the protected suite
- live execution for the opt-in GET smoke suite
- live execution for `--suite full` via delegation
- live execution for mapped opt-in parse and batch category selections
- structured reporting for protected, full, and parse matrix via existing helpers
- non-live `--suite extended --dry-run` preview for the planned Automation Hub
  with optional hub selector filtering
- synthetic non-live hub reports for `--suite extended --dry-run --report`
- live Automation Hub execution for the approved `get-smoke.health.core` node only
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.automation_hub.executor import HEALTH_CORE_NODE_ID, execute_approved_live_node  # noqa: E402
from tools.automation_hub.manifest import (  # noqa: E402
    DEFAULT_HUB_MANIFEST,
    ManifestSelectionError,
    is_live_capable_node,
    render_extended_dry_run,
)
from tools.automation_hub.report_writer import write_synthetic_report  # noqa: E402

FULL_WRAPPER = REPO_ROOT / "tools" / "run_parse_full_regression.py"
PARSE_MATRIX_WRAPPER = REPO_ROOT / "tools" / "reporting" / "run_parse_matrix_with_summary.py"
BATCH_WRAPPER = REPO_ROOT / "tools" / "run_batch_with_fixtures.py"
PARSE_REPORT_WRAPPER = REPO_ROOT / "tools" / "run_parse_with_report.py"
GET_SMOKE_TARGET = "tests/endpoints/get_smoke/"
HUB_REPORT_ROOT = REPO_ROOT / "reports" / "hub"

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

GET_SMOKE_ENV_VARS = PROTECTED_ENV_VARS
HUB_HEALTH_ENV_VARS = BATCH_ENV_VARS

IMPLEMENTED_SUITES = ("protected", "smoke", "full")
PLANNED_SUITES = ("extended",)
IMPLEMENTED_ENDPOINTS = ("parse", "batch")
IMPLEMENTED_CATEGORIES = ("auth", "contract", "matrix", "negative")
PLANNED_CATEGORIES = ("legacy",)


PARSE_CONTRACT_TARGETS = (
    "tests/endpoints/parse/test_parse.py::TestParseHappyPath::test_response_has_required_fields",
    "tests/endpoints/parse/test_parse.py::TestParseHappyPath::test_file_type_matches_request",
    "tests/endpoints/parse/test_parse.py::TestParseHappyPath::test_calculated_fields_not_stub",
    "tests/endpoints/parse/test_parse.py::TestParseValidation::test_422_conforms_to_openapi_schema",
)
PARSE_AUTH_TARGETS = ("tests/endpoints/parse/test_parse.py::TestParseAuth",)
PARSE_NEGATIVE_TARGETS = ("tests/endpoints/parse/test_parse.py::TestParseValidation",)
BATCH_CONTRACT_TARGETS = (
    "tests/endpoints/batch/test_batch.py::TestBatchHappyPath::test_response_has_expected_batch_structure",
    "tests/endpoints/batch/test_batch.py::TestBatchHappyPath::test_results_preserve_request_order_and_item_contract",
)
BATCH_NEGATIVE_TARGETS = ("tests/endpoints/batch/test_batch.py::TestBatchValidation",)


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
    dry_run_text: str = ""


@dataclass(frozen=True)
class CategoryMapping:
    endpoint: str
    category: str
    description: str
    targets: tuple[str, ...]
    required_env: tuple[str, ...]
    supported_flags: tuple[str, ...]
    notes: tuple[str, ...]

    @property
    def selector(self) -> str:
        return f"endpoint={self.endpoint} category={self.category}"


CATEGORY_MAPPINGS: tuple[CategoryMapping, ...] = (
    CategoryMapping(
        endpoint="parse",
        category="contract",
        description="Focused /parse response and validation contract checks.",
        targets=PARSE_CONTRACT_TARGETS,
        required_env=PROTECTED_ENV_VARS,
        supported_flags=("--k",),
        notes=(
            "Targets existing protected-suite tests only; no duplicate contract tests are introduced.",
            "Includes successful document result shape checks plus the current HTTPValidationError shape check.",
            "This mapping does not include the opt-in parse matrix; use category=matrix for fileType breadth.",
        ),
    ),
    CategoryMapping(
        endpoint="parse",
        category="auth",
        description="Focused /parse tenant-token auth-negative checks.",
        targets=PARSE_AUTH_TARGETS,
        required_env=PROTECTED_ENV_VARS,
        supported_flags=("--k",),
        notes=(
            "Targets the existing tenant-token auth-negative class.",
            "The tests accept the currently observed timeout behavior as a negative signal for /parse only.",
        ),
    ),
    CategoryMapping(
        endpoint="parse",
        category="negative",
        description="Focused /parse missing-payload validation checks.",
        targets=PARSE_NEGATIVE_TARGETS,
        required_env=PROTECTED_ENV_VARS,
        supported_flags=("--k",),
        notes=(
            "Targets the existing /parse request-validation class.",
            "Covers missing file, missing fileType, empty body, and HTTPValidationError shape behavior.",
        ),
    ),
    CategoryMapping(
        endpoint="batch",
        category="contract",
        description="Focused /documents/batch top-level and per-item contract checks.",
        targets=BATCH_CONTRACT_TARGETS,
        required_env=BATCH_ENV_VARS,
        supported_flags=("--k",),
        notes=(
            "Targets existing default batch-suite tests only; no duplicate contract tests are introduced.",
            "Covers response structure, summary accounting, request order, per-item shape, fileType echo, and calculatedFields stub guard.",
        ),
    ),
    CategoryMapping(
        endpoint="batch",
        category="negative",
        description="Focused /documents/batch validation, over-limit, and partial-failure checks.",
        targets=BATCH_NEGATIVE_TARGETS,
        required_env=BATCH_ENV_VARS,
        supported_flags=("--k",),
        notes=(
            "Targets the existing default batch-suite request-validation class.",
            "Covers missing items, empty items, over-limit requests, malformed items, and unsupported fileType partial failure.",
        ),
    ),
)

DEFERRED_CATEGORY_MAPPINGS = (
    (
        "endpoint=batch category=auth",
        "Deferred until missing and invalid tenant-token requests return confirmed 401 or 403 responses; "
        "see docs/knowledge-base/batch/auth-negative-blocker.md.",
    ),
)


INVENTORY: tuple[InventoryItem, ...] = (
    InventoryItem(
        selector="suite=protected",
        description="Current protected /parse baseline.",
        required_env=PROTECTED_ENV_VARS,
        supported_flags=("--report",),
        notes=(
            "Maps to the current protected pytest baseline.",
            "The no-arg and --suite protected runner invocations keep the exact protected baseline command.",
            "--report delegates to the existing baseline structured-report helper.",
            "Live protected execution accepts no targeting flags.",
            "Smoke and full are separate opt-in live suites.",
        ),
    ),
    InventoryItem(
        selector="suite=smoke",
        description="Opt-in GET smoke suite across safely testable VerifyIQ API endpoints.",
        required_env=GET_SMOKE_ENV_VARS,
        supported_flags=("--k",),
        notes=(
            "Runs the dedicated GET smoke pytest package.",
            "Keeps the default no-argument runner path unchanged; smoke remains opt-in.",
            "Live execution delegates to the existing GET smoke pytest surface.",
        ),
    ),
    InventoryItem(
        selector=f"suite=extended hub-node={HEALTH_CORE_NODE_ID}",
        description="Approved live Automation Hub health node for GET /health only.",
        required_env=HUB_HEALTH_ENV_VARS,
        supported_flags=("--report",),
        notes=(
            "This is the only live-capable Automation Hub node in the first executor tranche.",
            "Live execution always writes metadata-only reports under reports/hub/.",
            "Broad --suite extended and --hub-group execution remain blocked.",
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
            "Live execution delegates to the existing full-regression wrapper.",
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
            "Live execution delegates to the existing matrix wrapper; wrapper behavior stays the source of truth.",
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
            "Live execution delegates to the existing batch pytest surface.",
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
            "Live execution leaves selected-fixture validation to the delegated wrapper.",
        ),
    ),
)

_CATEGORY_MAPPING_BY_SELECTOR = {item.selector: item for item in CATEGORY_MAPPINGS}


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
    parser.add_argument("--hub-node", default="", help="Filter the non-live extended dry-run preview to one hub node id.")
    parser.add_argument("--hub-group", default="", help="Filter the non-live extended dry-run preview to one endpoint group.")
    return parser


def _format_command(command: tuple[str, ...] | list[str]) -> str:
    return subprocess.list2cmdline([str(part) for part in command])


def _usage_error(parser: argparse.ArgumentParser, message: str) -> int:
    parser.print_usage(sys.stderr)
    print(f"{parser.prog}: error: {message}", file=sys.stderr)
    return 2


def _validate_hub_selector_usage(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int | None:
    if args.hub_node and args.hub_group:
        return _usage_error(parser, "--hub-node and --hub-group are mutually exclusive.")
    if not args.hub_node and not args.hub_group:
        return None
    if _normalize(args.suite) != "extended" or args.list or args.endpoint or args.category:
        return _usage_error(parser, "--hub-node and --hub-group are supported only with --suite extended.")
    return None


def _write_extended_synthetic_report(*, hub_node: str = "", hub_group: str = "") -> str:
    paths = write_synthetic_report(
        output_root=HUB_REPORT_ROOT,
        hub_node=hub_node,
        hub_group=hub_group,
    )
    lines = [
        "",
        "Synthetic hub report:",
        f"- run directory: {paths.run_dir}",
        f"- JSON: {paths.json_path}",
        f"- Markdown: {paths.markdown_path}",
        f"- latest pointer: {paths.latest_path}",
        "- no endpoints were executed; this report contains only non-live plan evidence",
    ]
    return "\n".join(lines) + "\n"


def _base_pytest_command(target: str | tuple[str, ...], *, k_expr: str = "") -> tuple[str, ...]:
    targets = (target,) if isinstance(target, str) else target
    command = [sys.executable, "-m", "pytest", *targets, "-v"]
    if k_expr:
        command.extend(["-k", k_expr])
    return tuple(command)


def _protected_command(*, k_expr: str = "") -> tuple[str, ...]:
    return _base_pytest_command("tests/endpoints/parse/", k_expr=k_expr)


def _protected_report_command() -> tuple[str, ...]:
    return (
        sys.executable,
        str(PARSE_REPORT_WRAPPER),
        "--tier",
        "baseline",
    )


def _smoke_command(*, k_expr: str = "") -> tuple[str, ...]:
    return _base_pytest_command(GET_SMOKE_TARGET, k_expr=k_expr)


def _extended_health_command(*, report: bool = False) -> tuple[str, ...]:
    command = [
        sys.executable,
        "tools/run_regression.py",
        "--suite",
        "extended",
        "--hub-node",
        HEALTH_CORE_NODE_ID,
    ]
    if report:
        command.append("--report")
    return tuple(command)


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


def _category_command(mapping: CategoryMapping, *, k_expr: str = "") -> tuple[str, ...]:
    return _base_pytest_command(mapping.targets, k_expr=k_expr)


def _normalize(value: str) -> str:
    return value.strip().lower()


def resolve_plan(args: argparse.Namespace, parser: argparse.ArgumentParser) -> ResolvedPlan | int:
    suite = _normalize(args.suite)
    endpoint = _normalize(args.endpoint)
    category = _normalize(args.category)

    hub_selector_error = _validate_hub_selector_usage(args, parser)
    if hub_selector_error is not None:
        return hub_selector_error

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
        if suite == "extended":
            if args.file_types:
                return _usage_error(parser, "--file-types is not supported for --suite extended.")
            if args.fixtures_json:
                return _usage_error(parser, "--fixtures-json is not supported for --suite extended.")
            if args.k_expr:
                return _usage_error(parser, "--k is not supported for --suite extended.")
            if args.dry_run:
                try:
                    dry_run_text = render_extended_dry_run(hub_node=args.hub_node, hub_group=args.hub_group)
                except ManifestSelectionError as exc:
                    return _usage_error(parser, str(exc))
                if args.report:
                    dry_run_text += _write_extended_synthetic_report(
                        hub_node=args.hub_node,
                        hub_group=args.hub_group,
                    )
                return ResolvedPlan(
                    selector="suite=extended",
                    description="Planned Automation Hub dependency graph preview.",
                    commands=(),
                    required_env=(),
                    notes=(
                        "Dry-run prints a dependency-aware hub plan without executing endpoints.",
                        f"Live extended execution is approved only for --hub-node {HEALTH_CORE_NODE_ID}.",
                    ),
                    dry_run_text=dry_run_text,
                )
            if args.hub_group:
                return _usage_error(
                    parser,
                    "Live extended Automation Hub execution does not support --hub-group; "
                    f"use --hub-node {HEALTH_CORE_NODE_ID}.",
                )
            if not args.hub_node:
                return _usage_error(
                    parser,
                    "Live extended Automation Hub execution requires the approved selector "
                    f"--hub-node {HEALTH_CORE_NODE_ID}; broad --suite extended remains blocked.",
                )
            try:
                DEFAULT_HUB_MANIFEST.select_nodes(hub_node=args.hub_node)
            except ManifestSelectionError as exc:
                return _usage_error(parser, str(exc))
            if not is_live_capable_node(args.hub_node):
                return _usage_error(
                    parser,
                    "Live extended Automation Hub execution is approved only for "
                    f"--hub-node {HEALTH_CORE_NODE_ID}.",
                )
            return ResolvedPlan(
                selector=f"suite=extended hub-node={HEALTH_CORE_NODE_ID}",
                description="Approved live Automation Hub health node for GET /health only.",
                commands=(_extended_health_command(report=args.report),),
                required_env=HUB_HEALTH_ENV_VARS,
                notes=(
                    "Live execution calls only GET /health through the Automation Hub executor.",
                    "Metadata-only live reports are always written under reports/hub/.",
                    "Raw request bodies, raw response bodies, auth material, document identifiers, GCS names, fraud details, and artifact/export payloads are not persisted.",
                ),
            )
        if suite in PLANNED_SUITES:
            if args.dry_run:
                return _usage_error(parser, f"Suite {suite!r} is planned but not mapped in the current runner.")
            return ResolvedPlan(
                selector=f"suite={suite}",
                description=f"Planned suite {suite!r} is not yet available for live execution.",
                commands=(),
                required_env=(),
                notes=(
                    "This live mapping is still pending.",
                    "Use --dry-run for selections that already have a mapped command.",
                ),
            )
        if suite == "protected":
            if args.file_types:
                return _usage_error(parser, "--file-types is not supported for --suite protected.")
            if args.fixtures_json:
                return _usage_error(parser, "--fixtures-json is not supported for --suite protected.")
            if args.report and args.k_expr:
                return _usage_error(parser, "--k is not supported for --suite protected --report.")
            command = _protected_report_command() if args.report else _protected_command(k_expr=args.k_expr)
            if args.report:
                notes = [
                    "Dry-run prints the exact protected reporting command without executing it.",
                    "The protected suite is the current default dry-run mapping.",
                    "Live protected execution accepts only --report as an optional reporting mode; smoke and full are separate opt-in live suites.",
                    "--report delegates to tools/run_parse_with_report.py --tier baseline.",
                ]
            else:
                notes = [
                    "Dry-run prints the exact protected baseline command without executing it.",
                    "The protected suite is the current default dry-run mapping.",
                    "Live protected execution accepts only --report as an optional reporting mode; smoke and full are separate opt-in live suites.",
                ]
            if args.k_expr:
                notes.append(
                    "--k appears only in this protected dry-run command preview; live protected execution rejects it."
                )
            return ResolvedPlan(
                selector="suite=protected",
                description="Current protected /parse baseline.",
                commands=(command,),
                required_env=PROTECTED_ENV_VARS,
                notes=tuple(notes),
                defaulted_to_protected=defaulted_to_protected,
            )
        if suite == "smoke":
            if args.file_types:
                return _usage_error(parser, "--file-types is not supported for --suite smoke.")
            if args.fixtures_json:
                return _usage_error(parser, "--fixtures-json is not supported for --suite smoke.")
            if args.report:
                return _usage_error(parser, "--report is not supported for --suite smoke.")
            return ResolvedPlan(
                selector="suite=smoke",
                description="Opt-in GET smoke suite across safely testable VerifyIQ API endpoints.",
                commands=(_smoke_command(k_expr=args.k_expr),),
                required_env=GET_SMOKE_ENV_VARS,
                notes=(
                    "Dry-run prints the exact GET smoke pytest command without executing it.",
                    "This suite is opt-in and does not change the default protected baseline.",
                ),
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
                "Dry-run prints the exact delegated full-regression wrapper command without executing it.",
                "The full suite delegates to the existing full-regression wrapper for live execution.",
            ),
            defaulted_to_protected=defaulted_to_protected,
        )

    if endpoint not in IMPLEMENTED_ENDPOINTS:
        return _usage_error(parser, f"Unknown endpoint: {endpoint!r}.")

    if endpoint == "parse":
        if not category:
            return _usage_error(
                parser,
                "--endpoint parse currently requires --category auth, contract, matrix, or negative; "
                "or use --suite protected/full.",
            )
        if category not in IMPLEMENTED_CATEGORIES and category not in PLANNED_CATEGORIES:
            return _usage_error(parser, f"Unknown category: {category!r}.")
        if category in PLANNED_CATEGORIES:
            return _usage_error(
                parser,
                f"Category {category!r} is planned for --endpoint parse but not yet mapped in the current runner.",
            )
        if category == "matrix":
            if args.fixtures_json and args.file_types:
                return _usage_error(parser, "--fixtures-json and --file-types are mutually exclusive for parse matrix.")
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
                    "Live execution delegates to the existing matrix wrapper.",
                    "The wrapper manages RUN_PARSE_MATRIX=1 internally.",
                ),
            )
        if args.fixtures_json:
            return _usage_error(parser, f"--fixtures-json is not supported for --endpoint parse --category {category}.")
        if args.file_types:
            return _usage_error(parser, f"--file-types is not supported for --endpoint parse --category {category}.")
        if args.report:
            return _usage_error(parser, f"--report is not supported for --endpoint parse --category {category}.")
        mapping = _CATEGORY_MAPPING_BY_SELECTOR[f"endpoint=parse category={category}"]
        return ResolvedPlan(
            selector=mapping.selector,
            description=mapping.description,
            commands=(_category_command(mapping, k_expr=args.k_expr),),
            required_env=mapping.required_env,
            notes=mapping.notes,
        )

    if category:
        if category not in IMPLEMENTED_CATEGORIES and category not in PLANNED_CATEGORIES:
            return _usage_error(parser, f"Unknown category: {category!r}.")
        mapping = _CATEGORY_MAPPING_BY_SELECTOR.get(f"endpoint=batch category={category}")
        if mapping is None:
            return _usage_error(
                parser,
                f"Category {category!r} is not mapped for --endpoint batch in the current runner.",
            )
        if args.fixtures_json:
            return _usage_error(parser, f"--fixtures-json is not supported for --endpoint batch --category {category}.")
        if args.file_types:
            return _usage_error(parser, f"--file-types is not supported for --endpoint batch --category {category}.")
        if args.report:
            return _usage_error(parser, f"--report is not supported for --endpoint batch --category {category}.")
        return ResolvedPlan(
            selector=mapping.selector,
            description=mapping.description,
            commands=(_category_command(mapping, k_expr=args.k_expr),),
            required_env=mapping.required_env,
            notes=mapping.notes,
        )
    if args.file_types:
        return _usage_error(parser, "--file-types is not supported for --endpoint batch.")
    if args.report:
        return _usage_error(parser, "--report is not supported for --endpoint batch.")

    if args.fixtures_json:
        return ResolvedPlan(
            selector="endpoint=batch --fixtures-json",
            description="Fixture-selection /documents/batch wrapper path.",
            commands=(_batch_wrapper_command(fixtures_json=args.fixtures_json, k_expr=args.k_expr),),
            required_env=BATCH_ENV_VARS,
            notes=(
                "Live execution delegates to the existing batch wrapper.",
                "The batch wrapper manages BATCH_FIXTURES_JSON and chunking.",
                "Fixture JSON paths are not validated in dry-run mode.",
            ),
        )

    return ResolvedPlan(
        selector="endpoint=batch",
        description="Direct /documents/batch pytest validation path.",
        commands=(_batch_command(k_expr=args.k_expr),),
        required_env=BATCH_ENV_VARS,
        notes=(
            "Live execution delegates to the existing direct batch pytest mapping.",
            "The existing direct batch pytest surface remains available for debugging.",
        ),
    )


def render_list() -> str:
    lines: list[str] = []
    lines.append("Canonical regression runner inventory")
    lines.append("")
    lines.append("Implemented suites:")
    for suite in IMPLEMENTED_SUITES:
        lines.append(f"- {suite}")
    lines.append("")
    lines.append("Planned suites:")
    for suite in PLANNED_SUITES:
        if suite == "extended":
            lines.append(
                f"- extended (dry-run plan available; live execution approved only for --hub-node {HEALTH_CORE_NODE_ID})"
            )
        else:
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
    lines.append("Command mappings:")
    for item in INVENTORY:
        lines.append(f"- {item.selector}")
        lines.append(f"  description: {item.description}")
        supported_flags = ", ".join(item.supported_flags) if item.supported_flags else "none for live execution"
        lines.append(f"  supported flags: {supported_flags}")
        if item.selector == "suite=protected":
            command = _protected_command()
        elif item.selector == "suite=smoke":
            command = _smoke_command()
        elif item.selector == f"suite=extended hub-node={HEALTH_CORE_NODE_ID}":
            command = _extended_health_command()
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
    for mapping in CATEGORY_MAPPINGS:
        lines.append(f"- {mapping.selector}")
        lines.append(f"  description: {mapping.description}")
        supported_flags = ", ".join(mapping.supported_flags) if mapping.supported_flags else "none for live execution"
        lines.append(f"  supported flags: {supported_flags}")
        lines.append(f"  command: {_format_command(_category_command(mapping))}")
        lines.append("  required env:")
        for name in mapping.required_env:
            lines.append(f"    - {name}")
        if mapping.notes:
            lines.append("  notes:")
            for note in mapping.notes:
                lines.append(f"    - {note}")
    lines.append("")
    lines.append("Deferred endpoint/category mappings:")
    for selector, reason in DEFERRED_CATEGORY_MAPPINGS:
        lines.append(f"- {selector}: {reason}")
    lines.append("")
    lines.append(
        "Live execution is implemented for protected, smoke, full, parse matrix, mapped parse categories, "
        "direct batch, selected batch, and mapped batch categories. "
        f"--suite extended supports dry-run plan preview and live execution only for --hub-node {HEALTH_CORE_NODE_ID}. "
        "Use --dry-run to inspect commands without executing them."
    )
    return "\n".join(lines) + "\n"


def render_dry_run(plan: ResolvedPlan) -> str:
    if plan.dry_run_text:
        return plan.dry_run_text
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
    live_selectors = {
        "suite=protected",
        "suite=smoke",
        "suite=full",
        f"suite=extended hub-node={HEALTH_CORE_NODE_ID}",
        "endpoint=parse category=matrix",
        "endpoint=batch",
        "endpoint=batch --fixtures-json",
    }
    live_selectors.update(_CATEGORY_MAPPING_BY_SELECTOR)
    if plan.selector not in live_selectors:
        if plan.selector == "suite=extended":
            print(
                "Live extended Automation Hub execution requires the approved selector "
                f"--hub-node {HEALTH_CORE_NODE_ID}; use --suite extended --dry-run to inspect the hub plan.",
                file=sys.stderr,
            )
            return 2
        print(
            "Live execution is not implemented for this selection. "
            "Use --dry-run for pending selections where supported.",
            file=sys.stderr,
        )
        return 2

    if plan.selector == f"suite=extended hub-node={HEALTH_CORE_NODE_ID}":
        print(f"Executing Automation Hub node: {HEALTH_CORE_NODE_ID}")
        result = execute_approved_live_node(node_id=HEALTH_CORE_NODE_ID, output_root=HUB_REPORT_ROOT)
        print(f"Hub report directory: {result.report_paths.run_dir}")
        print(f"Hub report JSON: {result.report_paths.json_path}")
        print(f"Hub report Markdown: {result.report_paths.markdown_path}")
        print(f"Outcome: {result.endpoint_result['outcome']}")
        return result.exit_code

    if plan.selector == "suite=protected" and (args.file_types or args.fixtures_json or args.k_expr):
        print(
            "Live protected execution currently supports only the exact protected baseline command or --report. "
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

    hub_selector_error = _validate_hub_selector_usage(args, parser)
    if hub_selector_error is not None:
        return hub_selector_error

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
