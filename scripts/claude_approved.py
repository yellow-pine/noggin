"""The `claude` check in the merge queue (.github/workflows/queue.yml). A merge group has no PR to review: it passes
when claude[bot]'s last verdict on the queued PR's head commit is an approval, the review the PR's own `claude` check
already gated on. Usage: GITHUB_REPOSITORY=o/r python3 scripts/claude_approved.py <merge group head_ref>"""

import json
import os
import subprocess
import sys


def pr_number(head_ref: str) -> int:
    return int(head_ref.rsplit("/pr-", 1)[1].split("-")[0])  # refs/heads/gh-readonly-queue/main/pr-<n>-<sha>


def approved(reviews: list[dict], head_sha: str) -> bool:
    verdicts = [
        r["state"]
        for r in reviews
        if r["user"]["login"] == "claude[bot]"
        and r["commit_id"] == head_sha
        and r["state"] in ("APPROVED", "CHANGES_REQUESTED")
    ]
    return verdicts[-1:] == ["APPROVED"]


def gh(path: str, *flags: str):
    return json.loads(subprocess.run(["gh", "api", *flags, path], capture_output=True, text=True, check=True).stdout)


if __name__ == "__main__":
    pr_path = f"repos/{os.environ['GITHUB_REPOSITORY']}/pulls/{pr_number(sys.argv[1])}"
    head = gh(pr_path)["head"]["sha"]
    reviews = sum(gh(f"{pr_path}/reviews", "--paginate", "--slurp"), [])  # --slurp: one array per page
    ok = approved(reviews, head)
    print(f"{pr_path} at {head}: {'approved' if ok else 'no claude[bot] approval'}")
    sys.exit(0 if ok else 1)
