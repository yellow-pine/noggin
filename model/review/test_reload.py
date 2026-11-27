"""The installed review watcher consumes only a verified publication, including while the viewer is dirty."""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

from model import review, skeleton, stages


def watcher(tmp_path, monkeypatch, name="noggin-stage3.blend", env="NOGGIN_REVIEW"):
    path = tmp_path.resolve() / name
    path.write_bytes(b"previous review")
    callbacks, opened = [], []
    bpy = types.SimpleNamespace(
        data=types.SimpleNamespace(filepath=str(path), is_dirty=True),
        app=types.SimpleNamespace(
            handlers=types.SimpleNamespace(persistent=lambda f: f, load_post=[]),
            timers=types.SimpleNamespace(
                register=lambda f, **_kw: callbacks.append(f),
                unregister=lambda f: callbacks.remove(f),
                is_registered=lambda f: f in callbacks,
            ),
        ),
        ops=types.SimpleNamespace(wm=types.SimpleNamespace(open_mainfile=lambda **kw: opened.append(kw))),
    )
    monkeypatch.setitem(sys.modules, "bpy", bpy)
    monkeypatch.setenv(env, str(path))
    spec = importlib.util.spec_from_file_location("noggin_reload_test", Path(__file__).with_name("reload.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.register()
    for handler in bpy.app.handlers.load_post:  # as Blender opens the file once its scripts are registered
        handler(None)
    return path, callbacks, opened


def publish(path, checksum=None):
    path.write_bytes(b"new verified review")
    path.with_suffix(".blend.ready.json").write_text(
        json.dumps({"sha256": checksum or hashlib.sha256(path.read_bytes()).hexdigest()})
    )


def test_a_verified_review_refreshes_despite_incidental_viewer_edits(tmp_path, monkeypatch):
    path, callbacks, opened = watcher(tmp_path, monkeypatch)
    publish(path)
    assert callbacks[0]() == 2.0
    assert opened == [{"filepath": str(path), "load_ui": False, "use_scripts": False}]


def test_the_latest_file_refreshes_like_the_review(tmp_path, monkeypatch):
    path, callbacks, opened = watcher(tmp_path, monkeypatch, "noggin-latest.blend", "NOGGIN_LATEST")
    publish(path)
    callbacks[0]()
    assert opened == [{"filepath": str(path), "load_ui": False, "use_scripts": False}]


def test_an_incomplete_publication_keeps_the_last_view_and_retries(tmp_path, monkeypatch):
    path, callbacks, opened = watcher(tmp_path, monkeypatch)
    publish(path, "0" * 64)
    callbacks[0]()
    assert not opened
    publish(path)
    callbacks[0]()
    assert len(opened) == 1


def test_malformed_publication_metadata_does_not_disable_future_refreshes(tmp_path, monkeypatch):
    path, callbacks, opened = watcher(tmp_path, monkeypatch)
    publish(path)
    receipt = path.with_suffix(".blend.ready.json")
    for malformed in ("[]", "null", "{}", '{"sha256": null}', "incomplete json"):
        receipt.write_text(malformed)
        assert callbacks[0]() == 2.0
        assert not opened
    publish(path)
    callbacks[0]()
    assert len(opened) == 1


def test_a_different_file_cannot_reset_the_active_view(tmp_path, monkeypatch):
    path, callbacks, _ = watcher(tmp_path, monkeypatch)
    bpy = sys.modules["bpy"]

    def space(distance, perspective):
        return types.SimpleNamespace(
            region_3d=types.SimpleNamespace(
                view_rotation=(0.8, 0.2, 0.3, 0.4),
                view_location=(1, 2, 3),
                view_distance=distance,
                view_perspective=perspective,
            ),
            shading=types.SimpleNamespace(type="MATERIAL", color_type="MATERIAL"),
            overlay=types.SimpleNamespace(show_overlays=False),
        )

    def window(view):
        return types.SimpleNamespace(
            screen=types.SimpleNamespace(
                areas=[
                    types.SimpleNamespace(type="VIEW_3D", spaces=types.SimpleNamespace(active=view)),
                ]
            )
        )

    old, new = space(480, "ORTHO"), space(100, "PERSP")
    wm = types.SimpleNamespace(windows=[window(old)])
    bpy.context = types.SimpleNamespace(window_manager=wm)
    bpy.ops.wm.open_mainfile = lambda **_kw: setattr(wm, "windows", [window(new)])
    publish(path)
    callbacks[0]()
    assert new.region_3d.view_distance == 480
    assert new.region_3d.view_perspective == "ORTHO"


def test_the_local_review_build_publishes_what_the_watcher_refreshes_on(tmp_path, monkeypatch):
    """#1045: with the GX10 off, model.review's own build is the publisher (CONTRIBUTING.md, Code). A stand-in for
    Blender writes the file, an empty document has no bones to finish, and the slot is this test's own."""
    path, callbacks, opened = watcher(tmp_path, monkeypatch)
    monkeypatch.setattr(review, "SLOT", str(tmp_path / "slot"))
    monkeypatch.setattr(review, "job", lambda *_: {})
    monkeypatch.setitem(stages.STAGES, review.DOC, types.SimpleNamespace(parts={}))
    # each step's arguments end in the file it saves and the step's name
    monkeypatch.setattr(review, "_blender", lambda args: Path(args[-2]).write_bytes(b"a rebuilt review"))
    review.build(str(path))
    callbacks[0]()
    assert opened == [{"filepath": str(path), "load_ui": False, "use_scripts": False}]


@pytest.mark.skipif(not shutil.which(skeleton.BLENDER), reason="no Blender on this host")
def test_the_script_registers_when_blender_starts(tmp_path):
    """#1045: a real Blender start with the script installed, since only Blender has the restricted bpy.data its
    startup scripts register under. Its own user folder: neither Cansin's preferences nor his installed copy load."""
    startup = tmp_path / "scripts/startup"
    startup.mkdir(parents=True)
    shutil.copy(Path(__file__).with_name("reload.py"), startup / "noggin_reload.py")
    registered = (
        "import bpy, sys; m = sys.modules['noggin_reload']; "
        "assert bpy.app.timers.is_registered(m._tick) and m._loaded in bpy.app.handlers.load_post; "
        "print('reload: registered')"
    )
    run = subprocess.run(
        [skeleton.BLENDER, "-b", "--python-expr", registered],
        env=os.environ | {"BLENDER_USER_RESOURCES": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=50,
    )
    log = run.stdout + run.stderr
    # a traceback of the script's names its file; one of a bundled add-on, on a Blender built without its library, is
    # not this script's
    assert "noggin_reload" not in log and "reload: registered" in log, log
