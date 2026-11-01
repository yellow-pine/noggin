"""The CI budget (#219), the last step of each job in .github/workflows/check.yml: with a warm cache a run must finish
within its event's budget, wall time from the run's start (its latest attempt) to this step. A cold run (a cache that
missed) is only reported. Usage: python3 scripts/ci_budget.py <warm: true|false>, with GITHUB_EVENT_NAME,
GITHUB_REPOSITORY, GITHUB_RUN_ID and GH_TOKEN (actions: read) set."""

import os
import subprocess
import sys
from datetime import UTC, datetime

BUDGET_S = {"pull_request": 180, "merge_group": 180, "push": 540}  # the queue counts as a PR; push is main only


def over(event: str, started: str, now: str, warm: bool) -> str | None:
    """Why the run is over budget, or None."""
    took = (datetime.fromisoformat(now) - datetime.fromisoformat(started)).total_seconds()
    budget = BUDGET_S.get(event)
    print(f"{event}: {took:.0f} s since the run started, budget {budget} s, {'warm' if warm else 'cold'} cache")
    if warm and budget is not None and took > budget:
        return f"{event} run took {took:.0f} s > {budget} s with a warm cache"
    return None


if __name__ == "__main__":
    run = f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    started = subprocess.run(
        ["gh", "api", run, "--jq", ".run_started_at"], capture_output=True, text=True, check=True
    ).stdout.strip()
    why = over(os.environ["GITHUB_EVENT_NAME"], started, datetime.now(UTC).isoformat(), sys.argv[1] == "true")
    if why:
        print(f"::error::{why}")
    sys.exit(1 if why else 0)
