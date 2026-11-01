"""claude_approved.py: review.yml's `review` passes only when claude[bot]'s last verdict on the PR's head is an
approval, and Claude's verdict is refused until that last verdict matches it (#389)."""

from scripts.claude_approved import last_verdict, refusal, wanted

HEAD = "a" * 40


def review(state, sha=HEAD, login="claude[bot]"):
    return {"user": {"login": login}, "state": state, "commit_id": sha}


def test_an_approval_on_the_head_counts():
    assert last_verdict([review("COMMENTED"), review("APPROVED")], HEAD) == "APPROVED"


def test_no_review_is_no_verdict():
    assert last_verdict([], HEAD) is None


def test_an_approval_on_an_older_commit_is_no_verdict():
    assert last_verdict([review("APPROVED", sha="c" * 40)], HEAD) is None


def test_an_approval_by_anyone_else_is_no_verdict():
    assert last_verdict([review("APPROVED", login="claude")], HEAD) is None


def test_a_deleted_reviewer_is_skipped():
    deleted = {"user": None, "state": "APPROVED", "commit_id": HEAD}
    assert last_verdict([deleted, review("APPROVED")], HEAD) == "APPROVED"


def test_the_last_verdict_on_the_head_counts():
    assert last_verdict([review("APPROVED"), review("CHANGES_REQUESTED")], HEAD) == "CHANGES_REQUESTED"
    assert last_verdict([review("CHANGES_REQUESTED"), review("APPROVED"), review("COMMENTED")], HEAD) == "APPROVED"


def test_a_dismissed_approval_is_no_verdict():
    assert last_verdict([review("DISMISSED")], HEAD) is None


def test_the_hook_wants_the_review_claude_is_about_to_report_and_the_gate_an_approval():
    # #378: a re-run's approve met the earlier run's CHANGES_REQUESTED on the same head
    assert wanted("approve") == "APPROVED"
    assert wanted("request_changes") == "CHANGES_REQUESTED"
    assert wanted(None) == "APPROVED"


def test_the_hook_refuses_a_verdict_until_its_review_is_on_the_head():
    assert "gh pr review 378 --approve --body-file -" in (refusal("approve", "CHANGES_REQUESTED", 378, HEAD) or "")
    assert "gh pr review 378 --request-changes --body-file -" in (refusal("request_changes", None, 378, HEAD) or "")
    assert refusal("approve", "APPROVED", 378, HEAD) is None
    assert refusal(None, None, 378, HEAD) is None  # the Verdict step never refuses: it exits 1
