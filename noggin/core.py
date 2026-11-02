"""The Cores as the Mac knows them, read from their sources, never listed again (docs/adr/0011): each Core's servo ports
(model/geometry.py CHANNELS), the eye program's modules (what eyes/boot.py imports from eyes/, and what those import)
and the gestures it plays (eyes/eyes.py); read with ast, since they import machine. Also the repo's version (one source,
the git tag: docs/adr/0017) and commit, which the noggin service runs and `just mpy` stamps into the program.
Standard library and geometry.py only: `python -m noggin.core` (`just mpy-list`) prints the program's files for just
and the release workflow without the venv, `python -m noggin.core stamp` the program's stamp.py."""

import ast
import subprocess
import sys
from pathlib import Path

from model.geometry import CHANNELS

EYES = Path(__file__).resolve().parent.parent / "eyes"
CORES = {"eyes": CHANNELS["core1"], "neck": CHANNELS["core2"]}  # name -> {port: servo}, as each Core beacons


def _tree(module):
    return ast.parse((EYES / f"{module}.py").read_text())


def _gestures():
    eyes = next(n for n in _tree("eyes").body if isinstance(n, ast.ClassDef) and n.name == "Eyes")
    assigns = (n for n in eyes.body if isinstance(n, ast.Assign))
    table = next(n.value for n in assigns if getattr(n.targets[0], "id", None) == "GESTURES")
    assert isinstance(table, ast.Dict), "Eyes.GESTURES is a dict literal: name -> method"
    return tuple(ast.literal_eval(k) for k in table.keys if k)


def _modules():
    found, todo = set(), {"boot"}
    while todo:
        tree = _tree(todo.pop())
        names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        names |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        new = {m for m in names if (EYES / f"{m}.py").is_file()} - found
        found |= new
        todo |= new
    return tuple(sorted(found - {"boot"}))  # boot.py only goes over USB, as .py


def _git(*args):
    """git's output in the checkout, empty when git fails or is missing."""
    try:
        return subprocess.run(["git", *args], cwd=EYES.parent, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def version(described):
    """The version `git describe --tags` names: X.Y.Z on a release's tag, X.Y.Z-N-gHASH N commits past it, and
    0.0.0-untagged where no tag is reachable (a shallow checkout) or no git (docs/adr/0017)."""
    return described.removeprefix("v") or "0.0.0-untagged"


GESTURES = _gestures()
MODULES = _modules()  # each flashed as eyes/build/<module>.mpy (just mpy)
VERSION = version(_git("describe", "--tags", "--match", "v[0-9]*"))
COMMIT = _git("describe", "--always", "--dirty", "--exclude=*") or "unknown"  # no tag names: the commit, -dirty edited
# the program's version and commit, eyes/build/stamp.py (just mpy, never in git), which eyes/wifi.py beacons
STAMP = "stamp"


def stamp():
    """stamp.py's source: the version and commit the program is built from."""
    return f'VERSION = "{VERSION}"\nCOMMIT = "{COMMIT}"\n'


if __name__ == "__main__":
    if sys.argv[1:] == ["stamp"]:
        print(stamp(), end="")
    else:
        print(*(f"eyes/{m}.py" for m in MODULES))
