import os
import time
from pathlib import Path

import pytest

from tests.client import make_client
from tests.reporting import is_enabled
from tests.reporting.collector import CURRENT_NODEID, get_collector


@pytest.fixture(scope="session")
def client():
    with make_client() as c:
        yield c


# ── Regression reporter pytest hooks ──────────────────────────────────────────
# All hooks below are no-ops unless REGRESSION_REPORT=1. The protected baseline
# (`pytest tests/endpoints/parse/ -v`) must not change behavior when unset.


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _derive_fixture_and_endpoint(item: "pytest.Item") -> tuple[dict, dict, str]:
    """Best-effort: pull fixture identity + endpoint + fileType from the test item.

    Matrix tests parametrize a `fixture` dict with gcs_uri/file_type/etc.
    Baseline happy-path uses env vars. Validation/auth tests have no fixture.
    """
    fixture: dict = {}
    file_type: dict = {}
    endpoint = ""

    callspec = getattr(item, "callspec", None)
    params = getattr(callspec, "params", {}) if callspec else {}
    f = params.get("fixture") if isinstance(params, dict) else None
    if isinstance(f, dict):
        fixture = {
            "name": f.get("name"),
            "gcs_uri": f.get("gcs_uri"),
            "source_row": f.get("source_row"),
            "verification_status": f.get("verification_status"),
            "registry_file_type": f.get("file_type"),
        }
        try:
            from tests.endpoints.parse.file_types import request_file_type_for
            file_type = {
                "registry": f.get("file_type"),
                "request": request_file_type_for(f.get("file_type", "")) if f.get("file_type") else None,
            }
        except Exception:
            file_type = {"registry": f.get("file_type")}

    mod_name = getattr(item.module, "__name__", "") if hasattr(item, "module") else ""
    if "parse" in mod_name:
        endpoint = "/v1/documents/parse"
        if not fixture:
            # Baseline happy path uses env; expose safely (no secrets).
            env_file = os.getenv("PARSE_FIXTURE_FILE", "")
            env_ft = os.getenv("PARSE_FIXTURE_FILE_TYPE", "")
            if env_file or env_ft:
                fixture = {"gcs_uri": env_file, "registry_file_type": env_ft}
                if env_ft and not file_type:
                    try:
                        from tests.endpoints.parse.file_types import request_file_type_for
                        file_type = {
                            "registry": env_ft,
                            "request": request_file_type_for(env_ft),
                        }
                    except Exception:
                        file_type = {"registry": env_ft}
    elif "batch" in mod_name:
        endpoint = "/v1/documents/batch"

    return fixture, file_type, endpoint


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logstart(nodeid, location):
    if not is_enabled():
        return
    try:
        CURRENT_NODEID.set(nodeid)
        col = get_collector()
        module = location[0] if location else ""
        col.start_case(nodeid, module=module)
    except Exception:
        pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    if is_enabled():
        try:
            CURRENT_NODEID.set(item.nodeid)
            col = get_collector()
            case = col.start_case(item.nodeid, module=item.module.__name__ if hasattr(item, "module") else "", test=item.name)
            fixture, file_type, endpoint = _derive_fixture_and_endpoint(item)
            if fixture:
                case.fixture = fixture
            if file_type:
                case.file_type = file_type
            if endpoint:
                case.endpoint = endpoint
        except Exception:
            pass
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    if is_enabled():
        try:
            CURRENT_NODEID.set(item.nodeid)
        except Exception:
            pass
    yield


def _outcome_from_report(rep) -> str:
    if rep.skipped:
        return "SKIPPED"
    if rep.passed:
        return "PASSED"
    # failed — distinguish collection/setup errors from call failures
    if getattr(rep, "when", "call") != "call":
        return "ERROR"
    return "FAILED"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    if not is_enabled():
        return
    try:
        report = outcome.get_result()
    except Exception:
        return
    try:
        if report.when not in {"call", "setup"}:
            return
        col = get_collector()
        case = col.start_case(item.nodeid)
        # Promote setup/call outcomes; call overrides setup unless setup errored.
        new_outcome = _outcome_from_report(report)
        if report.when == "setup" and new_outcome != "PASSED":
            case.outcome = new_outcome
        elif report.when == "call":
            if case.outcome in {"", "PASSED"}:
                case.outcome = new_outcome
        # Capture traceback on failure/error.
        if not report.passed and not report.skipped:
            long = getattr(report, "longreprtext", "") or ""
            if long:
                case.longrepr = long
        case.end_ts = time.time()
    except Exception:
        pass


def pytest_sessionfinish(session, exitstatus):
    if not is_enabled():
        return
    try:
        from tests.config import BASE_URL
    except Exception:
        BASE_URL = ""
    try:
        from tests.reporting.writer import run_output_dir, write_run
        col = get_collector()
        out_dir = run_output_dir(_REPO_ROOT, col.run_started_at)
        tier = os.getenv("REGRESSION_REPORT_TIER", "").strip() or "baseline"
        paths = write_run(col, tier=tier, base_url=BASE_URL, out_dir=out_dir)
        writer_reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        msg = f"\n[regression-report] wrote {paths['json']}\n[regression-report] wrote {paths['md']}\n"
        if writer_reporter is not None:
            writer_reporter.write_line(msg.strip())
        else:
            import sys
            sys.stderr.write(msg)
    except Exception as exc:
        import sys
        sys.stderr.write(f"[regression-report] failed to write artifacts: {exc}\n")
