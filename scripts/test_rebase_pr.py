"""rebase_pr.sh: one session rebases a PR onto origin/main and pushes it, refusing another session's PR (its
`session:<name>` label) unless --take, a rebase in progress and a failing make check-light. Real git: a bare origin, a
clone and worktrees at noggin-wt/<session>/<branch>; GitHub is a fake gh and make check-light a fake make, on PATH."""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("rebase_pr.sh")


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A clone whose origin has PR branch `feat` (one commit, labelled session:s2) behind a newer main."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")  # no user config (hooks, signing) leaks in
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    git(tmp_path, "init", "-q", "--bare", "-b", "main", "origin.git")
    git(tmp_path, "clone", "-q", "origin.git", "noggin")
    clone = tmp_path / "noggin"
    git(clone, "commit", "-q", "--allow-empty", "-m", "first")
    git(clone, "push", "-q", "origin", "HEAD:main")
    git(clone, "switch", "-q", "-c", "feat")
    (clone / "feat.txt").write_text("feat\n")
    git(clone, "add", "feat.txt")
    git(clone, "commit", "-q", "-m", "feat")
    git(clone, "push", "-q", "origin", "feat")
    git(clone, "switch", "-q", "main")
    git(clone, "commit", "-q", "--allow-empty", "-m", "main moved")
    git(clone, "push", "-q", "origin", "main")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    # gh pr view prints view.txt (what the script's --jq asks for); every other gh call is logged
    (bin_ / "gh").write_text(
        f'#!/bin/sh\nif [ "$1 $2" = "pr view" ]; then cat {tmp_path}/view.txt\n'
        f'else echo "$@" >> {tmp_path}/gh.log; fi\n'
    )
    (bin_ / "make").write_text(f'#!/bin/sh\necho "$@" >> {tmp_path}/make.log\n[ ! -e {tmp_path}/red ]\n')
    for f in bin_.iterdir():
        f.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_}{os.pathsep}{os.environ['PATH']}")
    view(tmp_path, "session:s2")
    return clone


def view(tmp_path, *labels):
    """GitHub's PR #7: its head branch and commit, then its session labels."""
    head = git(tmp_path / "origin.git", "rev-parse", "feat")
    (tmp_path / "view.txt").write_text("\n".join(["feat", head, *labels]) + "\n")


def worktree(clone, session, branch):
    path = clone.parent / "noggin-wt" / session / branch
    git(clone, "worktree", "add", "-q", "-f", str(path), branch)
    return path


def rebase(cwd, *args):
    return subprocess.run([SCRIPT, "7", *args], cwd=cwd, capture_output=True, text=True)


def origin_feat(clone):
    return git(clone.parent / "origin.git", "rev-parse", "feat")


def test_another_sessions_pr_is_refused_untouched(repo):
    before = origin_feat(repo)

    run = rebase(worktree(repo, "s1", "feat"))

    assert run.returncode != 0
    assert "session:s2" in run.stderr
    assert origin_feat(repo) == before
    assert not (repo.parent / "gh.log").exists()


def test_take_swaps_the_label_rebases_in_this_sessions_worktree_pushes_and_prints_the_new_head(repo):
    theirs = worktree(repo, "s2", "feat")  # the session it takes the PR from still has the branch checked out
    git(repo, "branch", "other", "main")
    here = worktree(repo, "s1", "other")

    run = rebase(here, "--take")

    assert run.returncode == 0, run.stderr
    assert "pr edit 7 --add-label session:s1 --remove-label session:s2" in (repo.parent / "gh.log").read_text()
    new = origin_feat(repo)
    assert run.stdout.strip() == new
    assert git(repo, "merge-base", "--is-ancestor", "origin/main", new) == ""  # raises unless main is under it
    assert git(repo.parent / "noggin-wt" / "s1" / "feat", "rev-parse", "HEAD") == new
    assert git(theirs, "status", "--porcelain") == ""  # its branch did not move under its files


def test_a_rebase_in_progress_is_refused_before_anything_is_labelled_or_pushed(repo):
    view(repo.parent)  # unlabelled: it would take this session's label
    here = worktree(repo, "s1", "feat")
    subprocess.run(["git", "rebase", "--exec", "false", "origin/main"], cwd=here, capture_output=True)  # stops
    before = origin_feat(repo)

    run = rebase(here)

    assert run.returncode != 0
    assert "rebase" in run.stderr
    assert origin_feat(repo) == before
    assert not (repo.parent / "gh.log").exists()


def test_a_failing_check_light_pushes_nothing(repo):
    view(repo.parent, "session:s1")
    (repo.parent / "red").touch()
    before = origin_feat(repo)

    run = rebase(worktree(repo, "s1", "feat"))

    assert run.returncode != 0
    assert (repo.parent / "make.log").read_text() == "check-light\n"
    assert origin_feat(repo) == before
