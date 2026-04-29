from __future__ import annotations

import importlib.util
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "run_regression.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("run_regression", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _invoke(module, argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        rc = module.main(argv)
    return rc, stdout.getvalue(), stderr.getvalue()


def _no_call_runner(*args, **kwargs):
    raise AssertionError("subprocess runner should not have been called")


def test_list_exits_zero_and_mentions_core_mappings():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--list"])

    assert rc == 0
    assert stderr == ""
    assert "protected" in stdout
    assert "smoke" in stdout
    assert "full" in stdout
    assert "extended (dry-run plan available; live execution not implemented)" in stdout
    assert "parse" in stdout
    assert "batch" in stdout
    assert "matrix" in stdout
    assert "contract" in stdout
    assert "auth" in stdout
    assert "negative" in stdout
    assert "tools/run_batch_with_fixtures.py" in stdout
    assert "endpoint=batch category=auth" in stdout
    assert "Deferred endpoint/category mappings" in stdout


def test_list_marks_protected_as_exact_baseline_with_report_only():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--list"])

    assert rc == 0
    assert stderr == ""
    protected_start = stdout.index("- suite=protected")
    smoke_start = stdout.index("- suite=smoke")
    protected_block = stdout[protected_start:smoke_start]
    assert "supported flags: --report" in protected_block
    assert "The no-arg and --suite protected runner invocations keep the exact protected baseline command" in protected_block
    assert "--report delegates to the existing baseline structured-report helper" in protected_block
    assert "Live protected execution accepts no targeting flags" in protected_block
    assert "--k" not in protected_block


def test_dry_run_without_selection_defaults_to_protected():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "Selection: suite=protected" in stdout
    assert "Default selection: suite=protected" in stdout
    assert "-m pytest tests/endpoints/parse/ -v" in stdout


def test_dry_run_with_report_defaults_to_protected_report_wrapper():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--report", "--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "Selection: suite=protected" in stdout
    assert "Default selection: suite=protected" in stdout
    assert "tools/run_parse_with_report.py --tier baseline" in stdout
    assert "-m pytest tests/endpoints/parse/ -v" not in stdout


def test_suite_protected_dry_run_prints_protected_pytest_command():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, _ = _invoke(module, ["--suite", "protected", "--dry-run"])

    assert rc == 0
    assert "Selection: suite=protected" in stdout
    assert "-m pytest tests/endpoints/parse/ -v" in stdout


def test_suite_protected_report_dry_run_prints_baseline_report_wrapper():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "protected", "--report", "--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "Selection: suite=protected" in stdout
    assert "tools/run_parse_with_report.py --tier baseline" in stdout
    assert "--report delegates to tools/run_parse_with_report.py --tier baseline" in stdout


def test_suite_protected_dry_run_labels_extra_flags_as_preview_only():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(
        module,
        ["--suite", "protected", "--dry-run", "--k", "happy"],
    )

    assert rc == 0
    assert stderr == ""
    assert "-k happy" in stdout
    assert "Live protected execution accepts only --report as an optional reporting mode" in stdout
    assert "--k appears only in this protected dry-run command preview" in stdout


def test_suite_full_dry_run_prints_full_wrapper_command():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, _ = _invoke(module, ["--suite", "full", "--dry-run"])

    assert rc == 0
    assert "Selection: suite=full" in stdout
    assert "tools/run_parse_full_regression.py" in stdout


def test_suite_full_report_dry_run_forwards_report_to_full_wrapper():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "full", "--report", "--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "Selection: suite=full" in stdout
    assert "tools/run_parse_full_regression.py --report" in stdout
    assert "Executing command:" not in stdout


def test_suite_smoke_dry_run_prints_get_smoke_pytest_command():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, _ = _invoke(module, ["--suite", "smoke", "--dry-run"])

    assert rc == 0
    assert "Selection: suite=smoke" in stdout
    assert "-m pytest tests/endpoints/get_smoke/ -v" in stdout


