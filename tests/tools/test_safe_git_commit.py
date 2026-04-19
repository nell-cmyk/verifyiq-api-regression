from __future__ import annotations

import subprocess
from collections import defaultdict

import pytest

import tools.safe_git_commit as safe_git_commit


def _completed(command, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(list(command), returncode, stdout, stderr)


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], list[subprocess.CompletedProcess[str]]]):
        self._responses = defaultdict(list, responses)
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, command, *, repo_root, capture_output=False):
        key = tuple(str(part) for part in command)
        self.calls.append(key)
        queue = self._responses.get(key)
        if not queue:
            raise AssertionError(f"Unexpected command: {key}")
        return queue.pop(0)


def _staged_repo_responses() -> dict[tuple[str, ...], list[subprocess.CompletedProcess[str]]]:
    return {
        ("git", "status", "--porcelain=v1"): [
            _completed(("git", "status"), stdout="M  AGENTS.md\n"),
            _completed(("git", "status"), stdout="M  AGENTS.md\n"),
            _completed(("git", "status"), stdout="M  AGENTS.md\n"),
        ],
        ("git", "diff", "--cached", "--name-only"): [
            _completed(("git", "diff"), stdout="AGENTS.md\n"),
            _completed(("git", "diff"), stdout="AGENTS.md\n"),
        ],
        ("git", "diff", "--name-only"): [
            _completed(("git", "diff"), stdout=""),
            _completed(("git", "diff"), stdout=""),
        ],
        ("git", "ls-files", "--others", "--exclude-standard"): [
            _completed(("git", "ls-files"), stdout=""),
            _completed(("git", "ls-files"), stdout=""),
        ],
    }


def test_refuses_when_nothing_is_staged(monkeypatch, tmp_path, capsys):
    runner = FakeRunner(
        {
            ("git", "status", "--porcelain=v1"): [_completed(("git", "status"), stdout="")],
            ("git", "diff", "--cached", "--name-only"): [_completed(("git", "diff"), stdout="")],
            ("git", "diff", "--name-only"): [_completed(("git", "diff"), stdout="")],
            ("git", "ls-files", "--others", "--exclude-standard"): [
                _completed(("git", "ls-files"), stdout="")
            ],
        }
    )
    monkeypatch.setattr(safe_git_commit, "_run", runner)

    rc = safe_git_commit.run(["--message", "test commit"], repo_root=tmp_path)

    assert rc == 1
    stderr = capsys.readouterr().err
    assert "No staged changes found" in stderr
    assert ("git", "commit", "-m", "test commit") not in runner.calls


def test_refuses_when_leftover_changes_remain_after_targeted_stage(monkeypatch, tmp_path, capsys):
    runner = FakeRunner(
        {
            ("git", "status", "--porcelain=v1"): [
                _completed(("git", "status"), stdout=" M AGENTS.md\n M docs/operations/matrix.md\n")
            ],
            ("git", "diff", "--cached", "--name-only"): [_completed(("git", "diff"), stdout="")],
            ("git", "diff", "--name-only"): [
                _completed(("git", "diff"), stdout="AGENTS.md\ndocs/operations/matrix.md\n")
            ],
            ("git", "ls-files", "--others", "--exclude-standard"): [
                _completed(("git", "ls-files"), stdout="")
            ],
            ("git", "diff", "--cached", "--name-only", "--", "AGENTS.md"): [
                _completed(("git", "diff"), stdout="")
            ],
            ("git", "diff", "--name-only", "--", "AGENTS.md"): [
                _completed(("git", "diff"), stdout="AGENTS.md\n")
            ],
            ("git", "ls-files", "--others", "--exclude-standard", "--", "AGENTS.md"): [
                _completed(("git", "ls-files"), stdout="")
            ],
        }
    )
    monkeypatch.setattr(safe_git_commit, "_run", runner)

    rc = safe_git_commit.run(
        ["--message", "test commit", "--stage", "AGENTS.md"],
        repo_root=tmp_path,
    )

    assert rc == 1
    stderr = capsys.readouterr().err
    assert "unstaged changes" in stderr
    assert "docs/operations/matrix.md" in stderr
    assert ("git", "add", "-A", "--", "AGENTS.md") not in runner.calls


