"""The installed review watcher consumes only a verified publication, including while the viewer is dirty."""

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path


def watcher(tmp_path, monkeypatch):
    path = tmp_path.resolve() / "noggin-stage3.blend"
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
    monkeypatch.setenv("NOGGIN_REVIEW", str(path))
    spec = importlib.util.spec_from_file_location("noggin_reload_test", Path(__file__).with_name("reload.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.register()
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
