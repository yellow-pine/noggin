"""Merge noggin hooks into ~/.claude/settings.json (idempotent). `--remove` takes them out."""
import json, os, sys
path = os.path.expanduser("~/.claude/settings.json")
poke = os.path.abspath(os.path.join(os.path.dirname(__file__), "hook.sh"))
EVENTS = {"SessionStart": None, "UserPromptSubmit": None, "Stop": None, "StopFailure": None, "SessionEnd": None,
          "Notification": "permission_prompt|idle_prompt"}
cfg = json.load(open(path)) if os.path.exists(path) else {}
hooks = cfg.setdefault("hooks", {})
for event, matcher in EVENTS.items():
    groups = [g for g in hooks.get(event, []) if not any(h.get("command") == poke for h in g.get("hooks", []))]
    if "--remove" not in sys.argv:
        group = {"hooks": [{"type": "command", "command": poke, "async": True, "timeout": 2}]}
        if matcher: group["matcher"] = matcher
        groups.append(group)
    if groups: hooks[event] = groups
    else: hooks.pop(event, None)
json.dump(cfg, open(path, "w"), indent=2); open(path, "a").write("\n")
print("hooks", "removed from" if "--remove" in sys.argv else "installed in", path)
