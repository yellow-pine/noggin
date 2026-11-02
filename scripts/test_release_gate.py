"""release_gate.py: the release PR auto-merges when the newest version in release-please's changelog has a Features
or a BREAKING CHANGES section, or when the release App labelled it `release now`; a fix-only PR waits. The bodies are
recorded release PRs (#385 features, #395 a break, #374 a first version), trimmed to one entry a section; the
fix-only one is in release-please's same format. The events are GitHub's issue events, as the API returns them."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("release_gate.py")
HEAD = ":robot: I have created a release *beep* *boop*\n---\n\n\n"
FOOT = "\n---\nThe release PR of docs/adr/0010 (spec #303): the version bump and the CHANGELOG.md entry.\n"
FEAT = (  # #385
    HEAD + "## [0.1.1](https://github.com/yellow-pine/noggin/compare/v0.1.0...v0.1.1) (2026-11-01)\n\n\n"
    "### Features\n\n* **site:** footer and /version.json show the version and deployed commit "
    "([#380](https://github.com/yellow-pine/noggin/issues/380)) ([d012071](https://github.com/yellow-pine/noggin/"
    "commit/d012071))\n" + FOOT
)
BREAK = (  # #395: a break with no feature
    HEAD + "## [0.2.0](https://github.com/yellow-pine/noggin/compare/v0.1.1...v0.2.0) (2026-11-02)\n\n\n"
    "### ⚠ BREAKING CHANGES\n\n* **scripts:** ` footer without `!` → exit\n\n"
    "### Continuous Integration\n\n* **scripts:** every PR title names one scope derived from the repo "
    "([#388](https://github.com/yellow-pine/noggin/issues/388)) ([11f149c](https://github.com/yellow-pine/noggin/"
    "commit/11f149c))\n" + FOOT
)
FIRST = (  # #374: no previous tag, so no compare link
    HEAD + "## 0.1.0 (2026-11-01)\n\n\n### ⚠ BREAKING CHANGES\n\n* **noggin:** the Core's beacon reports its program's "
    "version and commit ([#366](https://github.com/yellow-pine/noggin/issues/366))\n" + FOOT
)
FIX = (
    HEAD + "## [0.2.1](https://github.com/yellow-pine/noggin/compare/v0.2.0...v0.2.1) (2026-11-02)\n\n\n"
    "### Bug Fixes\n\n* **noggin:** the beacon names the Core (#401)\n\n"
    "### Performance Improvements\n\n* **site:** the viewer loads the glTF once (#402)\n\n"
    "### Documentation\n\n* the Features section of the README (#403)\n" + FOOT
)


APP = "noggin-release[bot]"


def label(event: str, actor: str) -> dict:
    return {"event": event, "actor": {"login": actor}, "label": {"name": "release now"}}


PENDING = {"event": "labeled", "actor": {"login": APP}, "label": {"name": "autorelease: pending"}}
PUSHED = {"event": "head_ref_force_pushed", "actor": {"login": APP}}  # release-please's update: no label key


def gate(body: str, events: tuple[dict, ...] = (PENDING, PUSHED)) -> str:
    pr = {"body": body, "events": list(events)}
    run = [sys.executable, SCRIPT, APP]
    return subprocess.run(run, input=json.dumps(pr), capture_output=True, text=True, check=True).stdout.strip()


@pytest.mark.parametrize("body", [FEAT, BREAK, FIRST], ids=["feat", "breaking", "first"])
def test_a_feature_or_a_break_turns_auto_merge_on(body):
    assert gate(body) == "on"


def test_fixes_alone_turn_auto_merge_off():
    assert gate(FIX) == "off"


def test_only_the_newest_version_counts():
    """A feature in an older version's block (or anywhere past the newest) is already released."""
    assert gate(FIX.replace(FOOT, "\n" + FEAT.removeprefix(HEAD))) == "off"


def test_release_now_keeps_a_fix_only_release_on():
    assert gate(FIX, (PENDING, label("labeled", APP), PUSHED)) == "on"


@pytest.mark.parametrize(
    "events",
    [
        (PENDING, label("labeled", "someone")),  # anyone with triage rights can label
        (PENDING, label("labeled", APP), label("unlabeled", "cansin")),
        (PENDING, label("labeled", APP), label("unlabeled", "cansin"), label("labeled", "someone")),
    ],
    ids=["by someone else", "removed", "removed and re-added by someone else"],
)
def test_only_the_apps_standing_label_releases_fixes(events):
    assert gate(FIX, events) == "off"
