import re
import subprocess
import sys
from pathlib import Path

import eyes  # the Core program (the root conftest stubs machine)
from model.geometry import SERVO_LABEL
from noggin import core
from noggin.service import FLASH_FILES

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


def test_the_stamp_is_the_repos_version_and_commit_without_the_venv():
    """make mpy and the release workflow write eyes/build/stamp.py from `python -m noggin.core stamp`."""
    out = subprocess.run([sys.executable, "-S", "-m", "noggin.core", "stamp"], cwd=ROOT, capture_output=True, text=True)
    stamp = {}
    exec(out.stdout, stamp)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout
    assert re.fullmatch(r"\d+\.\d+\.\d+", stamp["VERSION"]), out
    assert f'version = "{stamp["VERSION"]}"' in (ROOT / "pyproject.toml").read_text()  # the one source (ADR 0010)
    assert re.fullmatch(r"[0-9a-f]{7,40}(-dirty)?", stamp["COMMIT"]) and head.startswith(stamp["COMMIT"][:7]), out


def test_both_flashes_send_the_stamp_with_the_program():
    make = subprocess.run(["make", "-n", "mpy", "flash-usb"], cwd=ROOT, capture_output=True, text=True).stdout
    assert "-m noggin.core stamp > eyes/build/stamp.py" in make, make
    for f in FLASH_FILES:  # what the Wi-Fi flash sends (noggin/service.py)
        assert f"-o eyes/build/{f}" in make and f"cp eyes/build/{f} :{f}" in make, (f, make)
