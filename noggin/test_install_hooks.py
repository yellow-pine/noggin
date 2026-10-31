import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(settings, *args):
    subprocess.run(
        [sys.executable, str(HERE / "install_hooks.py"), "--settings", str(settings), *args],
        check=True,
        capture_output=True,
    )
    return json.loads(settings.read_text()).get("hooks", {})


def commands(hooks):
    return [h["command"] for groups in hooks.values() for g in groups for h in g["hooks"]]


def test_installed_commands_exist_and_reinstall_is_idempotent(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "/somewhere/else.sh"}]}]}})
    )
    hooks = run(settings)
    cmds = commands(hooks)
    ours = [c for c in cmds if c.startswith(str(HERE.parent))]
    assert len(ours) == 6 and all(os.access(c, os.X_OK) for c in ours)  # six events, every script runnable
    assert "/somewhere/else.sh" in cmds  # other people's hooks untouched
    assert run(settings) == hooks  # idempotent


def test_stale_paths_from_a_rename_are_pruned(tmp_path):
    settings = tmp_path / "settings.json"
    stale = str(HERE.parent / "old-folder" / "old-hook.sh")  # a path from before a rename
    settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": stale}]}]}}))
    cmds = commands(run(settings))
    assert stale not in cmds and all(os.path.exists(c) for c in cmds)


def test_remove_leaves_only_foreign_hooks(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "/somewhere/else.sh"}]}]}})
    )
    run(settings)
    hooks = run(settings, "--remove")
    assert hooks == {"Stop": [{"hooks": [{"type": "command", "command": "/somewhere/else.sh"}]}]}


CRASH_MID_WRITE = """
import json, os, runpy, sys
def crash(obj, fp, **kw):  # write half the JSON, then die like a killed process
    fp.write(json.dumps(obj, **kw)[:20]); fp.flush(); os._exit(1)
json.dump = crash
script, sys.argv = sys.argv[1], sys.argv[1:]
runpy.run_path(script, run_name="__main__")
"""


def test_a_crash_mid_write_leaves_the_settings_intact(tmp_path):
    settings = tmp_path / "settings.json"
    original = json.dumps({"model": "opus", "hooks": {}}, indent=2)
    settings.write_text(original)
    script = str(HERE / "install_hooks.py")
    done = subprocess.run([sys.executable, "-c", CRASH_MID_WRITE, script, "--settings", str(settings)])
    assert done.returncode == 1 and settings.read_text() == original


def test_merge_keeps_unrelated_keys_and_a_dotfiles_symlink(tmp_path):
    real = tmp_path / "dotfiles" / "settings.json"
    real.parent.mkdir()
    real.write_text(json.dumps({"model": "opus", "permissions": {"allow": ["Bash(ls)"]}}))
    settings = tmp_path / "settings.json"
    settings.symlink_to(real)
    run(settings)
    cfg = json.loads(real.read_text())
    assert settings.is_symlink() and len(cfg["hooks"]) == 6
    assert cfg["model"] == "opus" and cfg["permissions"] == {"allow": ["Bash(ls)"]}
