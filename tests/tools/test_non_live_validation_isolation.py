from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
NON_LIVE_TARGET_DIRS = (
    "tests/tools/",
    "tests/reporting/",
    "tests/skills/",
)
LIVE_FIXTURE_IMPORTS = {
    "tests.endpoints.parse.fixtures",
    "tests.endpoints.batch.fixtures",
}


def _load_safe_git_commit_module():
    script_path = REPO_ROOT / "tools" / "safe_git_commit.py"
    spec = importlib.util.spec_from_file_location("safe_git_commit", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _python_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_safe_commit_non_live_validation_uses_only_offline_targets() -> None:
    safe_git_commit = _load_safe_git_commit_module()

    command = tuple(safe_git_commit.VALIDATION_COMMANDS["non-live"])

    assert "VERIFYIQ_SKIP_DOTENV=1" in command
    for target in NON_LIVE_TARGET_DIRS:
        assert target in command
    assert "tests/endpoints/" not in command


def test_non_live_ci_workflow_uses_skip_dotenv_and_offline_targets() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "non-live-validation.yml").read_text(
        encoding="utf-8"
    )

    assert "VERIFYIQ_SKIP_DOTENV: '1'" in workflow
    for target in NON_LIVE_TARGET_DIRS:
        assert f"python -m pytest {target} -v" in workflow
    assert "python -m pytest tests/endpoints/" not in workflow


def test_non_live_targets_do_not_import_live_endpoint_fixture_modules() -> None:
    imported_by_file: dict[str, set[str]] = {}
    for target in NON_LIVE_TARGET_DIRS:
        for path in (REPO_ROOT / target).rglob("*.py"):
            forbidden = _python_imports(path) & LIVE_FIXTURE_IMPORTS
            if forbidden:
                imported_by_file[path.relative_to(REPO_ROOT).as_posix()] = forbidden

    assert not imported_by_file
