"""sync_checkout.py, the project's SessionStart hook and PreToolUse hook on Agent (#577): it fast-forwards the session's
checkout to origin/main when that checkout is clean and detached, so subagents load current definitions. Real git: a
bare origin and a clone holding a copy of the hook, as the session's checkout holds it."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("sync_checkout.py")


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def checkout(tmp_path, monkeypatch):
    """A detached clone of a bare origin, with this hook at .claude/hooks/ as in the session's checkout."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")  # no user config (fetch.prune, signing) leaks in
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    git(tmp_path, "init", "-q", "--bare", "-b", "main", "origin.git")
    git(tmp_path, "clone", "-q", "origin.git", "upstream")  # where "main" gets its merges
    commit(tmp_path / "upstream", ".claude/agents/implementer.md", "v1")
    git(tmp_path, "clone", "-q", "origin.git", "checkout")
    repo = tmp_path / "checkout"
    git(repo, "checkout", "-q", "--detach")
    (repo / ".claude/hooks").mkdir(parents=True)
    shutil.copy(SCRIPT, repo / ".claude/hooks")
    return repo


def commit(upstream, path, text):
    """A commit on origin's main that writes text to path."""
    (upstream / path).parent.mkdir(parents=True, exist_ok=True)
    (upstream / path).write_text(text)
    git(upstream, "add", path)
    git(upstream, "commit", "-q", "-m", path)
    git(upstream, "push", "-q", "origin", "HEAD:main")
    return git(upstream, "rev-parse", "HEAD")


def hook(repo, event="SessionStart"):
    payload = {"cwd": str(repo), "hook_event_name": event}
    if event == "PreToolUse":
        payload |= {"tool_name": "Agent", "tool_input": {"subagent_type": "implementer"}}
    # python3, as .claude/settings.json runs it (the Mac's is 3.9; ruff's py39 target holds its syntax there)
    script = repo / ".claude/hooks" / SCRIPT.name
    return subprocess.run(["python3", script], input=json.dumps(payload), capture_output=True, text=True)


def test_session_start_moves_a_clean_detached_checkout_to_origin_main(checkout):
    main = commit(checkout.parent / "upstream", "README.md", "news")
    result = hook(checkout)
    assert result.returncode == 0, result.stderr
    assert git(checkout, "rev-parse", "HEAD") == main


def test_a_dispatch_after_a_merge_that_changes_an_agent_is_blocked_once(checkout):
    main = commit(checkout.parent / "upstream", ".claude/agents/implementer.md", "v2")
    blocked = hook(checkout, "PreToolUse")
    assert blocked.returncode == 2
    assert ".claude/agents/implementer.md" in blocked.stderr and "retry" in blocked.stderr
    assert git(checkout, "rev-parse", "HEAD") == main
    assert hook(checkout, "PreToolUse").returncode == 0  # the retry loads the new definition


def test_a_dispatch_after_a_merge_elsewhere_runs(checkout):
    main = commit(checkout.parent / "upstream", "README.md", "news")
    assert hook(checkout, "PreToolUse").returncode == 0
    assert git(checkout, "rev-parse", "HEAD") == main


def test_session_start_never_blocks(checkout):
    commit(checkout.parent / "upstream", ".claude/agents/implementer.md", "v2")
    assert hook(checkout).returncode == 0
    assert (checkout / ".claude/agents/implementer.md").read_text() == "v2"


def test_a_dirty_checkout_stays_and_warns_when_claude_differs(checkout):
    before = git(checkout, "rev-parse", "HEAD")
    commit(checkout.parent / "upstream", ".claude/agents/implementer.md", "v2")
    (checkout / "notes.md").write_text("untracked")  # untracked files aside: this alone would not stop it
    (checkout / ".claude/agents/implementer.md").write_text("mine")
    for event in ("SessionStart", "PreToolUse"):
        result = hook(checkout, event)
        assert result.returncode == 1  # a warning: the user sees its line, the call goes ahead
        assert ".claude/agents/implementer.md" in result.stderr
    assert git(checkout, "rev-parse", "HEAD") == before
    assert (checkout / ".claude/agents/implementer.md").read_text() == "mine"


def test_a_checkout_on_a_branch_is_never_moved(checkout):
    git(checkout, "switch", "-q", "-c", "mine")
    before = git(checkout, "rev-parse", "HEAD")
    commit(checkout.parent / "upstream", "CLAUDE.md", "new directive")
    result = hook(checkout, "PreToolUse")
    assert result.returncode == 1
    assert "CLAUDE.md" in result.stderr
    assert git(checkout, "rev-parse", "HEAD") == before


def test_a_dirty_checkout_that_matches_main_where_it_matters_stays_quiet(checkout):
    before = git(checkout, "rev-parse", "HEAD")
    commit(checkout.parent / "upstream", "README.md", "news")
    (checkout / "x.py").write_text("x")
    git(checkout, "add", "x.py")
    result = hook(checkout, "PreToolUse")
    assert result.returncode == 0, result.stderr
    assert git(checkout, "rev-parse", "HEAD") == before


def test_offline_it_warns_and_lets_the_dispatch_through(checkout):
    before = git(checkout, "rev-parse", "HEAD")
    commit(checkout.parent / "upstream", ".claude/agents/implementer.md", "v2")
    git(checkout, "remote", "set-url", "origin", str(checkout.parent / "gone.git"))
    result = hook(checkout, "PreToolUse")
    assert result.returncode == 1
    assert "fetch" in result.stderr
    assert git(checkout, "rev-parse", "HEAD") == before


def test_a_detached_checkout_with_its_own_commits_stays_and_warns(checkout):
    commit(checkout.parent / "upstream", ".claude/agents/implementer.md", "v2")
    git(checkout, "commit", "-q", "--allow-empty", "-m", "mine")
    before = git(checkout, "rev-parse", "HEAD")
    result = hook(checkout, "PreToolUse")
    assert result.returncode == 1
    assert "fast-forward" in result.stderr
    assert git(checkout, "rev-parse", "HEAD") == before


def test_a_hook_that_cannot_read_its_input_lets_the_call_through():
    result = subprocess.run(["python3", SCRIPT], input="not json", capture_output=True, text=True)
    assert result.returncode == 1
    assert "sync_checkout.py failed" in result.stderr
