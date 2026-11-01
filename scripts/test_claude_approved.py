"""claude_approved.py: the `claude` check in the merge queue passes only when claude[bot]'s last verdict on the PR's
head is an approval."""

from scripts.claude_approved import approved, pr_number

HEAD = "a" * 40


def review(state, sha=HEAD, login="claude[bot]"):
    return {"user": {"login": login}, "state": state, "commit_id": sha}


def test_the_pr_number_comes_from_the_merge_group_branch():
    assert pr_number(f"refs/heads/gh-readonly-queue/main/pr-192-{'b' * 40}") == 192


def test_an_approval_on_the_head_passes():
    assert approved([review("COMMENTED"), review("APPROVED")], HEAD)


def test_no_review_fails():
    assert not approved([], HEAD)


def test_an_approval_on_an_older_commit_fails():
    assert not approved([review("APPROVED", sha="c" * 40)], HEAD)


def test_an_approval_by_anyone_else_fails():
    assert not approved([review("APPROVED", login="claude")], HEAD)


def test_the_last_verdict_on_the_head_counts():
    assert not approved([review("APPROVED"), review("CHANGES_REQUESTED")], HEAD)
    assert approved([review("CHANGES_REQUESTED"), review("APPROVED"), review("COMMENTED")], HEAD)


def test_a_dismissed_approval_fails():
    assert not approved([review("DISMISSED")], HEAD)
