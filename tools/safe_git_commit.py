#!/usr/bin/env python3
"""Review-first Git automation for guarded local commit and push flows."""
from __future__ import annotations

import argparse
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
REGRESSION_RUNNER = REPO_ROOT / "tools" / "run_regression.py"

VALIDATION_COMMANDS: dict[str, list[str]] = {
    "baseline": [sys.executable, str(REGRESSION_RUNNER)],
    "full": [sys.executable, str(REGRESSION_RUNNER), "--suite", "full"],
    "non-live": [
        "env",
        "VERIFYIQ_SKIP_DOTENV=1",
        sys.executable,
        "-m",
        "pytest",
        "tests/tools/",
        "tests/reporting/",
        "tests/skills/",
        "-v",
    ],
}


class SafeGitError(RuntimeError):
    """Raised when the guarded Git workflow should stop before mutating history."""


@dataclass(frozen=True)
class WorktreeState:
    porcelain: str
    staged: tuple[str, ...]
    unstaged: tuple[str, ...]
    untracked: tuple[str, ...]


@dataclass(frozen=True)
class PushTarget:
    remote: str
    branch: str


@dataclass(frozen=True)
class PreviewState:
    staged: tuple[str, ...]
    unstaged: tuple[str, ...]
    untracked: tuple[str, ...]
    stage_command: list[str] | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Review-first Git helper for staging intended changes, validating, "
            "committing, and optionally pushing."
        )
    )
    message_group = parser.add_mutually_exclusive_group(required=True)
    message_group.add_argument("--message", help="Explicit commit message to use.")
    message_group.add_argument(
        "--auto-message",
        action="store_true",
        help="Compose a commit message from the staged file paths.",
    )
    parser.add_argument(
        "--validation",
        choices=tuple(VALIDATION_COMMANDS),
        default="baseline",
        help="Validation gate to run before commit.",
    )
    stage_group = parser.add_mutually_exclusive_group()
    stage_group.add_argument(
        "--stage",
        nargs="+",
        metavar="PATH",
        help="Stage only the provided path(s) with git add -A -- <paths...>.",
    )
    stage_group.add_argument(
        "--stage-all",
        action="store_true",
        help="Stage all tracked and untracked changes with git add -A.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push HEAD to the current branch's matching upstream after commit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned commands without changing Git state.",
    )
    return parser


