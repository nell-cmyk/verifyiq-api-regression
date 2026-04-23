from __future__ import annotations

import importlib.util
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


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
    assert "parse" in stdout
    assert "batch" in stdout
    assert "matrix" in stdout
    assert "tools/run_batch_with_fixtures.py" in stdout


def test_dry_run_without_selection_defaults_to_protected():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "Selection: suite=protected" in stdout
    assert "Default selection: suite=protected" in stdout
    assert "-m pytest tests/endpoints/parse/ -v" in stdout


def test_suite_protected_dry_run_prints_protected_pytest_command():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, _ = _invoke(module, ["--suite", "protected", "--dry-run"])

    assert rc == 0
    assert "Selection: suite=protected" in stdout
    assert "-m pytest tests/endpoints/parse/ -v" in stdout


def test_suite_full_dry_run_prints_full_wrapper_command():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, _ = _invoke(module, ["--suite", "full", "--dry-run"])

    assert rc == 0
    assert "Selection: suite=full" in stdout
    assert "tools/run_parse_full_regression.py" in stdout


def test_suite_smoke_dry_run_prints_get_smoke_pytest_command():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, _ = _invoke(module, ["--suite", "smoke", "--dry-run"])

    assert rc == 0
    assert "Selection: suite=smoke" in stdout
    assert "-m pytest tests/endpoints/get_smoke/ -v" in stdout


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


def test_batch_dry_run_prints_batch_pytest_command():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, _ = _invoke(module, ["--endpoint", "batch", "--dry-run"])

    assert rc == 0
    assert "Selection: endpoint=batch" in stdout
    assert "-m pytest tests/endpoints/batch/ -v" in stdout


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


def test_planned_suite_reports_not_yet_mapped():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "extended", "--dry-run"])

    assert rc != 0
    assert stdout == ""
    assert "planned but not mapped in this first slice" in stderr


def test_suite_full_dry_run_does_not_call_subprocess():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "full", "--dry-run"])

    assert rc == 0
    assert stderr == ""
    assert "Executing command:" not in stdout


def test_parse_matrix_executes_wrapper_and_returns_subprocess_code():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 4

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--endpoint", "parse", "--category", "matrix"])

    assert rc == 4
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
            "focus",
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
        "focus",
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
            "matrix-fixtures.json",
        ],
    )

    assert rc == 0
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        str(module.PARSE_MATRIX_WRAPPER),
        "--fixtures-json",
        "matrix-fixtures.json",
    )
    assert "Executing command:" in stdout


def test_batch_executes_direct_pytest_and_returns_subprocess_code():
    module = _load_module()
    calls: list[tuple[str, ...]] = []

    def fake_run_command(command: tuple[str, ...]) -> int:
        calls.append(command)
        return 6

    module._run_command = fake_run_command

    rc, stdout, stderr = _invoke(module, ["--endpoint", "batch"])

    assert rc == 6
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


def test_batch_executes_direct_pytest_with_supported_k_flag():
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


def test_batch_fixtures_json_executes_batch_wrapper():
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
            "batch",
            "--fixtures-json",
            "batch-fixtures.json",
            "--k",
            "warning",
        ],
    )

    assert rc == 0
    assert stderr == ""
    assert len(calls) == 1
    assert calls[0] == (
        sys.executable,
        str(module.BATCH_WRAPPER),
        "--fixtures-json",
        "batch-fixtures.json",
        "--k",
        "warning",
    )
    assert "Executing command:" in stdout


def test_suite_extended_without_dry_run_exits_nonzero_without_execution():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--suite", "extended"])

    assert rc != 0
    assert stdout == ""
    assert "Live execution is implemented for protected, smoke, and full suites" in stderr


def test_report_remains_rejected_for_batch_live_and_dry_run():
    module = _load_module()
    module._run_command = _no_call_runner

    rc, stdout, stderr = _invoke(module, ["--endpoint", "batch", "--report", "--dry-run"])

    assert rc != 0
    assert stdout == ""
    assert "--report is not yet supported for --endpoint batch dry-runs." in stderr
