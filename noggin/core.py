"""The Cores as the Mac knows them, read from their sources, never listed again (docs/adr/0011): each Core's servo ports
(model/geometry.py CHANNELS), the eye program's modules (what eyes/boot.py imports from eyes/, and what those import)
and the gestures it plays (eyes/eyes.py); read with ast, since they import machine. Standard library and geometry.py
only: `python -m noggin.core` (`make mpy-list`) prints the program's files for make and the release workflow without
the venv."""

import ast
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


GESTURES = _gestures()
MODULES = _modules()  # each flashed as eyes/build/<module>.mpy (make mpy)

if __name__ == "__main__":
    print(*(f"eyes/{m}.py" for m in MODULES))
