import subprocess
import sys
from pathlib import Path

import eyes  # the Core program (the root conftest stubs machine)
from model.geometry import SERVO_LABEL
from noggin import core

ROOT = Path(__file__).resolve().parent.parent


def test_gestures_are_the_ones_the_core_plays():
    assert core.GESTURES == tuple(eyes.Eyes.GESTURES)


def test_the_eye_program_drives_the_servos_on_the_ports_the_model_wires():
    """eyes/eyes.py keeps its own GPIO -> servo map (the Core runs it alone): it must be CHANNELS' eyes Core."""
    assert {eyes.PORT_GPIO[str(port)]: servo for port, servo in core.CORES["eyes"].items()} == eyes.NAME


def test_the_neck_core_drives_the_rest():
    assert list(core.CORES) == ["eyes", "neck"]  # the names each Core beacons and core.json carries
    assert {*core.CORES["eyes"].values(), *core.CORES["neck"].values()} == set(SERVO_LABEL)


def test_the_program_is_what_boot_imports_from_eyes():
    assert {"eyes", "wifi"} < set(core.MODULES)  # boot.py's own imports
    assert "gaze_trace" in core.MODULES  # through eyes.py's
    assert "replay" not in core.MODULES  # the Mac's copy of the clock, beside them in eyes/


def test_make_lists_the_program_without_the_venv():
    """The release workflow zips `make -s mpy-list PY=python3`: no site-packages (-S)."""
    make = ["make", "-s", "mpy-list", f"PY={sys.executable} -S"]
    out = subprocess.run(make, cwd=ROOT, capture_output=True, text=True)
    assert out.stdout.split() == [f"eyes/{m}.py" for m in core.MODULES], out.stderr
