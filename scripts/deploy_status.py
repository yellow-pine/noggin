"""pages.yml's last job on main: the `deploy` commit status on the commit Site Deploy ran for (#292), from its jobs'
results. Main builds only after a green check run (#295), so a red one is "not deployed: checks failed", linking it. A
cancelled run means a newer commit superseded it (CONTRIBUTING.md); that is `error`, not `failure`: nothing about this
commit failed, it just never deployed. Both make the commit's combined status red.
Usage: SHA=... CHECK=... CHECK_URL=... RENDER=... VIEWER=... SITE=... DEPLOY=... PAGE_URL=... RUN_URL=... \
GITHUB_REPOSITORY=o/r python3 scripts/deploy_status.py"""

import os
import subprocess


def status(check: str, render: str, viewer: str, site: str, deploy: str) -> tuple[str, str, str]:
    """`deploy`'s state, description and link (the site, the check run or this run) from Code Checks' conclusion and
    the render, viewer, site and deploy jobs' results"""
    superseded = "error", "superseded by a newer commit: nothing deployed", "run"
    if check == "cancelled":
        return superseded
    if check != "success":
        return "failure", "not deployed: checks failed", "check"
    for job, result in (("render", render), ("viewer", viewer), ("site", site), ("deploy", deploy)):
        if result == "failure":
            return "failure", f"{job} failed: nothing deployed", "run"
        if result != "success":  # cancelled, or skipped after the jobs before it succeeded: only a cancel does that
            return superseded
    return "success", "deployed to the site", "site"


if __name__ == "__main__":
    e = os.environ
    state, description, link = status(e["CHECK"], e["RENDER"], e["VIEWER"], e["SITE"], e["DEPLOY"])
    url = {"site": e["PAGE_URL"], "check": e["CHECK_URL"], "run": e["RUN_URL"]}[link]
    print(f"deploy: {state}, {description} ({url})")
    fields = {"state": state, "context": "deploy", "description": description, "target_url": url}
    path = f"repos/{e['GITHUB_REPOSITORY']}/statuses/{e['SHA']}"
    flags = [f for k, v in fields.items() for f in ("-f", f"{k}={v}")]
    subprocess.run(["gh", "api", path, *flags], check=True, stdout=subprocess.DEVNULL)
