"""The repo files a Python file is made from: it, every module of the repo it imports and every repo file it names as
a path (a script Blender runs, a data file it opens), followed through (ast, nothing runs). `python
scripts/inputs.py FILE...` prints them, one per line, for make ours's stamp; `--hash FILE...` prints one sha256 of
them, Checks' key for the pictures and the viewer (#469); test_derived.py holds the workflows' cache keys and
paths filters to them (docs/adr/0011, #305). A FILE that is not Python (a Dockerfile) is an input as it is."""

import ast
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = re.compile(r"[\w.-]+(/[\w.*-]+)*\.\w+")  # a string that is a relative file path or glob: "eyes/calibration.json"


def _file(module):
    path = ROOT / module.replace(".", "/")
    return next((p for p in (path.with_suffix(".py"), path / "__init__.py") if p.is_file()), None)


def _imported(path):
    """The dotted names a file imports, `from x import y` as both x and x.y (y may be a module). The repo imports
    absolutely only."""
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
            yield from (f"{node.module}.{a.name}" for a in node.names)


def _named(path):
    """The repo files a file names in a string that is all path, from the repo root (a glob too, as
    trajectories.SOURCES) or beside it (pictures.SCRIPT); a test file or conftest.py (pytest's, which also stubs
    `machine` for traces.py) is no input, nor a build output."""
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and PATH.fullmatch(node.value):
            for base in (ROOT, path.parent):
                yield from (
                    p
                    for p in base.glob(node.value)
                    if p.is_file()
                    and not p.name.startswith("test_")
                    and p.name != "conftest.py"
                    and "build" not in p.relative_to(ROOT).parts
                )


def inputs(*files):
    """{repo-relative path} of the files and the repo files they import or name, transitively, with their packages'
    __init__.py; an empty file (most __init__.py) is no input."""
    found, todo = set(), [ROOT / f for f in files]
    while todo:
        path = todo.pop()
        if path in found:
            continue
        found.add(path)
        if path.suffix != ".py":
            continue
        todo += [p for name in _imported(path) for p in [_file(name)] if p]
        todo += _named(path)
        todo += [p for p in [path.parent / "__init__.py"] if p.is_file()]
    return {p.relative_to(ROOT).as_posix() for p in found if p.stat().st_size}


def digest(*files):
    """sha256 of the inputs' paths and contents, in path order."""
    h = hashlib.sha256()
    for f in sorted(inputs(*files)):
        h.update(f.encode() + b"\0" + (ROOT / f).read_bytes())
    return h.hexdigest()


if __name__ == "__main__":
    if sys.argv[1:2] == ["--hash"]:
        print(digest(*sys.argv[2:]))
    else:
        print(*sorted(inputs(*sys.argv[1:])), sep="\n")
