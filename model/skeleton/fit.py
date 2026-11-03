"""PROTOTYPE (#872 step 3): how the Mech fits inside the warped skeleton, proposed as moved and rescaled stand-ins in the
live scene (model/ code untouched). Run after build.py; writes the change list to the scene's "Mech changes" text and
<out dir>/changes.json. Printed parts scale; bought parts (servos, horns, boards, packs, the dongle) keep their size
and move with what holds them. args: <targets.json> <out dir>"""

import json
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

TARGETS, OUT = sys.argv[sys.argv.index("--") + 1 :][:2]
T = json.load(open(TARGETS))
os.makedirs(OUT, exist_ok=True)
BOUGHT = ("servo", "horn", "Core", "Shield", "pack", "switch board", "dongle")
CLEAR, WALL = 1.6, 2.0
MORTY_EYE_R, LOWER_LID_R = 5.67, 33.5  # his eye's dome (build.py), raw; the lower lid's outside (gimbal.LOWER_R)
dg = bpy.context.evaluated_depsgraph_get()
mech = {o.name.removesuffix(":1"): o for o in bpy.data.collections["Mech"].objects}
mech |= {o.name.removesuffix(":1"): o for o in bpy.data.collections["Carve parts"].objects if "eyeball cap" in o.name}
keep = {o.name: o for o in bpy.data.collections["Keep-outs"].objects}
changes = []


def pts(o):
    ev = o.evaluated_get(dg)
    m = np.array(o.matrix_world)
    v = np.array([x.co[:] for x in ev.data.vertices])
    return v @ m[:3, :3].T + m[:3, 3]


def centre(o):
    v = pts(o)
    return (v.min(axis=0) + v.max(axis=0)) / 2


def bought(name):
    return any(k in name for k in BOUGHT)


def scale_about(names, at, k, why):
    """Printed parts scaled k about `at`; bought ones moved where their mount's point goes."""
    at = Vector(at)
    for n in names:
        o = mech[n]
        if bought(n):
            c = Vector(centre(o))
            o.location += (at + (c - at) * k) - c
        else:
            o.matrix_world = Matrix.Translation(at) @ Matrix.Scale(k, 4) @ Matrix.Translation(-at) @ o.matrix_world
    bpy.context.view_layer.update()
    if why:
        changes.append(why)


def move(names, d, why):
    for n in names:
        (mech.get(n) or keep[n]).location += Vector(d)
    bpy.context.view_layer.update()
    changes.append(why)


def skel(names):
    return np.vstack([pts(bpy.data.objects[n]) for n in names])


# --- 1. the eye gimbal: each eye (build.py put it on Morty's pupil) scaled about its centre to his eye's size, so its
# lids stay inside his eye's dome; the frame stretched across to the pupils
eyes = {s: centre(mech[f"next {s} eyeball core"]) for s in "LR"}
mid = (eyes["L"] + eyes["R"]) / 2
report = json.loads(bpy.context.scene["report"])
r_morty = report["morty_scale"] * MORTY_EYE_R
k_x = np.linalg.norm(eyes["L"] - eyes["R"]) / np.linalg.norm(np.subtract(T["eyes"]["L"], T["eyes"]["R"]))
k_ball = r_morty / LOWER_LID_R
EYE = ("eyeball core", "eyeball cap", "upper lid", "lower lid", "yaw yoke", "push-rod", "lid bar", "lid link",
       "lid servo", "lid horn")  # fmt: skip
for s in "LR":
    scale_about([f"next {s} {p}" for p in EYE if f"next {s} {p}" in mech], eyes[s], k_ball, None)
S = Matrix.Diagonal((k_x, k_ball, k_ball, 1.0))


def stretch(o, at):
    """A printed part's matrix stretched by S about `at`; a bought part moved where its centre goes."""
    at = Vector(at)
    if bought(o.name):
        c = Vector(centre(o))
        o.location += (at + (S @ (c - at).to_4d()).to_3d()) - c
    else:
        o.matrix_world = Matrix.Translation(at) @ S @ Matrix.Translation(-at) @ o.matrix_world


FRAME = ("next gimbal frame", "next bail", "next tie-bar", "next pitch bar", "next pitch horn", "next pitch servo",
         "next yaw horn", "next yaw servo", "next cranium tray", "next Core 1", "next Core 2", "next Shield 1",
         "next Shield 2")  # fmt: skip
for n in FRAME:
    stretch(mech[n], mid)
for n in ("keep USB-C next Core 1", "keep USB-C next Core 2", "keep next Core 1:1", "keep next Core 2:1",
          "keep next Shield 1:1", "keep next Shield 2:1"):  # fmt: skip
    o = keep[n]
    c = Vector(centre(o))
    o.location += (Vector(mid) + (S @ (c - Vector(mid)).to_4d()).to_3d()) - c
