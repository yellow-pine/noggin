"""The CI budget (#219), the last step of each job in .github/workflows (check, mech, pages): with a warm cache a
run must finish within its event's budget, wall time from the start of the first job that ran in this run attempt
(a "re-run failed jobs" is measured on its own; time spent waiting for a runner is not counted) to this step. Over
it, a PR or merge-queue run fails; a run on main only warns, in the log and the job summary. A cold run (a cache that
missed) is only reported. Usage: python3 scripts/ci_budget.py <warm: true|false>, with GITHUB_EVENT_NAME,
GITHUB_REPOSITORY, GITHUB_RUN_ID, GITHUB_RUN_ATTEMPT and GH_TOKEN (actions: read) set."""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime

BUDGET_S = {"pull_request": 180, "merge_group": 180, "push": 540}  # the queue counts as a PR; push is main only


def first_start(jobs: list[dict], attempt_started: str) -> str:
    """When the first of the attempt's jobs that ran started: a queued or waiting job has no runner yet, a skipped or
    cancelled one may never have had one, and a job "re-run failed jobs" kept from an earlier attempt is listed under
    this attempt's run_attempt but with the start it had back then, before this attempt started."""
    ran = [
        j
        for j in jobs
        if datetime.fromisoformat(j["started_at"]) >= datetime.fromisoformat(attempt_started)
        and (
            j["status"] == "in_progress"
            or j["status"] == "completed"
            and j["conclusion"] not in ("skipped", "cancelled")
        )
    ]
    return min(ran, key=lambda j: datetime.fromisoformat(j["started_at"]))["started_at"]


def over(event: str, started: str, now: str, warm: bool) -> tuple[str, str] | None:
    """("error" or "warning", why) when the run is over budget, or None."""
    took = (datetime.fromisoformat(now) - datetime.fromisoformat(started)).total_seconds()
    budget = BUDGET_S.get(event)
    print(f"{event}: {took:.0f} s since the first job started, budget {budget} s, {'warm' if warm else 'cold'} cache")
    if warm and budget is not None and took > budget:
        return (
            "warning" if event == "push" else "error",
            f"{event} run took {took:.0f} s > {budget} s with a warm cache",
        )
    return None


if __name__ == "__main__":
    env = os.environ
    run = f"repos/{env['GITHUB_REPOSITORY']}/actions/runs/{env['GITHUB_RUN_ID']}"
    attempt = f"{run}/attempts/{env['GITHUB_RUN_ATTEMPT']}"

    def gh(path: str, jq: str) -> str:
        return subprocess.run(
            ["gh", "api", "--paginate", "--jq", jq, path], capture_output=True, text=True, check=True
        ).stdout

    jobs = [json.loads(line) for line in gh(f"{attempt}/jobs", ".jobs[]").splitlines()]
    started = first_start(jobs, gh(attempt, ".run_started_at").strip())
    result = over(env["GITHUB_EVENT_NAME"], started, datetime.now(UTC).isoformat(), sys.argv[1] == "true")
    if result:
        level, why = result
        print(f"::{level}::{why}")
        with open(env["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(f"**Over budget ({level}):** {why}\n")
    sys.exit(1 if result and result[0] == "error" else 0)
