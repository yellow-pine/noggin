"""ci_budget.py: a warm PR run over its budget fails, a warm main run over its budget warns; a cold one is only
reported. The budget measures the critical path: the longest chain of jobs along the workflow's needs, each counted
from when a runner picked it up to when it finished, so time spent waiting for a runner, or an earlier attempt, is
not counted."""

from pathlib import Path

import yaml

from scripts.ci_budget import critical_path, over

# check.yml's jobs as yq -o=json reads them (docs/adr/0011): a renamed job breaks these tests, not the budget
CHECK = yaml.safe_load((Path(__file__).resolve().parents[1] / ".github/workflows/check.yml").read_text())["jobs"]


def job(name: str, started: str, completed: str | None, conclusion: str | None = "success") -> dict:
    return {
        "name": name,
        "status": "completed" if completed else "in_progress",
        "conclusion": conclusion,
        "started_at": f"2026-11-01T{started}Z",
        "completed_at": completed and f"2026-11-01T{completed}Z",
    }


# #304's first attempt (run 41349665861, its jobs by today's names): a busy queue held the model shards up to 2.5 min
# for a runner, so the run ended 285 s after its first job started and the old clock failed it, while no chain of jobs
# ran past 163 s
QUEUED_BUT_FAST = [
    job("Changes", "21:00:34", "21:00:38"),
    job("Convex", "20:59:59", "21:00:03"),
    job("Code", "21:01:14", "21:02:56"),
    job("Model (hero)", "21:01:28", "21:02:36"),
    job("Model (stage3)", "21:01:45", "21:03:44"),
    job("Model (stage2)", "21:02:21", "21:04:12"),
    job("Model (sim)", "21:01:25", "21:03:33"),
    job("Model (mouth pan-tilt)", "21:01:37", "21:02:51"),
    job("Model (mujoco)", "21:01:14", "21:03:49"),  # 155 s, the slowest shard
    job("Convex (${{ matrix.part }})", "21:00:04", "21:00:04", "skipped"),
    job("Mech", "21:02:25", "21:02:59"),
    job("Model", "21:04:40", "21:04:44"),
]
ATTEMPT = "2026-11-01T20:59:50Z"
NOW = "2026-11-01T21:04:44Z"


def test_a_busy_queue_does_not_count_only_the_jobs_own_run_times_along_their_needs():
    took = critical_path(QUEUED_BUT_FAST, CHECK, ATTEMPT, NOW)
    assert took == 4 + 155 + 4  # Convex, Model (mujoco), Model
    assert over("pull_request", took, warm=True) is None


def test_a_genuinely_slow_job_still_fails_the_run():
    slow = [
        j | {"completed_at": "2026-11-01T21:04:34Z"} if j["name"] == "Model (mujoco)" else j for j in QUEUED_BUT_FAST
    ]
    took = critical_path(slow, CHECK, ATTEMPT, NOW)
    assert took == 4 + 200 + 4
    level, why = over("pull_request", took, warm=True) or ("", "")
    assert level == "error" and "208 s > 180 s" in why


def test_a_job_still_running_counts_up_to_now_and_one_without_a_runner_not_at_all():
    jobs = [
        job("Convex", "12:00:00", "12:00:05"),
        job("Model (hero)", "12:00:10", None),  # the job this step runs in
        job("Model (sim)", "12:00:06", None) | {"status": "queued", "started_at": "2026-11-01T12:00:06Z"},
        job("Code", "12:00:00", None) | {"status": "waiting"},
        job("Mech", "12:00:00", "12:00:00", "cancelled"),
    ]
    assert critical_path(jobs, CHECK, "2026-11-01T11:59:58Z", "2026-11-01T12:01:10Z") == 5 + 60


def test_re_running_the_failed_jobs_measures_the_new_attempt_on_its_own():
    """Attempt 1 started at 17:36:35 and went red; "re-run failed jobs" lists the jobs it kept under attempt 2 too,
    with attempt 2's run_attempt but the run times they had in attempt 1 (as in #265's run 41332342549)."""
    attempt_2 = [
        job("Convex", "17:36:35", "17:36:40"),  # kept
        job("Model (hero)", "17:36:44", "17:38:50"),  # kept
        job("Code", "17:39:20", None),  # the job that failed, re-run
    ]
    assert critical_path(attempt_2, CHECK, "2026-11-01T17:39:17Z", "2026-11-01T17:40:33Z") == 73


def test_an_attempt_start_later_than_every_job_falls_back_to_every_job_that_ran():
    """Should the attempt's recorded start come after every job's (clock skew), the budget still reports, not crash."""
    jobs = [job("Convex", "12:00:02", "12:00:05"), job("Model (hero)", "12:00:05", None)]
    assert critical_path(jobs, CHECK, "2026-11-01T12:00:09Z", "2026-11-01T12:01:05Z") == 3 + 60


def test_a_warm_pr_run_within_three_minutes_passes():
    assert over("pull_request", 179, warm=True) is None


def test_a_warm_pr_run_past_three_minutes_fails(capsys):
    level, why = over("pull_request", 181, warm=True) or ("", "")
    assert level == "error" and "181 s > 180 s" in why
    assert "181 s along the critical path" in capsys.readouterr().out


def test_main_past_nine_minutes_warns_and_never_fails():
    assert over("push", 539, warm=True) is None
    assert (over("push", 541, warm=True) or ("",))[0] == "warning"


def test_a_cold_run_is_never_over():
    assert over("pull_request", 1800, warm=False) is None


def test_an_event_without_a_budget_is_never_over():
    assert over("workflow_dispatch", 1800, warm=True) is None
