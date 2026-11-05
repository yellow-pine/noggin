"""Blender startup script: refresh the published review while retaining the interactive view (#979).

Cansin permits discarding incidental edits to this generated review. Editable sources are separate files.
Only a matching publisher checksum permits a refresh; partial transfers keep the previous open review.
"""

import hashlib
import json
import os
from pathlib import Path

import bpy

TARGET = Path(os.environ.get("NOGGIN_REVIEW", Path.home() / "Desktop/noggin-stage3.blend")).resolve()
_seen = None


def _stamp():
    try:
        s = TARGET.stat()
        return s.st_mtime_ns, s.st_size
    except OSError:
        return None


@bpy.app.handlers.persistent
def _loaded(_):
    global _seen
    if Path(bpy.data.filepath).resolve() == TARGET:
        _seen = _stamp()


def _tick():
    global _seen
    if not bpy.data.filepath or Path(bpy.data.filepath).resolve() != TARGET:
        return 2.0
    now = _stamp()
    if now is None or now == _seen:
        return 2.0
    try:
        ready = json.loads(TARGET.with_suffix(".blend.ready.json").read_text())
        if not isinstance(ready, dict) or not isinstance(ready.get("sha256"), str):
            return 2.0
        with TARGET.open("rb") as source:
            checksum = hashlib.file_digest(source, "sha256").hexdigest()
        if checksum != ready["sha256"]:
            return 2.0
    except (OSError, ValueError, KeyError):
        return 2.0
    bpy.ops.wm.open_mainfile(filepath=str(TARGET), load_ui=False, use_scripts=False)
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
