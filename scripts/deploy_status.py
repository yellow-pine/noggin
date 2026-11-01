"""Site Deploy (pages.yml) on a main commit (#310): whether it deploys, and its `deploy` commit status (#292). Site
Checks set the status pending while they build the site; Site Deploy runs on the completion of each check workflow
for the commit and acts once both are done: it deploys Site Checks' site when both passed, else says why not. A red
one is "not deployed: checks failed", linking it (#295); a cancelled one means a newer commit superseded it
(CONTRIBUTING.md), which is `error`, not `failure`: nothing about this commit failed, it just never deployed. Both make
the commit's combined status red.
Usage: SHA=... RUN_URL=... GITHUB_REPOSITORY=o/r python3 scripts/deploy_status.py checks (site-run to GITHUB_OUTPUT
when it deploys), or with DEPLOY=<the deploy job's result> PAGE_URL=... python3 scripts/deploy_status.py deploy"""

import json
import os
import subprocess
import sys

CHECKS = ("Code Checks", "Site Checks")  # by their names, as Site Deploy's workflow_run names them


def superseded(run_url: str) -> tuple[str, str, str]:
    return "error", "superseded by a newer commit: nothing deployed", run_url


def gate(runs: list[dict], run_url: str) -> int | tuple[str, str, str] | None:
    """From the commit's push runs: None while a check workflow is not done (its completion runs Site Deploy again),
    else the Site Checks run whose site deploys when both passed, or the `deploy` status saying why nothing does"""
    latest = {r["name"]: r for r in sorted(runs, key=lambda r: r["id"]) if r["name"] in CHECKS}
    if len(latest) < len(CHECKS) or any(r["status"] != "completed" for r in latest.values()):
        return None
    failed = [r for r in latest.values() if r["conclusion"] not in ("success", "cancelled")]
    if failed:
        return "failure", "not deployed: checks failed", failed[0]["html_url"]
    if any(r["conclusion"] == "cancelled" for r in latest.values()):
        return superseded(run_url)
    return latest["Site Checks"]["id"]


def status(deploy: str, page_url: str, run_url: str) -> tuple[str, str, str]:
    """The deploy job's result as the status: a cancelled one was superseded by a newer commit's"""
    if deploy == "success":
        return "success", "deployed to the site", page_url
    if deploy == "failure":
        return "failure", "deploy failed: nothing deployed", run_url
    return superseded(run_url)


if __name__ == "__main__":
    e = os.environ
    repo = f"repos/{e['GITHUB_REPOSITORY']}"
    if sys.argv[1] == "checks":
        jq = "[.workflow_runs[] | {id, name, status, conclusion, html_url}]"
        out = subprocess.run(
            ["gh", "api", f"{repo}/actions/runs?head_sha={e['SHA']}&event=push", "--jq", jq],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        result = gate(json.loads(out), e["RUN_URL"])
        if result is None:
            print("deploy: waiting for the other check workflow")
            sys.exit()
        if isinstance(result, int):
            print(f"deploy: both checks passed, deploying Site Checks run {result}")
            with open(e["GITHUB_OUTPUT"], "a") as f:
                f.write(f"site-run={result}\n")
            sys.exit()
    else:
        result = status(e["DEPLOY"], e["PAGE_URL"], e["RUN_URL"])
    state, description, url = result
    print(f"deploy: {state}, {description} ({url})")
    fields = {"state": state, "context": "deploy", "description": description, "target_url": url}
    flags = [f for k, v in fields.items() for f in ("-f", f"{k}={v}")]
    subprocess.run(["gh", "api", f"{repo}/statuses/{e['SHA']}", *flags], check=True, stdout=subprocess.DEVNULL)