@pytest.mark.parametrize(
    ("validation", "expected_command"),
    [
        ("baseline", tuple(safe_git_commit.VALIDATION_COMMANDS["baseline"])),
        ("full", tuple(safe_git_commit.VALIDATION_COMMANDS["full"])),
    ],
)
def test_selects_expected_validation_command(
    monkeypatch,
    tmp_path,
    capsys,
    validation,
    expected_command,
):
    responses = _staged_repo_responses()
    responses[expected_command] = [_completed(expected_command)]
    responses[("git", "commit", "-m", "test commit")] = [
        _completed(("git", "commit", "-m", "test commit"))
    ]
    runner = FakeRunner(responses)
    monkeypatch.setattr(safe_git_commit, "_run", runner)

    rc = safe_git_commit.run(
        ["--message", "test commit", "--validation", validation],
        repo_root=tmp_path,
    )

    assert rc == 0
    stdout = capsys.readouterr().out
    assert f"Running validation ({validation})" in stdout
    assert expected_command in runner.calls
    assert ("git", "commit", "-m", "test commit") in runner.calls


def test_auto_message_dry_run_previews_generated_commit_subject(monkeypatch, tmp_path, capsys):
    runner = FakeRunner(
        {
            ("git", "status", "--porcelain=v1"): [
                _completed(
                    ("git", "status"),
                    stdout="M  tests/endpoints/parse/test_parse.py\nM  tools/safe_git_commit.py\n",
                )
            ],
            ("git", "diff", "--cached", "--name-only"): [
                _completed(
                    ("git", "diff"),
                    stdout="tests/endpoints/parse/test_parse.py\ntools/safe_git_commit.py\n",
                )
            ],
            ("git", "diff", "--name-only"): [_completed(("git", "diff"), stdout="")],
            ("git", "ls-files", "--others", "--exclude-standard"): [
                _completed(("git", "ls-files"), stdout="")
            ],
        }
    )
    monkeypatch.setattr(safe_git_commit, "_run", runner)

    rc = safe_git_commit.run(["--auto-message", "--dry-run"], repo_root=tmp_path)

    assert rc == 0
    stdout = capsys.readouterr().out
    assert "Commit message: Update parse tests and tooling" in stdout
    assert 'Would commit with: git commit -m "Update parse tests and tooling"' in stdout
    assert ("git", "commit", "-m", "Update parse tests and tooling") not in runner.calls


def test_dry_run_previews_commands_without_mutating_git(monkeypatch, tmp_path, capsys):
    runner = FakeRunner(
        {
            ("git", "status", "--porcelain=v1"): [
                _completed(("git", "status"), stdout=" M AGENTS.md\n?? tools/safe_git_commit.py\n")
            ],
            ("git", "diff", "--cached", "--name-only"): [_completed(("git", "diff"), stdout="")],
            ("git", "diff", "--name-only"): [_completed(("git", "diff"), stdout="AGENTS.md\n")],
            ("git", "ls-files", "--others", "--exclude-standard"): [
                _completed(("git", "ls-files"), stdout="tools/safe_git_commit.py\n")
            ],
            ("git", "branch", "--show-current"): [_completed(("git", "branch"), stdout="main\n")],
            ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): [
                _completed(("git", "rev-parse"), stdout="origin/main\n")
            ],
            ("git", "config", "--get", "branch.main.remote"): [
                _completed(("git", "config"), stdout="origin\n")
            ],
            ("git", "config", "--get", "branch.main.merge"): [
                _completed(("git", "config"), stdout="refs/heads/main\n")
            ],
        }
    )
    monkeypatch.setattr(safe_git_commit, "_run", runner)

    rc = safe_git_commit.run(
        ["--message", "test commit", "--stage-all", "--push", "--dry-run"],
        repo_root=tmp_path,
    )

    assert rc == 0
    stdout = capsys.readouterr().out
    assert "Dry run only" in stdout
    assert 'Would stage: git add -A' in stdout
    assert "Would validate with:" in stdout
    assert "Would commit with: git commit -m \"test commit\"" in stdout
    assert "Would push with: git push origin HEAD:main" in stdout
    assert ("git", "add", "-A") not in runner.calls
    assert ("git", "commit", "-m", "test commit") not in runner.calls
    assert ("git", "push", "origin", "HEAD:main") not in runner.calls


