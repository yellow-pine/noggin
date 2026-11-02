"""Should the release PR auto-merge? On when release-please's changelog in its body has a Features or a BREAKING
CHANGES section, or when Release Now labelled it `release now`; off otherwise, so fixes wait for the next feature
(docs/adr/0010, #407). The sections are release-please's own sorting of the commits, not a list of types (ADR 0011).
Usage: gh pr view N --json body,labels | python3 scripts/release_gate.py   (prints on or off)"""

import json
import re
import sys

SECTION = re.compile(r"^### (Features|⚠ BREAKING CHANGES)$", re.MULTILINE)

if __name__ == "__main__":
    pr = json.load(sys.stdin)
    now = any(label["name"] == "release now" for label in pr["labels"])
    print("on" if now or SECTION.search(pr["body"]) else "off")
