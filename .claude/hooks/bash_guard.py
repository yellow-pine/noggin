"""The project's PreToolUse hook on Bash (.claude/settings.json, #443): blocks the commands the agents' rules ban
(CONTRIBUTING.md, .claude/agents/implementer.md), each with a one-line reason naming the allowed alternative. Claude
Code's hook JSON on stdin; exit 2 blocks, stderr is the reason it shows the agent. Runs as the Mac's python3 (3.9),
stdlib only."""

import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

PUNCTUATION = "();<>|&`\n"  # ` too: an unquoted `cmd` is a command of its own
KEYWORDS = ("do", "then", "else", "{", "!")  # what may stand before a loop's until/while in a simple command
SHELLS = ("bash", "sh", "zsh", "dash")
INTERPRETERS = (*SHELLS, "python", "python3", "node", "perl", "ruby")  # what a pipe may not feed
TEXT = ("cat", "gh", "git", "tee")  # their heredocs are text (a file, a PR body, a commit message), not commands
UNPARSED = "this command does not parse (an open quote or heredoc); fix it, or write long text to a file first."


class Fed(str):
    """A heredoc's body or a here-string: text a command reads on stdin."""


def heavy_recipes(folder):
    """The recipes in the justfile's heavy group ([group('heavy')]), from just's JSON dump: CI builds those
    (docs/adr/0011, read from the justfile, not listed). None without just or a justfile, where just runs nothing."""
    venv = Path(__file__).resolve().parents[2] / ".venv" / "bin" / "just"  # rust-just, the dev group's
    just = str(venv) if venv.is_file() else shutil.which("just")
    dump = just and subprocess.run([just, "--dump", "--dump-format", "json"], cwd=folder, capture_output=True)
    if not dump or dump.returncode:
        return set()
    return {name for name, r in json.loads(dump.stdout)["recipes"].items() if {"group": "heavy"} in r["attributes"]}


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
    """The simple commands as (words, fed, piped): fed is what its heredocs and here-strings feed it, piped whether a
    pipe feeds it; a redirect's file is dropped."""
    found, words, fed, redirect, piped = [], [], [], None, False
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
                found.append((words, fed, piped))
            words, fed, piped = [], [], token in ("|", "|&")
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


def reason(command, folder):
    """Why the command is blocked, or None. Fails closed: a command it cannot read is blocked."""
    try:
        segments = commands(command)
    except ValueError:
        return UNPARSED
    for i, (words, fed, piped) in enumerate(segments):
        first = next((w for w in words if "=" not in w), "")
        if piped and Path(first).name in INTERPRETERS:
            return "a pipe into a shell or interpreter hides its commands; pipe into jq, or run a script file."
        if any(re.match(r"GIT_CONFIG_(PARAMETERS|COUNT|KEY_)", w) for w in words):
            return "GIT_CONFIG_*: run the git command itself, with no config from the environment."
        inner = [f for f in fed if first not in TEXT] + [c for w in words for c in substitutions(w)]
        shell = next((k for k, w in enumerate(words) if Path(w).name in SHELLS), len(words))
        inner += [words[k + 1] for k in range(shell + 1, len(words) - 1) if re.fullmatch(r"-\w*c\w*", words[k])][:1]
        if "eval" in words:
            inner.append(" ".join(after(words, "eval") or []))
        why = next((r for r in (reason(c, folder) for c in inner) if r), None)
        if why:
            return why
        loop = next(
            (w for k, w in enumerate(words) if w in ("until", "while") and (k == 0 or words[k - 1] in KEYWORDS)), None
        )
        git, gh, just = after(words, "git"), after(words, "gh"), after(words, "just")
        if git is not None and any(w.lower().removeprefix("-c").startswith("alias.") for w in git):
            return "git alias: run the git command itself, so the rules can see it."
        if git is not None and "stash" in git:
            return "git stash: work waits in commits; commit it on your branch (a WIP commit is fine)."
        merge = gh is not None and (
            ("merge" in gh and any(w.startswith("--admin") for w in gh))
            or ("api" in gh and any(re.search(r"pulls/[^/]+/merge\b|mergePullRequest", w) for w in gh))
        )
        if gh is not None and "graphql" in gh and any(w.startswith(("@", "--input")) or "=@" in w for w in gh):
            return "gh api graphql from a file: put the query inline, so the rules can read it."
        if merge:
            return "gh merge: a PR lands through its checks and review; gh pr merge --auto --squash."
        if just is not None and heavy_recipes(folder) & set(just):
            return "just: heavy builds run in CI, not here; run just check-light and the tests you touched, then push."
        if loop and any("pgrep" in w for w in words):
            return "pgrep in a loop matches itself; gh run watch, or kill -0 on a PID (CONTRIBUTING's Waiting on CI)."
        body = next((segments[i:j] for j in range(i, len(segments)) if segments[j][0][:1] == ["done"]), segments[i:])
        if loop == "until" and not any(Path(w).name == "sleep" for b, *_ in body for w in b):
            return "until without sleep spins the CPU; add sleep N to its body (CONTRIBUTING's Waiting on CI)."
    return None


def main():
    try:
        event = json.load(sys.stdin)
        # shortcut: the session's justfile, so just -f elsewhere passes; follow -f if agents start using it
        why = reason(event["tool_input"].get("command", ""), event.get("cwd", "."))
    except Exception as error:  # fail closed: a guard that crashes must not wave the command through
        why = f"bash_guard.py failed ({error!r}); fix the hook or tell Cansin."
    if why:
        print(why, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
