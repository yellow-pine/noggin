"""PROTOTYPE (#872 step 3): the review of stage3.py's scene, headless on Cansin's Desktop file: each finished piece
evaluated alone at a coarse pitch, measured and switched off again (light: one finish in memory at a time; the run
stops if Blender grows past MAX_RSS), then the landmarks, the inside of Morty, #865's electronics, the bed, the head's
weight against the 5 V servo, and the foot. Writes <build>/review.json.

  Blender -b --python-use-system-env <Desktop .blend> --python model/skeleton/review.py -- <targets.json> [voxel mm]"""

import json
import math
import os
import resource
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

A = sys.argv[sys.argv.index("--") + 1 :]
TARGETS = A[0]
VOXEL = float(A[1]) if len(A) > 1 else 1.5
T = json.load(open(TARGETS))
BUILD = os.path.dirname(os.path.abspath(TARGETS))
ST = json.load(open(os.path.join(BUILD, "stage3.json")))
MAX_RSS = 5e9  # bytes: stop before the laptop swaps (it crashed under load, 2026-11-03)
CLEAR, BED = 1.6, 256.0
BOUGHT = ("servo", "horn", "Core", "Shield", "pack", "switch board", "dongle")
BOUGHT_G = {"servo": 9.0, "horn": 1.0, "Core": 6.0, "Shield": 8.0, "pack": 45.0, "switch board": 5.0, "dongle": 10.0}
SHELL_MM, INFILL = 1.2, 0.15  # printed: three 0.4 mm perimeters, 15 % infill (inferred)
review = {"voxel_mm": VOXEL}


def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # bytes on macOS


def bought(name):
    return any(k in name for k in BOUGHT)


def world(o, dg):
    """(vertices, BVH, area mm2, volume mm3) of o as evaluated, in the world."""
    ev = o.evaluated_get(dg)
    bm = bmesh.new()
    bm.from_mesh(ev.data)
    bm.transform(o.matrix_world)
    v = np.array([x.co[:] for x in bm.verts]).reshape(-1, 3)
    area, vol = sum(f.calc_area() for f in bm.faces), abs(bm.calc_volume())
    tree = BVHTree.FromBMesh(bm) if bm.faces else None
    bm.free()
    return v, tree, area, vol


def grams(area, vol):
    shell = min(area * SHELL_MM, vol)
    return T["petg_g_cm3"] * (shell + INFILL * (vol - shell)) / 1000.0


# --- each finished piece alone
dg = bpy.context.evaluated_depsgraph_get()
finished = list(bpy.data.collections["Finished (render only)"].objects)
pieces = {}
for o in finished:
    mod = o.modifiers["Finish"]
    mod.node_group.interface.items_tree["Voxel"].default_value = VOXEL
    mod.show_viewport = True
    bpy.context.view_layer.update()
    v, tree, area, vol = world(o, bpy.context.evaluated_depsgraph_get())
    pieces[o.name.removeprefix("finished ")] = (v, tree, grams(area, vol), v.mean(axis=0) if len(v) else np.zeros(3))
    mod.show_viewport = False
    bpy.context.view_layer.update()
    print(
        f"review: {o.name}: {len(v)} verts, {pieces[o.name.removeprefix('finished ')][2]:.0f} g, "
        f"rss {rss() / 1e9:.2f} GB",
        flush=True,
    )
    if rss() > MAX_RSS:
        raise SystemExit(f"review: stopped, Blender at {rss() / 1e9:.1f} GB")
dg = bpy.context.evaluated_depsgraph_get()
review["pieces_mm"] = {n: np.ptp(p[0], axis=0).round(0).tolist() for n, p in pieces.items() if len(p[0])}
review["over_the_bed"] = {n: d for n, d in review["pieces_mm"].items() if max(d) > BED}
review["empty_pieces"] = [n for n, p in pieces.items() if not len(p[0])]
trees = [p[1] for p in pieces.values() if p[1]]
held = {}  # each surface landmark's target to the finished surface (the orbits' centres and the anchors aren't)
for t in bpy.data.collections["Landmarks"].objects:
    name = t.name.removeprefix("LM ").removesuffix(" target")
    if t.name.endswith(" target") and "anchor" not in name and name not in ("L orbit", "R orbit"):
        held[name] = round(min(tr.find_nearest(t.matrix_world.translation)[3] for tr in trees), 2)
