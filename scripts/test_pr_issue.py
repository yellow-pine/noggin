"""pr_issue.py: the PR Issue check passes a PR body that links an issue with a closing keyword or Refs, and fails one
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
