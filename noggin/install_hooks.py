"""Merge noggin hooks into Claude Code's user settings (idempotent). `--remove` takes them out.
`--settings PATH` overrides ~/.claude/settings.json (tests)."""
import json, os, sys
args = sys.argv[1:]
path = os.path.expanduser(args[args.index("--settings") + 1] if "--settings" in args else "~/.claude/settings.json")
hook = os.path.abspath(os.path.join(os.path.dirname(__file__), "hook.sh"))
repo = os.path.dirname(os.path.dirname(hook)) + "/"
EVENTS = {"SessionStart": None, "UserPromptSubmit": None, "Stop": None, "StopFailure": None, "SessionEnd": None,
          "Notification": "permission_prompt|idle_prompt"}
cfg = json.load(open(path)) if os.path.exists(path) else {}
hooks = cfg.setdefault("hooks", {})
ours = lambda h: h.get("command", "").startswith(repo)   # current path, or a stale path from before a rename
for event, matcher in EVENTS.items():
    groups = [g for g in hooks.get(event, []) if not any(ours(h) for h in g.get("hooks", []))]
    if "--remove" not in args:
        group = {"hooks": [{"type": "command", "command": hook, "async": True, "timeout": 2}]}
        if matcher: group["matcher"] = matcher
        groups.append(group)
    if groups: hooks[event] = groups
    else: hooks.pop(event, None)
json.dump(cfg, open(path, "w"), indent=2); open(path, "a").write("\n")
print("hooks", "removed from" if "--remove" in args else "installed in", path)
