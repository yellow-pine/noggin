"""The Core runs MicroPython 1.23 (pyproject.toml [tool.noggin]): its files type-check against that MicroPython's
stubs and compile with that mpy-cross to .mpy files the Core loads."""

import re
import subprocess
import sys
import sysconfig
import tomllib
from importlib.metadata import version
from pathlib import Path

from noggin.core import MODULES

REPO = Path(__file__).resolve().parent.parent
PIN = tomllib.loads((REPO / "pyproject.toml").read_text())["tool"]["noggin"]["micropython"]
CORE_MPY = 774  # sys.implementation._mpy on the Core: .mpy version 6 (low byte), sub-version 3, no native arch
CORE = [REPO / "eyes" / f"{m}.py" for m in MODULES] + [REPO / "eyes" / "boot.py"]


def pyright(*files):
    """pyright with the stubs' MicroPython as the standard library, the way the Core sees its imports."""
    site = sysconfig.get_path("purelib")  # micropython-stdlib-stubs puts stdlib/ there, the stubs package stubs/
    run = subprocess.run(
        [sys.executable, "-m", "pyright", "--typeshedpath", site, *map(str, files)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    return run.returncode, run.stdout


def test_the_stubs_and_mpy_cross_are_the_cores_micropython():
    for package in ("micropython-esp32-esp32_generic_c3-stubs", "micropython-stdlib-stubs", "mpy-cross"):
        assert version(package).startswith(PIN + "."), package


def test_the_makefile_tag_is_the_cores_micropython():  # the stand-in's unix port and both hmacs (make flash-usb, mech)
    tag = re.search(r"^MICROPYTHON := (\S+)$", (REPO / "Makefile").read_text(), re.M)
    assert tag and tag[1].startswith(f"v{PIN}."), tag


def test_pyright_flags_a_call_the_cores_micropython_lacks(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("import time\n\ntime.monotonic()\n")  # CPython has it, MicroPython's time does not
    code, out = pyright(bad)
    assert code == 1 and '"monotonic" is not a known attribute of module "time"' in out, out


def test_the_core_files_type_check_against_the_cores_micropython():
    code, out = pyright(*CORE)
    assert code == 0, out


def test_every_flashed_file_compiles_to_an_mpy_the_core_loads(tmp_path):
    for src in CORE[:-1]:  # boot.py stays .py
        out = tmp_path / src.with_suffix(".mpy").name
        subprocess.run([Path(sys.executable).parent / "mpy-cross", "-o", out, src], check=True)
        head = out.read_bytes()[:4]
        assert head[:2] == b"M" + bytes([CORE_MPY & 0xFF]), (src.name, head)  # sub-version only binds native code
        assert head[2] >> 2 == CORE_MPY >> 10 == 0 and head[3] <= 31, (src.name, head)  # no native code; 31-bit ints
