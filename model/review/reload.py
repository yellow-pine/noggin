"""Blender startup script: refresh the published review, or the latest file (model/latest), while retaining the
interactive view (#979, #998).

Cansin permits discarding incidental edits to this generated review. Editable sources are separate files.
Only a matching publisher checksum permits a refresh; partial transfers keep the previous open review.
"""

import hashlib
import json
import os
from pathlib import Path

import bpy

TARGETS = {
    Path(os.environ.get("NOGGIN_REVIEW", Path.home() / "Desktop/noggin-stage3.blend")).resolve(),
    Path(os.environ.get("NOGGIN_LATEST", Path.home() / "Desktop/noggin-latest.blend")).resolve(),
}
_seen = None


def _open():
    """The generated file open in this Blender, if one is."""
    # getattr: while startup scripts register, bpy.data is Blender's restricted stand-in, which has no filepath (#1045)
    filepath = getattr(bpy.data, "filepath", "")
    path = Path(filepath).resolve() if filepath else None
    return path if path in TARGETS else None


def _stamp(target):
    try:
        s = target.stat()
        return s.st_mtime_ns, s.st_size
    except OSError:
        return None


def _windows():
    wm = getattr(getattr(bpy, "context", None), "window_manager", None)
    return list(wm.windows) if wm else []


def _spaces(window):
    return [a.spaces.active for a in window.screen.areas if a.type == "VIEW_3D" and a.spaces.active.region_3d]


def _views():
    return [
        [
            (
                tuple(sp.region_3d.view_rotation),
                tuple(sp.region_3d.view_location),
                sp.region_3d.view_distance,
                sp.region_3d.view_perspective,
                sp.shading.type,
                sp.shading.color_type,
                sp.overlay.show_overlays,
            )
            for sp in _spaces(window)
        ]
        for window in _windows()
    ]


def _restore(views):
    # Loading can replace SpaceView3D datablocks even with load_ui=False: reacquire them after opening.
    for window, saved in zip(_windows(), views):
        for sp, (rotation, location, distance, perspective, shading, colour, overlays) in zip(_spaces(window), saved):
            sp.region_3d.view_rotation = rotation
            sp.region_3d.view_location = location
            sp.region_3d.view_distance = distance
            sp.region_3d.view_perspective = perspective
            sp.shading.type, sp.shading.color_type = shading, colour
            sp.overlay.show_overlays = overlays


@bpy.app.handlers.persistent
def _loaded(_):
    global _seen
    if target := _open():
        _seen = _stamp(target)


def _tick():
    global _seen
    if not (target := _open()):
        return 2.0
    now = _stamp(target)
    if now is None or now == _seen:
        return 2.0
    try:
        ready = json.loads(target.with_suffix(".blend.ready.json").read_text())
        if not isinstance(ready, dict) or not isinstance(ready.get("sha256"), str):
            return 2.0
        with target.open("rb") as source:
            checksum = hashlib.file_digest(source, "sha256").hexdigest()
        if checksum != ready["sha256"]:
            return 2.0
    except (OSError, ValueError, KeyError):
        return 2.0
    views = _views()
    bpy.ops.wm.open_mainfile(filepath=str(target), load_ui=False, use_scripts=False)
    _restore(views)
    _seen = now
    return 2.0


def register():
    _loaded(None)
    if _loaded not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_loaded)
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=2.0, persistent=True)


def unregister():
    if _loaded in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_loaded)
    if bpy.app.timers.is_registered(_tick):
        bpy.app.timers.unregister(_tick)
