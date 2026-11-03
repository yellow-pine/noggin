"""PROTOTYPE (#872 step 3): the Mech fitted into the warped skeleton and Morty, as Cansin re-grilled it (2026-11-04),
headless after build.py in the same Blender (`-b ... --python build.py --python stage3.py -- <args>`):

- the eyes on Morty's pupils at his eye's size, the frame stretched to them, its beam behind the maxilla;
- the jaw inside the mandible on his jawline; the tilt at C0/C1, its servo riding C1 inside the skull base;
- the pan at C1/C2: a bare servo upright in place of C5-C6, a shaft up C4-C2's canals turning C1 and the head;
- the base: T1..Tn, n the least that holds #865's contents, cut by one plane under rib n with Morty, a floor plate
  inside the ring the foot;
- Morty a classic bust in the "cansin" Skin palette, the bones in the "anatomical" Skeleton palette;
- the review (the finish at a coarse pitch), the head's weight against the 5 V servo and the foot, and the saves:
  Cansin's Desktop file (with Morty) and the committed .blend (without him).

Printed parts scale; bought ones (servos, horns, boards, packs, the dongle) keep their size. Every size inferred.
args (after build.py's five): <Desktop .blend> [voxel mm]"""

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
from scipy.spatial import Delaunay

A = sys.argv[sys.argv.index("--") + 1 :]
TARGETS, OUT, DESKTOP = A[2], A[3], A[5]
VOXEL = float(A[6]) if len(A) > 6 else 1.5
T = json.load(open(TARGETS))
BUILD = os.path.dirname(os.path.abspath(TARGETS))
scene = bpy.context.scene
report = json.loads(scene["report"])
BOUGHT = ("servo", "horn", "Core", "Shield", "pack", "switch board", "dongle", "bearing", "spring")
CLEAR, WALL, GAP = 1.6, 2.0, 2.0
CAP_R, UPPER_LID_R, LOWER_LID_R = 27.0, (28.5, 30.0), (31.5, 33.5)  # gimbal.CAP_R, LID_R, LOWER_R
H_NEED = 42.0  # the stacked packs (2 x 16.3) and their gap, on the floor plate, with room (inferred)
BED = 256.0  # Bambu's bed, each axis (inferred)
BOUGHT_G = {
    "tilt servo": 55.0,
    "bearing": 4.0,
    "spring": 3.0,
    "servo": 9.0,
    "horn": 1.0,
    "Core": 6.0,
    "Shield": 8.0,
    "pack": 45.0,
    "switch board": 5.0,
    "dongle": 10.0,
}
SHELL_MM, INFILL = 1.2, 0.15  # printed: three 0.4 mm perimeters, 15 % infill (inferred)
changes, review = [], {}


def ob(name):
    return bpy.data.objects.get(name) or bpy.data.objects[name + ":1"]


def pts(o):
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = np.array(o.matrix_world)
    v = np.array([x.co[:] for x in ev.data.vertices]).reshape(-1, 3)
    return v @ m[:3, :3].T + m[:3, 3]


def centre(o):
    v = pts(o)
    return (v.min(axis=0) + v.max(axis=0)) / 2


def bought(name):
    return any(k in name for k in BOUGHT)


def update():
    bpy.context.view_layer.update()


def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in [x.name for x in (parent or scene.collection).children]:
        (parent or scene.collection).children.link(c)
    return c


def relink(o, c, keep=("Carve parts", "Keep-outs")):
    for x in list(o.users_collection):
        if x.name not in keep:
            x.objects.unlink(o)
    if o.name not in c.objects:
        c.objects.link(o)


update()  # a loaded file's matrices are stale until the depsgraph runs (build.py moved parts without one)
helpers = bpy.data.collections["helpers"]
retired = coll("Retired (replaced in step 3)", helpers)
mech = {o.name.removesuffix(":1"): o for o in bpy.data.collections["Mech"].all_objects}
for o in bpy.data.collections["Carve parts"].objects:
    if "eyeball cap" in o.name:
        mech[o.name.removesuffix(":1")] = o
keep = {o.name: o for o in bpy.data.collections["Keep-outs"].objects}
carve_parts = bpy.data.collections["Carve parts"]


def scale_about(names, at, k):
    at = Vector(at)
    for n in names:
        o = mech[n]
        if bought(n):
            c = Vector(centre(o))
            o.location += (at + (c - at) * k) - c
        else:
            o.matrix_world = Matrix.Translation(at) @ Matrix.Scale(k, 4) @ Matrix.Translation(-at) @ o.matrix_world
    update()


def skel(names):
    return np.vstack([pts(bpy.data.objects[n]) for n in names])


def box_mesh(bm, lo, hi):
    lo, hi = Vector(lo), Vector(hi)
    r = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.LocRotScale((lo + hi) / 2, None, hi - lo), verts=r["verts"])


def cylinder_mesh(bm, a, b, r, seg=24):
    a, b = Vector(a), Vector(b)
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=(b - a).length)
    rot = Vector((0, 0, 1)).rotation_difference((b - a).normalized()).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ rot, verts=res["verts"])


