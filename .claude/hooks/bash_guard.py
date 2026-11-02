"""The project's PreToolUse hook on Bash (.claude/settings.json, #443): blocks the commands the agents' rules ban
(CONTRIBUTING.md, .claude/agents/implementer.md), each with a one-line reason naming the allowed alternative. Claude
Code's hook JSON on stdin; exit 2 blocks, stderr is the reason it shows the agent. Runs as the Mac's python3 (3.9),
stdlib only."""

import json
import re
import shlex
import sys
from pathlib import Path

PUNCTUATION = "();<>|&`\n"  # ` too: an unquoted `cmd` is a command of its own
KEYWORDS = ("do", "then", "else", "{", "!")  # what may stand before a loop's until/while in a simple command
SHELLS = ("bash", "sh", "zsh", "dash")
TEXT = ("cat", "gh", "git", "tee")  # their heredocs are text (a file, a PR body, a commit message), not commands
UNPARSED = "this command does not parse (an open quote or heredoc); fix it, or write long text to a file first."


class Fed(str):
    """A heredoc's body or a here-string: text a command reads on stdin."""


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


def lex(text):
    lexer = shlex.shlex(text, posix=True, punctuation_chars=PUNCTUATION)
    lexer.whitespace, lexer.whitespace_split = " \t\r", True  # newlines end a command, as ; does
    return list(lexer)


def tokens(command):
    """The command's tokens, each heredoc's delimiter replaced by its body (Fed). Raises ValueError when a quote or a
    heredoc stays open."""
    found, pending, heredocs = [], "", []  # heredocs: [index of its delimiter in found, delimiter, body lines]
    for line in command.replace("\\\n", " ").split("\n"):
        if heredocs:
            index, delimiter, body = heredocs[0]
            if line.strip() == delimiter:
                found[index] = Fed("\n".join(body))
                heredocs.pop(0)
            else:
                body.append(line)
            continue
        pending += line + "\n"
        try:
            chunk = lex(pending)
        except ValueError:  # a quote spans lines: read on
            continue
        pending = ""
        heredocs += [
            [len(found) + k + 1, chunk[k + 1].lstrip("-"), []] for k in range(len(chunk) - 1) if chunk[k] == "<<"
        ]
        found += chunk
    if pending.strip() or heredocs:
        raise ValueError(command)
    return found


def commands(command):
    """The simple commands as (words, fed): fed is what its heredocs and here-strings feed it, a redirect's file is
    dropped."""
    found, words, fed, redirect = [], [], [], None
    for token in tokens(command) + [";"]:
        if isinstance(token, Fed) or redirect == "<<<":
            fed.append(token)
            redirect = None
        elif redirect:
            redirect = None
        elif set(token) <= set(PUNCTUATION) and ("<" in token or ">" in token):
            redirect = token
        elif set(token) <= set(PUNCTUATION):
            if words or fed:
                found.append((words, fed))
            words, fed = [], []
        else:
            words.append(token)
    return found


def substitutions(word):
    """The commands inside a word's $(…) and `…`, which shlex leaves in a quoted word."""
    found, start = re.findall(r"`([^`]*)`", word), word.find("$(")
    while start != -1:
        depth, end = 0, len(word)
        for end in range(start + 1, len(word)):
            depth += {"(": 1, ")": -1}.get(word[end], 0)
            if depth == 0:
                break
        found.append(word[start + 2 : end])
        start = word.find("$(", end)
    return found


def after(words, word):
    """The words after the first `word`, or None: a wrapper (nohup, timeout N, VAR=x, uv run) may stand before it."""
    return words[words.index(word) + 1 :] if word in words else None


def reason(command, makefile):
    """Why the command is blocked, or None. Fails closed: a command it cannot read is blocked."""
    try:
        segments = commands(command)
    except ValueError:
        return UNPARSED
    for i, (words, fed) in enumerate(segments):
        first = next((w for w in words if "=" not in w), "")
        inner = [f for f in fed if first not in TEXT] + [c for w in words for c in substitutions(w)]
        if any(w in SHELLS for w in words) and "-c" in words[:-1]:
            inner.append(words[words.index("-c") + 1])
        if "eval" in words:
            inner.append(" ".join(after(words, "eval") or []))
        why = next((r for r in (reason(c, makefile) for c in inner) if r), None)
        if why:
            return why
        loop = next(
            (w for k, w in enumerate(words) if w in ("until", "while") and (k == 0 or words[k - 1] in KEYWORDS)), None
        )
        git, gh, make = after(words, "git"), after(words, "gh"), after(words, "make")
        if git is not None and any(w.startswith(("alias.", "-calias.")) for w in git):
            return "git alias: run the git command itself, so the rules can see it."
        if git is not None and "stash" in git:
            return "git stash: work waits in commits; commit it on your branch (a WIP commit is fine)."
        merge = gh is not None and (
            ("merge" in gh and any(w.startswith("--admin") for w in gh))
            or ("api" in gh and any(re.search(r"pulls/[^/]+/merge\b|mergePullRequest", w) for w in gh))
        )
        if merge:
            return "gh merge: a PR lands through its checks and review; gh pr merge --auto --squash."
        heavy = heavy_targets(makefile) if make is not None else set()
        if make is not None and heavy & set(make):
            light = "make check-light" if "check" in heavy else "make lint"
            return f"make: heavy builds run in CI, not here; run {light} and the tests you touched, then push."
        if loop and any("pgrep" in w for w in words):
            return "pgrep in a loop matches itself; wait with gh pr checks --watch, gh run watch or kill -0 on a PID."
        body = next((segments[i:j] for j in range(i, len(segments)) if segments[j][0][:1] == ["done"]), segments[i:])
        if loop == "until" and not any(Path(w).name == "sleep" for b, _ in body for w in b):
            return "until without sleep spins the CPU; add sleep N to its body, or use gh pr checks --watch."
    return None


def main():
    try:
        event = json.load(sys.stdin)
        # shortcut: the session's Makefile, so make -C elsewhere passes; follow -C if agents start using it
        why = reason(event["tool_input"].get("command", ""), Path(event.get("cwd", ".")) / "Makefile")
    except Exception as error:  # fail closed: a guard that crashes must not wave the command through
        why = f"bash_guard.py failed ({error!r}); fix the hook or tell Cansin."
    if why:
        print(why, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