def test_suite_smoke_dry_run_lists_parse_fixture_env_for_fraud_status_setup():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "smoke", "--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "PARSE_FIXTURE_FILE" in stdout
    assert "PARSE_FIXTURE_FILE_TYPE" in stdout


def test_suite_full_executes_full_wrapper_and_returns_subprocess_code():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 9

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--suite", "full"])

    assert rc == 9
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        str(module.FULL_WRAPPER),
    )
    assert "Executing command:" in stdout


def test_suite_protected_report_executes_baseline_report_wrapper_and_returns_subprocess_code():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 19

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--suite", "protected", "--report"])

    assert rc == 19
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        str(module.PARSE_REPORT_WRAPPER),
        "--tier",
        "baseline",
    )
    assert "Executing command:" in stdout


def test_no_argument_report_invocation_executes_protected_report_wrapper():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 23

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--report"])

    assert rc == 23
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        str(module.PARSE_REPORT_WRAPPER),
        "--tier",
        "baseline",
    )
    assert "Executing command:" in stdout


def test_suite_full_executes_wrapper_with_supported_forwarded_flags():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 0

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(
        module,
        [
            "--suite",
            "full",
            "--report",
            "--file-types",
            "Payslip,TIN",
            "--k",
            "focus",
        ],
    )

    assert rc == 0
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        str(module.FULL_WRAPPER),
        "--report",
        "--file-types",
        "Payslip,TIN",
        "--k",
        "focus",
    )
    assert "Executing command:" in stdout


def test_parse_matrix_dry_run_prints_matrix_wrapper_command():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, _ = _invoke(module, ["--endpoint", "parse", "--category", "matrix", "--dry-run"])

    assert rc == 0
    assert "Selection: endpoint=parse category=matrix" in stdout
    assert "tools/reporting/run_parse_matrix_with_summary.py" in stdout


def test_parse_matrix_report_dry_run_forwards_report_to_matrix_wrapper():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(
        module,
        ["--endpoint", "parse", "--category", "matrix", "--report", "--dry-run"],
    )

    assert rc == 0
    assert stderr == ""
    assert "Selection: endpoint=parse category=matrix" in stdout
    assert "tools/reporting/run_parse_matrix_with_summary.py --report" in stdout
    assert "Executing command:" not in stdout


@pytest.mark.parametrize(
    ("argv", "expected_command_fragment", "unexpected_fragments"),
    [
        (
            ["--report", "--dry-run"],
            "tools/run_parse_with_report.py --tier baseline",
            (
                "tools/run_parse_full_regression.py",
                "tools/reporting/run_parse_matrix_with_summary.py",
                "-m pytest tests/endpoints/parse/ -v",
            ),
        ),
        (
            ["--suite", "protected", "--report", "--dry-run"],
            "tools/run_parse_with_report.py --tier baseline",
            (
                "tools/run_parse_full_regression.py",
                "tools/reporting/run_parse_matrix_with_summary.py",
                "-m pytest tests/endpoints/parse/ -v",
            ),
        ),
        (
            ["--suite", "full", "--report", "--dry-run"],
            "tools/run_parse_full_regression.py --report",
            (
                "tools/run_parse_with_report.py",
                "tools/reporting/run_parse_matrix_with_summary.py",
                "-m pytest tests/endpoints/parse/ -v",
            ),
        ),
        (
            ["--endpoint", "parse", "--category", "matrix", "--report", "--dry-run"],
            "tools/reporting/run_parse_matrix_with_summary.py --report",
            (
                "tools/run_parse_with_report.py",
                "tools/run_parse_full_regression.py",
                "-m pytest tests/endpoints/parse/ -v",
            ),
        ),
    ],
)
def test_structured_report_dry_runs_delegate_to_supported_wrappers_only(
    argv: list[str],
    expected_command_fragment: str,
    unexpected_fragments: tuple[str, ...],
):
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, argv)

    assert rc == 0
    assert stderr == ""
    assert expected_command_fragment in stdout
    for fragment in unexpected_fragments:
        assert fragment not in stdout
    assert "Executing command:" not in stdout


