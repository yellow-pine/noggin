"""claude_approved.py: claude-review.yml's `Review` passes only when claude[bot]'s last verdict on the PR's head is an
approval, and Claude's verdict is refused until that last verdict matches it (#389)."""

import pytest

from scripts.claude_approved import last_verdict, new_review, outdated_threads, refusal, stale, wanted

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


def test_the_hook_posts_the_verdict_on_the_reviewed_commit_with_an_allowed_event_alone():
    """#950: the hook, not the model, posts the review: on the commit the run read (`gh pr review` would land on the
    head of the moment, a newer push's), its event from the verdict, the model's reasons only as its body."""
    assert new_review("approve", "ok", HEAD) == {"commit_id": HEAD, "event": "APPROVE", "body": "ok"}
    assert new_review("request_changes", "no", HEAD)["event"] == "REQUEST_CHANGES"
    with pytest.raises(KeyError):
        new_review("DISMISS", "x", HEAD)


def test_the_hook_refuses_a_verdict_until_its_review_is_on_the_reviewed_commit():
    assert HEAD in (refusal("approve", "CHANGES_REQUESTED", HEAD) or "")
    assert refusal("request_changes", None, HEAD)
    assert refusal("approve", "APPROVED", HEAD) is None
    assert refusal(None, None, HEAD) is None  # `Check the verdict` never refuses: it exits 1


def test_the_gate_fails_a_review_of_a_commit_the_pr_moved_past():
    """#950: no run is cancelled early (#944), so an older push's review can end after a newer push; its approval is on
    the commit it read, and `Review` fails unless that commit is still the PR's head."""
    assert stale(HEAD, HEAD) is None
    assert "newer push" in (stale(HEAD, "b" * 40) or "")


def thread(tid, outdated=True, resolved=False, login="claude"):  # GraphQL names a bot without its [bot]
    return {
        "id": tid,
        "isOutdated": outdated,
        "isResolved": resolved,
        "comments": {"nodes": [{"author": {"login": login}}]},
    }


def test_an_approval_resolves_only_claudes_open_outdated_threads():
    threads = [
        thread("mine"),
        thread("current", outdated=False),
        thread("done", resolved=True),
        thread("cansin", login="cansin"),
        {"id": "ghost", "isOutdated": True, "isResolved": False, "comments": {"nodes": [{"author": None}]}},
    ]
    assert outdated_threads(threads) == ["mine"]
