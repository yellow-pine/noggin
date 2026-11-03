"""PROTOTYPE (#872): the one live Blender window Cansin watches. Launched once (relaunched only after a crash):

  PYTHONPATH=.blender-site /Applications/Blender.app/Contents/MacOS/Blender --python-use-system-env [skeleton.blend] \
    --python model/skeleton/live.py -- <cmd.py> [<a GLB to show when no .blend is open>]

Every 0.5 s, if <cmd.py> exists, it is read, deleted and exec()'d here (each step: build.py, finish.py, a hide or a
show); a failure's traceback goes to <cmd.py>.err. The Skin and #854's box stay hidden, the view framed on the rest."""

import os
import sys
import traceback

import bpy

ARGS = sys.argv[sys.argv.index("--") + 1 :]
CMD = ARGS[0]
HIDDEN = ("morty", "eyeball cap", "worn skull", "worn mandible", "next torso")


def view3d():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == "VIEW_3D":
                return {"window": w, "area": a, "region": [r for r in a.regions if r.type == "WINDOW"][0]}
    return None


def hide_skin():
    for o in bpy.context.view_layer.objects:
        if any(k in o.name for k in HIDDEN):
            o.hide_set(True)
            o.hide_render = True


def frame(view="FRONT"):
    c = view3d()
    if c:
        with bpy.context.temp_override(**c):
            bpy.ops.view3d.view_axis(type=view)
            bpy.ops.view3d.view_all()
        sp = c["area"].spaces.active
        sp.shading.type, sp.clip_start, sp.clip_end = "SOLID", 0.001, 20000.0
    return None


if not bpy.data.filepath and len(ARGS) > 1:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=ARGS[1])
hide_skin()
bpy.app.timers.register(frame, first_interval=1.0)


def watch():
    if os.path.exists(CMD):
        src = open(CMD).read()
        os.remove(CMD)
        try:
            exec(compile(src, CMD, "exec"), {"bpy": bpy, "__name__": "__live__"})
        except Exception:
            err = traceback.format_exc()
            print(err, flush=True)
            open(CMD + ".err", "w").write(err)
    return 0.5


bpy.app.timers.register(watch, persistent=True)
