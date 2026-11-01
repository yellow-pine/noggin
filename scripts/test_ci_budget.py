"""ci_budget.py: a warm PR or queue run over its budget fails, a warm main run over its budget warns; a cold one is only
reported. The clock starts when the run's first job did, so time spent waiting for a runner is not counted."""

from scripts.ci_budget import first_start, over

START = "2026-11-01T12:00:00Z"


def test_a_warm_pr_run_within_three_minutes_passes():
    assert over("pull_request", START, "2026-11-01T12:02:59Z", warm=True) is None


def test_a_warm_pr_run_past_three_minutes_fails():
    level, why = over("pull_request", START, "2026-11-01T12:03:01Z", warm=True) or ("", "")
    assert level == "error" and "181 s > 180 s" in why


def test_the_merge_queue_has_the_pr_budget():
    assert (over("merge_group", START, "2026-11-01T12:03:01Z", warm=True) or ("",))[0] == "error"


def test_main_past_nine_minutes_warns_and_never_fails():
    assert over("push", START, "2026-11-01T12:08:59Z", warm=True) is None
    assert (over("push", START, "2026-11-01T12:09:01Z", warm=True) or ("",))[0] == "warning"


def test_a_cold_run_is_never_over():
    assert over("pull_request", START, "2026-11-01T12:30:00Z", warm=False) is None


def test_an_event_without_a_budget_is_never_over():
    assert over("workflow_dispatch", START, "2026-11-01T12:30:00Z", warm=True) is None


def test_the_clock_starts_at_the_first_job_that_ran_not_at_the_queued_run():
    jobs = [
        {"run_attempt": 2, "status": "completed", "conclusion": "success", "started_at": "2026-11-01T12:20:05Z"},
        {"run_attempt": 2, "status": "in_progress", "conclusion": None, "started_at": "2026-11-01T12:20:01Z"},
        {
            "run_attempt": 2,
            "status": "queued",
            "conclusion": None,
            "started_at": "2026-11-01T12:00:00Z",
        },  # no runner yet
        {
            "run_attempt": 2,
            "status": "waiting",
            "conclusion": None,
            "started_at": "2026-11-01T12:00:00Z",
        },  # on its needs
        {"run_attempt": 2, "status": "completed", "conclusion": "skipped", "started_at": "2026-11-01T12:00:00Z"},
        {"run_attempt": 2, "status": "completed", "conclusion": "cancelled", "started_at": "2026-11-01T12:00:00Z"},
        {
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "success",
            "started_at": "2026-11-01T11:00:00Z",
        },  # kept
    ]
    assert first_start(jobs, attempt=2) == "2026-11-01T12:20:01Z"
