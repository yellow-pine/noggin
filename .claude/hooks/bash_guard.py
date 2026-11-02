"""The project's PreToolUse hook on Bash (.claude/settings.json, #443): blocks the commands the agents' rules ban
(CONTRIBUTING.md, .claude/agents/implementer.md), each with a one-line reason naming the allowed alternative. Claude
Code's hook JSON on stdin; exit 2 blocks, stderr is the reason it shows the agent. Claude Code runs it as the Mac's
python3 (3.9), and it runs itself again on the checkout's .venv, whose tree-sitter-bash reads bash's grammar (#591)."""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tree_sitter_bash
    from tree_sitter import Language, Parser

    BASH = Parser(Language(tree_sitter_bash.language()))
except ImportError:  # the Mac's python3, or a checkout before uv sync
    BASH = None

VENV = Path(__file__).resolve().parents[2] / ".venv"
PUNCTUATION = "();<>|&`\n"  # ` too: an unquoted `cmd` is a command of its own
KEYWORDS = ("do", "then", "else", "{", "!")  # what may stand before a loop's until/while in a simple command
SHELLS = ("bash", "sh", "zsh", "dash")
INTERPRETERS = (*SHELLS, "python", "python3", "node", "perl", "ruby")  # what a pipe may not feed
TEXT = ("cat", "gh", "git", "tee")  # their heredocs are text (a file, a PR body, a commit message), not commands
UNPARSED = "this command does not parse as bash (an open quote or heredoc, zsh-only syntax); fix it, or write a file."
NOPARSER = "no tree-sitter-bash to read its $(…), `…` or <(…); run uv sync (just venv) in the checkout, then retry."
# zsh, the Bash tool's shell, runs code where bash's grammar sees none: a glob qualifier's (…), whatever stands inside
# it; =(…) opening a word; ${(…)…} flags such as (e); and a <1-5> range glob, whose >(… bash's grammar reads as a
# process substitution. With the grammar, an unquoted ( passes only as the opening of an OPENS node; without it, any
# ( right after a word's character blocks (WORDPAREN). ${=var} stays (UNSPLIT asks for it).
ZSH = r"(?:^|[\s;&|(){}])=\(|<\d*-\d*>"
WORDPAREN = r"[^\s$<>=(|&;{]\("
OPENS = ("process_substitution", "command_substitution", "array", "subshell", "function_definition")
OPENS += ("arithmetic_expansion", "parenthesized_expression", "compound_statement", "c_style_for_statement")  # $(( ((
QUOTED = ("string", "raw_string", "ansi_c_string", "translated_string", "heredoc_body")  # where zsh never globs
ZSHONLY = "zsh runs code at a glob qualifier (…), =(…), <1-5> or ${(…)…}; quote it, or put text holding one in a file."
UNSPLIT = "zsh won't split an unquoted $var in a for list: it runs once. Use ${=var}, an array or a bash script file."


class Fed(str):
    """A heredoc's body or a here-string: text a command reads on stdin."""


def heavy_recipes(folder):
    """The recipes in the justfile's heavy group ([group('heavy')]): CI builds those (docs/adr/0011, read from the
    justfile, not listed). From just's JSON dump, else from the justfile's own lines (no just yet, as uv run just
    installs it); None when neither reads, so the caller fails closed."""
    venv = VENV / "bin" / "just"  # rust-just, the dev group's
    just = str(venv) if venv.is_file() else shutil.which("just")
    dump = just and subprocess.run([just, "--dump", "--dump-format", "json"], cwd=folder, capture_output=True)
    if dump and not dump.returncode:
        return {name for name, r in json.loads(dump.stdout)["recipes"].items() if {"group": "heavy"} in r["attributes"]}
    folder = Path(folder).resolve()
    justfile = next((d / "justfile" for d in (folder, *folder.parents) if (d / "justfile").is_file()), None)
    if not justfile:
        return None
    # an attribute line naming the group, any more attribute or comment lines, then the recipe's name
    heavy = r"""^\[.*\bgroup(?:\(|:)\s*['"]heavy['"].*\n(?:[\[#].*\n)*@?([A-Za-z_][\w-]*)"""
    return set(re.findall(heavy, justfile.read_text(), re.M))


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


