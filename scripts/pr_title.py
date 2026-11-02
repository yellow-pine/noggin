"""The PR check's title part the action can't do (docs/adr/0010, .github/workflows/pr-checks.yml, run as on main).
No argument: prints the scopes a title may name, one per line, derived from the repo (docs/adr/0011): each tracked
top-level folder (no dot-folders), each tracked folder in docs/, and Dependabot's deps and deps-dev.
--subject-pattern: prints SUBJECT, which the action takes as its subjectPattern, so the two can't disagree (#548).
TITLE argument: exits 1 with an Actions error for a list of scopes, a header over 100 characters or a subject SUBJECT
fails. A breaking change is the title's `!` alone: the squash commit is the title, so a body footer never reaches main
(CONTRIBUTING.md).
Usage: python3 scripts/pr_title.py (in the repo) | python3 scripts/pr_title.py --subject-pattern | ... TITLE"""

import re
import subprocess
import sys

BOT_SCOPES = {"deps", "deps-dev"}
# config-conventional's subject-full-stop, and its subject-case (never sentence-, start-, pascal- or upper-case), which
# fails exactly a subject whose first letter is a capital, a leading acronym or file name too (#509): sentence-case is
# upperFirst(s) === s (commitlint v21.2.4's @commitlint/ensure/src/to-case.ts; a subject not starting with a letter,
# `PR` in backticks say, is skipped by @commitlint/rules/src/subject-case.ts). Python's re and the action's JS RegExp
# read it alike. shortcut: ASCII capitals only, a Unicode class needs the u flag the action doesn't set; upgrade if a
# title ever starts with a non-ASCII letter
SUBJECT = r"^(?![A-Z]).*[^.]$"
# conventional-changelog-conventionalcommits' headerPattern, which the action's parser splits the subject off with
HEADER = r"^(\w*)(?:\((.*)\))?!?: (.*)$"


def problem(title: str):  # the message, or None
    if re.match(r"\w+\([^)]*,", title):  # the action checks each scope of a list: the spec's scope is one noun
        return "Name one scope, not a list."
    if len(title) > 100:  # @commitlint/config-conventional's header-max-length
        return f"Keep the title to 100 characters ({len(title)} now)."
    if (header := re.match(HEADER, title)) and not re.fullmatch(SUBJECT, header[3]):
        return "Start the subject lowercase (a leading acronym or file name in backticks), with no period at the end."
    return None


if __name__ == "__main__":
    if sys.argv[1:] == ["--subject-pattern"]:
        print(SUBJECT)
        sys.exit()
    if len(sys.argv) > 1:
        if error := problem(sys.argv[1]):
            print(f"::error::{error}")
            sys.exit(1)
        sys.exit()
    files = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True).stdout.splitlines()
    folders = [f.split("/")[:-1] for f in files]
    scopes = {p[1] if p[0] == "docs" and len(p) > 1 else p[0] for p in folders if p}
    print("\n".join(sorted({s for s in scopes if not s.startswith(".")} | BOT_SCOPES)))
