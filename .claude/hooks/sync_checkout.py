"""The project's SessionStart hook and PreToolUse hook on Agent (.claude/settings.json, #577): fast-forwards the
session's checkout, the one holding this script, to origin/main, since subagents load .claude/agents/ from it and Claude
Code reloads that folder within seconds (docs/research/2026-11-02-hooks-agent-dispatch.md). Claude Code's hook JSON on
stdin; exit 2 blocks a dispatch (stderr is the reason the agent sees), exit 1 warns (the user sees stderr's line) and
lets it through. Fails open: a hook that wedged dispatching would cost more than a stale checkout. Runs as the Mac's
python3 (3.9), stdlib only."""

import json
import os
import subprocess
import sys
from pathlib import Path

CHECKOUT = Path(__file__).resolve().parents[2]
ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}  # a fetch that wants credentials fails instead of waiting on a prompt


def git(*args):
    return subprocess.run(["git", "-C", str(CHECKOUT), *args], capture_output=True, text=True, env=ENV, timeout=60)


def first_line(result):
    return (result.stderr.strip().splitlines() or ["no output"])[0]


def sync():
    """(why, block): one line for the agent or the user, or None, and whether to block this dispatch."""
    fetch = git("fetch", "-q", "origin", "main")
    if fetch.returncode:
        return f"sync_checkout: git fetch failed ({first_line(fetch)}); the checkout stays where it is.", False
    dirty = git("status", "--porcelain", "--untracked-files=no").stdout.strip()
    if dirty or not git("symbolic-ref", "-q", "HEAD").returncode:  # symbolic-ref succeeds only on a branch
        differs = git("diff", "--name-only", "origin/main", "--", ".claude", "CLAUDE.md").stdout.split()
        place = "has uncommitted changes" if dirty else "is on a branch"
        why = f"sync_checkout: the checkout {place}, so it stays; differs from main: {', '.join(differs)}"
        return (why if differs else None), False
    head = git("rev-parse", "HEAD").stdout.strip()
    merge = git("merge", "-q", "--ff-only", "origin/main")
    if merge.returncode:
        return f"sync_checkout: no fast-forward to origin/main ({first_line(merge)}); the checkout stays.", False
    agents = git("diff", "--name-only", head, "HEAD", "--", ".claude/agents").stdout.split()
    if agents:
        return f"sync_checkout: main changed {', '.join(agents)}; retry this dispatch to load the new definition.", True
    return None, False


def main():
    try:
        event = json.load(sys.stdin)
        why, block = sync()
    except Exception as error:  # fail open: warn and let the call through
        event, why, block = {}, f"sync_checkout.py failed ({error!r}); fix the hook or tell Cansin.", False
    if why:
        print(why, file=sys.stderr)
    if block:  # exit 2 blocks a PreToolUse; SessionStart can't block, and its moved checkout needs no word
        sys.exit(2 if event.get("hook_event_name") == "PreToolUse" else 0)
    if why:
        sys.exit(1)


if __name__ == "__main__":
    main()
