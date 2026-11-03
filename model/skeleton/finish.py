"""PROTOTYPE (#872): the Finish step, its pictures and its review, run in the live window (model/skeleton/live.py):
the slow finish switched on at a coarse pitch (CI's full run finishes fine), the source bones hidden, front, side and
3/4 pictures from the scene's cameras (and one with Morty's Shells see-through), then the review against #872's
decisions, written beside the pictures as review.json.

  args: <out dir> [voxel mm]"""

import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from scipy.spatial import Delaunay

OUT = sys.argv[sys.argv.index("--") + 1]
VOXEL = float(sys.argv[sys.argv.index("--") + 2]) if len(sys.argv) > sys.argv.index("--") + 2 else 1.0
os.makedirs(OUT, exist_ok=True)
ELECTRONICS = ("next pack", "next spare pack", "next switch board", "next charger dongle", "next Core", "next Shield",
               "next cranium tray")  # fmt: skip
SURFACE_MARKS = ("rim", "condyle", "gonion", "menton", "prosthion", "glabella", "vertex", "opisthocranion", "euryon",
                 "zygion")  # fmt: skip
CLEAR = 1.6


def view3d():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == "VIEW_3D":
                return {"window": w, "area": a, "region": [r for r in a.regions if r.type == "WINDOW"][0]}
    return {}


def world_mesh(ob, dg):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    m = np.array(ob.matrix_world)
    v = np.array([x.co[:] for x in me.vertices]).reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]
    f = [list(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return v, f


def bvh(ob, dg):
    v, f = world_mesh(ob, dg)
    return BVHTree.FromPolygons([Vector(p) for p in v], f) if len(f) else None


def inside(tree, p):
    """Ray parity along +x (a closed mesh): odd hits, inside."""
    n, o = 0, Vector(p)
    while True:
        hit = tree.ray_cast(o, Vector((1, 0, 0)))
        if hit[0] is None:
            return n % 2 == 1
        n += 1
        o = hit[0] + Vector((1e-3, 0, 0))


bones = [o for o in bpy.data.collections["Skeleton"].all_objects if o.type == "MESH"]
finished = list(bpy.data.collections["Finished (render only)"].objects)
for o in bones:
    o.hide_set(True)
for o in finished:
    mod = o.modifiers["Finish"]
    mod.node_group.interface.items_tree["Voxel"].default_value = VOXEL
    mod.show_viewport = True  # the Finish step
    o.color = bpy.data.materials["Bone"].diffuse_color
    print(f"finish: {o.name}", flush=True)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    print(f"finish: {o.name} {len(o.evaluated_get(dg).data.vertices)} verts", flush=True)
dg = bpy.context.evaluated_depsgraph_get()

# --- pictures: the scene's cameras, viewport-rendered (no second evaluation of the finish)
scene = bpy.context.scene
scene.display.shading.color_type = "OBJECT"
shells = [o for o in bpy.data.collections["Morty Shells (reference)"].objects] + [
    o for o in bpy.data.objects if "eyeball cap" in o.name
]
pictures = []
c = view3d()
for show_shells, names in ((False, ("front", "side", "3-4")), (True, ("3-4",))):
    for o in shells:
        o.hide_set(not show_shells)
    for name in names:
        scene.camera = bpy.data.objects[f"camera {name}"]
        path = os.path.join(OUT, f"{name}{'-in-morty' if show_shells else ''}.png")
        scene.render.filepath = path
        with bpy.context.temp_override(**c):
            bpy.ops.render.opengl(write_still=True, view_context=False)
        pictures.append(path)
        print(f"finish: picture {path}", flush=True)
for o in shells:
    o.hide_set(False)

# --- the review
review = {"voxel_mm": VOXEL, "pictures": pictures, "warp_least_jacobian": scene.get("warp_min_jacobian")}
pieces = {o.name: world_mesh(o, dg) for o in finished}
allv = np.vstack([v for v, _ in pieces.values() if len(v)])
review["pieces"] = {n: len(v) for n, (v, _) in pieces.items()}
review["empty_pieces"] = [n for n, (v, _) in pieces.items() if not len(v)]

# landmarks: each surface landmark's target within 1 mm of the finished surface (or carved away by the mechanism)
trees = {n: BVHTree.FromPolygons([Vector(p) for p in v], f) for n, (v, f) in pieces.items() if len(f)}
held = {}
for t in bpy.data.collections["Landmarks"].objects:
    if not t.name.endswith(" target") or not any(k in t.name for k in SURFACE_MARKS):
        continue
    p = t.matrix_world.translation
    d = min(tr.find_nearest(p)[3] for tr in trees.values())
    held[t.name.removeprefix("LM ").removesuffix(" target")] = round(d, 2)
review["landmark_to_surface_mm"] = held
review["landmarks_over_1mm"] = {k: v for k, v in held.items() if v > 1.0}

# inside Morty's Shells: no finished vertex inside a Shell's wall, none outside their hull
sample = allv[:: max(1, len(allv) // 20000)]
shell_pts = np.vstack([world_mesh(o, dg)[0] for o in shells if "eyeball cap" not in o.name])
review["outside_shells_hull"] = int((Delaunay(shell_pts).find_simplex(sample) < 0).sum())
walls = [bvh(o, dg) for o in shells]
review["inside_a_shell_wall"] = int(sum(any(inside(w, p) for w in walls if w) for p in sample[::4]))

# #865's electronics carved round: no finished vertex within the clearance of a board, a pack, the dongle or a keep-out
elec = [o for o in bpy.data.objects if o.name.startswith(ELECTRONICS) and o.type == "MESH"]
elec += list(bpy.data.collections["Keep-outs"].objects)
closest = {}
for o in elec:
    tr = bvh(o, dg)
    d = min(tr.find_nearest(Vector(p))[3] for p in sample)
    closest[o.name] = round(d, 2)
review["electronics_closest_mm"] = closest
review["electronics_under_clearance"] = {k: v for k, v in closest.items() if v < CLEAR - VOXEL}
# print rules by construction (the SDF finish): walls >= 2 (grow - shrink), gaps under 2 grow closed, filleted
g = finished[0].modifiers["Finish"].node_group.interface.items_tree
review["print_rules"] = {
    "least_wall_mm": 2 * (g["Grow"].default_value - g["Shrink"].default_value),
    "holes_closed_under_mm": 2 * g["Grow"].default_value,
    "fillet_iterations": g["Fillet"].default_value,
}
json.dump(review, open(os.path.join(OUT, "review.json"), "w"), indent=1)
print("review:", json.dumps({k: v for k, v in review.items() if k != "landmark_to_surface_mm"}), flush=True)
with bpy.context.temp_override(**c):
    r3d = c["area"].spaces.active.region_3d
    r3d.view_perspective = "CAMERA"
    scene.camera = bpy.data.objects["camera 3-4"]
open(os.path.join(OUT, "done"), "w").write("ok\n")
