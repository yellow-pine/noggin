"""review.yml's gate on claude[bot]'s last verdict on the PR's head commit. Claude can give its verdict without its
review landing (#247, #389), so:
- the Verdict step (no flag): `review` passes only when that last verdict is an approval;
- Claude's PreToolUse hook on StructuredOutput (--hook, the hook's JSON on stdin): the verdict is refused (exit 2, the
  reason fed back to Claude) until the last review on the head matches it, so the review lands while the session lives.
Usage: GITHUB_REPOSITORY=o/r python3 scripts/claude_approved.py <PR number> [--hook]"""

import json
import os
import subprocess
import sys

STATES = {"approve": "APPROVED", "request_changes": "CHANGES_REQUESTED"}


def last_verdict(reviews: list[dict], head_sha: str) -> str | None:
    verdicts = [
        r["state"]
        for r in reviews
        if (r["user"] or {}).get("login") == "claude[bot]"  # user is null for a deleted account
        and r["commit_id"] == head_sha
        and r["state"] in STATES.values()
    ]
    return verdicts[-1] if verdicts else None


def wanted(verdict: str | None) -> str:
    return STATES[verdict] if verdict else "APPROVED"  # the Verdict step (no verdict given) wants an approval


def refusal(verdict: str | None, got: str | None, pr: int, head: str) -> str | None:
    """What the hook tells Claude when its verdict doesn't match its last review on the head yet."""
    if not verdict or got == wanted(verdict):
        return None
    return (
        f"Your verdict needs your review on the head first: claude[bot]'s last review on {head} is {got}. Submit it now"
        f" (step 4: `gh pr review {pr} --{verdict.replace('_', '-')} --body-file -` with the review body on stdin),"
        " then give the same verdict again."
    )


def gh(path: str, *flags: str):  # a failure exits 1: non-blocking for the hook, so the Verdict step's backstop decides
    return json.loads(subprocess.run(["gh", "api", *flags, path], capture_output=True, text=True, check=True).stdout)


if __name__ == "__main__":
    verdict = json.load(sys.stdin)["tool_input"]["verdict"] if "--hook" in sys.argv else None
    pr = int(sys.argv[1])
    pr_path = f"repos/{os.environ['GITHUB_REPOSITORY']}/pulls/{pr}"
    head = gh(pr_path)["head"]["sha"]
    reviews = sum(gh(f"{pr_path}/reviews", "--paginate", "--slurp"), [])  # --slurp: one array per page
    got = last_verdict(reviews, head)
    if message := refusal(verdict, got, pr, head):
        print(message, file=sys.stderr)
        sys.exit(2)
    print(f"{pr_path} at {head}: {got or 'no claude[bot] verdict'}")
    sys.exit(0 if got == wanted(verdict) else 1)