def new_part(name, build, coll_to):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll_to.objects.link(o)
    return o


def servo_mesh(bm, m):
    """The 9 g servo's envelope (model/envelopes.py SERVO, its frame: the spline down -z) moved by the 4x4 m."""
    s = T["servo"]
    sub = bmesh.new()
    box_mesh(sub, *zip(*s["case"]))
    box_mesh(sub, *zip(*s["tabs"]))
    (bx0, bx1) = (min(u - r for u, _, r in ((16.69, 5.9, 5.4), (11.7, 5.9, 3.8))), 16.69 + 5.4)
    box_mesh(sub, (bx0, 0.5, s["boss_z"][0]), (bx1, 11.3, s["boss_z"][1]))
    sx, sy = s["shaft"]
    cylinder_mesh(sub, (sx, sy, s["tip_z"]), (sx, sy, s["boss_z"][0]), s["spline_r"])
    bmesh.ops.transform(sub, matrix=m, verts=sub.verts[:])
    tmp = bpy.data.meshes.new("tmp")
    sub.to_mesh(tmp)
    sub.free()
    bm.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)


# ---------------------------------------------------------------------------------------------------- 1. the eyes
eyes = {s: centre(mech[f"next {s} eyeball core"]) for s in "LR"}
mid = (eyes["L"] + eyes["R"]) / 2
r_morty = report["morty_eye_r"]
k_x = np.linalg.norm(eyes["L"] - eyes["R"]) / np.linalg.norm(np.subtract(T["eyes"]["L"], T["eyes"]["R"]))
# round 2 (Cansin): the eye from Morty's own: the eyeball's cap his eye's sphere, the lids 1 mm off it, their rest
# edges where his outline is (build.py measured it every 30 deg)
k_ball = r_morty / CAP_R
outline = report["morty_eye_outline_mm"]
BALL = ("eyeball core", "eyeball cap", "yaw yoke", "push-rod", "lid bar", "lid link", "lid servo", "lid horn")
for s_ in "LR":
    scale_about([f"next {s_} {p}" for p in BALL if f"next {s_} {p}" in mech], eyes[s_], k_ball)
    for lid, inner_r in (("upper lid", UPPER_LID_R[0]), ("lower lid", LOWER_LID_R[0])):
        scale_about([f"next {s_} {lid}"], eyes[s_], (r_morty + 1.0) / inner_r)
edges = {s_: (math.degrees(math.asin(min(outline[s_][3] / r_morty, 1))),
              math.degrees(math.asin(min(outline[s_][9] / r_morty, 1)))) for s_ in "LR"}  # fmt: skip
S = Matrix.Diagonal((k_x, k_ball, k_ball, 1.0))
FRAME = ("next gimbal frame", "next bail", "next tie-bar", "next pitch bar", "next pitch horn", "next pitch servo",
         "next yaw horn", "next yaw servo", "next cranium tray", "next Core 1", "next Core 2", "next Shield 1",
         "next Shield 2")  # fmt: skip


def stretch_point(c):
    return Vector(mid) + (S @ (Vector(c) - Vector(mid)).to_4d()).to_3d()


for n in FRAME:
    o = mech[n]
    if bought(n):
        c = Vector(centre(o))
        o.location += stretch_point(c) - c
    else:
        o.matrix_world = Matrix.Translation(Vector(mid)) @ S @ Matrix.Translation(-Vector(mid)) @ o.matrix_world
for n in ("keep USB-C next Core 1", "keep USB-C next Core 2", "keep next Core 1:1", "keep next Core 2:1",
          "keep next Shield 1:1", "keep next Shield 2:1"):  # fmt: skip
    c = Vector(centre(keep[n]))
    keep[n].location += stretch_point(c) - c
update()
changes.append(
    f"Eyes, from Morty's own (his sculpt at x{report['morty_scale']}): his eye a {r_morty:.1f} mm sphere, its outline "
    f"{min(outline['L']):.0f}-{max(outline['L']):.0f} mm round about its centre (every 30 deg: {outline['L']}), his "
    f"pupil a flat about 8.5 mm round at its apex (his sculpt's depth, inferred); each eyeball core, cap, yaw yoke, push-rod, lid bar and link "
    f"x{k_ball:.2f} about its centre so the cap is his eye's sphere ({r_morty:.1f}); each lid scaled to ride 1 mm off "
    f"it (upper x{(r_morty + 1) / UPPER_LID_R[0]:.2f}, lower x{(r_morty + 1) / LOWER_LID_R[0]:.2f}), their rest edges "
    f"set where his outline is: the upper {edges['L'][0]:.0f} deg over the gaze, the lower {edges['L'][1]:.0f} under "
    f"(the lid drive's rest angles follow, in model/gimbal.py); the eyes on his pupils "
    f"({np.linalg.norm(eyes['L'] - eyes['R']):.1f} mm apart, was 52); the lid servos and horns keep their size"
)
changes.append(
    f"Gimbal frame, bail, tie-bar, pitch bar and cranium tray: x{k_x:.2f} across (to the pupils), x{k_ball:.2f} front "
    f"to back and up; the pitch and yaw servos and horns and the Cores and Shields on the tray ride their mounts"
)

