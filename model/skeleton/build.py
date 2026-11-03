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

GLB, BP3D, TARGETS, OUT = sys.argv[sys.argv.index("--") + 1 :][:4]
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
MAX_FACES = 6000  # each bone decimated to at most this: the light working copy (CI finishes from full resolution)
STANDIN_FACES = 4000  # each stand-in part, likewise
SKIN = ("next morty ", "next worn ", "eyeball cap")  # the Skin's nodes, hidden (Cansin, 2026-11-03)
SHELLS_KEPT = ("next morty face", "next morty hair", "next morty shirt front", "next morty shirt back",
               "next morty mouth cover")  # fmt: skip
CLEAR = 2.0  # each landmark target's room off what it clears (inferred)
SHELL_RGBA = (1.0, 0.72, 0.55, 0.3)  # the Morty Shells and eyeball caps, see-through (Cansin, 2026-11-03)
CUT_Z = 222.0  # the calvaria's cut, level, above the brow (inferred)


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
    if not c:
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
mech = collection("Mech stand-in")
carve = collection("Carve")
carve.children.link(mech)
keepouts = collection("Keep-outs", carve)
shells = collection("Morty Shells (reference)")
box = collection("Torso box (#854, replaced by the ribcage)")
with bpy.context.temp_override(**view3d()):
    bpy.ops.import_scene.gltf(filepath=GLB)
