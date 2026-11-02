"""worktrees_clean.py: make worktrees-clean removes a worktree whose branch is gone from origin or whose PR merged or
closed, and keeps one never pushed, with uncommitted changes or unpushed commits, or on an open PR's branch. Real git: a
bare origin, a clone and its worktrees; GitHub's PRs are a fake gh on PATH."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("worktrees_clean.py")


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def clone(tmp_path, monkeypatch):
    """A clone of a bare origin with one commit on main."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")  # no user config (fetch.prune, signing) leaks in
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    git(tmp_path, "init", "-q", "--bare", "-b", "main", "origin.git")
    git(tmp_path, "clone", "-q", "origin.git", "clone")
    repo = tmp_path / "clone"
    git(repo, "commit", "-q", "--allow-empty", "-m", "first")
    git(repo, "push", "-q", "origin", "HEAD:main")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "gh").write_text(f"#!/bin/sh\ncat {tmp_path / 'prs.json'}\n")
    (bin_ / "gh").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_}{os.pathsep}{os.environ['PATH']}")
    prs(repo)
    return repo


def prs(repo, **states):
    """GitHub's PRs as `gh pr list --json headRefName,state` prints them: head branch -> OPEN, MERGED or CLOSED."""
    (repo.parent / "prs.json").write_text(json.dumps([{"headRefName": b, "state": s} for b, s in states.items()]))


def worktree(repo, branch, *, commit=True, push=True):
    """A worktree beside the clone on a new branch off origin/main, with a commit, pushed."""
    path = repo.parent / "wt" / branch
    git(repo, "worktree", "add", "-q", "-b", branch, str(path), "origin/main")
    if commit:
        git(path, "commit", "-q", "--allow-empty", "-m", branch)
    if push:
        git(path, "push", "-q", "origin", branch)
    return path


def clean(repo):
    return subprocess.run([sys.executable, SCRIPT], cwd=repo, check=True, capture_output=True, text=True).stdout


def test_a_worktree_whose_pr_merged_or_closed_or_whose_branch_is_gone_from_origin_is_removed_and_named(clone):
    merged = worktree(clone, "merged")
    git(merged, "push", "-q", "origin", "merged:main")  # main fast-forwards onto it; the branch stays on origin
    closed = worktree(clone, "closed")
    squashed = worktree(clone, "squashed")
    git(clone.parent / "origin.git", "branch", "-D", "squashed")  # its PR squash-merged and GitHub deleted it
    prs(clone, merged="MERGED", closed="CLOSED", squashed="MERGED")

    out = clean(clone)

    for path in (merged, closed, squashed):
        assert not path.exists()
        assert str(path) in out


def test_a_worktree_never_pushed_with_changes_unpushed_commits_or_a_live_branch_is_kept(clone):
    dirty = worktree(clone, "dirty")
    (dirty / "notes.txt").write_text("not committed")
    unpushed = worktree(clone, "unpushed", push=False)  # gone from origin, but never there
    ahead = worktree(clone, "ahead")
    git(ahead, "commit", "-q", "--allow-empty", "-m", "since the push")
    git(clone.parent / "origin.git", "branch", "-D", "dirty", "ahead")
    live = worktree(clone, "live")  # an open PR's branch
    fresh = worktree(clone, "fresh", commit=False, push=False)  # a session just started it, nothing on it yet
    prs(clone, live="OPEN")

    out = clean(clone)

    for path in (dirty, unpushed, ahead, live, fresh):
        assert path.exists()
        assert str(path) not in out


def test_a_pushed_branch_at_mains_tip_is_kept_with_its_pr_open_or_with_none_yet(clone):
    opened = worktree(clone, "opened", commit=False)  # pushed before its first commit: an ancestor of main
    started = worktree(clone, "started", commit=False)
    prs(clone, opened="OPEN")

    out = clean(clone)

    for path in (opened, started):
        assert path.exists()
        assert str(path) not in out