bpy.context.view_layer.update()
changes = [c for c in changes if c]
changes.append(
    f"Eyes: each eye assembly (eyeball core and cap, upper and lower lids, yaw yoke, push-rod, lid bar and link) scaled "
    f"x{k_ball:.2f} about its own centre, on Morty's pupil ({np.linalg.norm(eyes['L'] - eyes['R']):.1f} mm apart, "
    f"was 52): the cap {27 * k_ball:.1f} mm round, the lower lid's outside {LOWER_LID_R * k_ball:.1f}, inside "
    f"Morty's eye ({r_morty:.1f}); its lid servo and horn keep their size and ride their mount")
changes.append(
    f"Gimbal frame, bail, tie-bar, pitch bar and cranium tray: stretched x{k_x:.2f} across (to the pupils) and "
    f"x{k_ball:.2f} front-to-back and up, about the eyes' middle; the pitch and yaw servos and horns and the Cores on "
    f"the tray keep their size and ride their mounts. Open: the frame's front beam (under the eyes) stands in front of "
    f"the maxilla; recess it behind the cheekbones or run it through the orbits' floor, so the mechanism shows only "
    f"through the orbits")

# --- 2. the jaw inside the mandible: scaled about the hinge (build.py put it on Morty's jawline)
hinge = np.array((0.0, *json.loads(bpy.context.scene["report"])["jawline_yz"]))
mand = skel(["mandible"])
inner = np.abs(mand[(mand[:, 2] > hinge[2] - 40) & (mand[:, 2] < hinge[2] - 10)][:, 0]).max() - 9.0 - CLEAR
k_jaw = inner / 37.0
scale_about(["next jaw", "next jaw bar", "next mouth horn", "next mouth servo"], hinge, k_jaw,
            f"Jaw: scaled x{k_jaw:.2f} about the hinge so its arms sit inside the mandible's rami (their inner faces "
            f"at x ±{inner + CLEAR:.0f}); its hinge on Morty's jawline and the condyles (y {hinge[1]:.1f}, z {hinge[2]:.1f}, "
            f"was y -124, z 153); the mouth servo and horn keep their size")

# --- 3. the tilt axis onto the occipital condyles, the pan axis onto the neck's canals
occ = skel(["occipital bone"])
oc = occ[occ[:, 2] < occ[:, 2].min() + 4].mean(axis=0)
tilt_new = np.array((0.0, oc[1], oc[2] - 3.0))
d_tilt = tilt_new - np.array(T["tilt"])
move(["next head mount"], d_tilt, f"Head mount: moved {np.round(d_tilt, 1)} mm so the tilt axis runs under the "
     f"occipital condyles (y {tilt_new[1]:.1f}, z {tilt_new[2]:.1f}); redrawn to bridge from there forward "
     f"{abs(tilt_new[1] - centre(mech['next gimbal frame'])[1]):.0f} mm to the scaled gimbal frame's plate")
neck_top = ["next pan yoke", "next tilt servo", "next tilt horn", "next tilt bar"]
move(neck_top, d_tilt, f"Tilt drive (pan yoke's cheeks, tilt servo, horn and bar): moved {np.round(d_tilt, 1)} mm with "
     f"the tilt axis")
c1 = np.array(bpy.data.objects["pose C1"].matrix_world.translation)
c7 = np.array(bpy.data.objects["pose C7"].matrix_world.translation)
rib = skel([o.name for o in bpy.data.collections["Ribcage"].objects])
post_y = (c1[1] + c7[1]) / 2
yoke = pts(mech["next pan yoke"])
foot_z = c7[2] - 25.0  # the pan at the neck's base, inside the top of the ribcage, under C7
d_pan = np.array((0.0, post_y - T["tilt"][1], foot_z - pts(mech["next neck mount"])[:, 2].max()))
move(["next neck mount", "next pan servo", "next pan horn", "next pan bar"], d_pan,
     f"Pan drive (neck mount's top, pan servo, horn and bar): moved {np.round(d_pan, 1)} mm, down to the neck's base "
     f"inside the top of the ribcage, under C7 (the post's foot at z {foot_z:.0f})")
o = mech["next pan yoke"]
z0, z1 = yoke[:, 2].min(), yoke[:, 2].max()
k_post = (z1 - foot_z) / (z1 - z0)
o.matrix_world = Matrix.Translation((0, 0, z1)) @ Matrix.Diagonal((1, 1, k_post, 1)) @ Matrix.Translation((0, 0, -z1)) @ (
    o.matrix_world)
