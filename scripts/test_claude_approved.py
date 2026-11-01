"""claude_approved.py: review.yml's `review` passes only when claude[bot]'s last verdict on the PR's head is an
approval."""

from scripts.claude_approved import approved

HEAD = "a" * 40


def review(state, sha=HEAD, login="claude[bot]"):
    return {"user": {"login": login}, "state": state, "commit_id": sha}


def test_an_approval_on_the_head_passes():
    assert approved([review("COMMENTED"), review("APPROVED")], HEAD)


def test_no_review_fails():
    assert not approved([], HEAD)


def test_an_approval_on_an_older_commit_fails():
    assert not approved([review("APPROVED", sha="c" * 40)], HEAD)


def test_an_approval_by_anyone_else_fails():
    assert not approved([review("APPROVED", login="claude")], HEAD)


def test_a_deleted_reviewer_is_skipped():
    assert approved([{"user": None, "state": "APPROVED", "commit_id": HEAD}, review("APPROVED")], HEAD)


def test_the_last_verdict_on_the_head_counts():
    assert not approved([review("APPROVED"), review("CHANGES_REQUESTED")], HEAD)
    assert approved([review("CHANGES_REQUESTED"), review("APPROVED"), review("COMMENTED")], HEAD)


def test_a_dismissed_approval_fails():
    assert not approved([review("DISMISSED")], HEAD)