def _run(
    command: Sequence[str],
    *,
    repo_root: Path,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    kwargs = {
        "cwd": str(repo_root),
        "check": False,
        "text": True,
    }
    if capture_output:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    return subprocess.run(list(command), **kwargs)


def _format_command(command: Sequence[str]) -> str:
    return subprocess.list2cmdline([str(part) for part in command])


def _lines_from_output(text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in text.splitlines() if line.strip())


def _unique_paths(*groups: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for group in groups:
        for path in group:
            if path not in seen:
                seen.add(path)
                ordered.append(path)
    return tuple(ordered)


def _capture(command: Sequence[str], *, repo_root: Path, failure_message: str) -> str:
    completed = _run(command, repo_root=repo_root, capture_output=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise SafeGitError(f"{failure_message}\n{detail}".rstrip())
    return completed.stdout


def _git_name_list(
    args: Sequence[str],
    *,
    repo_root: Path,
    pathspecs: Sequence[str] | None = None,
) -> tuple[str, ...]:
    command = ["git", *args]
    if pathspecs:
        command.extend(["--", *pathspecs])
    output = _capture(command, repo_root=repo_root, failure_message=f"Git command failed: {_format_command(command)}")
    return _lines_from_output(output)


def read_worktree_state(*, repo_root: Path) -> WorktreeState:
    porcelain = _capture(
        ["git", "status", "--porcelain=v1"],
        repo_root=repo_root,
        failure_message="Unable to read git status.",
    )
    return WorktreeState(
        porcelain=porcelain,
        staged=_git_name_list(["diff", "--cached", "--name-only"], repo_root=repo_root),
        unstaged=_git_name_list(["diff", "--name-only"], repo_root=repo_root),
        untracked=_git_name_list(
            ["ls-files", "--others", "--exclude-standard"],
            repo_root=repo_root,
        ),
    )


def build_stage_command(args: argparse.Namespace) -> list[str] | None:
    if args.stage_all:
        return ["git", "add", "-A"]
    if args.stage:
        return ["git", "add", "-A", "--", *args.stage]
    return None


def preview_worktree_state(
    args: argparse.Namespace,
    *,
    repo_root: Path,
    current: WorktreeState,
) -> PreviewState:
    stage_command = build_stage_command(args)
    if args.stage_all:
        return PreviewState(
            staged=_unique_paths(current.staged, current.unstaged, current.untracked),
            unstaged=(),
            untracked=(),
            stage_command=stage_command,
        )

    if args.stage:
        targeted = _unique_paths(
            _git_name_list(
                ["diff", "--cached", "--name-only"],
                repo_root=repo_root,
                pathspecs=args.stage,
            ),
            _git_name_list(
                ["diff", "--name-only"],
                repo_root=repo_root,
                pathspecs=args.stage,
            ),
            _git_name_list(
                ["ls-files", "--others", "--exclude-standard"],
                repo_root=repo_root,
                pathspecs=args.stage,
            ),
        )
        targeted_set = set(targeted)
        return PreviewState(
            staged=_unique_paths(current.staged, targeted),
            unstaged=tuple(path for path in current.unstaged if path not in targeted_set),
            untracked=tuple(path for path in current.untracked if path not in targeted_set),
            stage_command=stage_command,
        )

    return PreviewState(
        staged=current.staged,
        unstaged=current.unstaged,
        untracked=current.untracked,
        stage_command=None,
    )


def _format_paths(label: str, paths: Sequence[str]) -> str:
    lines = [f"{label}:"]
    lines.extend(f"  - {path}" for path in paths)
    return "\n".join(lines)


LABEL_PRIORITY = {
    "parse tests": 0,
    "parse docs": 1,
    "tests": 2,
    "tooling": 3,
    "docs": 4,
    "skills": 5,
    "repo files": 99,
}


def _classify_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("tests/endpoints/parse/"):
        return "parse tests"
    if normalized.startswith("tests/"):
        return "tests"
    if normalized.startswith("tools/"):
        return "tooling"
    if normalized.startswith("docs/knowledge-base/parse/"):
        return "parse docs"
    if normalized.startswith("docs/"):
        return "docs"
    if normalized.startswith(".codex/skills/"):
        return "skills"
    if normalized in {"AGENTS.md", "CLAUDE.md"}:
        return "docs"
    return "repo files"


def compose_commit_message(paths: Sequence[str]) -> str:
    counts = Counter(_classify_path(path) for path in paths)
    if len(counts) > 1 and "repo files" in counts:
        del counts["repo files"]
    labels = [
        label
        for label, _ in sorted(
            counts.items(),
            key=lambda item: (-item[1], LABEL_PRIORITY.get(item[0], 50), item[0]),
        )
    ]
    if not labels:
        raise SafeGitError("Cannot compose a commit message without staged changes.")
    if len(labels) == 1:
        subject = labels[0]
    elif len(labels) == 2:
        subject = f"{labels[0]} and {labels[1]}"
    else:
        subject = f"{labels[0]}, {labels[1]}, and related repo files"
    return f"Update {subject}"


def ensure_safe_worktree(
    *,
    staged: Sequence[str],
    unstaged: Sequence[str],
    untracked: Sequence[str],
) -> None:
    if not staged:
        raise SafeGitError(
            "No staged changes found. Review and stage intended changes first, "
            "or use --stage/--stage-all."
        )

    problems: list[str] = []
    if unstaged:
        problems.append(_format_paths("Refusing to continue with unstaged changes", unstaged))
    if untracked:
        problems.append(_format_paths("Refusing to continue with untracked files", untracked))
    if problems:
        raise SafeGitError("\n".join(problems))


def resolve_push_target(*, repo_root: Path) -> PushTarget:
    branch = _capture(
        ["git", "branch", "--show-current"],
        repo_root=repo_root,
        failure_message="Unable to determine the current branch.",
    ).strip()
    if not branch:
        raise SafeGitError("Push requested, but HEAD is detached. Check out a branch first.")

    upstream = _run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        repo_root=repo_root,
        capture_output=True,
    )
    if upstream.returncode != 0 or not upstream.stdout.strip():
        detail = (upstream.stderr or upstream.stdout or "").strip()
        raise SafeGitError(
            "Push requested, but the current branch has no upstream configured."
            + (f"\n{detail}" if detail else "")
        )

    remote = _run(
        ["git", "config", "--get", f"branch.{branch}.remote"],
        repo_root=repo_root,
        capture_output=True,
    )
    merge_ref = _run(
        ["git", "config", "--get", f"branch.{branch}.merge"],
        repo_root=repo_root,
        capture_output=True,
    )
    if remote.returncode != 0 or merge_ref.returncode != 0:
        raise SafeGitError("Push requested, but branch remote/merge settings could not be resolved.")

    remote_name = remote.stdout.strip()
    merge_value = merge_ref.stdout.strip()
    expected_merge = f"refs/heads/{branch}"
    if not remote_name:
        raise SafeGitError("Push requested, but branch remote settings are empty.")
    if merge_value != expected_merge:
        raise SafeGitError(
            "Push requested, but the upstream branch does not match the current branch.\n"
            f"Current branch: {branch}\n"
            f"Upstream ref: {merge_value}\n"
            f"Expected ref: {expected_merge}"
        )

    return PushTarget(remote=remote_name, branch=branch)


def print_plan(
    *,
    preview: PreviewState,
    commit_message: str,
    validation_command: Sequence[str],
    commit_command: Sequence[str],
    push_command: Sequence[str] | None,
) -> None:
    if preview.stage_command:
        print(f"Would stage: {_format_command(preview.stage_command)}")
    else:
        print("Would use the current index exactly as staged.")

    print(_format_paths("Would commit these paths", preview.staged))
    print(f"Commit message: {commit_message}")
    print(f"Would validate with: {_format_command(validation_command)}")
    print(f"Would commit with: {_format_command(commit_command)}")
    if push_command:
        print(f"Would push with: {_format_command(push_command)}")
    else:
        print("Would not push after commit.")


def run(argv: Sequence[str] | None = None, *, repo_root: Path = REPO_ROOT) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    try:
        current = read_worktree_state(repo_root=repo_root)
        preview = preview_worktree_state(args, repo_root=repo_root, current=current)
        ensure_safe_worktree(
            staged=preview.staged,
            unstaged=preview.unstaged,
            untracked=preview.untracked,
        )

        push_target = resolve_push_target(repo_root=repo_root) if args.push else None
        validation_command = VALIDATION_COMMANDS[args.validation]
        commit_message = args.message or compose_commit_message(preview.staged)
        commit_command = ["git", "commit", "-m", commit_message]
        push_command = (
            ["git", "push", push_target.remote, f"HEAD:{push_target.branch}"]
            if push_target
            else None
        )

        if args.dry_run:
            print("Dry run only. No Git state will be changed.")
            print_plan(
                preview=preview,
                commit_message=commit_message,
                validation_command=validation_command,
                commit_command=commit_command,
                push_command=push_command,
            )
            return 0

        stage_command = build_stage_command(args)
        if stage_command:
            print(f"Staging intended changes: {_format_command(stage_command)}")
            staged = _run(stage_command, repo_root=repo_root)
            if staged.returncode != 0:
                raise SafeGitError(f"Staging failed: {_format_command(stage_command)}")

        state = read_worktree_state(repo_root=repo_root)
        ensure_safe_worktree(
            staged=state.staged,
            unstaged=state.unstaged,
            untracked=state.untracked,
        )
        tracked_snapshot = state.porcelain
        commit_message = args.message or compose_commit_message(state.staged)
        commit_command = ["git", "commit", "-m", commit_message]

        print(f"Running validation ({args.validation}): {_format_command(validation_command)}")
        validation = _run(validation_command, repo_root=repo_root)
        if validation.returncode != 0:
            print(f"Validation failed with exit code {validation.returncode}. Commit aborted.")
            return validation.returncode

        post_validation = _capture(
            ["git", "status", "--porcelain=v1"],
            repo_root=repo_root,
            failure_message="Unable to re-read git status after validation.",
        )
        if post_validation != tracked_snapshot:
            raise SafeGitError(
                "Validation changed tracked git state. Aborting before commit.\n"
                "Review the diff and restage before retrying."
            )

        if args.auto_message:
            print(f"Auto-generated commit message: {commit_message}")
        print(f"Creating commit: {_format_command(commit_command)}")
        commit = _run(commit_command, repo_root=repo_root)
        if commit.returncode != 0:
            print(f"Commit failed with exit code {commit.returncode}.")
            return commit.returncode

        if push_command:
            print(f"Pushing commit: {_format_command(push_command)}")
            push = _run(push_command, repo_root=repo_root)
            if push.returncode != 0:
                print(f"Push failed with exit code {push.returncode}.")
                return push.returncode

        print("Safe Git workflow completed successfully.")
        return 0
    except SafeGitError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
