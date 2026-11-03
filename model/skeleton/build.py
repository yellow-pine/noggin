"""PROTOTYPE (#872, throwaway builder): builds model/skeleton/skeleton.blend once, with its window open, from raw
BodyParts3D 4.0 (every bone) and the deployed Stage 3 GLB (the stand-in Mech). Afterwards the .blend is the source:
Cansin's edits land in it, rewarp.py re-runs the warp, finish.py runs the slow finish and the pictures.

  PYTHONPATH=.blender-site /Applications/Blender.app/Contents/MacOS/Blender --python-use-system-env \
    --python model/skeleton/build.py -- <next-mech-back.glb> <bodyparts3d obj dir> <targets.json> <out.blend>

Frame: the Stage 3 document's (model/skeleton/targets.py), in mm (scene unit 1 mm), z up, -y forward. BodyParts3D is
already in mm, z up, -y forward (its OBJ headers' bounds), the body's left at +x, as the Mech's L."""

import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree
from scipy import ndimage

sys.path.insert(0, os.path.dirname(__file__))
import importlib  # noqa: E402

import rewarp  # noqa: E402

rewarp = importlib.reload(rewarp)  # the live window keeps modules between steps

GLB, BP3D, TARGETS, OUT, MORTY = sys.argv[sys.argv.index("--") + 1 :][:5]
T = json.load(open(TARGETS))

# BodyParts3D element files (partof_element_parts.txt), by the group each is posed with
SKULL = {
    "frontal bone": "FJ3200", "L parietal bone": "FJ3274", "R parietal bone": "FJ3380", "occipital bone": "FJ3309",
    "L temporal bone": "FJ3281", "R temporal bone": "FJ3386", "sphenoid bone": "FJ3394", "ethmoid": "FJ3199",
    "L maxilla": "FJ3269", "R maxilla": "FJ3375", "L zygomatic bone": "FJ3287", "R zygomatic bone": "FJ3392",
    "L nasal bone": "FJ3272", "R nasal bone": "FJ3378", "L lacrimal bone": "FJ3265", "R lacrimal bone": "FJ3371",
    "L palatine bone": "FJ3273", "R palatine bone": "FJ3379", "vomer": "FJ3395",
    "L inferior nasal concha": "FJ3263", "R inferior nasal concha": "FJ3369",
}  # fmt: skip
MANDIBLE = {"mandible": "FJ3289"}
NECK = {"C1": "FJ3176", "C2": "FJ3177", "C3": "FJ3161", "C4": "FJ3164", "C5": "FJ3167", "C6": "FJ3170", "C7": "FJ3172"}
THORACIC = ["FJ3158", "FJ3160", "FJ3163", "FJ3166", "FJ3169", "FJ3171", "FJ3173", "FJ3174", "FJ3175", "FJ3154",
            "FJ3155", "FJ3156"]  # fmt: skip
RIBS_L = ["FJ3228", "FJ3229", "FJ3230", "FJ3231", "FJ3232", "FJ3233", "FJ3234", "FJ3235", "FJ3236", "FJ3225",
          "FJ3226", "FJ3227"]  # fmt: skip
RIBS_R = ["FJ3334", "FJ3336", "FJ3338", "FJ3340", "FJ3342", "FJ3344", "FJ3346", "FJ3347", "FJ3348", "FJ3330",
          "FJ3331", "FJ3332"]  # fmt: skip
CART_L = ["FJ3239", "FJ3242", "FJ3245", "FJ3248", "FJ3251", "FJ3254", "FJ3255"]
CART_R = ["FJ3333", "FJ3335", "FJ3337", "FJ3339", "FJ3341", "FJ3343", "FJ3345"]
RIBCAGE = (
    {f"T{i + 1}": f for i, f in enumerate(THORACIC)}
    | {f"L rib {i + 1}": f for i, f in enumerate(RIBS_L)}
    | {f"R rib {i + 1}": f for i, f in enumerate(RIBS_R)}
    | {f"L costal cartilage {i + 1}": f for i, f in enumerate(CART_L)}
    | {f"R costal cartilage {i + 1}": f for i, f in enumerate(CART_R)}
    | {"manubrium": "FJ3290", "body of sternum": "FJ3178", "xiphoid process": "FJ3153"}
    | {"L clavicle": "FJ3237", "R clavicle": "FJ3362", "L scapula": "FJ3279", "R scapula": "FJ3384"}
)
SCLERA = {"L": "FJ1317", "R": "FJ1368"}
MAX_FACES = 3000  # each bone decimated to at most this: the light working copy (CI finishes from full resolution)
STANDIN_FACES = 4000  # each stand-in part, likewise
SKIN = ("next morty ", "next worn ", "eyeball cap")  # the Skin's nodes, hidden (Cansin, 2026-11-03)
CLEAR = 1.6  # each landmark target's room off what it clears: the carve's clearance
# the three layers Cansin toggles, innermost first, and their opacity (Cansin, 2026-11-03)
MECH_RGBA, BONE_RGBA, MORTY_RGBA = (0.30, 0.32, 0.36, 1.0), (0.86, 0.80, 0.68, 0.69), (1.0, 0.72, 0.55, 0.33)
INSET = 1.6 + 1.6  # inside Morty: his wall, then the gap (inferred)
CUT_ABOVE_BROW = 12.0  # the calvaria's cut, level, this far over the glabella (inferred)
# the cranium's length in Morty's head, of life; any width at most this of life; its height at most this of life
CRANIUM_FIT, LIFE_MAX, CRANIUM_H_MAX = 0.97, 1.05, 1.08
# the real Morty's sculpt, measured on its front depth map (#872; raw mm, z up, -y forward): each eye's centre (its
# pupil's apex, its dome's radius behind it), the neck's top, the ribcage's span (his shoulders down to his ribs'
# end over his hips), his torso's half-width inside his arms (inferred from the front view)
MORTY_EYES = {"L": (84.36, 245.85, 107.2), "R": (74.16, 245.85, 107.4)}
MORTY_EYE_R, MORTY_NECK_Z, MORTY_RIBCAGE_Z, MORTY_TORSO_HALF = 5.67, 92.0, (50.0, 88.0), 9.5


