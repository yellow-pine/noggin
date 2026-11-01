"""ci_budget.py: a warm PR or queue run over its budget fails, a warm main run over its budget warns; a cold one is only
reported. The clock starts when the run attempt's first job did, so time spent waiting for a runner, or an
earlier attempt, is not counted."""

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
    ]
    assert first_start(jobs, attempt_started="2026-11-01T12:00:00Z") == "2026-11-01T12:20:01Z"


def test_re_running_the_failed_jobs_measures_the_new_attempt_on_its_own():
    """Attempt 1 started at 17:36:35 and went red; "re-run failed jobs" lists the jobs it kept under attempt 2 too,
    with attempt 2's run_attempt but the start they had in attempt 1 (as in #265's run 41332342549)."""
    passed = {"status": "completed", "conclusion": "success"}
    attempt_2 = [
        passed | {"started_at": "2026-11-01T17:39:20Z"},  # the job that failed, re-run
        passed | {"started_at": "2026-11-01T17:36:35Z"},  # convex, kept
        passed | {"started_at": "2026-11-01T17:36:44Z"},  # a model shard, kept
    ]
    started = first_start(attempt_2, attempt_started="2026-11-01T17:39:17Z")
    assert started == "2026-11-01T17:39:20Z"
    assert over("pull_request", started, "2026-11-01T17:40:33Z", warm=True) is None  # 73 s
    assert over("pull_request", "2026-11-01T17:36:35Z", "2026-11-01T17:40:33Z", warm=True)  # from attempt 1: 238 s