def test_parse_matrix_executes_matrix_wrapper_and_returns_subprocess_code():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 11

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--endpoint", "parse", "--category", "matrix"])

    assert rc == 11
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        str(module.PARSE_MATRIX_WRAPPER),
    )
    assert "Executing command:" in stdout


def test_parse_matrix_executes_wrapper_with_supported_forwarded_flags():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 0

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(
        module,
        [
            "--endpoint",
            "parse",
            "--category",
            "matrix",
            "--report",
            "--file-types",
            "Payslip,TIN",
            "--k",
            "contract",
        ],
    )

    assert rc == 0
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        str(module.PARSE_MATRIX_WRAPPER),
        "--report",
        "--file-types",
        "Payslip,TIN",
        "--k",
        "contract",
    )
    assert "Executing command:" in stdout


def test_parse_matrix_executes_wrapper_with_fixtures_json():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 0

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(
        module,
        [
            "--endpoint",
            "parse",
            "--category",
            "matrix",
            "--fixtures-json",
            "fixtures.json",
            "--k",
            "focus",
        ],
    )

    assert rc == 0
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        str(module.PARSE_MATRIX_WRAPPER),
        "--fixtures-json",
        "fixtures.json",
        "--k",
        "focus",
    )
    assert "Executing command:" in stdout


def test_parse_contract_dry_run_prints_existing_test_nodeids():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--endpoint", "parse", "--category", "contract", "--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "Selection: endpoint=parse category=contract" in stdout
    assert "tests/endpoints/parse/test_parse.py::TestParseHappyPath::test_response_has_required_fields" in stdout
    assert "tests/endpoints/parse/test_parse.py::TestParseValidation::test_422_conforms_to_openapi_schema" in stdout
    assert "RUN_PARSE_MATRIX=1" not in stdout


@pytest.mark.parametrize(
    ("argv", "expected_targets", "unexpected_fragments"),
    [
        (
            ["--endpoint", "parse", "--category", "auth", "--dry-run"],
            ("tests/endpoints/parse/test_parse.py::TestParseAuth",),
            ("tests/endpoints/batch/", "tools/reporting/run_parse_matrix_with_summary.py"),
        ),
        (
            ["--endpoint", "parse", "--category", "negative", "--dry-run"],
            ("tests/endpoints/parse/test_parse.py::TestParseValidation",),
            ("tests/endpoints/batch/", "tools/reporting/run_parse_matrix_with_summary.py"),
        ),
        (
            ["--endpoint", "batch", "--category", "contract", "--dry-run"],
            (
                "tests/endpoints/batch/test_batch.py::TestBatchHappyPath::test_response_has_expected_batch_structure",
                "tests/endpoints/batch/test_batch.py::TestBatchHappyPath::test_results_preserve_request_order_and_item_contract",
            ),
            ("tests/endpoints/parse/", "tools/reporting/run_parse_matrix_with_summary.py"),
        ),
        (
            ["--endpoint", "batch", "--category", "negative", "--dry-run"],
            ("tests/endpoints/batch/test_batch.py::TestBatchValidation",),
            ("tests/endpoints/parse/", "tools/reporting/run_parse_matrix_with_summary.py"),
        ),
    ],
)
def test_focused_category_dry_runs_stay_endpoint_scoped(
    argv: list[str],
    expected_targets: tuple[str, ...],
    unexpected_fragments: tuple[str, ...],
):
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, argv)

    assert rc == 0
    assert stderr == ""
    for target in expected_targets:
        assert target in stdout
    for fragment in unexpected_fragments:
        assert fragment not in stdout


def test_parse_auth_executes_existing_auth_class():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 0

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--endpoint", "parse", "--category", "auth", "--k", "missing"])

    assert rc == 0
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        "-m",
        "pytest",
        "tests/endpoints/parse/test_parse.py::TestParseAuth",
        "-v",
        "-k",
        "missing",
    )
    assert "Executing command:" in stdout


