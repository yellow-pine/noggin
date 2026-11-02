"""pr_title.py: the PR Title check's scopes are derived from the repo (its tracked top-level folders, docs/'s tracked
subfolders, Dependabot's and release-please's), and it fails what the action can't see: a list of scopes, a header over
100 characters. A body's BREAKING CHANGE footer is not read: it never reaches main. The action's subject pattern gives
commitlint's verdicts."""

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).with_name("pr_title.py")
PR_CHECKS = yaml.safe_load((SCRIPT.parents[1] / ".github/workflows/pr-checks.yml").read_text())
TITLE_STEP = next(
    s for job in PR_CHECKS["jobs"].values() for s in job["steps"] if "semantic-pull-request" in s.get("uses", "")
)


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


# what commitlint v21.2.4 (cli, config-conventional) says of `docs(docs): <subject>` (#509): subject-case fails a
# subject whose first letter is a capital, acronym or not; backticked text is stripped before the check
@pytest.mark.parametrize(
    ("subject", "passes"),
    [
        ("OpenSSF Scorecard weekly", False),
        ("SECURITY.md points at x", False),
        ("PR titles take any scope", False),
        ("Add a thing", False),
        ("Add A Thing", False),
        ("ADD A THING", False),
        ("add a thing.", False),
        ("add a thing", True),
        ("`OpenSSF` Scorecard weekly", True),
        ("`SECURITY.md` points at x", True),
        ("`PR` titles take any scope", True),
        ("1 more thing", True),
    ],
)
def test_the_subject_pattern_gives_commitlints_verdict(subject, passes):
    assert bool(re.fullmatch(TITLE_STEP["with"]["subjectPattern"], subject)) is passes


def test_the_subject_error_says_a_leading_acronym_goes_in_backticks():
    assert "backticks" in TITLE_STEP["with"]["subjectPatternError"]
