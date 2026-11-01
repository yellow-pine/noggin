"""setup.sh: a stage name it does not know stops before anything runs (the whole wizard would flash the Core)."""

import subprocess
from pathlib import Path


def test_an_unknown_stage_stops_with_the_usage():
    r = subprocess.run(
        ["bash", str(Path(__file__).with_name("setup.sh")), "nope"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 2
    assert "usage: scripts/setup.sh [wifi]" in r.stderr