# ------------------------------------------------------------------ 2. the frame's beam behind the maxilla's face
skull_bones = list(bpy.data.collections["Skull"].objects)
sv, sf, off = [], [], 0
for o in skull_bones:
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = o.matrix_world
    sv += [m @ v.co for v in ev.data.vertices]
    sf += [[off + i for i in p.vertices] for p in ev.data.polygons]
    off += len(ev.data.vertices)
skull_bvh = BVHTree.FromPolygons(sv, sf)
frame = mech["next gimbal frame"]
fm = frame.matrix_world
bm = bmesh.new()
bm.from_mesh(frame.data)
proud, need = [], 0.0
for f in bm.faces:
    c = fm @ f.calc_center_median()
    if min((c - Vector(e)).length for e in eyes.values()) < r_morty + 6.0:
        continue  # in an orbit: a natural opening
    hit = skull_bvh.ray_cast(Vector((c.x, c.y - 600, c.z)), Vector((0, 1, 0)))[0]
    if hit is not None and c.y < hit.y - 0.5:
        proud.append(f)
        need = max(need, hit.y - c.y + CLEAR + WALL)
if proud:
    beam_bm = bmesh.new()
    beam_bm.from_mesh(frame.data)
    keep_idx = {f.index for f in proud}
    bmesh.ops.delete(beam_bm, geom=[f for f in beam_bm.faces if f.index not in keep_idx], context="FACES")
    bmesh.ops.delete(bm, geom=proud, context="FACES")
    for b in (bm, beam_bm):  # closed again: an open mesh's distance field floods (the finish ran out of memory)
        bmesh.ops.holes_fill(b, edges=[e for e in b.edges if e.is_boundary], sides=0)
        bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
    bm.to_mesh(frame.data)
    beam = bpy.data.objects.new("next gimbal frame beam", bpy.data.meshes.new("next gimbal frame beam"))
    beam_bm.to_mesh(beam.data)
    beam_bm.free()
    beam.matrix_world = Matrix.Translation((0, need, 0)) @ fm
    bpy.data.collections["Mech"].objects.link(beam)
    carve_parts.objects.link(beam)
    mech["next gimbal frame beam"] = beam
    changes.append(
        f"Gimbal frame's front beam: the {len(proud)} faces of it that stood proud of the maxilla, outside the orbits, "
        f"split off and moved {need:.1f} mm back, inside the face's bone (carved round), the lid uprights reaching "
        f"back to it: the mechanism shows only through the orbits"
    )
bm.free()
update()

# -------------------------------------------------------------------------------- 3. the jaw inside the mandible
hinge = np.array((0.0, *report["jawline_yz"]))
mand = skel(["mandible"])
inner = np.abs(mand[(mand[:, 2] > hinge[2] - 40) & (mand[:, 2] < hinge[2] - 10)][:, 0]).max() - 9.0 - CLEAR
k_jaw = inner / 37.0
scale_about(["next jaw", "next jaw bar", "next mouth horn", "next mouth servo"], hinge, k_jaw)
changes.append(
    f"Jaw: x{k_jaw:.2f} about its hinge, its arms inside the mandible's rami (inner faces at x ±{inner + CLEAR:.0f}); "
    f"the hinge on Morty's jawline and the condyles (y {hinge[1]:.1f}, z {hinge[2]:.1f}, was y -124, z 153); the "
    f"mouth servo and horn keep their size"
)

# -------------------------------------------------------------------- 4. the neck: tilt at C0/C1, pan at C1/C2
vz = {n: pts(ob(n))[:, 2] for n in ("C1", "C2", "C3", "C4", "C5", "C6", "C7")}
vc = {n: (z.min() + z.max()) / 2 for n, z in vz.items()}
canal = {n: np.array(bpy.data.objects[f"pose {n}"].matrix_world.translation) for n in vz}
occ = skel(["occipital bone"])
oc = occ[occ[:, 2] < occ[:, 2].min() + 4].mean(axis=0)
tilt = np.array((0.0, oc[1], oc[2] - 3.0))
d_tilt = tilt - np.array(T["tilt"])
mech["next head mount"].location += Vector(d_tilt)
update()
changes.append(
    f"Tilt at C0/C1: the head mount moved {np.round(d_tilt, 1)} mm, its tilt axis under the occipital condyles "
    f"(y {tilt[1]:.1f}, z {tilt[2]:.1f}); it bears on C1's lateral masses (C1 carries the tilt lugs)"
)
# round 2 (Cansin): the neck all anatomical, C1-C7; both servos in the skull base. The order: neck, then tilt at C0/C1
# (the real joint: the occipital condyles sit on C1's facets, no height under them for a pan stage), then pan above it
# inside the skull, its axis tilting with the head (Cansin: acceptable) and set through the head's centre of mass, so
# gravity never turns it however the head tilts
for n in ("next neck mount", "next pan yoke", "next pan horn", "next pan bar", "next pan servo", "next tilt servo",
          "next tilt horn", "next tilt bar"):  # fmt: skip
    relink(mech.pop(n), retired, keep=())


