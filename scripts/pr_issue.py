"""Does a PR body link its issue? GitHub's closing keywords (close, fix, resolve and their forms; docs.github.com/en/
issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) or Refs, then #N or
owner/repo#N. Exits 1 with an Actions error otherwise. Required check `PR Issue` (.github/workflows/pr-issue.yml).
Usage: python3 scripts/pr_issue.py < body"""

import re
import sys

LINK = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|refs):?\s+(?:[\w.-]+/[\w.-]+)?#\d+\b", re.IGNORECASE)

if __name__ == "__main__":
    if not LINK.search(sys.stdin.read()):
        print("::error::Link the PR's issue in its body: Closes #N (or Fixes/Resolves #N), or Refs #N.")
        sys.exit(1)