def test_auto_message_is_used_for_real_commit(monkeypatch, tmp_path, capsys):
    responses = {
        ("git", "status", "--porcelain=v1"): [
            _completed(
                ("git", "status"),
                stdout="M  tests/endpoints/parse/test_parse.py\nM  tools/safe_git_commit.py\n",
            ),
            _completed(
                ("git", "status"),
                stdout="M  tests/endpoints/parse/test_parse.py\nM  tools/safe_git_commit.py\n",
            ),
            _completed(
                ("git", "status"),
                stdout="M  tests/endpoints/parse/test_parse.py\nM  tools/safe_git_commit.py\n",
            ),
        ],
        ("git", "diff", "--cached", "--name-only"): [
            _completed(
                ("git", "diff"),
                stdout="tests/endpoints/parse/test_parse.py\ntools/safe_git_commit.py\n",
            ),
            _completed(
                ("git", "diff"),
                stdout="tests/endpoints/parse/test_parse.py\ntools/safe_git_commit.py\n",
            ),
        ],
        ("git", "diff", "--name-only"): [
            _completed(("git", "diff"), stdout=""),
            _completed(("git", "diff"), stdout=""),
        ],
        ("git", "ls-files", "--others", "--exclude-standard"): [
            _completed(("git", "ls-files"), stdout=""),
            _completed(("git", "ls-files"), stdout=""),
        ],
    }
    auto_message = "Update parse tests and tooling"
    validation_command = tuple(safe_git_commit.VALIDATION_COMMANDS["baseline"])
    responses[validation_command] = [
        _completed(validation_command)
    ]
    responses[("git", "commit", "-m", auto_message)] = [
        _completed(("git", "commit", "-m", auto_message))
    ]
    runner = FakeRunner(responses)
    monkeypatch.setattr(safe_git_commit, "_run", runner)

    rc = safe_git_commit.run(["--auto-message"], repo_root=tmp_path)

    assert rc == 0
    stdout = capsys.readouterr().out
    assert f"Auto-generated commit message: {auto_message}" in stdout
    assert ("git", "commit", "-m", auto_message) in runner.calls


def test_push_requires_safe_branch_configuration(monkeypatch, tmp_path, capsys):
    scenarios = [
        (
            "detached",
            {
                ("git", "status", "--porcelain=v1"): [
                    _completed(("git", "status"), stdout="M  AGENTS.md\n")
                ],
                ("git", "diff", "--cached", "--name-only"): [
                    _completed(("git", "diff"), stdout="AGENTS.md\n")
                ],
                ("git", "diff", "--name-only"): [_completed(("git", "diff"), stdout="")],
                ("git", "ls-files", "--others", "--exclude-standard"): [
                    _completed(("git", "ls-files"), stdout="")
                ],
                ("git", "branch", "--show-current"): [_completed(("git", "branch"), stdout="")],
            },
            "detached",
        ),
        (
            "no-upstream",
            {
                ("git", "status", "--porcelain=v1"): [
                    _completed(("git", "status"), stdout="M  AGENTS.md\n")
                ],
                ("git", "diff", "--cached", "--name-only"): [
                    _completed(("git", "diff"), stdout="AGENTS.md\n")
                ],
                ("git", "diff", "--name-only"): [_completed(("git", "diff"), stdout="")],
                ("git", "ls-files", "--others", "--exclude-standard"): [
                    _completed(("git", "ls-files"), stdout="")
                ],
                ("git", "branch", "--show-current"): [
                    _completed(("git", "branch"), stdout="main\n")
                ],
                ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): [
                    _completed(("git", "rev-parse"), returncode=128, stderr="no upstream")
                ],
            },
            "no upstream",
        ),
        (
            "mismatched-upstream",
            {
                ("git", "status", "--porcelain=v1"): [
                    _completed(("git", "status"), stdout="M  AGENTS.md\n")
                ],
                ("git", "diff", "--cached", "--name-only"): [
                    _completed(("git", "diff"), stdout="AGENTS.md\n")
                ],
                ("git", "diff", "--name-only"): [_completed(("git", "diff"), stdout="")],
                ("git", "ls-files", "--others", "--exclude-standard"): [
                    _completed(("git", "ls-files"), stdout="")
                ],
                ("git", "branch", "--show-current"): [
                    _completed(("git", "branch"), stdout="main\n")
                ],
                ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): [
                    _completed(("git", "rev-parse"), stdout="origin/develop\n")
                ],
                ("git", "config", "--get", "branch.main.remote"): [
                    _completed(("git", "config"), stdout="origin\n")
                ],
                ("git", "config", "--get", "branch.main.merge"): [
                    _completed(("git", "config"), stdout="refs/heads/develop\n")
                ],
            },
            "does not match the current branch",
        ),
    ]

    for _, responses, expected_text in scenarios:
        runner = FakeRunner(responses)
        monkeypatch.setattr(safe_git_commit, "_run", runner)
        rc = safe_git_commit.run(
            ["--message", "test commit", "--push"],
            repo_root=tmp_path,
        )
        assert rc == 1
        stderr = capsys.readouterr().err
        assert expected_text in stderr
        assert ("git", "commit", "-m", "test commit") not in runner.calls
