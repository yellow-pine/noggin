"""PROTOTYPE (#872): quick pictures of the live scene as Cansin sees it (no finish): the three layers, Mech opaque,
Skeleton and Morty see-through, from the front, side and 3/4 cameras. args: <out dir>"""

import os
import sys

import bpy

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
scene.display.shading.color_type = "OBJECT"
c = next(
    {"window": w, "area": a, "region": [r for r in a.regions if r.type == "WINDOW"][0]}
    for w in bpy.context.window_manager.windows
    for a in w.screen.areas
    if a.type == "VIEW_3D"
)
for name in ("front", "side", "3-4"):
    scene.camera = bpy.data.objects[f"camera {name}"]
    scene.render.filepath = os.path.join(OUT, f"{name}.png")
    with bpy.context.temp_override(**c):
        bpy.ops.render.opengl(write_still=True, view_context=False)
    print(f"pictures: {scene.render.filepath}", flush=True)
open(os.path.join(OUT, "done"), "w").write("ok\n")