def grams_of(o):
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    b = bmesh.new()
    b.from_mesh(ev.data)
    b.transform(o.matrix_world)
    area, vol = sum(f.calc_area() for f in b.faces), abs(b.calc_volume())
    com = np.mean([v.co[:] for v in b.verts], axis=0)
    b.free()
    if bought(o.name):
        return next((g for k, g in BOUGHT_G.items() if k in o.name), 5.0), com
    shell = min(area * 1.2, vol)
    return T["petg_g_cm3"] * (shell + 0.15 * (vol - shell)) / 1000.0, com


head_objs = [o for n, o in mech.items() if "eyeball cap" not in n]
head_objs += list(bpy.data.collections["Skull"].objects) + list(bpy.data.collections["Mandible"].objects)
ms = [grams_of(o) for o in head_objs]
head_com = sum(m * c for m, c in ms) / sum(m for m, _ in ms)
c1v = pts(ob("C1"))
c1_top = c1v[:, 2].max()
pan_axis = np.array((0.0, head_com[1], 0.0))  # x 0, under the head's centre of mass
PLATE = (56.0, 5.0)  # the nod plate's width across, its thickness (inferred)
pz0 = max(c1_top, tilt[2] + 6.0) + 1.0  # its underside, clear of C1's top
y0p, y1p = min(tilt[1], pan_axis[1]) - 12.0, max(tilt[1], pan_axis[1]) + 12.0


def nod_plate(bm):
    box_mesh(bm, (-PLATE[0] / 2, y0p, pz0), (PLATE[0] / 2, y1p, pz0 + PLATE[1]))
    for sx_ in (-1, 1):  # its knuckles down onto the tilt axis, beside C1's lateral masses
        x = sx_ * 22.0
        box_mesh(bm, (x - 4, tilt[1] - 5, tilt[2]), (x + 4, tilt[1] + 5, pz0))
        cylinder_mesh(bm, (x - 4, tilt[1], tilt[2]), (x + 4, tilt[1], tilt[2]), 5.0)


plate = new_part("next nod plate", nod_plate, bpy.data.collections["Mech"])
BEARING = (8.0, 16.0, 5.0)  # F8-16M thrust bearing: bore, outside, height (its maker's catalogue)
bz = pz0 + PLATE[1]
bearing = new_part("next F8-16M thrust bearing", lambda bm: cylinder_mesh(bm, (0, pan_axis[1], bz),
                   (0, pan_axis[1], bz + BEARING[2]), BEARING[1] / 2), bpy.data.collections["Mech"])  # fmt: skip
d_head = Vector((0.0, pan_axis[1], bz + BEARING[2])) - Vector(centre(mech["next head mount"]))
d_head.z += np.ptp(pts(mech["next head mount"])[:, 2]) / 2
mech["next head mount"].location += d_head
s = T["servo"]
sx, sy = s["shaft"]
flip = Matrix.Rotation(math.pi, 4, "X")  # the 9 g pan servo upright on the plate, its spline up into the head mount
spline_at = flip @ Vector((sx, sy, s["tip_z"]))
case_bottom = (flip @ Vector((0, 0, s["case"][2][1]))).z
m_pan = Matrix.Translation((-spline_at.x, pan_axis[1] - spline_at.y, bz - case_bottom)) @ flip
pan_servo = new_part("next pan servo", lambda bm: servo_mesh(bm, m_pan), bpy.data.collections["Mech"])
# the tilt servo: a standard-size metal-gear servo (~10 kgf.cm at 5 V, e.g. the MG996R class; its envelope inferred:
# case 40.7 x 19.7 x 37, tabs to 54.5, the spline 10 mm in from one end), on the plate's +x end, its spline on the
# tilt axis into a lever on C1's lateral mass: it nods the plate and the head about C0/C1
STD = {"case": (40.7, 19.7, 37.0), "tabs": (54.5, 2.5, 27.0), "spline": (10.0, 3.0, 4.0)}


def std_servo(bm, m):
    sub = bmesh.new()
    L, W, H = STD["case"]
    box_mesh(sub, (0, 0, 0), (L, W, H))
    box_mesh(sub, ((L - STD["tabs"][0]) / 2, 0, STD["tabs"][2]), ((L + STD["tabs"][0]) / 2, W, STD["tabs"][2] + 2.5))
    cylinder_mesh(sub, (STD["spline"][0], W / 2, H), (STD["spline"][0], W / 2, H + STD["spline"][2]), STD["spline"][1])
    bmesh.ops.transform(sub, matrix=m, verts=sub.verts[:])
    tmp = bpy.data.meshes.new("tmp")
    sub.to_mesh(tmp)
    sub.free()
    bm.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)