SUBS = {}  # placeholder: the body of a $(…), `…`, <(…) or >(…) that split() took out
PLACEHOLDER = r"_noggin_sub_\d+_"


def split(command):
    """The command with each $(…), `…`, <(…) and >(…) that bash would run swapped for a placeholder word, its body
    kept in SUBS: shlex can't tell where one ends ($(…) holding a quote inside "…", #579), bash's grammar can. Raises
    ValueError(ZSHONLY) on zsh's code syntax, ValueError(NOPARSER) for one of those without tree-sitter-bash, and
    ValueError(UNPARSED) where the grammar finds an error."""
    if "${(" in command:
        raise ValueError(ZSHONLY)
    if not BASH:
        if re.search(ZSH, command) or re.search(WORDPAREN, command):
            raise ValueError(ZSHONLY)
        if re.search(r"\$\(|`|[<>]\(", command):
            raise ValueError(NOPARSER)
        return command
    source = command.encode()
    tree = BASH.parse(source)

    def nodes(node):
        yield node
        for child in node.children:
            yield from nodes(child)

    # each quoted span and heredoc body filled with _ (a ( in one is text to zsh); opens: where an OPENS node's own
    # ( $( <( >( $(( (( token puts a (
    unquoted, opens, functions = bytearray(source), set(), set()
    for node in nodes(tree.root_node):
        if node.type in QUOTED:
            unquoted[node.start_byte : node.end_byte] = b"_" * (node.end_byte - node.start_byte)
        if not node.is_named and node.parent.type in OPENS:
            opens |= {node.start_byte + k for k, c in enumerate(node.type) if c == "("}
            functions |= {node.start_byte} if node.parent.type == "function_definition" else set()
    parens = {found.start() for found in re.finditer(rb"\(", unquoted)}
    words = {found.end() - 1 for found in re.finditer(WORDPAREN.encode(), unquoted)}  # f() { is the one word( to pass
    if parens - opens or words - functions or re.search(ZSH.encode(), unquoted):
        raise ValueError(ZSHONLY)
    if tree.root_node.has_error:
        raise ValueError(UNPARSED)

    def outermost(node):
        """Each substitution bash runs as (start, end, body), outermost first."""
        if node.type in ("command_substitution", "process_substitution"):
            return [(node.start_byte, node.end_byte, source[node.children[0].end_byte : node.children[-1].start_byte])]
        found = [span for child in node.children for span in outermost(child)]
        heredoc = node.type == "heredoc_body"
        opener = [c.text for c in node.parent.children if c.type == "heredoc_start"] if heredoc else []
        if not opener or re.search(rb"['\"\\]", opener[0]):  # <<'EOF', <<"EOF", <<\EOF: the body stays text
            return found
        # an unquoted heredoc runs its `…` too, which bash's grammar leaves as text (#608); \` there is a plain `
        masked, ticks = bytearray(source), []  # each $(…) found blanked, so a ` inside one stays its own
        for start, stop, _ in found:
            masked[start:stop] = b"_" * (stop - start)
        for tick in re.compile(rb"\\.|`((?:\\.|[^`\\])*)(`?)", re.S).finditer(masked, node.start_byte, node.end_byte):
            if tick[0][:1] == b"`" and not tick[2]:
                raise ValueError(UNPARSED)  # an open `, which bash fails on
            if tick[0][:1] == b"`":
                body = source[tick.start(1) : tick.end(1)]
                ticks.append((tick.start(), tick.end(), re.sub(rb"\\([$`\\])", rb"\1", body)))
        # a $(…) inside a `…` goes with that `…`'s body
        return sorted(ticks + [s for s in found if not any(t[0] < s[0] < t[1] for t in ticks)])

    text, end = b"", 0
    for start, stop, body in outermost(tree.root_node):
        key = f"_noggin_sub_{len(SUBS)}_"  # PLACEHOLDER
        SUBS[key] = body.decode()
        text, end = text + source[end:start] + key.encode(), stop
    return (text + source[end:]).decode()


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
            words, fed, piped = [], [], bool(re.search(r"(?<!\|)\|&?$", token))  # | or |&, after a ) too
        else:
            words.append(token)
    return found