def test_parse_negative_executes_existing_validation_class():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 0

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--endpoint", "parse", "--category", "negative"])

    assert rc == 0
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        "-m",
        "pytest",
        "tests/endpoints/parse/test_parse.py::TestParseValidation",
        "-v",
    )
    assert "Executing command:" in stdout


def test_batch_dry_run_prints_batch_pytest_command():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, _ = _invoke(module, ["--endpoint", "batch", "--dry-run"])

    assert rc == 0
    assert "Selection: endpoint=batch" in stdout
    assert "-m pytest tests/endpoints/batch/ -v" in stdout


def test_batch_executes_batch_pytest_command_and_returns_subprocess_code():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 13

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--endpoint", "batch"])

    assert rc == 13
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        "-m",
        "pytest",
        "tests/endpoints/batch/",
        "-v",
    )
    assert "Executing command:" in stdout


def test_batch_executes_batch_pytest_command_with_supported_k_flag():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 0

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--endpoint", "batch", "--k", "happy"])

    assert rc == 0
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        "-m",
        "pytest",
        "tests/endpoints/batch/",
        "-v",
        "-k",
        "happy",
    )
    assert "Executing command:" in stdout


def test_batch_fixtures_json_dry_run_prints_batch_wrapper_command():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, _ = _invoke(
        module,
        ["--endpoint", "batch", "--fixtures-json", "some.json", "--dry-run"],
    )

    assert rc == 0
    assert "Selection: endpoint=batch --fixtures-json" in stdout
    assert "tools/run_batch_with_fixtures.py" in stdout
    assert "--fixtures-json some.json" in stdout


def test_batch_fixtures_json_executes_batch_wrapper_and_returns_subprocess_code():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 17

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(
        module,
        ["--endpoint", "batch", "--fixtures-json", "some.json", "--k", "happy"],
    )

    assert rc == 17
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        str(module.BATCH_WRAPPER),
        "--fixtures-json",
        "some.json",
        "--k",
        "happy",
    )
    assert "Executing command:" in stdout


def test_batch_contract_executes_existing_contract_nodeids():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 0

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--endpoint", "batch", "--category", "contract"])

    assert rc == 0
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        "-m",
        "pytest",
        "tests/endpoints/batch/test_batch.py::TestBatchHappyPath::test_response_has_expected_batch_structure",
        "tests/endpoints/batch/test_batch.py::TestBatchHappyPath::test_results_preserve_request_order_and_item_contract",
        "-v",
    )
    assert "Executing command:" in stdout


def test_batch_negative_dry_run_prints_existing_validation_class():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--endpoint", "batch", "--category", "negative", "--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "Selection: endpoint=batch category=negative" in stdout
    assert "tests/endpoints/batch/test_batch.py::TestBatchValidation" in stdout


def test_batch_auth_remains_deferred():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--endpoint", "batch", "--category", "auth", "--dry-run"])

    assert rc != 0
    assert stdout == ""
    assert "Category 'auth' is not mapped for --endpoint batch" in stderr


@pytest.mark.parametrize(
    ("argv", "expected_error"),
    [
        (
            ["--endpoint", "parse", "--category", "contract", "--report"],
            "--report is not supported for --endpoint parse --category contract",
        ),
        (
            ["--endpoint", "parse", "--category", "auth", "--file-types", "Payslip"],
            "--file-types is not supported for --endpoint parse --category auth",
        ),
        (
            ["--endpoint", "parse", "--category", "negative", "--fixtures-json", "fixtures.json"],
            "--fixtures-json is not supported for --endpoint parse --category negative",
        ),
        (
            ["--endpoint", "batch", "--category", "contract", "--report"],
            "--report is not supported for --endpoint batch --category contract",
        ),
        (
            ["--endpoint", "batch", "--category", "negative", "--file-types", "Payslip"],
            "--file-types is not supported for --endpoint batch --category negative",
        ),
        (
            ["--endpoint", "batch", "--category", "contract", "--fixtures-json", "fixtures.json"],
            "--fixtures-json is not supported for --endpoint batch --category contract",
        ),
    ],
)
def test_focused_categories_reject_unsupported_targeting_and_report_flags(
    argv: list[str],
    expected_error: str,
):
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, argv)

    assert rc == 2
    assert stdout == ""
    assert expected_error in stderr


