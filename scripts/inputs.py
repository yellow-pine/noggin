"""The repo files a Python file is made from: it and every module of the repo it imports, followed through their
imports (ast, nothing runs). `python scripts/inputs.py FILE...` prints them, one per line, for make ours's
stamp; test_derived.py holds the workflows' cache keys and paths filters to them (docs/adr/0011, #305).
shortcut: imports only, not the data files a module opens (none today), upgrade when one feeds a cache."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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


def inputs(*files):
    """{repo-relative path} of the files and the repo modules they import, transitively, with their packages'
    __init__.py; an empty file (most __init__.py) is no input."""
    found, todo = set(), [ROOT / f for f in files]
    while todo:
        path = todo.pop()
        if path in found:
            continue
        found.add(path)
        todo += [p for name in _imported(path) for p in [_file(name)] if p]
        todo += [p for p in [path.parent / "__init__.py"] if p.is_file()]
    return {p.relative_to(ROOT).as_posix() for p in found if p.stat().st_size}


if __name__ == "__main__":
    print(*sorted(inputs(*sys.argv[1:])), sep="\n")