# its spline along -x onto the tilt axis at x +26, the case outboard, lying with its length along y and its width
# upright, so it stays inside the skull base (stood on end it hung below the occiput beside C1)
m_tilt = (
    Matrix.Translation((26.0, tilt[1], tilt[2]))
    @ Matrix.Rotation(-math.pi / 2, 4, "X")  # its length back from the spline, clear of the L condyle in front
    @ Matrix.Rotation(-math.pi / 2, 4, "Y")
    @ Matrix.Translation((-STD["spline"][0], -STD["case"][1] / 2, -(STD["case"][2] + STD["spline"][2])))
)
tilt_servo = new_part("next tilt servo", lambda bm: std_servo(bm, m_tilt), bpy.data.collections["Mech"])
spring = new_part("next tilt balance spring", lambda bm: cylinder_mesh(bm, (-34, tilt[1], tilt[2]),
                  (-26, tilt[1], tilt[2]), 8.0), bpy.data.collections["Mech"])  # fmt: skip
for o in (plate, bearing, pan_servo, tilt_servo, spring):
    carve_parts.objects.link(o)
    mech[o.name] = o
update()
changes.append(
    "Neck: all anatomical, C1-C7, real vertebrae, no servo or post in the column; the neck mount, the pan yoke and its "
    "post, the pan horn and bar, and the tilt horn and bar go. The pack's lead climbs the cervical canal"
)
changes.append(
    f"Order: neck, then tilt at C0/C1, then pan inside the skull. The occipital condyles sit on C1's facets, with no "
    f"height under them for a pan stage, so the tilt is the real C0/C1 joint; the pan rides above it and its axis "
    f"tilts with the head (Cansin: acceptable), set through the head's centre of mass (y {pan_axis[1]:.0f}, "
    f"{abs(pan_axis[1] - tilt[1]):.0f} mm in front of the tilt axis), so gravity never turns it"
)
changes.append(
    f"Nod plate (Joints, printed): {PLATE[0]:.0f} x {y1p - y0p:.0f} x {PLATE[1]:.0f} mm in the skull base over C1, its "
    f"two knuckles hinged on the tilt axis beside C1's lateral masses (y {tilt[1]:.1f}, z {tilt[2]:.1f}); the head "
    f"bears on it through an F8-16M thrust bearing (new, bought) on the pan axis; the head mount moved onto the bearing"
)
changes.append(
    "Pan servo: the 9 g servo upright on the nod plate, its spline up the pan axis into the head mount: it turns the "
    "head on the bearing"
)
changes.append(
    "Tilt servo: a standard-size metal-gear servo, about 10 kgf.cm at 5 V (new, bought; the MG996R class, envelope "
    "inferred), on the nod plate's +x end lying along y inside the skull base, its spline on the tilt axis into a "
    "lever fixed to C1's lateral mass; a "
    "torsion balance spring (new, bought) on the -x knuckle holds the head's resting moment"
)

# ------------------------------------------------------------------------- 5. the base: T1..Tn, the least n that fits
rib = {o.name: o for o in bpy.data.collections["Ribcage"].objects}
pk, sw, dn = (np.ptp(pts(mech[n]), axis=0) for n in ("next pack", "next switch board", "next charger dongle"))
need_w, need_d = pk[0] + GAP + sw[0], max(pk[1], sw[1] + GAP + dn[1])
t1 = pts(rib["T1"])
z_top = (t1[:, 2].min() + t1[:, 2].max()) / 2  # the contents stay under T1's middle, the neck on it
cell = 2.0


def base_set(n):
    names = [f"T{i}" for i in range(1, n + 1)] + [f"{s} rib {i}" for s in "LR" for i in range(1, n + 1)]
    names += [f"{s} costal cartilage {i}" for s in "LR" for i in range(1, min(n, 7) + 1)]
    names += [f"{s} costal cartilage {i} (modelled)" for s in "LR" for i in range(8, min(n, 10) + 1)]
    return names + ["manubrium", "body of sternum", "xiphoid process", "L clavicle", "R clavicle", "L scapula",
                    "R scapula"]  # fmt: skip


ITEMS = (("next pack", pk, "middle"), ("next charger dongle", dn, "-x"), ("next switch board", sw, "-x"))


