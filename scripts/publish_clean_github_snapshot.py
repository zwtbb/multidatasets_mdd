#!/usr/bin/env python3
"""Publish the current tracked tree onto the clean GitHub history.

The local experiment branch has useful history for server work, but it once
contained generated Phase 2 result blobs. This helper avoids pushing that local
history. It archives a committed source ref, overlays the archive onto a fresh
clone of the clean remote branch, checks the publish tree for banned artifacts
and secrets, commits the snapshot on the clean lineage, and optionally pushes.

By default the command is a dry run. Add ``--push`` only after reviewing the
reported checks and diff summary.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REMOTE = "https://github.com/zwtbb/multidatasets_mdd.git"
DEFAULT_BRANCH = "main"
DEFAULT_MESSAGE = "Publish clean experiment snapshot"

BANNED_PATH_PATTERNS = [
    re.compile(r"^analysis/phase2_baselines/"),
    re.compile(r"(^|/).*predictions.*\.csv$", re.IGNORECASE),
    re.compile(r"(^|/).*embeddings.*\.csv$", re.IGNORECASE),
    re.compile(r"(^|/).*model.*\.(joblib|pkl)$", re.IGNORECASE),
    re.compile(r"(^|/).*weights.*\.csv$", re.IGNORECASE),
]

SECRET_PATTERNS = [
    re.compile(rb"gho_[A-Za-z0-9_]{20,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(rb"https://[^/\s:@]+:[^/\s:@]+@github\.com/"),
    re.compile(rb"(?i)\b(password|passwd|pwd|token|secret)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
]

TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str


def run(
    args: list[str],
    cwd: Path,
    *,
    capture: bool = True,
    check: bool = True,
) -> CommandResult:
    process = subprocess.run(
        args,
        cwd=str(cwd),
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    stdout = process.stdout or ""
    if check and process.returncode != 0:
        if stdout:
            print(stdout, file=sys.stderr)
        raise SystemExit(f"command failed ({process.returncode}): {' '.join(args)}")
    return CommandResult(args=args, returncode=process.returncode, stdout=stdout)


def source_tree_is_clean(source_repo: Path) -> bool:
    unstaged = run(["git", "diff", "--quiet"], source_repo, capture=True, check=False)
    staged = run(["git", "diff", "--cached", "--quiet"], source_repo, capture=True, check=False)
    return unstaged.returncode == 0 and staged.returncode == 0


def tracked_file_count(source_repo: Path, source_ref: str) -> int:
    result = run(["git", "ls-tree", "-r", "--name-only", source_ref], source_repo)
    return len([line for line in result.stdout.splitlines() if line.strip()])


def archive_source(source_repo: Path, source_ref: str, archive_path: Path) -> None:
    run(["git", "archive", "--format=tar", source_ref, "-o", str(archive_path)], source_repo, capture=True)


def clone_or_init(remote: str, branch: str, target: Path) -> None:
    branch_probe = run(
        ["git", "ls-remote", "--exit-code", remote, f"refs/heads/{branch}"],
        Path.cwd(),
        capture=True,
        check=False,
    )
    if branch_probe.returncode == 0:
        run(
            ["git", "clone", "--branch", branch, "--single-branch", remote, str(target)],
            Path.cwd(),
            capture=False,
        )
        return

    if branch_probe.stdout.strip():
        print(branch_probe.stdout, file=sys.stderr)
        raise SystemExit("unable to inspect remote branch; refusing to initialize a publish repo")

    # No matching branch exists. This is only for first-publish or empty-remote
    # cases; existing clean remotes should have been cloned above.
    target.mkdir(parents=True)
    run(["git", "init", "-b", branch], target)
    run(["git", "remote", "add", "origin", remote], target)


def clear_worktree(repo: Path) -> None:
    for child in repo.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def extract_archive(archive_path: Path, target: Path) -> None:
    with tarfile.open(archive_path, "r") as archive:
        archive.extractall(target)


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file():
            yield path


def relative_posix(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def check_banned_paths(repo: Path) -> list[str]:
    violations: list[str] = []
    for path in iter_files(repo):
        rel = relative_posix(repo, path)
        if any(pattern.search(rel) for pattern in BANNED_PATH_PATTERNS):
            violations.append(rel)
    return sorted(violations)


def should_scan_content(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    try:
        sample = path.read_bytes()[:2048]
    except OSError:
        return False
    return b"\0" not in sample


def check_secrets(repo: Path) -> list[str]:
    violations: list[str] = []
    for path in iter_files(repo):
        if not should_scan_content(path):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(data):
                violations.append(relative_posix(repo, path))
                break
    return sorted(set(violations))


def git_file_policy_check(repo: Path) -> None:
    banned = check_banned_paths(repo)
    if banned:
        print("Banned publish paths:", file=sys.stderr)
        for path in banned:
            print(f"  {path}", file=sys.stderr)
        raise SystemExit("publish tree contains banned artifacts")

    secrets = check_secrets(repo)
    if secrets:
        print("Secret-like content found:", file=sys.stderr)
        for path in secrets:
            print(f"  {path}", file=sys.stderr)
        raise SystemExit("publish tree contains secret-like content")


def configure_commit_identity(repo: Path) -> None:
    name = run(["git", "config", "user.name"], repo, check=False).stdout.strip()
    email = run(["git", "config", "user.email"], repo, check=False).stdout.strip()
    if not name:
        run(["git", "config", "user.name", "Codex"], repo)
    if not email:
        run(["git", "config", "user.email", "codex@local"], repo)


def has_changes(repo: Path) -> bool:
    result = run(["git", "status", "--porcelain"], repo)
    return bool(result.stdout.strip())


def print_summary(repo: Path, source_repo: Path, source_ref: str, remote: str, branch: str) -> None:
    print("Clean publish candidate")
    print(f"- source: {source_repo} @ {run(['git', 'rev-parse', '--short', source_ref], source_repo).stdout.strip()}")
    print(f"- tracked files from source ref: {tracked_file_count(source_repo, source_ref)}")
    print(f"- remote: {remote}")
    print(f"- branch: {branch}")
    print(f"- staged/working changes: {'yes' if has_changes(repo) else 'no'}")
    status = run(["git", "status", "--short"], repo).stdout.strip()
    if status:
        print("")
        print(status)
    stat = run(["git", "diff", "--stat"], repo).stdout.strip()
    if stat:
        print("")
        print(stat)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--source-repo", type=Path, default=ROOT)
    parser.add_argument("--source-ref", default="HEAD")
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    parser.add_argument("--push", action="store_true", help="push after checks and commit")
    parser.add_argument("--allow-dirty", action="store_true", help="allow dirty source worktree; archive still uses source-ref only")
    parser.add_argument("--keep-temp", action="store_true", help="keep temporary clean repo for inspection")
    args = parser.parse_args()

    source_repo = args.source_repo.resolve()
    if not (source_repo / ".git").exists():
        raise SystemExit(f"not a git repository: {source_repo}")
    if not args.allow_dirty and not source_tree_is_clean(source_repo):
        raise SystemExit("source worktree has tracked changes; commit or stash before publishing")

    temp_root = Path(tempfile.mkdtemp(prefix="clean_publish_"))
    clean_repo = temp_root / "remote"
    archive_path = temp_root / "source.tar"
    try:
        archive_source(source_repo, args.source_ref, archive_path)
        clone_or_init(args.remote, args.branch, clean_repo)
        clear_worktree(clean_repo)
        extract_archive(archive_path, clean_repo)
        git_file_policy_check(clean_repo)
        configure_commit_identity(clean_repo)
        print_summary(clean_repo, source_repo, args.source_ref, args.remote, args.branch)

        if not has_changes(clean_repo):
            print("No clean publish changes to commit.")
            return

        run(["git", "add", "-A"], clean_repo)
        git_file_policy_check(clean_repo)
        sys.stdout.flush()
        run(["git", "commit", "-m", args.message], clean_repo, capture=False)

        if args.push:
            sys.stdout.flush()
            run(["git", "push", "origin", args.branch], clean_repo, capture=False)
            print("Pushed clean snapshot.")
        else:
            print("Dry run complete. Re-run with --push to update the remote.")
    finally:
        if args.keep_temp:
            print(f"Kept temporary repo: {temp_root}")
        else:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
