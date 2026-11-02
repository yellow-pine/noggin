"""Renumber a draft ADR whose number main has taken (docs/adr/0015): it moves to the number after the highest on main
and in the working tree, and its old number is rewritten on the lines the branch added since it left main (committed,
uncommitted or untracked), so main's own references to that number stay. Check the result with git diff.
Usage, from the repo's root: python3 scripts/adr_number.py docs/adr/NNNN-slug.md [base, default origin/main]"""

import re
import subprocess
import sys
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def numbers(names) -> set[int]:
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
    for line in git("diff", "-U0", "--no-color", "--no-renames", fork).splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("+") and path:
            added.setdefault(path, set()).add(line[1:])
    for path in git("ls-files", "--others", "--exclude-standard").splitlines():
        if (text := read(path)) is not None:
            added[path] = set(text.splitlines())
    return added


def renumber(draft: Path, base: str) -> Path:
    old = draft.name[:4]
    taken = numbers(git("ls-tree", "--name-only", f"{base}:{draft.parent}").split())
    taken |= numbers(p.name for p in draft.parent.glob("*.md") if p != draft)
    new = f"{max(taken, default=0) + 1:04d}"
    if int(old) not in taken:
        print(f"{draft}: {old} is free, nothing to do")
        return draft
    number = re.compile(rf"(?<![\w.]){old}(?!\w)")  # 0015 in "ADR 0015", "docs/adr/0015-slug.md", "0013, 0015"
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
