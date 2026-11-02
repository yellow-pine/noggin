"""Renumber a draft ADR whose number main has taken (docs/adr/0015): it moves to the number after the highest on main
and in the working tree, and its old number is rewritten on the lines the branch added since it left main (committed,
uncommitted or untracked), so main's own references to that number stay. Check the result with git diff.
Usage: .venv/bin/python scripts/adr_number.py docs/adr/NNNN-slug.md [base, default origin/main, fetched first]"""

import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def numbers(names: Iterable[str]) -> set[int]:
    return {int(m[1]) for n in names if (m := re.match(r"(\d{4})-", Path(n).name))}


def read(path: str) -> str | None:
    """The file's text, None for a binary one (a picture) or a link to a folder (a worktree's .venv)."""
    try:
        return Path(path).read_text()
    except UnicodeDecodeError, IsADirectoryError:
        return None


def added_lines(fork: str) -> dict[str, set[str]]:
    """{path: the lines the working tree added since fork}, untracked files whole."""
    added: dict[str, set[str]] = {}
    path = None
    for line in git("-c", "core.quotePath=false", "diff", "-U0", "--no-color", "--no-renames", fork).splitlines():
        if line.startswith("+++ "):
            path = line[6:].rstrip("\t") if line.startswith("+++ b/") else None  # a tab ends a path with a space
        elif line.startswith("+") and path:
            added.setdefault(path, set()).add(line[1:])
    for path in git("ls-files", "--others", "--exclude-standard").splitlines():
        if (text := read(path)) is not None:
            added[path] = set(text.splitlines())
    return added


def renumber(draft: Path, base: str) -> Path:
    root = Path(git("rev-parse", "--show-toplevel").strip())
    draft = draft.resolve().relative_to(root)
    os.chdir(root)  # git's paths are the root's
    if base == "origin/main":
        git("fetch", "-q", "origin", "main")
    old = draft.name[:4]
    on_base = git("ls-tree", "--name-only", f"{base}:{draft.parent}").split()
    taken = numbers(n for n in [*on_base, *(p.name for p in draft.parent.glob("*.md"))] if n != draft.name)
    if int(old) not in taken:
        print(f"{draft}: {old} is free, nothing to do")
        return draft
    new = f"{max(taken) + 1:04d}"
    number = re.compile(rf"(?<![\w.]){old}(?!\w)")  # 0015 in "ADR 0015", "docs/adr/0015-slug.md", "0013, 0015"
    # shortcut: a line the branch added citing main's own ADR of that number is rewritten too; read the diff
    for path, lines in added_lines(git("merge-base", base, "HEAD").strip()).items():
        text = read(path)
        if text is None:
            continue
        fixed = "".join(number.sub(new, ln) if ln.rstrip("\n") in lines else ln for ln in text.splitlines(True))
        if fixed != text:
            Path(path).write_text(fixed)
            print(f"{path}: ADR {old} -> {new}")
    moved = draft.with_name(new + draft.name[4:])
    if git("ls-files", str(draft)):
        git("mv", str(draft), str(moved))
    else:
        draft.rename(moved)
    print(f"{draft} -> {moved}")
    return moved


if __name__ == "__main__":
    renumber(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "origin/main")