bpy.context.view_layer.update()
changes.append(f"Neck post (the pan yoke's): stretched x{k_post:.2f} in height, {z1 - foot_z:.0f} mm from the pan at the "
               f"neck's base up to the tilt axis, through C7 to C1's canals (life-width canals, carved round it), "
               f"on the canals' line (y {post_y:.1f})")

# --- 4. the Torso's contents (#865) down into the ribcage's base, re-laid to its narrower plan: the packs stacked,
# the switch board and the dongle side by side on -x by the swap opening; their floor the foot
floor_z = rib[:, 2].min() - 3.0
w = rib[(rib[:, 2] > floor_z) & (rib[:, 2] < floor_z + 60)]
rx, ry = (w[:, 0].min() + w[:, 0].max()) / 2, (w[:, 1].min() + w[:, 1].max()) / 2
W, D = np.ptp(w[:, 0]) - 2 * (WALL + CLEAR), np.ptp(w[:, 1]) - 2 * (WALL + CLEAR)
f = floor_z + 3.0


def place(name, at):
    for o in [mech[name], keep[f"keep {name}:1"]]:
        c = Vector(centre(o))
        o.location += Vector(at) - c
    bpy.context.view_layer.update()


def size(name):
    return np.ptp(pts(mech[name]), axis=0)


pk, sw, dn = size("next pack"), size("next switch board"), size("next charger dongle")
px = rx + W / 2 - pk[0] / 2  # the packs on +x, the switch and dongle on -x
place("next pack", (px, ry, f + pk[2] / 2))
place("next spare pack", (px, ry, f + pk[2] * 1.5 + 4.0))
place("next switch board", (rx - W / 2 + sw[0] / 2, ry - D / 2 + sw[1] / 2, f + sw[2] / 2))
place("next charger dongle", (rx - W / 2 + dn[0] / 2, ry + D / 2 - dn[1] / 2, f + dn[2] / 2))
fl = keep["keep Torso floor"]
fl.matrix_world = Matrix.LocRotScale((rx, ry, floor_z + 1.5), None, (W, D, 3.0))
door = keep["keep swap door"]
dc = Vector(centre(door))
door.location += Vector((rx - W / 2 - 10.0, ry, f + 20.0)) - dc
bpy.context.view_layer.update()
changes.append(f"Torso's contents (#865) re-laid into the ribcage's base, whose inside there is {W:.0f} W x {D:.0f} D mm "
               f"(the Torso's plan was 120 x 116): the pack and the spare pack stacked on +x "
               f"({pk[0]:.0f} x {pk[1]:.0f} each), the switch board and the dongle side by side on -x, by the swap "
               f"opening, which now opens between the lower ribs' -x sides and through Morty's side; their floor, the "
               f"foot, at z {floor_z:.0f} under the lowest ribs, a printed tray the ribs and spine hold (its form open "
               f"with Cansin); the Torso box and lid go")
# --- 5. the Cores' USB-C reach: out through the back of the cranium and Morty's head
back = max(pts(o)[:, 1].max() for o in bpy.data.collections["Morty"].objects)
for n in ("keep USB-C next Core 1", "keep USB-C next Core 2"):
    o = keep[n]
    v = pts(o)
    o.matrix_world = Matrix.Translation((0, v[:, 1].min(), 0)) @ Matrix.Diagonal(
        (1, (back + 5 - v[:, 1].min()) / np.ptp(v[:, 1]), 1, 1)) @ Matrix.Translation((0, -v[:, 1].min(), 0)) @ (
        o.matrix_world)  # fmt: skip
skull_back = skel(["occipital bone", "L parietal bone"])[:, 1].max()
changes.append(f"USB-C openings: the Cores ride the scaled tray; each plug's opening now runs back through the "
               f"cranium (its back at y {skull_back:.0f}) and out through Morty's head (y {back:.0f})")
lead = np.linalg.norm(centre(mech["next pack"]) - centre(mech["next Core 1"]))
changes.append(f"Leads: the pack's Y lead now climbs about {lead:.0f} mm straight-line from the ribcage's base up the "
               f"post into the cranium (was about 230), longer by that")
changes.append("Printability (Bambu bed 256 mm, inferred): the scaled gimbal frame, the calvaria, the face and skull "
               "base, the mandible and each ribcage half fit; the ribcage is split level at its middle")

txt = bpy.data.texts.get("Mech changes") or bpy.data.texts.new("Mech changes")
txt.from_string("\n".join(f"{i + 1}. {c}" for i, c in enumerate(changes)))
txt.use_fake_user = True
json.dump(changes, open(os.path.join(OUT, "changes.json"), "w"), indent=1)
print("fit:", *changes, sep="\n  ", flush=True)
open(os.path.join(OUT, "done"), "w").write("ok\n")