def view3d():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == "VIEW_3D":
                return {"window": w, "area": a, "region": [r for r in a.regions if r.type == "WINDOW"][0]}
    return {}


def show(msg, objs=None, view="3/4"):
    """Print a step and draw it in the live window: solid, front or 3/4, framed on objs (all visible if None)."""
    print("build:", msg, flush=True)
    c = view3d()
    if not c or bpy.app.background:
        return
    sp = c["area"].spaces.active
    sp.shading.type, sp.clip_start, sp.clip_end = "SOLID", 0.5, 20000.0
    sp.shading.color_type = "OBJECT"  # Cansin's look: Shells see-through, bones ivory, the Mech grey
    r3d = sp.region_3d
    r3d.view_perspective = "PERSP"
    r3d.view_rotation = (Euler((math.radians(78), 0, math.radians(35))) if view == "3/4" else
                         Euler((math.radians(90), 0, 0))).to_quaternion()  # fmt: skip
    bpy.context.view_layer.update()
    with bpy.context.temp_override(**c):
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in objs or [o for o in bpy.context.view_layer.objects if o.visible_get() and o.type == "MESH"]:
            if o.visible_get():
                o.select_set(True)
        bpy.ops.view3d.view_selected()
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)


def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def move(ob, coll):
    for c in ob.users_collection:
        c.objects.unlink(ob)
    coll.objects.link(ob)


def material(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)
    return m


def decimate(ob, cap):
    n = len(ob.data.polygons)
    if n > cap:
        mod = ob.modifiers.new("decimate", "DECIMATE")
        mod.ratio = cap / n
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.remove(mod)
        old, ob.data = ob.data, me
        if old.users == 0:
            bpy.data.meshes.remove(old)


def corners(objs):
    """Every vertex of objs, in the world."""
    out = []
    for o in objs:
        m = np.array(o.matrix_world)
        out.append(verts(o) @ m[:3, :3].T + m[:3, 3])
    return np.vstack(out)


def verts(ob):
    co = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def obj_verts(path):
    return np.array([list(map(float, ln.split()[1:4])) for ln in open(path) if ln.startswith("v ")])


def empty(name, coll, kind="PLAIN_AXES", size=3.0):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type, e.empty_display_size = kind, size
    coll.objects.link(e)
    return e


# --- the scene: mm, emptied (the live window is reused, never reloaded)
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
for kind in (bpy.data.meshes, bpy.data.materials, bpy.data.node_groups, bpy.data.cameras, bpy.data.curves,
             bpy.data.texts, bpy.data.images):  # fmt: skip
    for d in list(kind):
        kind.remove(d)
scene = bpy.context.scene
scene.unit_settings.scale_length, scene.unit_settings.length_unit = 1.0, "METERS"  # the GLB comes in in metres
BONE = material("Bone", (0.86, 0.80, 0.68))
STANDIN = material("Stand-in", (0.30, 0.32, 0.36))
KEEP = material("Keep-out", (0.9, 0.2, 0.2))

# --- the stand-in Mech: the deployed Stage 3 GLB, in mm, decimated; the Skin hidden, #855's bones and #854's box out
mech = collection("Mech")
skeleton = collection("Skeleton")
morty_c = collection("Morty")
helpers = collection("helpers")  # cutters, empties, full meshes: hidden (Cansin)
carve = collection("Carve", helpers)
carve_parts = collection("Carve parts", carve)  # the stand-in's parts, linked (electronics: their hulls, below)
keepouts = collection("Keep-outs", carve)
box = collection("Torso box (#854, replaced by the ribcage)", helpers)
with bpy.context.temp_override(**view3d()):
    bpy.ops.import_scene.gltf(filepath=GLB)
