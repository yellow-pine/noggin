"""The project's PreToolUse hook on Bash (.claude/settings.json, #443): blocks the commands the agents' rules ban
(CONTRIBUTING.md, .claude/agents/implementer.md), each with a one-line reason naming the allowed alternative. Claude
Code's hook JSON on stdin; exit 2 blocks, stderr is the reason it shows the agent. Runs as the Mac's python3 (3.9),
stdlib only."""

import json
import re
import shlex
import sys
from pathlib import Path

SEPARATORS = set("();<>|&\n")
KEYWORDS = ("do", "then", "else", "{", "!")  # what may stand before a loop's until/while in a simple command


def heavy_targets(makefile):
    """The targets whose recipe takes the heavy lock ($(HEAVY), scripts/heavy.py), and the full check once
    check-light exists: CI builds those (docs/adr/0011, derived from the Makefile, not listed)."""
    text = makefile.read_text() if makefile.is_file() else ""
    heavy, targets = set(), []
    for line in text.splitlines():
        header = re.match(r"([\w-]+(?: [\w-]+)*):(?!=)", line)
        if header:
            targets = header.group(1).split()
        elif line.startswith("\t") and "$(HEAVY)" in line:
            heavy.update(targets)
    if re.search(r"^check-light:", text, re.M):
        heavy.add("check")
    return heavy


def without_heredocs(command):
    """The command with each heredoc's body cut: it is text (a PR body, a commit message), not commands."""
    lines, delimiter = [], None
    for line in command.split("\n"):
        if delimiter is not None:
            delimiter = None if line.strip() == delimiter else delimiter
            continue
        lines.append(line)
        heredoc = re.search(r"(?<!<)<<-?\s*['\"]?(\w+)", line)
        delimiter = heredoc.group(1) if heredoc else None
    return "\n".join(lines)


def after(words, word):
    """The words after the first `word`, or None: a wrapper (nohup, timeout N, VAR=x, uv run) may stand before it."""
    return words[words.index(word) + 1 :] if word in words else None


def reason(command, makefile):
    try:
        lexer = shlex.shlex(without_heredocs(command).replace("\\\n", " "), posix=True, punctuation_chars="();<>|&\n")
        lexer.whitespace, lexer.whitespace_split = " \t\r", True  # newlines end a command, as ; does
        tokens = list(lexer)
    except ValueError:  # unbalanced quotes: let bash report it
        return None
    segments, words = [], []
    for token in tokens + [";"]:
        if set(token) <= SEPARATORS:  # a simple command ends
            if words:
                segments.append(words)
            words = []
        else:
            words.append(token)
    for i, words in enumerate(segments):
        loop = next(
            (w for k, w in enumerate(words) if w in ("until", "while") and (k == 0 or words[k - 1] in KEYWORDS)), None
        )
        git, gh, make = after(words, "git"), after(words, "gh"), after(words, "make")
        if git is not None and "stash" in git:
            return "git stash: work waits in commits; commit it on your branch (a WIP commit is fine)."
        if gh is not None and "merge" in gh and any(w.startswith("--admin") for w in gh):
            return "gh pr merge --admin: a PR lands through its checks and review; gh pr merge --auto --squash."
        heavy = heavy_targets(makefile) if make is not None else set()
        if make is not None and heavy & set(make):
            light = "make check-light" if "check" in heavy else "make lint"
            return f"make: heavy builds run in CI, not here; run {light} and the tests you touched, then push."
        if loop and any("pgrep" in w for w in words):
            return "pgrep in a loop matches itself; wait with gh pr checks --watch, gh run watch or kill -0 on a PID."
        body = next((segments[i:j] for j in range(i, len(segments)) if segments[j][0] == "done"), segments[i:])
        if loop == "until" and not any(Path(w).name == "sleep" for b in body for w in b):
            return "until without sleep spins the CPU; add sleep N to its body, or use gh pr checks --watch."
    return None


def main():
    event = json.load(sys.stdin)
    # shortcut: the session's Makefile, so make -C elsewhere passes; follow -C if agents start using it
    why = reason(event["tool_input"].get("command", ""), Path(event.get("cwd", ".")) / "Makefile")
    if why:
        print(why, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
