"""Remove the worktrees whose branch is merged into origin/main or gone from origin (its PR squash-merged), never one
with uncommitted changes (git worktree remove refuses those), unpushed commits, or the one this runs in; prints each
removed path. Usage: make worktrees-clean"""

import os
import subprocess
from pathlib import Path


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], check=check, capture_output=True, text=True)


if __name__ == "__main__":
    git("fetch", "-q", "origin")  # never --prune: a gone branch's origin/ ref is what shows its commits were pushed
    on_origin = {ref.split("refs/heads/", 1)[1] for ref in git("ls-remote", "--heads", "origin").stdout.splitlines()}
    here = git("rev-parse", "--show-toplevel").stdout.strip()
    for block in git("worktree", "list", "--porcelain").stdout.strip().split("\n\n")[1:]:  # [0] is the main worktree
        fields = {k: v for k, _, v in (line.partition(" ") for line in block.splitlines())}
        path, branch = fields["worktree"], fields.get("branch", "").removeprefix("refs/heads/")
        if not branch or path == here:  # detached, or our own
            continue
        merged = git("merge-base", "--is-ancestor", branch, "origin/main", check=False).returncode == 0
        unpushed = git("rev-list", "-1", branch, "--not", "--remotes").stdout
        if (merged or branch not in on_origin) and not unpushed:
            if git("worktree", "remove", path, check=False).returncode == 0:
                print(path)
                try:
                    os.removedirs(Path(path).parent)  # ../noggin-wt/<session>/ once its last worktree goes
                except OSError:
                    pass
