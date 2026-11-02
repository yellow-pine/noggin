"""Should the release PR auto-merge? On when the newest version in release-please's changelog (the body's first
`## [x.y.z]` block) has a Features or a BREAKING CHANGES section, or when the release App itself labelled the PR
`release now` (Release Now) and nobody removed it since; off otherwise, so fixes wait for the next feature
(docs/adr/0010, #407). The sections are release-please's own sorting of the commits, not a list of types (ADR 0011).
Anyone with triage rights can add a label, so only the App's own label event counts.
Usage: {"body": the PR's body, "events": its issue events} | python3 scripts/release_gate.py APP[bot]   (on or off)"""

import json
import re
import sys

NEWEST = re.compile(r"^## \[?\d+\.\d+\.\d+.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
SECTION = re.compile(r"^### (Features|⚠ BREAKING CHANGES)$", re.MULTILINE)


def gate(body: str, events: list[dict], app: str) -> str:
    newest = NEWEST.search(body)
    label = [e for e in events if e["event"] in ("labeled", "unlabeled") and e["label"]["name"] == "release now"]
    asked = bool(label) and label[-1]["event"] == "labeled" and label[-1]["actor"]["login"] == app
    return "on" if asked or (newest and SECTION.search(newest[0])) else "off"


if __name__ == "__main__":
    pr = json.load(sys.stdin)
    print(gate(pr["body"], pr["events"], sys.argv[1]))
