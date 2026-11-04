"""claude-review.yml's gate on claude[bot]'s last verdict on the commit its run reviewed (REVIEWED_SHA, #950; the PR's
head when unset). Claude can give its verdict without its review landing (#247, #389), so:
- `Check the verdict` (no flag): `Review` passes only when that last verdict is an approval;
- Claude's PreToolUse hook on StructuredOutput (--hook, the hook's JSON on stdin): the verdict is refused (exit 2, the
  reason fed back to Claude) until the last review on the head matches it, so the review lands while the session lives.
No run is cancelled early (#944), so an older push's run can end after a newer push: its review names the commit it
read (commit_id), and `Check the verdict` fails once the PR's head moved past it (the newer push's run decides).
On an approval, `Check the verdict` also resolves claude[bot]'s open threads that later pushes outdated (#441), so they
don't hold the PR (required_review_thread_resolution).
Usage: GITHUB_REPOSITORY=o/r [REVIEWED_SHA=<sha>] python3 scripts/claude_approved.py <PR number> [--hook]"""

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
    return STATES[verdict] if verdict else "APPROVED"  # `Check the verdict` (no verdict given) wants an approval


def refusal(verdict: str | None, got: str | None, pr: int, head: str, repo: str) -> str | None:
    """What the hook tells Claude when its verdict doesn't match its last review on the reviewed commit yet."""
    if not verdict or got == wanted(verdict):
        return None
    return (
        f"Your verdict needs your review on {head} first: claude[bot]'s last review on it is {got}. Submit it now (step"
        f" 4: `gh api repos/{repo}/pulls/{pr}/reviews -f commit_id={head} -f event={verdict.upper()} -F body=@-` with"
        " the review body on stdin), then give the same verdict again."
    )


def stale(reviewed: str, live: str) -> str | None:
    """Why `Check the verdict` fails a review of a commit the PR has since moved past."""
    if reviewed == live:
        return None
    return f"the PR moved from {reviewed} to {live}: the newer push's run reviews its head, not this one"


THREADS = """query($owner: String!, $name: String!, $pr: Int!) { repository(owner: $owner, name: $name) {
  pullRequest(number: $pr) { reviewThreads(first: 100) {
    nodes { id isOutdated isResolved comments(first: 1) { nodes { author { login } } } } } } } }"""
RESOLVE = "mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { id } } }"


def outdated_threads(threads: list[dict]) -> list[str]:
    """The ids of claude[bot]'s unresolved threads whose lines a later push changed."""
    return [
        t["id"]
        for t in threads
        if t["isOutdated"]
        and not t["isResolved"]
        and (t["comments"]["nodes"][0]["author"] or {}).get("login") == "claude"  # GraphQL drops the [bot]
    ]


def gh(path: str, *flags: str):  # a failure exits 1: non-blocking for the hook, so `Check the verdict` decides
    return json.loads(subprocess.run(["gh", "api", *flags, path], capture_output=True, text=True, check=True).stdout)


if __name__ == "__main__":
    verdict = json.load(sys.stdin)["tool_input"]["verdict"] if "--hook" in sys.argv else None
    pr = int(sys.argv[1])
    pr_path = f"repos/{os.environ['GITHUB_REPOSITORY']}/pulls/{pr}"
    live = gh(pr_path)["head"]["sha"]
    head = os.environ.get("REVIEWED_SHA") or live
    reviews = sum(gh(f"{pr_path}/reviews", "--paginate", "--slurp"), [])  # --slurp: one array per page
    got = last_verdict(reviews, head)
    if message := refusal(verdict, got, pr, head, os.environ["GITHUB_REPOSITORY"]):
        print(message, file=sys.stderr)
        sys.exit(2)
    print(f"{pr_path} at {head}: {got or 'no claude[bot] verdict'}")
    if not verdict and (moved := stale(head, live)):  # the hook lets the session end; the gate fails
        print(f"::error::{moved}")
        sys.exit(1)
    if got == "APPROVED" and not verdict:
        owner, name = os.environ["GITHUB_REPOSITORY"].split("/")
        try:  # best effort: a thread left open is the PR author's to resolve, never a failed review
            # shortcut: the first 100 threads only, paginate if a PR ever has more
            data = gh(
                "graphql", "-f", f"query={THREADS}", "-f", f"owner={owner}", "-f", f"name={name}", "-F", f"pr={pr}"
            )
            for tid in outdated_threads(data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]):
                gh("graphql", "-f", f"query={RESOLVE}", "-f", f"id={tid}")
                print(f"resolved claude[bot]'s outdated thread {tid}")
        except subprocess.CalledProcessError as e:
            print(f"::warning::couldn't resolve claude[bot]'s outdated threads: {e.stderr.strip()}")
    sys.exit(0 if got == wanted(verdict) else 1)
