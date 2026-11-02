"""pr_title.py: the PR Title check's scopes are derived from the repo (its tracked top-level folders, docs/'s tracked
subfolders, Dependabot's and release-please's), and it fails what the action can't see: a list of scopes, a header over
100 characters. A body's BREAKING CHANGE footer is not read: it never reaches main."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("pr_title.py")


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, SCRIPT, *args], cwd=cwd, capture_output=True, text=True)


def test_scopes_are_the_tracked_folders_docs_subfolders_and_the_bots(tmp_path):
    tracked = ("eyes/eyes.py", "docs/adr/0001.md", "docs/index.md", ".github/workflows/x.yml", "README.md")
    for f in (*tracked, "untracked/x", "docs/drafts/x.md"):
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / f).write_text("")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", *tracked], cwd=tmp_path, check=True)
    assert run(cwd=tmp_path).stdout.split() == ["adr", "deps", "deps-dev", "docs", "eyes", "release"]


def test_a_title_with_a_list_of_scopes_fails_and_says_one():
    result = run("feat(eyes,web): blink")
    assert result.returncode == 1
    assert "one scope" in result.stdout


def test_a_header_over_100_characters_fails_and_100_passes():
    head = "feat(eyes): "
    assert run(head + "b" * (100 - len(head))).returncode == 0
    result = run(head + "b" * (101 - len(head)))
    assert result.returncode == 1
    assert "100" in result.stdout
