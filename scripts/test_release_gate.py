"""release_gate.py: the release PR auto-merges when release-please's changelog in its body has a Features or a
BREAKING CHANGES section, or when Release Now labelled it; a fix-only PR waits. The bodies are recorded release PRs
(#385 features, #395 a break), trimmed to one entry a section; the fix-only one is in release-please's same format."""

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
FIX = (
    HEAD + "## [0.2.1](https://github.com/yellow-pine/noggin/compare/v0.2.0...v0.2.1) (2026-11-02)\n\n\n"
    "### Bug Fixes\n\n* **noggin:** the beacon names the Core (#401)\n\n"
    "### Performance Improvements\n\n* **site:** the viewer loads the glTF once (#402)\n\n"
    "### Documentation\n\n* the Features section of the README (#403)\n" + FOOT
)


def gate(body: str, labels: tuple[str, ...] = ()) -> str:
    pr = {"body": body, "labels": [{"name": n} for n in labels]}
    result = subprocess.run([sys.executable, SCRIPT], input=json.dumps(pr), capture_output=True, text=True, check=True)
    return result.stdout.strip()


@pytest.mark.parametrize("body", [FEAT, BREAK], ids=["feat", "breaking"])
def test_a_feature_or_a_break_turns_auto_merge_on(body):
    assert gate(body) == "on"


def test_fixes_alone_turn_auto_merge_off():
    assert gate(FIX) == "off"


def test_release_now_keeps_a_fix_only_release_on():
    assert gate(FIX, ("autorelease: pending", "release now")) == "on"
