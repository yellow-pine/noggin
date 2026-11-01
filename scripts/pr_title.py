"""The PR Title check's part the action can't do (docs/adr/0010, .github/workflows/pr-title.yml, run as on main).
No argument: prints the scopes a title may name, one per line, derived from the repo (docs/adr/0011): each tracked
top-level folder (no dot-folders), each tracked folder in docs/, and the bots' (Dependabot's deps and deps-dev,
release-please's release).
TITLE argument, the PR body on stdin: exits 1 with an Actions error for a list of scopes, a header over 100 characters,
or a BREAKING CHANGE footer the title doesn't mark with `!` (conventionalcommits.org/en/v1.0.0).
Usage: python3 scripts/pr_title.py (in the repo) | python3 scripts/pr_title.py TITLE < body"""

import re
import subprocess
import sys

BOT_SCOPES = {"deps", "deps-dev", "release"}


def problem(title: str, body: str):  # the message, or None
    if re.match(r"\w+\([^)]*,", title):  # the action checks each scope of a list: the spec's scope is one noun
        return "Name one scope, not a list."
    if len(title) > 100:  # @commitlint/config-conventional's header-max-length
        return f"Keep the title to 100 characters ({len(title)} now)."
    if re.search(r"^BREAKING[ -]CHANGE: ", body, re.MULTILINE) and not re.match(r"[^:]*!:", title):
        return "The body has a BREAKING CHANGE footer: mark the title with ! (feat(scope)!: subject)."
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if error := problem(sys.argv[1], sys.stdin.read()):
            print(f"::error::{error}")
            sys.exit(1)
        sys.exit()
    files = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True).stdout.splitlines()
    folders = [f.split("/")[:-1] for f in files]
    scopes = {p[1] if p[0] == "docs" and len(p) > 1 else p[0] for p in folders if p}
    print("\n".join(sorted({s for s in scopes if not s.startswith(".")} | BOT_SCOPES)))
