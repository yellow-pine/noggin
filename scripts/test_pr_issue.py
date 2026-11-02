"""pr_issue.py: the PR check passes a PR body that links an issue with a closing keyword or Refs, and fails one
that doesn't."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("pr_issue.py")


def check(body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, SCRIPT], input=body, capture_output=True, text=True)


@pytest.mark.parametrize(
    "body",
    [
        "## What\n\nCloses #356",
        "fixes #1",
        "Resolved: #12",
        "This closed #7.",
        "Refs #307",
        "refs yellow-pine/noggin#307",
    ],
)
def test_a_body_that_links_its_issue_passes(body):
    assert check(body).returncode == 0


@pytest.mark.parametrize("body", ["", "See #356", "Closes issue 356", "Prefixes #3", "Closes #", "Refs: none"])
def test_a_body_without_a_linked_issue_fails_and_says_how_to_link_one(body):
    result = check(body)
    assert result.returncode == 1
    assert "Closes #N" in result.stdout


def test_list_prints_each_issue_the_body_links_in_this_repo():
    """#446: Issue Labels sets each linked issue in-progress; another repo's issue isn't ours to label."""
    body = "Closes #446\nRefs #438, fixes yellow-pine/noggin#12\nRefs other/repo#9\nSee #5\nfixes #446"
    result = subprocess.run(
        [sys.executable, SCRIPT, "--list"],
        input=body,
        capture_output=True,
        text=True,
        env={"GITHUB_REPOSITORY": "yellow-pine/noggin"},
    )
    assert result.stdout.split() == ["446", "438", "12"]