review["landmarks_over_1mm"] = {k: v for k, v in held.items() if v > 1.0}
allv = np.vstack([p[0] for p in pieces.values() if len(p[0])])
sample = allv[:: max(1, len(allv) // 3000)]
vol_tree = world(bpy.data.objects["Morty volume"], dg)[1]


def inside(tree, p):
    n, o = 0, Vector(p)
    for _ in range(64):
        hit = tree.ray_cast(o, Vector((1, 0, 0)))
        if hit[0] is None:
            break
        n += 1
        o = hit[0] + Vector((1e-3, 0, 0))
    return n % 2 == 1


review["outside_morty_of_sampled"] = [int(sum(not inside(vol_tree, p) for p in sample)), len(sample)]
mech = {o.name.removesuffix(":1"): o for c in ("Mech Skull", "Mech Mechanism", "Mech Pedestal")
        for o in bpy.data.collections[c].objects}  # fmt: skip
keep = {o.name: o for o in bpy.data.collections["Keep-outs"].objects}
closest = {}
for name in ("next pack", "next spare pack", "next switch board", "next charger dongle", "next Core 1", "next Core 2",
             "next Shield 1", "next Shield 2", "next cranium tray"):  # fmt: skip
    tr = world(mech[name], dg)[1]
    closest[name] = round(min(tr.find_nearest(Vector(p))[3] for p in sample), 1)
for name in ("keep USB-C next Core 1", "keep USB-C next Core 2", "keep swap door", "keep Torso floor"):
    tr = world(keep[name], dg)[1]
    closest[name] = round(min(tr.find_nearest(Vector(p))[3] for p in sample), 1)
review["electronics_closest_mm"] = closest
review["electronics_under_clearance"] = {k: v for k, v in closest.items() if v < CLEAR - VOXEL}


# --- the head's weight, the tilt servo, the foot
def part(o):
    v, _, area, vol = world(o, dg)
    g = next(g for k, g in BOUGHT_G.items() if k in o.name) if bought(o.name) else grams(area, vol)
    return g, (v.min(axis=0) + v.max(axis=0)) / 2 if len(v) else np.zeros(3)


def total(items):
    g = sum(m for m, _ in items)
    return g, sum(m * c for m, c in items) / g


head = [part(o) for o in bpy.data.collections["Mech Skull"].objects]
head += [(pieces[n][2], pieces[n][3]) for n in ("Calvaria", "Face and skull base", "Mandible")]
head_g, head_com = total(head)
neck = [part(o) for o in bpy.data.collections["Mech Mechanism"].objects]
neck += [(pieces[n][2], pieces[n][3]) for n in ("C1", "C2", "C3", "C4", "C7") if n in pieces]
base = [part(o) for o in bpy.data.collections["Mech Pedestal"].objects] + [
    (pieces["Pedestal"][2], pieces["Pedestal"][3])
]
all_g, all_com = total(head + neck + base)
tilt = np.array(ST["tilt"])
arm = head_com - tilt
rest = head_g / 1000 * abs(arm[1]) / 10
worst = head_g / 1000 * np.linalg.norm(arm[1:]) / 10
rated, stall = T["servo_kgf_cm"]["rated_kgfcm"], T["servo_kgf_cm"]["stall_kgfcm"]
x0, y0, x1, y1 = ST["foot"]
margin = []
for tilt_deg in (-20.0, 20.0):
    for pan_deg in (-45.0, 0.0, 45.0):
        rot = Matrix.Rotation(math.radians(pan_deg), 3, "Z") @ Matrix.Rotation(math.radians(tilt_deg), 3, "X")
        moved = np.array(rot @ Vector(arm)) + tilt
        com = (all_com * all_g - head_com * head_g + moved * head_g) / all_g
        margin.append(min(com[0] - (x0 - 2), (x1 + 2) - com[0], com[1] - (y0 - 2), (y1 + 2) - com[1]))
review["weights"] = {
    "head_g": round(head_g),
    "head_com_from_tilt_axis_mm": np.round(arm, 1).tolist(),
    "tilt_hold_rest_kgf_cm": round(rest, 2),
    "tilt_hold_worst_kgf_cm": round(worst, 2),
    "servo_5v_rated_stall_kgf_cm": [rated, stall],
    "bust_g": round(all_g),
    "foot_mm": [round(x1 - x0 + 4), round(y1 - y0 + 4)],
    "com_margin_to_foot_edge_mm": round(min(margin), 1),
}
json.dump(review, open(os.path.join(BUILD, "review.json"), "w"), indent=1)
print("review:", json.dumps(review), flush=True)
