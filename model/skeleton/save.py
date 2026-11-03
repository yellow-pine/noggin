"""PROTOTYPE (#872): save the live scene: the full local copy (Morty in it, gitignored) and the committed .blend,
written without Morty (his sculpt is CC BY 4.0, local only). args: <committed .blend> <local copy .blend>"""

import os
import sys

import bpy

OUT, LOCAL = sys.argv[sys.argv.index("--") + 1 :][:2]
scene = bpy.context.scene
c = next(
    {"window": w, "area": a, "region": [r for r in a.regions if r.type == "WINDOW"][0]}
    for w in bpy.context.window_manager.windows
    for a in w.screen.areas
    if a.type == "VIEW_3D"
)
bpy.data.orphans_purge(do_recursive=True)
with bpy.context.temp_override(**c):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(LOCAL), compress=True)
mortys = [o for o in bpy.data.objects if o.name.startswith("Morty")]
refs = [(n, n.inputs["Object"].default_value) for g in bpy.data.node_groups for n in g.nodes
        if n.bl_idname == "GeometryNodeObjectInfo" and n.inputs["Object"].default_value in mortys]  # fmt: skip
for n, _ in refs:
    n.inputs["Object"].default_value = None
homes = {o: list(o.users_collection) for o in mortys}
for o, cs in homes.items():
    for col in cs:
        col.objects.unlink(o)
bpy.data.libraries.write(os.path.abspath(OUT), {scene, *bpy.data.texts}, path_remap="NONE", compress=True)
for o, cs in homes.items():
    for col in cs:
        col.objects.link(o)
for n, o in refs:
    n.inputs["Object"].default_value = o
for o in mortys:
    if "full" in o.name:
        o.hide_set(True)
print(f"save: {OUT} (without Morty), {LOCAL}", flush=True)
open(os.path.abspath(OUT) + ".done", "w").write("ok\n")