def after(words, word):
    """The words after the first `word`, or None: a wrapper (nohup, timeout N, VAR=x, uv run) may stand before it."""
    return words[words.index(word) + 1 :] if word in words else None


def reason(command, folder):
    """Why the command is blocked, or None. Fails closed: a command it cannot read is blocked."""
    try:
        command = split(command)
        segments = commands(command)
    except ValueError as error:
        return error.args[0] if error.args[0] in (ZSHONLY, NOPARSER) else UNPARSED
    # every $(…) split() took out, wherever it stood: a redirect's target too, which commands() drops; a heredoc's body
    # is text, its $(…) a command bash runs (unless the heredoc is quoted: split() leaves those)
    bodies = (SUBS[k] for k in re.findall(PLACEHOLDER, command) if k in SUBS)
    why = next((r for r in (reason(b, folder) for b in bodies) if r), None)
    if why:
        return why
    for i, (words, fed, piped) in enumerate(segments):
        first = next((w for w in words if "=" not in w), "")
        if piped and Path(first).name in INTERPRETERS:
            return "a pipe into a shell or interpreter hides its commands; pipe into jq, or run a script file."
        if any(re.match(r"GIT_CONFIG_(PARAMETERS|COUNT|KEY_)", w) for w in words):
            return "GIT_CONFIG_*: run the git command itself, with no config from the environment."
        subs = [SUBS[k] for w in words for k in re.findall(PLACEHOLDER, w) if k in SUBS]  # for the pgrep rule
        inner = [f for f in fed if first not in TEXT]
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
        heavy = heavy_recipes(folder) if just is not None else set()
        if heavy is None:
            return "just: no just or justfile to read the heavy recipes from; uv sync, then run it from the checkout."
        if heavy & set(just or ()):
            return "just: heavy builds run in CI, not here; run just check-light and the tests you touched, then push."
        if loop and any("pgrep" in w for w in words + subs):
            return "pgrep in a loop matches itself; gh run watch, or kill -0 on a PID (CONTRIBUTING's Waiting on CI)."
        body = next((segments[i:j] for j in range(i, len(segments)) if segments[j][0][:1] == ["done"]), segments[i:])
        if loop == "until" and not any(Path(w).name == "sleep" for b, *_ in body for w in b):
            return "until without sleep spins the CPU; add sleep N to its body (CONTRIBUTING's Waiting on CI)."
    return None


def unsplit(command):
    """Why a for loop would run once, or None: zsh, the Bash tool's shell, doesn't split an unquoted $var or ${…}
    (#578). Only the outer command is zsh's; a heredoc or -c fed to bash splits. Each $ gets a \\NUL before it, which
    shlex drops outside quotes and keeps inside them, so the words show which $ stood unquoted."""
    for words, *_ in commands(split(command).replace("$", "\\\0$")):
        for k, word in enumerate(words[:-2]):
            loop = word == "for" and words[k + 2] == "in" and (k == 0 or words[k - 1] in KEYWORDS)
            # ${=var} is zsh's own splitting (reason() blocks ${(f)…} with every flag); $(…) splits in zsh too
            if loop and any(re.search(r"(?<!\\)\0\$(\w|\{(?![=(]))", w) for w in words[k + 3 :]):
                return UNSPLIT
    return None


def main():
    try:
        python = VENV / "bin" / "python"
        if not BASH and python.is_file() and Path(sys.prefix).resolve() != VENV.resolve():
            # the checkout's own python, with stdin still unread; S606: exec is the point, no shell takes part
            os.execv(python, [str(python), __file__])  # noqa: S606
        event = json.load(sys.stdin)
        command = event["tool_input"].get("command", "")
        # shortcut: the session's justfile, so just -f elsewhere passes; follow -f if agents start using it
        why = reason(command, event.get("cwd", ".")) or unsplit(command)
    except Exception as error:  # fail closed: a guard that crashes must not wave the command through
        why = f"bash_guard.py failed ({error!r}); fix the hook or tell Cansin."
    if why:
        print(why, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
