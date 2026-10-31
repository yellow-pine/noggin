"""Merge noggin hooks into Claude Code's user settings (idempotent). `--remove` takes them out.
`--settings PATH` overrides ~/.claude/settings.json (tests)."""

import json
import os
import shutil
import sys

args = sys.argv[1:]
path = os.path.expanduser(args[args.index("--settings") + 1] if "--settings" in args else "~/.claude/settings.json")
path = os.path.realpath(path)  # swap the file a dotfiles symlink points at, not the link
hook = os.path.abspath(os.path.join(os.path.dirname(__file__), "hook.sh"))
repo = os.path.dirname(os.path.dirname(hook)) + "/"
EVENTS = {
    "SessionStart": None,
    "UserPromptSubmit": None,
    "Stop": None,
    "StopFailure": None,
    "SessionEnd": None,
    "Notification": "permission_prompt|idle_prompt",
}
cfg = json.load(open(path)) if os.path.exists(path) else {}
hooks = cfg.setdefault("hooks", {})


def ours(h):  # current path, or a stale path from before a rename
    return h.get("command", "").startswith(repo)


for event, matcher in EVENTS.items():
    groups = [g for g in hooks.get(event, []) if not any(ours(h) for h in g.get("hooks", []))]
    if "--remove" not in args:
        group = {"hooks": [{"type": "command", "command": hook, "async": True, "timeout": 2}]}
        if matcher:
            group["matcher"] = matcher
        groups.append(group)
    if groups:
        hooks[event] = groups
    else:
        hooks.pop(event, None)
tmp = path + ".tmp"  # write beside it, then swap in: a crash mid-write leaves the old settings whole
with open(tmp, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
    f.flush()
    os.fsync(f.fileno())
if os.path.exists(path):
    shutil.copymode(path, tmp)  # keep its permissions
os.replace(tmp, path)
print("hooks", "removed from" if "--remove" in args else "installed in", path)