def test_no_argument_invocation_executes_protected_live_path():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 0

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, [])

    assert rc == 0
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        "-m",
        "pytest",
        "tests/endpoints/parse/",
        "-v",
    )
    assert "Executing command:" in stdout


def test_suite_smoke_executes_smoke_live_path_and_returns_subprocess_code():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 5

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--suite", "smoke"])

    assert rc == 5
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        "-m",
        "pytest",
        "tests/endpoints/get_smoke/",
        "-v",
    )
    assert "Executing command:" in stdout


def test_suite_smoke_executes_with_supported_k_flag():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 0

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--suite", "smoke", "--k", "health"])

    assert rc == 0
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        "-m",
        "pytest",
        "tests/endpoints/get_smoke/",
        "-v",
        "-k",
        "health",
    )
    assert "Executing command:" in stdout


def test_suite_protected_executes_protected_live_path_and_returns_subprocess_code():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 7

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--suite", "protected"])

    assert rc == 7
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        "-m",
        "pytest",
        "tests/endpoints/parse/",
        "-v",
    )
    assert "Executing command:" in stdout


def test_dry_run_does_not_call_subprocess():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "protected", "--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "Executing command:" not in stdout


def test_list_does_not_call_subprocess():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--list"])

    assert rc == 0
    assert stderr == ""
    assert "Executing command:" not in stdout


def test_invalid_or_incompatible_selections_fail_clearly():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "protected", "--endpoint", "batch", "--dry-run"])

    assert rc != 0
    assert stdout == ""
    assert "--suite cannot be combined with --endpoint or --category" in stderr


def test_parse_category_requires_endpoint():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--category", "matrix", "--dry-run"])

    assert rc != 0
    assert stdout == ""
    assert "--category currently requires --endpoint" in stderr


def test_suite_extended_dry_run_prints_non_live_hub_plan():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "extended", "--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "Selection: suite=extended" in stdout
    assert "Planned Automation Hub dependency graph preview" in stdout
    assert "Live execution: not implemented" in stdout
    assert "parse.protected" in stdout
    assert "document-processing.fraud-status.producer" in stdout
    assert "document-processing.fraud-status.consumer" in stdout
    assert "fraud_status.job_reference from document-processing.fraud-status.producer" in stdout
    assert "Raw response bodies are not automatically persisted" in stdout
    assert "Executing command:" not in stdout


def test_suite_extended_hub_node_filters_to_selected_node():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(
        module,
        ["--suite", "extended", "--dry-run", "--hub-node", "get-smoke.safe-read-only"],
    )

    assert rc == 0
    assert stderr == ""
    assert "Hub selector: --hub-node get-smoke.safe-read-only" in stdout
    assert "Selection scope: selected node plus required prerequisite closure." in stdout
    assert "1. get-smoke.safe-read-only" in stdout
    assert "   inclusion: selected node" in stdout
    assert "endpoint group: get-smoke" in stdout
    assert "parse.protected" not in stdout
    assert "batch.validation" not in stdout
    assert "document-processing.fraud-status.producer" not in stdout
    assert "document-processing.fraud-status.consumer" not in stdout
    assert "Dependency semantics:" in stdout
    assert "Reporting contract scaffold:" in stdout
    assert "Executing command:" not in stdout


def test_suite_extended_hub_node_includes_prerequisite_closure():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(
        module,
        [
            "--suite",
            "extended",
            "--dry-run",
            "--hub-node",
            "document-processing.fraud-status.consumer",
        ],
    )

    assert rc == 0
    assert stderr == ""
    assert "Hub selector: --hub-node document-processing.fraud-status.consumer" in stdout
    assert "1. document-processing.fraud-status.producer" in stdout
    assert "   inclusion: prerequisite for selected node" in stdout
    assert "2. document-processing.fraud-status.consumer" in stdout
    assert "   inclusion: selected node" in stdout
    assert "fraud_status.job_reference from document-processing.fraud-status.producer" in stdout
    assert "parse.protected" not in stdout
    assert "Executing command:" not in stdout


