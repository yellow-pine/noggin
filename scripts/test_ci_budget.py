"""ci_budget.py: a warm run over its event's budget fails; a cold one is only reported."""

from scripts.ci_budget import over

START = "2026-11-01T12:00:00Z"


def test_a_warm_pr_run_within_three_minutes_passes():
    assert over("pull_request", START, "2026-11-01T12:02:59Z", warm=True) is None


def test_a_warm_pr_run_past_three_minutes_fails():
    assert "181 s > 180 s" in (over("pull_request", START, "2026-11-01T12:03:01Z", warm=True) or "")


def test_the_merge_queue_has_the_pr_budget():
    assert over("merge_group", START, "2026-11-01T12:03:01Z", warm=True)


def test_main_has_nine_minutes():
    assert over("push", START, "2026-11-01T12:08:59Z", warm=True) is None
    assert over("push", START, "2026-11-01T12:09:01Z", warm=True)


def test_a_cold_run_is_never_over():
    assert over("pull_request", START, "2026-11-01T12:30:00Z", warm=False) is None


def test_an_event_without_a_budget_is_never_over():
    assert over("workflow_dispatch", START, "2026-11-01T12:30:00Z", warm=True) is None
