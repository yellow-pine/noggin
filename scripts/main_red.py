"""Main Red (main-red.yml, #697): a red main opens one 'main red' issue, a green one closes it. PRs run a slim gate, so
main's post-merge Checks catch what they no longer run, and a failure must surface at once. A failed Checks or Site
Deploy run on main opens the issue (labels bug, ready-for-agent) with the commit, the failing jobs and their key log
lines, or comments on the open one while main stays red; Site Deploy deploying a commit (its Checks passed, its site is
up) closes it. CI Images builds on main alone (#729), so its failure files its own 'main red (CI Images)', which its
next successful run closes. A cancelled run was superseded and says nothing.
Usage: WORKFLOW=... CONCLUSION=... RUN_ID=... RUN_URL=... SHA=... GITHUB_REPOSITORY=o/r python3 scripts/main_red.py"""

import json
import os
import re
import subprocess

TITLE = "main red"
WATCHED = ["Checks", "Site Deploy", "CI Images"]  # by their names, as main-red.yml's workflow_run names them
RED = {"failure", "timed_out", "startup_failure"}
KEY = re.compile(r"FAILED|Error")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
LINES, WIDTH = 40, 300  # the issue stays readable; the run has the rest


def title(workflow: str) -> str:
    """CI Images' issue is its own: a deploy says nothing about the images"""
    return f"{TITLE} (CI Images)" if workflow == "CI Images" else TITLE


def verdict(workflow: str, conclusion: str, jobs: list[dict]) -> str | None:
    """red for a failed run; green once Site Deploy's Deploy job put a commit up, or CI Images pushed; else None"""
    if conclusion in RED:
        return "red"
    if workflow == "CI Images":
        return "green" if conclusion == "success" else None
    deployed = any(j["name"] == "Deploy" and j["conclusion"] == "success" for j in jobs)
    return "green" if workflow == "Site Deploy" and deployed else None


def report(workflow: str, sha: str, commit_url: str, run_url: str, jobs: list[dict], log: str) -> str:
    """The issue's body or comment, from the run's jobs and `gh run view --log-failed` (job, step, time and line)"""
    failing = ", ".join(j["name"] for j in jobs if j["conclusion"] in RED) or "none listed"
    key = []
    for row in ANSI.sub("", log).splitlines():
        job, _, rest = row.split("\t", 2) if row.count("\t") >= 2 else ("", "", row)
        line = rest.split(" ", 1)[-1]  # past the timestamp
        if KEY.search(line):
            key.append(f"{job}: {line}"[:WIDTH])
    lines = "\n".join(key[:LINES]) or "(no FAILED or Error line: see the run)"
    return (
        f"Main's {workflow} failed on [{sha[:7]}]({commit_url}): {run_url}\n\n"
        f"Failing jobs: {failing}\n\n```text\n{lines}\n```\n"
    )


if __name__ == "__main__":
    e = os.environ
    repo = ["--repo", e["GITHUB_REPOSITORY"]]

    def gh(*args: str, check: bool = True) -> str:
        return subprocess.run(["gh", *args, *repo], capture_output=True, text=True, check=check).stdout

    jobs = json.loads(gh("run", "view", e["RUN_ID"], "--json", "jobs"))["jobs"]
    state = verdict(e["WORKFLOW"], e["CONCLUSION"], jobs)
    # the issues API, not search, which lags a just-opened issue
    listed = json.loads(gh("issue", "list", "--limit", "500", "--json", "number,title"))  # the open ones
    issue = next((str(i["number"]) for i in listed if i["title"] == title(e["WORKFLOW"])), None)
    commit_url = f"https://github.com/{e['GITHUB_REPOSITORY']}/commit/{e['SHA']}"
    print(f"main red: {e['WORKFLOW']} {e['CONCLUSION']}, {state or 'nothing to do'}, open issue: {issue or 'none'}")
    if state == "red":
        log = gh("run", "view", e["RUN_ID"], "--log-failed", check=False)  # none for a run that never started
        body = report(e["WORKFLOW"], e["SHA"], commit_url, e["RUN_URL"], jobs, log)
        if issue:
            gh("issue", "comment", issue, "--body", body)
        else:
            gh("issue", "create", "--title", title(e["WORKFLOW"]), "--label", "bug,ready-for-agent", "--body", body)
    elif state == "green" and issue:
        gh("issue", "edit", issue, "--remove-label", "ready-for-agent,in-progress,blocked,on-hold")
        done = "deployed it" if e["WORKFLOW"] == "Site Deploy" else "pushed the images"
        gh("issue", "close", issue, "--comment", f"Main is green again: {e['WORKFLOW']} {done} ({e['RUN_URL']}).")
