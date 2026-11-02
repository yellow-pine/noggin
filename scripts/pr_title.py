"""The PR check's title part the action can't do (docs/adr/0010, .github/workflows/pr-checks.yml, run as on main).
No argument: prints the scopes a title may name, one per line, derived from the repo (docs/adr/0011): each tracked
top-level folder (no dot-folders), each tracked folder in docs/, and the bots' (Dependabot's deps and deps-dev,
release-please's release).
TITLE argument: exits 1 with an Actions error for a list of scopes or a header over 100 characters. A breaking change
is the title's `!` alone: the squash commit is the title, so a body footer never reaches main (CONTRIBUTING.md).
Usage: python3 scripts/pr_title.py (in the repo) | python3 scripts/pr_title.py TITLE"""

import re
import subprocess
import sys

BOT_SCOPES = {"deps", "deps-dev", "release"}


def problem(title: str):  # the message, or None
    if re.match(r"\w+\([^)]*,", title):  # the action checks each scope of a list: the spec's scope is one noun
        return "Name one scope, not a list."
    if len(title) > 100:  # @commitlint/config-conventional's header-max-length
        return f"Keep the title to 100 characters ({len(title)} now)."
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if error := problem(sys.argv[1]):
            print(f"::error::{error}")
            sys.exit(1)
        sys.exit()
    files = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True).stdout.splitlines()
    folders = [f.split("/")[:-1] for f in files]
    scopes = {p[1] if p[0] == "docs" and len(p) > 1 else p[0] for p in folders if p}
    print("\n".join(sorted({s for s in scopes if not s.startswith(".")} | BOT_SCOPES)))