for ob in list(scene.objects):
    if ob.type != "MESH":
        bpy.data.objects.remove(ob)
        continue
    ob.animation_data_clear()  # the GLB's baked poses (#863) would put every moved part back on evaluation
    if ob.data.users > 1:
        ob.data = ob.data.copy()
    ob.data.transform(Matrix.Scale(1000.0, 4) @ ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    name = ob.name.removesuffix(":1")
    if name in ("next atlas", "next axis") or name.startswith(SKIN):
        if "eyeball cap" in name:  # the caps front the eyes: cut round (a helper), not shown
            decimate(ob, STANDIN_FACES)
            move(ob, carve_parts)
            ob.hide_render = True
        else:
            bpy.data.objects.remove(ob)
        continue
    decimate(ob, STANDIN_FACES)
    ob.data.materials.clear()
    ob.data.materials.append(STANDIN)
    ob.color = MECH_RGBA
    move(ob, box if name in ("next torso", "next torso lid") else mech)
bpy.context.view_layer.update()
scene.unit_settings.scale_length, scene.unit_settings.length_unit = 0.001, "MILLIMETERS"  # then 1 unit = 1 mm
show("stand-in Mech imported", list(mech.objects))


def box_obj(name, lo, hi, coll):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.matrix_world = Matrix.LocRotScale((Vector(lo) + Vector(hi)) / 2, None, Vector(hi) - Vector(lo))
    coll.objects.link(ob)
    return ob


# keep-outs (#865): the Torso's floor (the foot, kept), the -x swap door out through the ribcage and Shirt, each Core's
# USB-C opening out the cranium's back
for ob in [
    box_obj("keep Torso floor", *T["floor"], keepouts),
    *[box_obj(f"keep USB-C {n}", lo, hi, keepouts) for n, (lo, hi) in T["usb"].items()],
]:
    ob.data.materials.append(KEEP)
door = bpy.data.meshes.new("keep swap door")
bm = bmesh.new()
x0, x1 = T["door_x"] - 40.0, T["door_x"] + 25.0
ring = [bm.verts.new((x0, y, z)) for y, z in T["door"]] + [bm.verts.new((x1, y, z)) for y, z in T["door"]]
k = len(T["door"])
bm.faces.new(ring[:k][::-1])
bm.faces.new(ring[k:])
for i in range(k):
    j = (i + 1) % k
    bm.faces.new((ring[i], ring[j], ring[k + j], ring[k + i]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(door)
bm.free()
ob = bpy.data.objects.new("keep swap door", door)
ob.data.materials.append(KEEP)
keepouts.objects.link(ob)
ELECTRONICS = ("next pack", "next spare pack", "next switch board", "next charger dongle", "next Core", "next Shield")


def hull(ob, coll):
    """A closed convex copy of ob (a box-like board or pack), so its SDF's sign can't flip on an open mesh."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    me = bpy.data.meshes.new(f"keep {ob.name}")
    bm.to_mesh(me)
    bm.free()
    h = bpy.data.objects.new(me.name, me)
    h.matrix_world = ob.matrix_world
    coll.objects.link(h)
    return h


for ob in mech.objects:
    if ob.name.startswith(ELECTRONICS):
        hull(ob, keepouts)
    else:
        carve_parts.objects.link(ob)
for ob in keepouts.objects:
    ob.display_type, ob.hide_render = "WIRE", True

# --- the bones, raw BodyParts3D
groups = {}  # group -> [objects]


def load(name, fj, coll):
    v, f = [], []
    for ln in open(os.path.join(BP3D, fj + ".obj")):
        if ln.startswith("v "):
            v.append(tuple(map(float, ln.split()[1:4])))
        elif ln.startswith("f "):
            f.append([int(t.split("/")[0]) - 1 for t in ln.split()[1:]])
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    decimate(ob, MAX_FACES)
    ob.data.materials.clear()
    ob.data.materials.append(BONE)
    ob.color = BONE_RGBA
    return ob


skull_c, mandible_c = collection("Skull", skeleton), collection("Mandible", skeleton)
neck_c, ribcage_c = collection("Neck", skeleton), collection("Ribcage", skeleton)
groups["skull"] = [load(n, f, skull_c) for n, f in SKULL.items()] + [
    load(n, f, mandible_c) for n, f in MANDIBLE.items()
]
for n, f in NECK.items():
    groups[n] = [load(n, f, collection(n, neck_c))]
groups["ribcage"] = [load(n, f, ribcage_c) for n, f in RIBCAGE.items()]
z = verts(groups["skull"][-1])[:, 2]
assert 1400 < z.mean() < 1520, f"BodyParts3D's frame: the mandible at z {z.mean():.0f}, expected ~1460"
show("BodyParts3D bones imported (raw)", [o for g in groups.values() for o in g])


# costal cartilages 8-10 (BodyParts3D lacks them; modelled, inferred): a tube from each rib's front end up to the
# cartilage above, ~5 mm round
def tube(name, a, b, r=5.0):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", r, 3
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(1)
    mid = (Vector(a) + Vector(b)) / 2 + Vector((0, -6, 4))
    for p, co in zip(sp.bezier_points, (a, b)):
        p.co, p.handle_left_type, p.handle_right_type = co, "AUTO", "AUTO"
    sp.bezier_points[0].handle_right = mid
    tmp = bpy.data.objects.new(name, cu)
    ribcage_c.objects.link(tmp)
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(BONE)
    ob.color = BONE_RGBA
    ribcage_c.objects.link(ob)
    return ob


by = {o.name: o for o in groups["ribcage"]}
for side in "LR":
    above = by[f"{side} costal cartilage 7"]
    for rib in (8, 9, 10):
        v = verts(by[f"{side} rib {rib}"])
        tip = v[np.argmin(v[:, 1])]  # the rib's front end
        u = verts(above)
        join = u[np.argmin(np.linalg.norm(u - (tip + (0, -10, 25)), axis=1))]
        above = tube(f"{side} costal cartilage {rib} (modelled)", tip, join)
        groups["ribcage"].append(above)


# --- the poses: each group a scale, rotation and offset (its pose empty), from its source centre
poses = collection("Poses", helpers)


def pose(group, centre, at, scale, rot=(0, 0, 0)):
    e = empty(f"pose {group}", poses, "ARROWS", 15.0)
    e.matrix_world = Matrix.LocRotScale(Vector(at), Euler(rot), Vector(scale))
    for ob in groups[group]:
        ob.parent, ob.matrix_parent_inverse = e, Matrix.Translation(-Vector(centre))
    return e


def world(group, p):
    """A source point (raw) through its group's pose."""
    ob = groups[group][0]
    return np.array(ob.matrix_world @ Vector(p))


def stack(group):
    return np.vstack([verts(o) for o in groups[group]])


sclera = {s: obj_verts(os.path.join(BP3D, f + ".obj")).mean(axis=0) for s, f in SCLERA.items()}
assert sclera["L"][0] > 0 > sclera["R"][0], "the body's left at +x"
c_skull = (sclera["L"] + sclera["R"]) / 2
raw = {o.name: verts(o) for o in groups["skull"]}
fr = raw["frontal bone"]
fr = fr[(np.abs(fr[:, 0]) < 5) & (fr[:, 2] > c_skull[2] + 10) & (fr[:, 2] < c_skull[2] + 40)]
glabella, opisthocranion = fr[np.argmin(fr[:, 1])], raw["occipital bone"][np.argmax(raw["occipital bone"][:, 1])]
top = np.vstack(list(raw.values()))
top = top[np.argmax(top[:, 2])]

# --- the fit target: the real Morty (ChelsCCT's sculpt, CC BY 4.0, local only: never saved into the committed .blend),
# scaled so his head hosts a life-size cranium: his eyes' spacing is the skull's interorbital, about life (Cansin)
with bpy.context.temp_override(**view3d()):
    bpy.ops.wm.stl_import(filepath=MORTY)
full = bpy.context.selected_objects[0]
full.name = "Morty (full, measuring)"
move(full, helpers)
eyes_raw = {s: np.array(c) for s, c in MORTY_EYES.items()}
# his scale, from the cranium (Cansin): his head deep enough, along the brow's line, for a life-size cranium's length
# (glabella to opisthocranion, CRANIUM_FIT of life) inside his wall and the gap; its width and height then follow life
mid_raw, mid = (eyes_raw["L"] + eyes_raw["R"]) / 2, (np.array(T["eyes"]["L"]) + np.array(T["eyes"]["R"])) / 2
raw_bvh = BVHTree.FromObject(full, bpy.context.evaluated_depsgraph_get())


def through(origin, d, tree):
    """The first skin a ray from outside meets."""
    hit = tree.ray_cast(Vector(origin), Vector(d))[0]
    assert hit is not None, f"no skin along {d} from {origin}"
    return np.array(hit)


MORTY_SCALE = 6.0
for _ in range(4):
    zb = mid_raw[2] + (glabella[2] - c_skull[2]) / MORTY_SCALE
    depth = (
        through((mid_raw[0], 9999, zb), (0, -1, 0), raw_bvh)[1]
        - through((mid_raw[0], -9999, zb), (0, 1, 0), raw_bvh)[1]
    )
    MORTY_SCALE = (CRANIUM_FIT * (opisthocranion[1] - glabella[1]) + 2 * INSET) / depth
full.data.transform(
    Matrix.Translation(Vector(mid)) @ Matrix.Scale(MORTY_SCALE, 4) @ Matrix.Translation(Vector(-mid_raw))
)
full.data.update()
eye = {s: (c - mid_raw) * MORTY_SCALE + mid for s, c in eyes_raw.items()}
r_eye = MORTY_EYE_R * MORTY_SCALE
morty = bpy.data.objects.new("Morty", full.data.copy())
morty_c.objects.link(morty)
decimate(morty, 100_000)
morty.color, morty.hide_render = MORTY_RGBA, True
full.hide_set(True)
full.hide_render = True
mv = corners([morty])
print(
    f"build: Morty x{MORTY_SCALE}: {np.ptp(mv[:, 2]):.0f} mm tall; eyes {np.linalg.norm(eye['L'] - eye['R']):.1f} apart, "
    f"r {r_eye:.1f}"
)
show("the real Morty, scaled", [morty])
mbvh = BVHTree.FromPolygons([Vector(p) for p in mv], [list(p.vertices) for p in morty.data.polygons])


def inner(origin, d):
    """Morty's inside, met by a ray from outside him along d: his skin, then INSET further in (rays from inside meet
    the sculpt's folds)."""
    d = np.array(d, float) / np.linalg.norm(d)
    return through(np.asarray(origin, float) - d * 9999, d, mbvh) + d * INSET


neck_z = (MORTY_NECK_Z - mid_raw[2]) * MORTY_SCALE + mid[2]
head_v = mv[mv[:, 2] > neck_z]
c_h = (head_v.min(axis=0) + head_v.max(axis=0)) / 2
c_h[0] = 0.0
ez = eye["L"][2]
t_vertex = inner(c_h, (0, 0, -1))
t_opis = inner((0, c_h[1], ez + (opisthocranion[2] - c_skull[2])), (0, -1, 0))
t_glab = inner((0, c_h[1], ez + max(glabella[2] - c_skull[2], r_eye + 8)), (0, 1, 0))
raw_all = np.vstack(list(raw.values()))


def life_half(names, z_rel):
    """A source bone set's half-width at its widest, the most it may warp out to (LIFE_MAX of life)."""
    v = np.vstack([raw[n] for n in names])
    return LIFE_MAX * np.abs(v[:, 0] - c_skull[0]).max()


eury_max = life_half(("L parietal bone", "R parietal bone", "L temporal bone", "R temporal bone"), 0)
zyg_max = life_half(("L zygomatic bone", "R zygomatic bone"), 0)
t_eury = {s: inner((0, c_h[1], ez + 20), (-sx, 0, 0)) for s, sx in (("L", 1), ("R", -1))}
t_zyg = {s: inner((0, eye["L"][1] + 15, ez - r_eye * 0.9), (-sx, 0, 0)) for s, sx in (("L", 1), ("R", -1))}
t_vertex[2] = min(t_vertex[2], ez + LIFE_MAX * (top[2] - c_skull[2]))  # the vault no taller than life allows
for t, cap in ((t_eury, eury_max), (t_zyg, zyg_max)):
    for s in t:
        t[s][0] = np.sign(t[s][0]) * min(abs(t[s][0]), cap)
# the chin: his face's front where his head meets his neck
z_chin = neck_z + 8.0
t_ment = inner((0, 0, z_chin), (0, 1, 0)) + (0, 0, INSET)
# his jawline (inferred): the hinge just in front of and under each ear (his head's widest points)
ears = {}
for s, sx in (("L", 1), ("R", -1)):
    side = head_v[head_v[:, 0] * sx > (head_v[:, 0] * sx).max() - 6.0]
    ears[s] = side.mean(axis=0)
hinge_yz = np.array((ears["L"][1] + ears["R"][1], ears["L"][2] + ears["R"][2])) / 2 + (-10.0, -8.0)

# --- the Mech's first moves (#872 step 3, stand-ins only): its eyes out onto Morty's pupils, its jaw onto his jawline
CHANGES = []
for s in "LR":
    d = eye[s] - np.array(T["eyes"][s])
    for o in mech.objects:
        if o.name.startswith(f"next {s} "):
            o.location += Vector(d)
    CHANGES.append(f"{s} eye assembly (eyeball, lids, yoke, push-rod, lid servo and linkage) moved {np.round(d, 1)} mm")
dj = np.array((0.0, hinge_yz[0] - T["hinge"][0][1], hinge_yz[1] - T["hinge"][0][2]))
for o in mech.objects:
    if o.name.removesuffix(":1") in ("next jaw", "next jaw bar", "next mouth horn", "next mouth servo"):
        o.location += Vector(dj)
CHANGES.append(f"jaw, jaw bar, mouth horn and mouth servo moved {np.round(dj, 1)} mm (the hinge onto Morty's jawline)")

# the skull's pose: across, the eyes' spacing; front to back and up, Morty's head inside (glabella to opisthocranion,
# the orbits to the vertex), so the warp is left the regional changes; each held near life (Cansin: within ~10%)
s_skull = 1.0  # across, life: the orbits warp out onto his pupils
sk_y = (t_opis[1] - t_glab[1]) / (opisthocranion[1] - glabella[1])
sk_z = (t_vertex[2] - ez) / (top[2] - c_skull[2])
pose("skull", c_skull, (eye["L"] + eye["R"]) / 2, (s_skull, sk_y, sk_z))
print(f"build: skull pose scale {s_skull:.3f} {sk_y:.3f} {sk_z:.3f} (life 1.0)")

# the ribcage: into Morty's torso, inside his shirt and clear of his arms (the squash: a loop topic, Cansin to confirm)
tz = [(z - mid_raw[2]) * MORTY_SCALE + mid[2] for z in MORTY_RIBCAGE_Z]
band = mv[(mv[:, 2] > tz[0]) & (mv[:, 2] < tz[1]) & (np.abs(mv[:, 0]) < MORTY_TORSO_HALF * MORTY_SCALE)]
lo = np.array((-MORTY_TORSO_HALF * MORTY_SCALE + INSET, band[:, 1].min() + INSET, tz[0]))
hi = np.array((MORTY_TORSO_HALF * MORTY_SCALE - INSET, band[:, 1].max() - INSET, tz[1]))
v = stack("ribcage")
src_lo, src_hi = v.min(axis=0), v.max(axis=0)
pose("ribcage", (src_lo + src_hi) / 2, (lo + hi) / 2, (hi - lo) / (src_hi - src_lo))
bpy.context.view_layer.update()
print(f"build: ribcage pose scale {np.round((hi - lo) / (src_hi - src_lo), 3)}")


def canal(v, b=0.5):
    """(x, y) of a vertebra's canal: the largest hole in its plan view (model/printed/skull.py _canal, ported)."""
    p = v[:, :2]
    lo = p.min(axis=0)
    ij = np.floor((p - lo) / b).astype(int)
    occ = np.zeros(ij.max(axis=0) + 1, bool)
    occ[ij[:, 0], ij[:, 1]] = True
    occ = ndimage.binary_closing(occ, iterations=3)
    holes = ndimage.binary_fill_holes(occ) & ~occ
    label, n = ndimage.label(holes)
    if n == 0:
        return p.mean(axis=0)
    biggest = np.argmax(ndimage.sum(holes, label, range(1, n + 1))) + 1
    return np.argwhere(label == biggest).mean(axis=0) * b + lo


# the neck: C1 under the occipital condyles, C7 on T1, each canal on the line between (the post's, once the Mech
# moves, #872 step 3), at life width, squashed in height to the room Morty's short neck gives
occ = raw["occipital bone"]
low = occ[occ[:, 2] < occ[:, 2].min() + 4].mean(axis=0)
c1_at = world("skull", low) - (0, 0, 2.0)
t1 = verts(by["T1"])
t1_canal = (*canal(t1), t1[:, 2].max())
c7_at = world("ribcage", t1_canal) + (0, 0, 2.0)
zs = {n: (verts(groups[n][0])[:, 2].min(), verts(groups[n][0])[:, 2].max()) for n in NECK}
z_hi, z_lo = zs["C1"][1], zs["C7"][0]
s_z = (c1_at[2] - c7_at[2]) / (z_hi - z_lo)
for n in NECK:
    v = verts(groups[n][0])
    cx, cy = canal(v)
    cz = v[:, 2].mean()
    f = (cz - z_lo) / (z_hi - z_lo)
    at = c7_at + (c1_at - c7_at) * f
    pose(n, (cx, cy, cz), at, (1.0, 1.0, s_z))
print(f"build: neck {c1_at[2] - c7_at[2]:.0f} mm C1 to C7 (life {z_hi - z_lo:.0f}): squash {s_z:.2f}")
bpy.context.view_layer.update()
show("bones posed (scale, rotation, offset per group)", [o for g in groups.values() for o in g] + [morty], "front")

# --- landmarks: each a source empty on the anatomy (riding its group's pose) and a target inside Morty
marks = collection("Landmarks", helpers)


def landmark(name, group, src, target=None):
    e = empty(f"LM {name}", marks, "SPHERE", 1.5)
    e.parent = groups[group][0].parent
    e.matrix_parent_inverse = groups[group][0].matrix_parent_inverse
    e.location = Vector(src)
    bpy.context.view_layer.update()
    t = empty(f"LM {name} target", marks, "PLAIN_AXES", 4.0)
    t.location = Vector(world(group, src) if target is None else target)


allv = np.vstack(list(raw.values()))
faces = []
off = 0
for o in groups["skull"]:
    faces += [[off + i for i in p.vertices] for p in o.data.polygons]
    off += len(o.data.vertices)
bvh = BVHTree.FromPolygons([Vector(p) for p in allv], faces)
for s, sx in (("L", 1), ("R", -1)):
    landmark(f"{s} orbit", "skull", sclera[s], eye[s])
    # no medial rim: the walls between the orbits are carved by the eyes (a loop topic, Cansin to confirm); the lateral
    # rim stays inside the cheekbones' life width
    lateral = min(r_eye + CLEAR, zyg_max - 6.0 - abs(eye[s][0]))
    for d, r, tag in (((0, 0, 1), r_eye + CLEAR, "up"), ((0, 0, -1), r_eye + CLEAR, "down"),
                      ((sx, 0, 0), lateral, "lateral")):  # fmt: skip
        hit = bvh.ray_cast(Vector(sclera[s]), Vector(d))[0]
        if hit is None:
            continue
        hit = np.array(hit)
        t = eye[s] + np.array(d) * r
        t[1] = eye[s][1] + (hit[1] - sclera[s][1]) * sk_y
        landmark(f"{s} orbit rim {tag}", "skull", hit, t)
md = raw["mandible"]
back = md[md[:, 1] > np.median(md[:, 1])]
for s, sx in (("L", 1), ("R", -1)):
    side = back[back[:, 0] * sx > 20]
    cond = side[side[:, 2] > side[:, 2].max() - 3].mean(axis=0)
    landmark(f"{s} condyle", "skull", cond, (world("skull", cond)[0], *hinge_yz))  # on the jawline, Mech's and Morty's
ch = md[np.abs(md[:, 0]) < 5]
landmark("menton", "skull", ch[np.argmin(ch[:, 2])], t_ment)
landmark("glabella", "skull", glabella, t_glab)
# the forehead curving back under Morty's sloping brow, so the limit never opens the frontal bone
frontal = raw["frontal bone"]
for up in (55.0, 85.0):
    band = frontal[(np.abs(frontal[:, 0]) < 6) & (np.abs(frontal[:, 2] - (c_skull[2] + up)) < 4)]
    src = band[np.argmin(band[:, 1])]
    z = t_glab[2] + (src[2] - glabella[2]) * sk_z  # above the glabella's target as far as life has it above
    landmark(f"forehead {up:.0f}", "skull", src, inner((0, c_h[1], z), (0, 1, 0)))
landmark("vertex", "skull", top, t_vertex)
landmark("opisthocranion", "skull", opisthocranion, t_opis)
par = np.vstack([raw[n] for n in ("L parietal bone", "R parietal bone", "L temporal bone", "R temporal bone")])
zy = np.vstack([raw[n] for n in ("L zygomatic bone", "R zygomatic bone")])
for s, sx in (("L", 1), ("R", -1)):
    p = par[par[:, 0] * sx > 0]
    landmark(f"{s} euryon", "skull", p[np.argmax(np.abs(p[:, 0]))], t_eury[s])
    z = zy[zy[:, 0] * sx > 0]
    landmark(f"{s} zygion", "skull", z[np.argmax(np.abs(z[:, 0]))], t_zyg[s])

# anchors: the neck and the ribcage are posed to fit, so their landmarks start on their targets
for n in NECK:
    v = verts(groups[n][0])
    for i, p in enumerate((v[np.argmin(v[:, 0])], v[np.argmax(v[:, 0])], v[np.argmin(v[:, 1])], v[np.argmax(v[:, 1])])):
        landmark(f"{n} anchor {i}", n, p)
v = stack("ribcage")
mid_r = (v.min(axis=0) + v.max(axis=0)) / 2
for i, c in enumerate(np.array(np.meshgrid([-1, 1], [-1, 1], [-1, 1])).T.reshape(-1, 3)):
    landmark(f"ribcage anchor {i}", "ribcage", mid_r + c * (v.max(axis=0) - v.min(axis=0)) * 0.4)
landmark("ribcage anchor centre", "ribcage", mid_r)
# the frame: fixed points round the bust, so the warp never extrapolates
for i, c in enumerate(np.array(np.meshgrid([-500, 500], [-600, 400], [-600, 700])).T.reshape(-1, 3)):
    empty(f"LM frame {i}", marks, "CUBE", 5.0).location = Vector(c)
bpy.context.view_layer.update()

# --- the warp
VAULT = ("frontal bone", "L parietal bone", "R parietal bone", "occipital bone", "L temporal bone", "R temporal bone")
raw_vault = np.vstack([raw[n] for n in VAULT])


def warped_vault():
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for n in VAULT:
        o = bpy.data.objects[n].evaluated_get(dg)
        out.append(np.array([o.matrix_world @ v.co for v in o.data.vertices]))
    return np.vstack(out)


det, err = rewarp.rewarp()
# the cranium's height held within life's +-10% (Cansin): the vertex's target lowered by any excess, re-warped
for _ in range(3):
    excess = np.ptp(warped_vault()[:, 2]) - CRANIUM_H_MAX * np.ptp(raw_vault[:, 2])
    if excess <= 0:
        break
    bpy.data.objects["LM vertex target"].location.z -= excess
    bpy.context.view_layer.update()
    det, err = rewarp.rewarp()
vault = warped_vault()
REPORT = {
    "morty_scale": round(float(MORTY_SCALE), 3),
    "morty_height_mm": round(float(np.ptp(mv[:, 2])), 1),
    "cranium_mm": np.ptp(vault, axis=0).round(1).tolist(),
    "cranium_bp3d_mm": np.ptp(raw_vault, axis=0).round(1).tolist(),
    "pupils_mm": {"skeleton orbits": round(float(np.linalg.norm(eye["L"] - eye["R"])), 1),
                  "Morty": round(float(np.linalg.norm(eye["L"] - eye["R"])), 1),
                  "Mech": round(float(np.ptp([corners([bpy.data.objects[f"next {s} eyeball core:1"]]).mean(axis=0)[0]
                                              for s in "LR"])), 1)},
    "jawline_yz": np.round(hinge_yz, 1).tolist(),
    "morty_neck_z": round(float(neck_z), 1),  # his head's underside
    "morty_shoulder_z": round(float(tz[1]), 1),
    "morty_torso_half": round(float(MORTY_TORSO_HALF * MORTY_SCALE), 1),
    "morty_eye_r": round(float(r_eye), 1),
    "changes": CHANGES,
}  # fmt: skip
scene["report"] = json.dumps(REPORT)
print("build: report", json.dumps(REPORT), flush=True)
show(f"warped: least Jacobian {det:.2f}", [o for g in groups.values() for o in g], "front")

# --- the teaching skull's cut, its magnet pockets (#51's 4x2 discs), and the finish
cuts = collection("Cuts", helpers)
CUT_Z = float(t_glab[2] + CUT_ABOVE_BROW)
cut = box_obj("Calvaria cut", (-250, -400, CUT_Z), (250, 200, CUT_Z + 400), cuts)
cut.display_type, cut.hide_render = "WIRE", True
pockets = collection("Magnet pockets", cuts)
dg = bpy.context.evaluated_depsgraph_get()
ring = []
for o in skull_c.objects:
    me = o.evaluated_get(dg).to_mesh()
    w = np.array([o.matrix_world @ v.co for v in me.vertices])
    ring.append(w[np.abs(w[:, 2] - CUT_Z) < 1.5])
    o.evaluated_get(dg).to_mesh_clear()
ring = np.vstack(ring)
centre = ring.mean(axis=0)
for tag, ang in (("front", -90), ("back L", 45), ("back R", 135)):
    d = np.array((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0))
    rel = ring - centre
    pick = ring[np.argmax(rel @ d - 0.5 * np.linalg.norm(rel - np.outer(rel @ d, d), axis=1))]
    at = pick - d * 3.0
    me = bpy.data.meshes.new(f"magnet pocket {tag}")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=2.1, radius2=2.1, depth=4.6)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    ob.location = (at[0], at[1], CUT_Z)
    pockets.objects.link(ob)
    ob.display_type, ob.hide_render = "WIRE", True
carve_skull = collection("Carve (skull)", helpers)
carve_skull.children.link(carve)
carve_skull.children.link(pockets)


def finish_group(name, side, bones, carver, cut, limit=None):
    """The finish (docs/research/2026-11-03-skeleton-warp.md 3): the bones' SDF thickened (grow, then shrink: walls of
    at least 2 (grow - shrink)), the carve's SDF grown by the clearance taken out, cut at the calvaria's plane (side:
    0 none, 1 above, 2 below, a 0.4 mm seam), filleted, meshed at the zero level."""
    g = bpy.data.node_groups.new(name, "GeometryNodeTree")
    iface = g.interface
    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    socks = {}
    for n, t, d in (("Voxel", "NodeSocketFloat", 1.0),
                    ("Grow", "NodeSocketFloat", 1.25), ("Shrink", "NodeSocketFloat", 0.25),
                    ("Clearance", "NodeSocketFloat", 1.6), ("Fillet", "NodeSocketInt", 3),
                    ("Inset", "NodeSocketFloat", INSET)):  # fmt: skip
        socks[n] = iface.new_socket(n, in_out="INPUT", socket_type=t)
        if d is not None:
            socks[n].default_value = d
    N, L = g.nodes, g.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")

    def sdf(geo, band=6):
        m = N.new("GeometryNodeMeshToSDFGrid")
        L.new(geo, m.inputs["Mesh"])
        L.new(gi.outputs["Voxel"], m.inputs["Voxel Size"])
        m.inputs["Band Width"].default_value = band
        return m.outputs[0]

    def coll(collection):
        c = N.new("GeometryNodeCollectionInfo")
        c.transform_space = "RELATIVE"
        c.inputs["Collection"].default_value = collection
        c.inputs["Separate Children"].default_value = False
        r = N.new("GeometryNodeRealizeInstances")
        L.new(c.outputs[0], r.inputs[0])
        return r.outputs[0]

    def offset(grid, dist=None, sock=None, neg=False):
        o = N.new("GeometryNodeSDFGridOffset")
        L.new(grid, o.inputs["Grid"])
        if sock is not None:
            if neg:
                m = N.new("ShaderNodeMath")
                m.operation = "MULTIPLY"
                L.new(sock, m.inputs[0])
                m.inputs[1].default_value = -1.0
                sock = m.outputs[0]
            L.new(sock, o.inputs["Distance"])
        else:
            o.inputs["Distance"].default_value = dist
        return o.outputs[0]

    def boolean(a, b, op):
        n = N.new("GeometryNodeSDFGridBoolean")
        n.operation = op
        live = [s for s in n.inputs if s.enabled]
        if op == "DIFFERENCE":
            L.new(a, n.inputs["Grid 1"])
            L.new(b, n.inputs["Grid 2"])
        else:  # union and intersect take every grid in one multi-input socket
            multi = next(s for s in live if s.is_multi_input)
            L.new(a, multi)
            L.new(b, multi)
        return n.outputs[0]

    bone = offset(offset(sdf(coll(bones)), sock=gi.outputs["Grow"]), sock=gi.outputs["Shrink"], neg=True)
    f = N.new("GeometryNodeSDFGridFillet")  # rounded before the carve: its faces are interfaces, kept sharp
    L.new(bone, f.inputs["Grid"])
    L.new(gi.outputs["Fillet"], f.inputs["Iterations"])
    keep = offset(sdf(coll(carver)), sock=gi.outputs["Clearance"])
    out = boolean(f.outputs[0], keep, "DIFFERENCE")
    if limit is not None:  # inside Morty: his inner volume, the wall and the gap taken off
        li = N.new("GeometryNodeObjectInfo")
        li.transform_space = "RELATIVE"
        li.inputs["Object"].default_value = limit
        out = boolean(out, offset(sdf(li.outputs["Geometry"]), sock=gi.outputs["Inset"], neg=True), "INTERSECT")
    if side:
        oi = N.new("GeometryNodeObjectInfo")
        oi.transform_space = "RELATIVE"
        oi.inputs["Object"].default_value = cut
        c = sdf(oi.outputs["Geometry"])
        out = boolean(out, offset(c, -0.2), "INTERSECT") if side == 1 else boolean(out, offset(c, 0.2), "DIFFERENCE")
    m = N.new("GeometryNodeGridToMesh")
    L.new(out, m.inputs["Grid"])
    m.inputs["Threshold"].default_value = 0.0  # an SDF's surface (the node's default 0.1 is a density's)
    st = N.new("GeometryNodeSetMaterial")
    st.inputs["Material"].default_value = BONE
    L.new(m.outputs[0], st.inputs["Geometry"])
    L.new(st.outputs[0], go.inputs[0])
    return g


def hull_points(name, pts, coll):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


limit = morty  # Morty's inside, his wall and the gap off (the finish's Inset): the bones' outer limit
finished = collection("Finished (render only)", skeleton)
# the ribcage taller than the bed (256 mm, Bambu, inferred): split level at its middle, a 0.4 mm seam, like the calvaria
rib_z = float(np.mean(corners(groups["ribcage"])[:, 2]))
rib_cut = box_obj("Ribcage cut", (-250, -400, rib_z), (250, 200, rib_z + 400), cuts)
rib_cut.hide_render = True
pieces = [("Calvaria", skull_c, carve_skull, 1, cut), ("Face and skull base", skull_c, carve_skull, 2, cut),
          ("Mandible", mandible_c, carve, 0, cut), ("Ribcage upper", ribcage_c, carve, 1, rib_cut),
          ("Ribcage lower", ribcage_c, carve, 2, rib_cut)]  # fmt: skip
pieces += [(n, bpy.data.collections[n], carve, 0, cut) for n in NECK]
for name, src, cv, side, knife in pieces:
    ob = bpy.data.objects.new(f"finished {name}", bpy.data.meshes.new(f"finished {name}"))
    finished.objects.link(ob)
    mod = ob.modifiers.new("Finish", "NODES")
    mod.node_group = finish_group(f"Finish {name}", side, src, cv, knife, limit)
    mod.show_viewport = False  # the slow finish: render and export only (finish.py turns it on)

# cameras: front, side (from the L), 3/4; orthographic, on the bust
cams = collection("Cameras", helpers)
aim = Vector((0, -95, 15))
for name, d in (("front", (0, -1, 0)), ("side", (1, 0, 0)), ("3-4", (0.75, -1, 0.35))):
    cam = bpy.data.objects.new(f"camera {name}", bpy.data.cameras.new(name))
    cam.data.type, cam.data.ortho_scale, cam.data.clip_end = "ORTHO", 620.0, 5000.0
    cam.location = aim + Vector(d).normalized() * 1000
    cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()
    cams.objects.link(cam)
scene.camera = bpy.data.objects["camera front"]
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "OBJECT"
scene.display.shading.show_cavity = True
scene.render.resolution_x = scene.render.resolution_y = 1100
scene.render.film_transparent = False
txt = bpy.data.texts.new("rewarp.py")
txt.from_string(open(os.path.join(os.path.dirname(__file__), "rewarp.py")).read())
txt.use_fake_user = True

bpy.context.view_layer.layer_collection.children[helpers.name].hide_viewport = True


def save_without_morty(path):
    """The committed .blend never holds Morty (his sculpt is CC BY 4.0, local only): his objects unlinked and the
    finish's reference to him cleared while it saves, then put back in this window."""
    mortys = [o for o in bpy.data.objects if o.name.startswith("Morty")]
    refs = [n for g in bpy.data.node_groups for n in g.nodes
            if n.bl_idname == "GeometryNodeObjectInfo" and n.inputs["Object"].default_value in mortys]  # fmt: skip
    for n in refs:
        n.inputs["Object"].default_value = None
    homes = {o: list(o.users_collection) for o in mortys}
    for o, cs in homes.items():
        for c in cs:
            c.objects.unlink(o)
    # only the scene and what it uses: nothing orphaned (Morty's meshes) reaches the file
    bpy.data.libraries.write(os.path.abspath(path), {scene, *bpy.data.texts}, path_remap="NONE", compress=True)
    for o, cs in homes.items():
        for c in cs:
            c.objects.link(o)
    for n in refs:
        n.inputs["Object"].default_value = limit
    full.hide_set(True)


bpy.data.orphans_purge(do_recursive=True)
with bpy.context.temp_override(**view3d()):  # the window's own file: the full local copy, Morty in it (gitignored)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(TARGETS), "skeleton-with-morty.blend"),
                                compress=True)  # fmt: skip
save_without_morty(OUT)
show(f"saved {OUT} (without Morty)", [o for g in groups.values() for o in g] + [morty], "front")
open(os.path.abspath(OUT) + ".done", "w").write(f"{det} {err}\n")
