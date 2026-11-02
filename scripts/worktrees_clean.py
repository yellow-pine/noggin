"""Remove the worktrees whose branch is gone from origin (its PR squash-merged) or sits where a merged or closed PR
ended, never one on an open PR's branch, never pushed, with uncommitted changes (git worktree remove refuses those)
or unpushed commits, or the one this runs in; prints each removed path. Never by ancestry alone: a branch pushed
before its first commit sits on main. Usage: just worktrees-clean"""

import contextlib
import json
import os
import subprocess
from pathlib import Path


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], check=check, capture_output=True, text=True)


if __name__ == "__main__":
    git("fetch", "-q", "origin")  # never --prune: a gone branch's origin/ ref is what shows its commits were pushed
    on_origin = {ref.split("refs/heads/", 1)[1] for ref in git("ls-remote", "--heads", "origin").stdout.splitlines()}
    # shortcut: the newest 1000 PRs, enough while a worktree's PR is among them; page further if the repo outgrows it
    prs = json.loads(
        subprocess.run(
            ["gh", "pr", "list", "--state", "all", "--limit", "1000", "--json", "headRefName,headRefOid,state"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    open_heads = {pr["headRefName"] for pr in prs if pr["state"] == "OPEN"}
    # by its head commit too: a new branch may reuse an old PR's name
    ended = {(pr["headRefName"], pr["headRefOid"]) for pr in prs if pr["state"] in ("MERGED", "CLOSED")}
    here = git("rev-parse", "--show-toplevel").stdout.strip()
    git("worktree", "prune")  # the entries of worktrees whose folder is already gone
    for block in git("worktree", "list", "--porcelain").stdout.strip().split("\n\n")[1:]:  # [0] is the main worktree
        fields = {k: v for k, _, v in (line.partition(" ") for line in block.splitlines())}
        path, branch = fields["worktree"], fields.get("branch", "").removeprefix("refs/heads/")
        if not branch or path == here:  # detached, or our own
            continue
        if not git("rev-parse", "-q", "--verify", f"refs/remotes/origin/{branch}", check=False).stdout:
            continue  # never pushed: a session may have just started it
        unpushed = git("rev-list", "-1", branch, "--not", "--remotes").stdout
        done = branch not in on_origin or (branch, fields["HEAD"]) in ended
        if branch not in open_heads and done and not unpushed:
            if git("worktree", "remove", path, check=False).returncode == 0:
                print(path)
                with contextlib.suppress(OSError):  # the parents it leaves empty: ../noggin-wt/<session>/, ...
                    os.removedirs(Path(path).parent)