def test_suite_extended_hub_group_filters_to_endpoint_group_nodes():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "extended", "--dry-run", "--hub-group", "get-smoke"])

    assert rc == 0
    assert stderr == ""
    assert "Hub selector: --hub-group get-smoke" in stdout
    assert "Selection scope: endpoint-group nodes plus required prerequisite closure." in stdout
    assert "1. get-smoke.safe-read-only" in stdout
    assert "   inclusion: selected endpoint-group node" in stdout
    assert "endpoint group: get-smoke" in stdout
    assert "parse.protected" not in stdout
    assert "batch.validation" not in stdout
    assert "Executing command:" not in stdout


def test_suite_extended_unknown_hub_node_fails_clearly():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "extended", "--dry-run", "--hub-node", "missing.node"])

    assert rc == 2
    assert stdout == ""
    assert "Unknown hub node id for --hub-node: missing.node" in stderr


def test_suite_extended_unknown_hub_group_fails_clearly():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "extended", "--dry-run", "--hub-group", "missing-group"])

    assert rc == 2
    assert stdout == ""
    assert "Unknown hub endpoint group for --hub-group: missing-group" in stderr


def test_suite_extended_hub_node_and_group_are_mutually_exclusive():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(
        module,
        [
            "--suite",
            "extended",
            "--dry-run",
            "--hub-node",
            "get-smoke.safe-read-only",
            "--hub-group",
            "get-smoke",
        ],
    )

    assert rc == 2
    assert stdout == ""
    assert "--hub-node and --hub-group are mutually exclusive" in stderr


@pytest.mark.parametrize(
    "argv",
    [
        ["--hub-node", "get-smoke.safe-read-only", "--dry-run"],
        ["--suite", "extended", "--hub-node", "get-smoke.safe-read-only"],
        ["--suite", "smoke", "--dry-run", "--hub-node", "get-smoke.safe-read-only"],
        ["--endpoint", "parse", "--category", "matrix", "--dry-run", "--hub-group", "get-smoke"],
        ["--list", "--hub-group", "get-smoke"],
    ],
)
def test_hub_selectors_are_valid_only_for_extended_dry_run(argv: list[str]):
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, argv)

    assert rc == 2
    assert stdout == ""
    assert "--hub-node and --hub-group are supported only with --suite extended --dry-run" in stderr


def test_suite_full_dry_run_does_not_call_subprocess():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "full", "--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "Executing command:" not in stdout


def test_parse_matrix_rejects_mutually_exclusive_fixture_targeting():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(
        module,
        [
            "--endpoint",
            "parse",
            "--category",
            "matrix",
            "--fixtures-json",
            "fixtures.json",
            "--file-types",
            "Payslip",
        ],
    )

    assert rc != 0
    assert stdout == ""
    assert "--fixtures-json and --file-types are mutually exclusive for parse matrix" in stderr


def test_batch_rejects_unsupported_report_flag():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--endpoint", "batch", "--report"])

    assert rc != 0
    assert stdout == ""
    assert "--report is not supported for --endpoint batch" in stderr


def test_suite_smoke_rejects_report_flag():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "smoke", "--report"])

    assert rc != 0
    assert stdout == ""
    assert "--report is not supported for --suite smoke" in stderr


def test_suite_protected_report_rejects_targeting_flags():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "protected", "--report", "--k", "happy"])

    assert rc != 0
    assert stdout == ""
    assert "--k is not supported for --suite protected --report" in stderr


def test_suite_extended_without_dry_run_exits_nonzero_without_execution():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "extended"])

    assert rc != 0
    assert stdout == ""
    assert "Live extended Automation Hub execution is not implemented yet" in stderr
