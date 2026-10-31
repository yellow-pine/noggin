import json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def run(settings, *args):
    subprocess.run([sys.executable, str(HERE / "install_hooks.py"), "--settings", str(settings), *args], check=True, capture_output=True)
    return json.loads(settings.read_text()).get("hooks", {})

def commands(hooks):
    return [h["command"] for groups in hooks.values() for g in groups for h in g["hooks"]]

def test_installed_commands_exist_and_reinstall_is_idempotent(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "/somewhere/else.sh"}]}]}}))
    hooks = run(settings)
    cmds = commands(hooks)
    ours = [c for c in cmds if c.startswith(str(HERE.parent))]
    assert len(ours) == 6 and all(os.access(c, os.X_OK) for c in ours)       # six events, every script runnable
    assert "/somewhere/else.sh" in cmds                                       # other people's hooks untouched
    assert run(settings) == hooks                                             # idempotent

def test_stale_paths_from_a_rename_are_pruned(tmp_path):
    settings = tmp_path / "settings.json"
    stale = str(HERE.parent / "old-folder" / "old-hook.sh")   # a path from before a rename
    settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": stale}]}]}}))
    cmds = commands(run(settings))
    assert stale not in cmds and all(os.path.exists(c) for c in cmds)

def test_remove_leaves_only_foreign_hooks(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "/somewhere/else.sh"}]}]}}))
    run(settings)
    hooks = run(settings, "--remove")
    assert hooks == {"Stop": [{"hooks": [{"type": "command", "command": "/somewhere/else.sh"}]}]}