for ob in list(scene.objects):
    if ob.type != "MESH":
        bpy.data.objects.remove(ob)
        continue
    if ob.data.users > 1:
        ob.data = ob.data.copy()
    ob.data.transform(Matrix.Scale(1000.0, 4) @ ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    name = ob.name.removesuffix(":1")
    if name in ("next atlas", "next axis") or (name.startswith(SKIN) and not name.startswith(SHELLS_KEPT)):
        if "eyeball cap" in name:  # the caps front the eyes: cut round, shown see-through like the Shells
            decimate(ob, STANDIN_FACES)
            move(ob, mech)
            ob.color, ob.hide_render = SHELL_RGBA, True
        else:
            bpy.data.objects.remove(ob)
        continue
    if name.startswith(SHELLS_KEPT):
        move(ob, shells)
        ob.color, ob.hide_render = SHELL_RGBA, True
        continue
    decimate(ob, STANDIN_FACES)
    ob.data.materials.clear()
    ob.data.materials.append(STANDIN)
    ob.color = STANDIN.diffuse_color
    move(ob, box if name in ("next torso", "next torso lid") else mech)
bpy.context.view_layer.update()
scene.unit_settings.scale_length, scene.unit_settings.length_unit = 0.001, "MILLIMETERS"  # then 1 unit = 1 mm
bpy.context.view_layer.layer_collection.children[box.name].exclude = True
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
for ob in keepouts.objects:
    ob.display_type, ob.hide_render = "WIRE", True

# --- the bones, raw BodyParts3D
skeleton = collection("Skeleton")
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
    ob.color = BONE.diffuse_color
    return ob


skull_c, mandible_c = collection("Skull", skeleton), collection("Mandible", skeleton)
neck_c, ribcage_c = collection("Neck", skeleton), collection("Ribcage", skeleton)
groups["skull"] = [load(n, f, skull_c) for n, f in SKULL.items()] + [load(n, f, mandible_c) for n, f in MANDIBLE.items()]
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
    ob.color = BONE.diffuse_color
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
poses = collection("Poses")


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
eye = {s: np.array(T["eyes"][s]) for s in "LR"}
s_skull = np.linalg.norm(eye["L"] - eye["R"]) / np.linalg.norm(sclera["L"] - sclera["R"])  # interorbital to the eyes'
c_skull = (sclera["L"] + sclera["R"]) / 2
# the skull's pose: across, the eyes' spacing; front to back and up, Morty's head (glabella to opisthocranion, the
# orbits to the vertex, inside the hair and face Shells), so the warp is left the regional changes
head = corners([o for o in shells.objects if "hair" in o.name or "face" in o.name])
hlo, hhi = np.min(head, axis=0) + 1.6 + CLEAR + 2.0, np.max(head, axis=0) - 1.6 - CLEAR - 2.0
lids = corners([o for o in mech.objects if " upper lid" in o.name])
brow, front = lids[:, 2].max() + CLEAR + 6.0, lids[:, 1].min() + 3.0
raw = {o.name: verts(o) for o in groups["skull"]}
fr = raw["frontal bone"]
fr = fr[(np.abs(fr[:, 0]) < 5) & (fr[:, 2] > c_skull[2] + 10) & (fr[:, 2] < c_skull[2] + 40)]
glabella, opisthocranion = fr[np.argmin(fr[:, 1])], raw["occipital bone"][np.argmax(raw["occipital bone"][:, 1])]
top = np.vstack(list(raw.values()))
top = top[np.argmax(top[:, 2])]
sk_y = (hhi[1] - front) / (opisthocranion[1] - glabella[1])
sk_z = (hhi[2] - eye["L"][2]) / (top[2] - c_skull[2])
pose("skull", c_skull, (eye["L"] + eye["R"]) / 2, (s_skull, sk_y, sk_z))
print(f"build: skull pose scale {s_skull:.3f} {sk_y:.3f} {sk_z:.3f}")

# the neck: C1's top under the tilt lugs, C7 on T1 at the Shirt's top; each canal on the post (x 0, the pan axis)
tilt = np.array(T["tilt"])
neck_top, neck_bottom = tilt[2] - 3.5 - 1.6 - 1.0, T["lid_top"] + 5.0  # under the lugs (BOSS_R, clearance); on T1
zs = {n: (verts(groups[n][0])[:, 2].min(), verts(groups[n][0])[:, 2].max()) for n in NECK}
z_hi, z_lo = zs["C1"][1], zs["C7"][0]
s_z = (neck_top - neck_bottom) / (z_hi - z_lo)
S_XY = 0.85  # their width (inferred): the canals opened round the post by the carve


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


for n in NECK:
    v = verts(groups[n][0])
    cx, cy = canal(v)
    cz = v[:, 2].mean()
    pose(n, (cx, cy, cz), (tilt[0], tilt[1], neck_bottom + (cz - z_lo) * s_z), (S_XY, S_XY, s_z))

# the ribcage: its box into the Shirt's inside, on the Torso's floor (the squash: a loop topic, Cansin to confirm)
shell_box = corners([o for o in shells.objects if "shirt" in o.name])
lo, hi = np.min(shell_box, axis=0) + (3.6, 3.6, 0), np.max(shell_box, axis=0) - (3.6, 3.6, 0)
lo[2], hi[2] = T["floor"][1][2] + 0.5, T["lid_top"] + 5.0
v = stack("ribcage")
src_lo, src_hi = v.min(axis=0), v.max(axis=0)
pose("ribcage", (src_lo + src_hi) / 2, (lo + hi) / 2, (hi - lo) / (src_hi - src_lo))
bpy.context.view_layer.update()
show("bones posed (scale, rotation, offset per group)", [o for g in groups.values() for o in g], "front")

# --- landmarks: each a source empty on the anatomy (riding its group's pose) and a target in the Mech
marks = collection("Landmarks")


def landmark(name, group, src, target=None):
    e = empty(f"LM {name}", marks, "SPHERE", 1.5)
    e.parent = groups[group][0].parent
    e.matrix_parent_inverse = groups[group][0].matrix_parent_inverse
    e.location = Vector(src)
    bpy.context.view_layer.update()
    t = empty(f"LM {name} target", marks, "PLAIN_AXES", 4.0)
    t.location = Vector(world(group, src) if target is None else target)


def lid(side, part):
    return corners([o for o in mech.objects if o.name.startswith(f"next {side} {part}")])


bones_skull = {o.name: verts(o) for o in groups["skull"]}
allv = np.vstack(list(bones_skull.values()))
faces = []
off = 0
for o in groups["skull"]:
    faces += [[off + i for i in p.vertices] for p in o.data.polygons]
    off += len(o.data.vertices)
bvh = BVHTree.FromPolygons([Vector(p) for p in allv], faces)
for s, sx in (("L", 1), ("R", -1)):
    landmark(f"{s} orbit", "skull", sclera[s], eye[s])
    up = max(p[2] for p in lid(s, "upper lid")) - eye[s][2] + CLEAR
    down = eye[s][2] - min(p[2] for p in lid(s, "lower lid")) + CLEAR
    lateral = max(abs(p[0]) for p in lid(s, "lower lid")) - abs(eye[s][0]) + CLEAR
    medial = abs(eye[s][0]) - 2.5  # the walls between the orbits meet at the midline: a loop topic (Cansin to confirm)
    for d, r, tag in (((0, 0, 1), up, "up"), ((0, 0, -1), down, "down"), ((sx, 0, 0), lateral, "lateral"),
                      ((-sx, 0, 0), medial, "medial")):  # fmt: skip
        hit = bvh.ray_cast(Vector(sclera[s]), Vector(d))[0]
        if hit is None:
            continue
        hit = np.array(hit)
        t = eye[s] + np.array(d) * r
        t[1] = eye[s][1] + (hit[1] - sclera[s][1]) * sk_y
        landmark(f"{s} orbit rim {tag}", "skull", hit, t)

md = bones_skull["mandible"]
back = md[md[:, 1] > np.median(md[:, 1])]
for (s, sx), h in zip((("L", 1), ("R", -1)), T["hinge"]):
    side = back[back[:, 0] * sx > 20]
    landmark(f"{s} condyle", "skull", side[side[:, 2] > side[:, 2].max() - 3].mean(axis=0), h)
    gon = side[np.argmax(side[:, 1] - side[:, 2])]
    landmark(f"{s} gonion", "skull", gon, (sx * 36.0, h[1] - 2.0, h[2] - 29.0))
occ = bones_skull["occipital bone"]
low = occ[occ[:, 2] < occ[:, 2].min() + 4]
for s, sx in (("L", 1), ("R", -1)):
    c = low[low[:, 0] * sx > 0].mean(axis=0)
    landmark(f"{s} occipital condyle", "skull", c, (s_skull * (c[0] - c_skull[0]), tilt[1], tilt[2] + 2.0))
ch = md[np.abs(md[:, 0]) < 5]
landmark("menton", "skull", ch[np.argmin(ch[:, 2])], T["chin"])
mx = np.vstack([bones_skull["L maxilla"], bones_skull["R maxilla"]])
mx = mx[np.abs(mx[:, 0]) < 4]
landmark("prosthion", "skull", mx[np.argmin(mx[:, 2])], (0.0, T["chin"][1] + 2.0, T["hinge"][0][2] - 24.0))
landmark("glabella", "skull", glabella, (0.0, front, brow))

# the cranium up to the inside of Morty's head (the hair and face Shells), CLEAR off their 1.6 mm wall
landmark("vertex", "skull", top, (0.0, (hlo[1] + hhi[1]) / 2 + 5.0, hhi[2]))
landmark("opisthocranion", "skull", opisthocranion, (0.0, hhi[1], eye["L"][2] + 15.0))
par = np.vstack([bones_skull[n] for n in ("L parietal bone", "R parietal bone", "L temporal bone", "R temporal bone")])
zy = np.vstack([bones_skull[n] for n in ("L zygomatic bone", "R zygomatic bone")])
for s, sx in (("L", 1), ("R", -1)):
    p = par[par[:, 0] * sx > 0]
    landmark(f"{s} euryon", "skull", p[np.argmax(np.abs(p[:, 0]))], (sx * (hhi[0] - 2.0), -112.0, eye[s][2] + 20.0))
    z = zy[zy[:, 0] * sx > 0]
    landmark(f"{s} zygion", "skull", z[np.argmax(np.abs(z[:, 0]))], (sx * (hhi[0] - 6.0), -140.0, eye[s][2] - 18.0))

# anchors: the neck and the ribcage are posed to fit, so their landmarks start on their targets
for n in NECK:
    v = verts(groups[n][0])
    for i, p in enumerate((v[np.argmin(v[:, 0])], v[np.argmax(v[:, 0])], v[np.argmin(v[:, 1])], v[np.argmax(v[:, 1])])):
        landmark(f"{n} anchor {i}", n, p)
v = stack("ribcage")
mid = (v.min(axis=0) + v.max(axis=0)) / 2
for i, c in enumerate(np.array(np.meshgrid([-1, 1], [-1, 1], [-1, 1])).T.reshape(-1, 3)):
    landmark(f"ribcage anchor {i}", "ribcage", mid + c * (v.max(axis=0) - v.min(axis=0)) * 0.4)
landmark("ribcage anchor centre", "ribcage", mid)
# the frame: fixed points round the bust, so the warp never extrapolates
for i, c in enumerate(np.array(np.meshgrid([-300, 300], [-450, 250], [-250, 550])).T.reshape(-1, 3)):
    empty(f"LM frame {i}", marks, "CUBE", 5.0).location = Vector(c)
bpy.context.view_layer.update()

# --- the warp
det, err = rewarp.rewarp()
show(f"warped: least Jacobian {det:.2f}", [o for g in groups.values() for o in g], "front")

# --- the teaching skull's cut, its magnet pockets (#51's 4x2 discs), and the finish
cuts = collection("Cuts")
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
for c in (keepouts, cuts):
    lc = bpy.context.view_layer.layer_collection
    for part in ([carve.name, keepouts.name] if c is keepouts else [cuts.name]):
        lc = lc.children[part]
    lc.hide_viewport = True  # helpers: hidden, they would fill the view (still evaluated by the finish)
carve_skull = collection("Carve (skull)")
carve_skull.children.link(carve)
carve_skull.children.link(pockets)
for c in (carve_skull,):
    bpy.context.view_layer.layer_collection.children[c.name].exclude = True


def finish_group(name, side, bones, carver, cut):
    """The finish (docs/research/2026-11-03-skeleton-warp.md 3): the bones' SDF thickened (grow, then shrink: walls of
    at least 2 (grow - shrink)), the carve's SDF grown by the clearance taken out, cut at the calvaria's plane (side:
    0 none, 1 above, 2 below, a 0.4 mm seam), filleted, meshed at the zero level."""
    g = bpy.data.node_groups.new(name, "GeometryNodeTree")
    iface = g.interface
    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    socks = {}
    for n, t, d in (("Voxel", "NodeSocketFloat", 1.0),
                    ("Grow", "NodeSocketFloat", 1.25), ("Shrink", "NodeSocketFloat", 0.25),
                    ("Clearance", "NodeSocketFloat", 1.6), ("Fillet", "NodeSocketInt", 3)):  # fmt: skip
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
    keep = offset(sdf(coll(carver)), sock=gi.outputs["Clearance"])
    out = boolean(bone, keep, "DIFFERENCE")
    if side:
        oi = N.new("GeometryNodeObjectInfo")
        oi.transform_space = "RELATIVE"
        oi.inputs["Object"].default_value = cut
        c = sdf(oi.outputs["Geometry"])
        out = boolean(out, offset(c, -0.2), "INTERSECT") if side == 1 else boolean(out, offset(c, 0.2), "DIFFERENCE")
    f = N.new("GeometryNodeSDFGridFillet")
    L.new(out, f.inputs["Grid"])
    L.new(gi.outputs["Fillet"], f.inputs["Iterations"])
    m = N.new("GeometryNodeGridToMesh")
    L.new(f.outputs[0], m.inputs["Grid"])
    m.inputs["Threshold"].default_value = 0.0  # an SDF's surface (the node's default 0.1 is a density's)
    st = N.new("GeometryNodeSetMaterial")
    st.inputs["Material"].default_value = BONE
    L.new(m.outputs[0], st.inputs["Geometry"])
    L.new(st.outputs[0], go.inputs[0])
    return g


finished = collection("Finished (render only)")
pieces = [("Calvaria", skull_c, carve_skull, 1), ("Face and skull base", skull_c, carve_skull, 2),
          ("Mandible", mandible_c, carve, 0), ("Ribcage", ribcage_c, carve, 0)]  # fmt: skip
pieces += [(n, bpy.data.collections[n], carve, 0) for n in NECK]
for name, src, cv, side in pieces:
    ob = bpy.data.objects.new(f"finished {name}", bpy.data.meshes.new(f"finished {name}"))
    finished.objects.link(ob)
    mod = ob.modifiers.new("Finish", "NODES")
    mod.node_group = finish_group(f"Finish {name}", side, src, cv, cut)
    mod.show_viewport = False  # the slow finish: render and export only (finish.py turns it on)

# cameras: front, side (from the L), 3/4; orthographic, on the bust
cams = collection("Cameras")
aim = Vector((0, -100, 125))
for name, d in (("front", (0, -1, 0)), ("side", (1, 0, 0)), ("3-4", (0.75, -1, 0.35))):
    cam = bpy.data.objects.new(f"camera {name}", bpy.data.cameras.new(name))
    cam.data.type, cam.data.ortho_scale, cam.data.clip_end = "ORTHO", 290.0, 5000.0
    cam.location = aim + Vector(d).normalized() * 1000
    cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()
    cams.objects.link(cam)
scene.camera = bpy.data.objects["camera front"]
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "MATERIAL"
scene.display.shading.show_cavity = True
scene.render.resolution_x = scene.render.resolution_y = 1100
scene.render.film_transparent = False
txt = bpy.data.texts.new("rewarp.py")
txt.from_string(open(os.path.join(os.path.dirname(__file__), "rewarp.py")).read())
txt.use_fake_user = True

with bpy.context.temp_override(**view3d()):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=True)
show(f"saved {OUT}", [o for g in groups.values() for o in g], "3/4")
open(os.path.abspath(OUT) + ".done", "w").write(f"{det} {err}\n")
