"""The CI budget (#219), the last step of each job in .github/workflows (check, mech, pages): with a warm cache a
run must finish within its event's budget, wall time from the start of the run's first job that ran (its latest
attempt; time spent waiting for a runner is not counted) to this step. Over it, a PR or merge-queue run fails; a run
on main only warns, in the log and the job summary. A cold run (a cache that missed) is only reported. Usage:
python3 scripts/ci_budget.py <warm: true|false>, with GITHUB_EVENT_NAME, GITHUB_REPOSITORY, GITHUB_RUN_ID,
GITHUB_RUN_ATTEMPT and GH_TOKEN (actions: read) set."""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime

BUDGET_S = {"pull_request": 180, "merge_group": 180, "push": 540}  # the queue counts as a PR; push is main only
LEVEL = {"pull_request": "error", "merge_group": "error", "push": "warning"}


def first_start(jobs: list[dict]) -> str:
    """When the first of the run's jobs that ran started: a queued or waiting job has no runner yet, a skipped one
    never ran."""
    ran = [
        j for j in jobs if j["status"] == "in_progress" or (j["status"] == "completed" and j["conclusion"] != "skipped")
    ]
    return min(ran, key=lambda j: datetime.fromisoformat(j["started_at"]))["started_at"]


def over(event: str, started: str, now: str, warm: bool) -> tuple[str, str] | None:
    """("error" or "warning", why) when the run is over budget, or None."""
    took = (datetime.fromisoformat(now) - datetime.fromisoformat(started)).total_seconds()
    budget = BUDGET_S.get(event)
    print(f"{event}: {took:.0f} s since the first job started, budget {budget} s, {'warm' if warm else 'cold'} cache")
    if warm and budget is not None and took > budget:
        return LEVEL[event], f"{event} run took {took:.0f} s > {budget} s with a warm cache"
    return None


if __name__ == "__main__":
    e = os.environ
    jobs = subprocess.run(
        ["gh", "api", "--paginate", "--jq", ".jobs[]",
         f"repos/{e['GITHUB_REPOSITORY']}/actions/runs/{e['GITHUB_RUN_ID']}/attempts/{e['GITHUB_RUN_ATTEMPT']}/jobs"],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    started = first_start([json.loads(line) for line in jobs.splitlines()])
    result = over(e["GITHUB_EVENT_NAME"], started, datetime.now(UTC).isoformat(), sys.argv[1] == "true")
    if result:
        level, why = result
        print(f"::{level}::{why}")
        with open(e["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(f"**Over budget ({level}):** {why}\n")
    sys.exit(1 if result and result[0] == "error" else 0)