def fits(n):
    """(plane z, {item: (x0, y0, x1, y1)}) when T1..Tn's ring holds #865's contents, each placed in the free cells
    in turn (the packs stacked, in the middle; the dongle and the switch board on -x, by the swap opening), else
    (plane z, None)."""
    zr = np.vstack([pts(rib[f"{s} rib {n}"]) for s in "LR"])
    plane = zr[:, 2].min() - 1.0
    if z_top - (plane + 3.0) < H_NEED:
        return plane, None
    p = np.vstack([pts(rib[x]) for x in base_set(n) if x in rib])
    p = p[(p[:, 2] > plane + 3.0) & (p[:, 2] < plane + 3.0 + H_NEED)]  # the ring round the contents' height
    lo = p[:, :2].min(axis=0) - 10
    ij = np.floor((p[:, :2] - lo) / cell).astype(int)
    occ = np.zeros(ij.max(axis=0) + 12, bool)
    occ[ij[:, 0], ij[:, 1]] = True
    # inside the ring: inside the bones' plan hull (the slab cuts the sloping ribs open), clear of every bone
    gx, gy = np.meshgrid(*[np.arange(k) for k in occ.shape], indexing="ij")
    ring = Delaunay(ij).find_simplex(np.c_[gx.ravel(), gy.ravel()]).reshape(occ.shape) >= 0
    free = ring & ~ndimage.binary_dilation(occ, iterations=int((WALL + CLEAR) / cell) + 1)
    area = free.sum() * cell * cell
    fi = np.argwhere(free)
    ring_box = (*(lo + fi.min(axis=0) * cell), *(lo + (fi.max(axis=0) + 1) * cell)) if len(fi) else None
    centroid = np.argwhere(free).mean(axis=0) if free.any() else np.zeros(2)
    placed = {}
    for name, size_mm, where in ITEMS:
        best = None
        for w, d in ((size_mm[0], size_mm[1]), (size_mm[1], size_mm[0])):
            a, b = int(np.ceil(w / cell)), int(np.ceil(d / cell))
            if a >= free.shape[0] or b >= free.shape[1]:
                continue
            sat = np.pad(free.astype(int), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
            tot = sat[a:, b:] - sat[:-a, b:] - sat[a:, :-b] + sat[:-a, :-b]
            ok = np.argwhere(tot == a * b)
            if not len(ok):
                continue
            mids = ok + (a / 2, b / 2)
            score = np.linalg.norm(mids - centroid, axis=1) if where == "middle" else mids[:, 0]
            k = ok[np.argmin(score)]
            if best is None or score.min() < best[0]:
                best = (score.min(), k, a, b)
        if best is None:
            print(f"stage3: T1..T{n}: plane {plane:.0f}, free {area:.0f} mm2, {name} has no room", flush=True)
            return plane, None
        _, (i, j), a, b = best
        g = int(np.ceil(GAP / cell))
        free[max(i - g, 0) : i + a + g, max(j - g, 0) : j + b + g] = False
        x0, y0 = lo + np.array((i, j)) * cell
        placed[name] = (x0, y0, x0 + a * cell, y0 + b * cell)
    print(f"stage3: T1..T{n}: plane {plane:.0f}, free {area:.0f} mm2, all placed", flush=True)
    placed["ring"] = ring_box
    return plane, placed


chosen = None
for n in range(1, 13):
    plane, placed = fits(n)
    if placed:
        chosen = (n, plane, placed)
        break
assert chosen, "no T1..Tn ring holds #865's contents"
n, plane, placed = chosen
f = plane + 3.0
below = coll("Below the base (cut away)", helpers)
for name, o in list(rib.items()):
    if name not in base_set(n):
        relink(o, below)
rib = {k: v for k, v in rib.items() if k in base_set(n)}
cut = bpy.data.objects.new("Base cut", bpy.data.meshes.new("Base cut"))
bm = bmesh.new()
box_mesh(bm, (-400, -500, plane), (400, 400, plane + 900))
bm.to_mesh(cut.data)
bm.free()
bpy.data.collections["Cuts"].objects.link(cut)


def place(name, rect, z, turn):
    for o in (mech[name], keep[f"keep {name}:1"]):
        if turn:
            c = Vector(centre(o))
            o.matrix_world = Matrix.Translation(c) @ Matrix.Rotation(math.pi / 2, 4, "Z") @ Matrix.Translation(-c) @ (
                o.matrix_world)  # fmt: skip
            update()
        c = Vector(centre(o))
        o.location += Vector(((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2, z)) - c
    update()


for name, size_mm, _ in ITEMS:
    r = placed[name]
    turn = abs((r[2] - r[0]) - size_mm[0]) > abs((r[2] - r[0]) - size_mm[1])
    place(name, r, f + size_mm[2] / 2, turn)
    if name == "next pack":
        place("next spare pack", r, f + size_mm[2] * 1.5 + GAP, turn)
x0, y0, x1, y1 = placed.pop("ring")  # the foot: the floor plate across the ring's whole inside, the widest stance
floor = new_part("next floor plate", lambda bm: box_mesh(bm, (x0 - 2, y0 - 2, plane), (x1 + 2, y1 + 2, f)),
                 bpy.data.collections["Mech"])  # fmt: skip
mech["next floor plate"] = floor
fl = keep["keep Torso floor"]
fl.matrix_world = Matrix.LocRotScale(((x0 + x1) / 2, (y0 + y1) / 2, plane + 1.5), None, (x1 - x0, y1 - y0, 3.0))
side = [placed["next switch board"], placed["next charger dongle"]]
dx0 = min(r[0] for r in side)
dy0, dy1 = min(r[1] for r in side), max(r[3] for r in side)
door = keep["keep swap door"]
bm = bmesh.new()  # a unit box, sized by its matrix (build.py drew the door's prism in place)
bmesh.ops.create_cube(bm, size=1.0)
bm.to_mesh(door.data)
bm.free()
door.matrix_world = Matrix.LocRotScale((dx0 - 30.0, (dy0 + dy1) / 2, f + 22.0), None, (64.0, dy1 - dy0 + 4, 40.0))
update()
changes.append(
    f"Base: T1..T{n} (the least that holds #865's contents), with ribs 1-{n}, their costal cartilages, the sternum's "
    f"top, both clavicles and scapulae; one level plane under rib {n} (z {plane:.0f}) cuts the bones and Morty; "
    f"inside the ring a floor plate ({x1 - x0 + 4:.0f} x {y1 - y0 + 4:.0f} mm, Mounts) is the foot"
)
changes.append(
    f"Torso's contents (#865) on the floor plate inside the ring: both packs stacked, the switch board and the "
    f"dongle side by side by the swap opening, which opens on -x between the ribs and through Morty's side; the "
    f"Torso box and lid go; the ribs and T{n + 1}..T12 below the plane go"
)

# ------------------------------------------------------------------ 6. the finish: the base piece, Morty's volume
morty = bpy.data.objects["Morty"]
volume = bpy.data.objects.new("Morty volume", morty.data.copy())  # closed: the finish's outer limit
helpers.objects.link(volume)
volume.hide_render = True
for g in bpy.data.node_groups:
    for nd in g.nodes:
        if nd.bl_idname == "GeometryNodeObjectInfo" and nd.inputs["Object"].default_value == morty:
            nd.inputs["Object"].default_value = volume
lower = bpy.data.objects.get("finished Ribcage lower")
if lower:
    bpy.data.objects.remove(lower)
ped = bpy.data.objects["finished Ribcage upper"]
ped.name = ped.data.name = "finished Pedestal"
for nd in ped.modifiers["Finish"].node_group.nodes:
    v = nd.inputs["Object"].default_value if nd.bl_idname == "GeometryNodeObjectInfo" else None
    if v is not None and v.name == "Ribcage cut":
        nd.inputs["Object"].default_value = cut

# ----------------------------------------------------------- 7. Morty: a classic bust, in the "cansin" Skin palette


def lin(h, a):
    c = [int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return (*[x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c], a)


def material(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m


skin = T["skin_palette"]
MORTY_A, BONE_A = 0.33, 0.69
paint = {k: material(f"Morty {k}", lin(skin[k], MORTY_A)) for k in ("face", "hair", "pupils", "clothes", "eye whites")}
me = morty.data
me.materials.clear()
for k in paint:
    me.materials.append(paint[k])
idx = {k: i for i, k in enumerate(paint)}
neck_z, shoulder_z, half = report["morty_neck_z"], report["morty_shoulder_z"], report["morty_torso_half"]
eye_c = {s: np.array(json.loads(json.dumps(eyes[s].tolist()))) for s in "LR"}
mv = np.array([v.co[:] for v in me.vertices])
y_front, y_back = mv[mv[:, 2] > neck_z][:, 1].min(), mv[mv[:, 2] > neck_z][:, 1].max()
ez = mid[2]
bm = bmesh.new()
bm.from_mesh(me)
dead = []
for fc in bm.faces:
    c = np.array(fc.calc_center_median())
    if c[2] < plane or (abs(c[0]) > half and c[2] < shoulder_z + 10.0):
        dead.append(fc)  # the bust: cut at the base plane, no arms
        continue
    k = "face"
    if c[2] < shoulder_z:
        k = "clothes"
    for e in eye_c.values():
        r = np.linalg.norm(c - e)
        if r < r_morty + 1.5 and c[1] < e[1]:
            k = "pupils" if np.linalg.norm(c - (e + (0, -r_morty, 0))) < 0.22 * r_morty else "eye whites"
    if k == "face" and c[2] > neck_z:
        t = (c[1] - y_front) / (y_back - y_front)  # the hairline: over the brow in front, down to the nape behind
        if c[2] > (ez + r_morty + 14.0) * (1 - t) + (neck_z + 18.0) * t:
            k = "hair"
    fc.material_index = idx[k]
bmesh.ops.delete(bm, geom=dead, context="FACES")
bm.to_mesh(me)
bm.free()
morty_parts = {}
for part, (z0, z1) in {
    "Skull": (neck_z, 1e9),
    "Mechanism": (shoulder_z, neck_z),
    "Pedestal": (-1e9, shoulder_z),
}.items():
    o = bpy.data.objects.new(f"Morty {part.lower()}", me.copy())
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[fc for fc in bm.faces if not z0 <= fc.calc_center_median().z < z1], context="FACES")
    bm.to_mesh(o.data)
    bm.free()
    morty_parts[part] = o
morty_full = bpy.data.objects.get("Morty (full, measuring)")
bpy.data.objects.remove(morty)
changes.append(
    "Morty: a classic bust, no arms, cut at the base plane, in the 'cansin' Skin palette: face, neck and skin Milky "
    "Pink, hair and pupils Absolute Black, shirt and eye whites Pure White (no accessory in his sculpt for Apricot); "
    "its regions by position (inferred)"
)

# --------------------------------------------------------------- 8. Cansin's layers, sub-collections and palettes
pal = T["skeleton_palette"]
mats = {
    (grp, a): material(f"{grp} {'Skeleton' if a < 1 else 'Mech'}", lin(pal[grp], a))
    for grp in pal
    for a in (1.0, BONE_A)
}  # fmt: skip
grey = material("Bought", (0.25, 0.26, 0.28, 1.0))


def group(name):
    base = name.removesuffix(":1")
    for cand in (base, base.replace(" L ", " ").replace(" R ", " ")):
        if cand in T["groups"]:
            return T["groups"][cand]
    return {"next gimbal frame beam": "Bones", "next nod plate": "Joints", "next floor plate": "Mounts"}.get(base)


def paint_obj(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)
    o.color = m.diffuse_color


layers = {k: bpy.data.collections[k] for k in ("Mech", "Skeleton", "Morty")}
subs = {(layer, part): coll(f"{layer} {part}", layers[layer]) for layer in layers for part in
        ("Skull", "Mechanism", "Pedestal")}  # fmt: skip
NECK_PARTS = ("next nod plate", "next F8-16M thrust bearing", "next pan servo", "next tilt servo",
              "next tilt balance spring")  # fmt: skip
BASE_PARTS = ("next pack", "next spare pack", "next switch board", "next charger dongle", "next floor plate")
for name, o in mech.items():
    if o.name not in bpy.data.objects or "eyeball cap" in name:
        continue
    part = "Mechanism" if name in NECK_PARTS else "Pedestal" if name in BASE_PARTS else "Skull"
    relink(o, subs[("Mech", part)])
    grp = None if bought(name) else group(name)
    paint_obj(o, mats[(grp, 1.0)] if grp in pal else grey)
sk = layers["Skeleton"]
for child, part in (("Skull", "Skull"), ("Mandible", "Skull"), ("C1", "Mechanism"), ("C2", "Mechanism"),
                    ("C3", "Mechanism"), ("C4", "Mechanism"), ("C5", "Mechanism"), ("C6", "Mechanism"),
                    ("C7", "Mechanism"), ("Ribcage", "Pedestal")):  # fmt: skip
    c = bpy.data.collections[child]
    for parent in [x for x in bpy.data.collections if child in x.children]:
        parent.children.unlink(c)
    subs[("Skeleton", part)].children.link(c)
neck = bpy.data.collections.get("Neck")
if neck:
    for parent in [x for x in bpy.data.collections if "Neck" in x.children]:
        parent.children.unlink(neck)
    retired.children.link(neck)
for o in bpy.data.collections["Skeleton"].all_objects:
    if o.type == "MESH":
        paint_obj(o, mats[("Joints" if "cartilage" in o.name else "Bones", BONE_A)])
for part, o in morty_parts.items():
    subs[("Morty", part)].objects.link(o)
    o.color = (1, 1, 1, MORTY_A)
    o.hide_render = True
for o in (cut, volume):
    o.hide_set(True)
for c in (helpers,):
    bpy.context.view_layer.layer_collection.children[c.name].hide_viewport = True
for scr in bpy.data.screens:
    for area in scr.areas:
        if area.type == "VIEW_3D":
            sp = area.spaces.active
            sp.shading.type, sp.shading.color_type, sp.shading.show_xray = "SOLID", "MATERIAL", False
            sp.clip_start, sp.clip_end = 1.0, 20000.0
            r3d = sp.region_3d
            r3d.view_perspective, r3d.view_location, r3d.view_distance = "PERSP", (0, -95, 20), 1100.0
            r3d.view_rotation = Euler((math.radians(90), 0, 0)).to_quaternion()
scene.display.shading.color_type = "MATERIAL"
update()

# ---------------------------------------------------------------------------------------------- 10. the saves
open_parts = []
for o in list(carve_parts.all_objects) + list(bpy.data.collections["Keep-outs"].objects):
    b = bmesh.new()
    b.from_mesh(o.data)
    n_open = sum(1 for e in b.edges if e.is_boundary)
    b.free()
    if n_open:
        open_parts.append((o.name, n_open))
print("stage3: open carving parts (boundary edges):", open_parts, flush=True)
txt = bpy.data.texts.get("Mech changes") or bpy.data.texts.new("Mech changes")
txt.from_string("\n".join(f"{i + 1}. {c}" for i, c in enumerate(changes)))
txt.use_fake_user = True
json.dump({"changes": changes, "report": report, "base_n": n, "tilt": tilt.tolist(), "foot": [x0, y0, x1, y1],
           "pan_axis_y": float(pan_axis[1])},
          open(os.path.join(BUILD, "stage3.json"), "w"), indent=1)  # fmt: skip
bpy.data.orphans_purge(do_recursive=True)
tmp = DESKTOP + ".tmp.blend"
bpy.ops.wm.save_as_mainfile(filepath=tmp, compress=True, copy=True)
os.replace(tmp, DESKTOP)  # one write Cansin's Blender sees
mortys = [o for o in bpy.data.objects if o.name.startswith("Morty")]
refs = [(nd, nd.inputs["Object"].default_value) for g in bpy.data.node_groups for nd in g.nodes
        if nd.bl_idname == "GeometryNodeObjectInfo" and nd.inputs["Object"].default_value in mortys]  # fmt: skip
for nd, _ in refs:
    nd.inputs["Object"].default_value = None
for o in mortys:
    for c in list(o.users_collection):
        c.objects.unlink(o)
bpy.data.libraries.write(os.path.abspath(OUT), {scene, *bpy.data.texts}, path_remap="NONE", compress=True)
print("stage3:", json.dumps({"base": f"T1..T{n}"}), flush=True)
print("stage3: changes", *changes, sep="\n  ", flush=True)
