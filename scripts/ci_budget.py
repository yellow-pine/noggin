"""The CI budget (#219, #327), the last step of each job in .github/workflows (check, site-checks): with a warm
cache a run's critical path must stay within its event's budget. The critical path is the longest chain of jobs along
the workflow's needs, each job counted from when a runner picked it up to when it finished (or to this step, still
running): time spent waiting for a runner, or on a job's needs, is not counted, so a busy queue never fails a run and
a slow job still does. Only this run attempt's jobs count (a "re-run failed jobs" is measured on its own). Over it, a
PR run fails; a run on main only warns, in the log and the job summary. A cold run (a cache that missed) is only
reported. Usage: python3 scripts/ci_budget.py <warm: true|false>, with GITHUB_EVENT_NAME, GITHUB_REPOSITORY,
GITHUB_RUN_ID, GITHUB_RUN_ATTEMPT, GITHUB_WORKFLOW_REF and GH_TOKEN (actions: read) set, and yq on the PATH."""

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from functools import cache

BUDGET_S = {"pull_request": 180, "push": 540}  # push is main only


def critical_path(jobs: list[dict], workflow: dict, attempt_started: str, now: str) -> float:
    """Seconds along the longest chain of the workflow's needs (its jobs mapping, as in the YAML) of the attempt's jobs
    that ran (the API's jobs: a queued or waiting job has no runner yet, a skipped or cancelled one may never have had
    one), a matrix job by its slowest runner. A job "re-run failed jobs" kept from an earlier attempt is listed under
    this attempt with the run it had back then, before this attempt started, so it counts nothing; should the
    attempt's recorded start be later than every job's, every job that ran counts, so the budget still reports."""

    def at(t: str) -> datetime:
        return datetime.fromisoformat(t)

    ran = [
        j
        for j in jobs
        if j["status"] == "in_progress"
        or j["status"] == "completed"
        and j["conclusion"] not in ("skipped", "cancelled")
    ]
    ran = [j for j in ran if at(j["started_at"]) >= at(attempt_started)] or ran

    def job_id(name: str) -> str:
        """The API lists a job by its name with the matrix filled in (every job is named: test_workflows.py)."""
        for id_, spec in workflow.items():
            if re.fullmatch(".*".join(map(re.escape, re.split(r"\$\{\{.*?\}\}", spec.get("name", id_)))), name):
                return id_
        return name  # not in the workflow: a chain of its own

    took: dict[str, float] = {}
    for j in ran:
        id_ = job_id(j["name"])
        took[id_] = max(took.get(id_, 0), (at(j["completed_at"] or now) - at(j["started_at"])).total_seconds())

    @cache
    def chain(id_: str) -> float:
        needs = workflow.get(id_, {}).get("needs", [])
        return took.get(id_, 0) + max((chain(n) for n in ([needs] if isinstance(needs, str) else needs)), default=0)

    return max(map(chain, took), default=0)


def over(event: str, took: float, warm: bool) -> tuple[str, str] | None:
    """("error" or "warning", why) when the run's critical path is over budget, or None."""
    budget = BUDGET_S.get(event)
    print(f"{event}: {took:.0f} s along the critical path, budget {budget} s, {'warm' if warm else 'cold'} cache")
    if warm and budget is not None and took > budget:
        return (
            "warning" if event == "push" else "error",
            f"{event} run took {took:.0f} s > {budget} s along its critical path with a warm cache",
        )
    return None


if __name__ == "__main__":
    env = os.environ
    run = f"repos/{env['GITHUB_REPOSITORY']}/actions/runs/{env['GITHUB_RUN_ID']}"
    attempt = f"{run}/attempts/{env['GITHUB_RUN_ATTEMPT']}"

    def out(*cmd: str) -> str:
        return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout

    jobs = out("gh", "api", "--paginate", "--jq", ".jobs[]", f"{attempt}/jobs").splitlines()
    started = out("gh", "api", "--jq", ".run_started_at", attempt).strip()
    # owner/repo/.github/workflows/<file>@<ref>: the workflow file, checked out at the run's commit
    workflow = json.loads(out("yq", "-o=json", ".jobs", env["GITHUB_WORKFLOW_REF"].split("@")[0].split("/", 2)[2]))
    took = critical_path(list(map(json.loads, jobs)), workflow, started, datetime.now(UTC).isoformat())
    result = over(env["GITHUB_EVENT_NAME"], took, sys.argv[1] == "true")
    if result:
        level, why = result
        print(f"::{level}::{why}")
        with open(env["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(f"**Over budget ({level}):** {why}\n")
    sys.exit(1 if result and result[0] == "error" else 0)
