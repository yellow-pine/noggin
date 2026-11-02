"""Does a PR body link its issue? GitHub's closing keywords (close, fix, resolve and their forms; docs.github.com/en/
issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) or Refs, then #N or
owner/repo#N. Exits 1 with an Actions error otherwise. Required check `PR` (.github/workflows/pr-checks.yml).
With --list, prints each linked issue of this repo ($GITHUB_REPOSITORY) once instead (Issue Labels, issue-labels.yml).
Usage: python3 scripts/pr_issue.py [--list] < body"""

import os
import re
import sys

LINK = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|refs):?\s+([\w.-]+/[\w.-]+)?#(\d+)\b", re.IGNORECASE)

if __name__ == "__main__":
    body = sys.stdin.read()
    if sys.argv[1:] == ["--list"]:
        repo = os.environ["GITHUB_REPOSITORY"].lower()
        links = (n for r, n in LINK.findall(body) if not r or r.lower() == repo)
        print("\n".join(dict.fromkeys(links)))
    elif not LINK.search(body):
        print("::error::Link the PR's issue in its body: Closes #N (or Fixes/Resolves #N), or Refs #N.")
        sys.exit(1)
