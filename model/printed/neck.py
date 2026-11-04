"""The Mech's neck and jaw (#641) as CadQuery parts, every size from model/neck.py (its frame and its design), each
drawn where it sits at rest. Turning bores take the busy pivots' M3 shanks (model/gimbal.py PIN_R); the part a shank
is fixed in has a tapping hole instead. A tie slot through a tab clamps each end of a flexing span."""

import math

import cadquery as cq
import numpy as np

from model import gimbal as gm
from model import neck as nk
from model.envelopes import box
from model.printed import bone
from model.printed.gimbal import LID_BONE, collar, cyl, lid_bone, link

TAP_R = 1.25  # an M3 shank's tapping hole: the part it is fixed in (inferred)
NECK_R = 5.0  # the post's top, in the pan bar's layer: the bar swings to 6.8 mm of the axis at pan 45 (#642)
# the post's bore for the neck cable (#858: its four 24 AWG conductors, inferred), up to under the pan shank's tapping
# hole, and its window out over the pan servo's shelf, under the pan span's lower clamp
BORE_R, BORE_TOP, WINDOW_Z = 3.0, -106.0, (-120.0, -115.0)
# (x, y) through the yoke's floor: the tilt horn and bar swing into it at tilt -20
POCKET = ((0.5, 10.0), (nk.AXIS[0] + 18.5, nk.AXIS[0] + 32.5))
Y, Z = nk.AXIS
FLOOR_D = 35.0  # the yoke's floor, back from the pan axis under the tilt servo
JAW_BONE = ((2.0, 3.9), (1.6, 3.0))  # the jaw's Bones (head, waist): within its arms' 4 mm
BAR_BONE = ((3.0, 2.9), (2.4, 2.6))  # the tilt and jaw bars' Bones: their heads the mechanical bars' round ends
FLANGE_BONE = LID_BONE  # the head mount's Bones (head, waist): within its flange's 3 mm, as the lid drives' in theirs


def _servo(label):
    face, shaft, tab, _ = nk.drives()[label]
    return gm.servo_matrix(face, shaft, tab)


def tie(x, y, z):
    """A clamp tab centred at (x, y, z) with a slot along x for a zip tie."""
    return box((x - 3, x + 3), (y - 3, y + 3), (z - 2, z + 2)).cut(
        box((x - 3, x + 3), (y - 2, y + 2), (z - 0.75, z + 0.75))
    )


@bone.carved
def mount(mechanical=False):
    """The neck mount (static, printed upright): a foot for the base, the post up from it through the Torso's lid, its
    top the yoke's thrust face under the head (#858; the pan shank's tapping hole down its axis, narrowed where the pan
    bar swings past), hollow below that for the neck cable (a window in its front over the foot and one over the lid),
    the shelf the pan servo's collar stands on over the lid and the pan span's lower clamp in front. As Bones (#708):
    the post waisted, the clamp's arm a strut."""
    out = box((-16, 16), (Y - 16, Y + 16), nk.MOUNT_Z)
    r, (z0, _) = nk.PAN_SPAN
    if mechanical:
        out = out.union(cyl("z", (0, Y, 0), nk.POST_R, (nk.MOUNT_Z[1], nk.PAN_Z[0] - 1)))  # 1 mm under the bar
        out = out.union(box((-3, 3), (Y - r - 3, Y - nk.POST_R + 1), (z0 - 2, z0 + 2)))
    else:
        post = (nk.POST_R, nk.POST_R), (nk.POST_R - 3, nk.POST_R - 3)  # into the foot, no face shared with it
        out = out.union(strut((0, Y, nk.MOUNT_Z[1] - 1), (0, Y, nk.PAN_Z[0] - 1), *post))
        out = out.union(strut((0, Y - nk.POST_R + 3, z0), (0, Y - r, z0), (2.0, 2.0), (1.6, 1.6)))
        out = out.union(box((-3, 3), (Y - r - 3, Y - r + 3), (z0 - 2, z0 + 2)))
    out = out.cut(box((-3, 3), (Y - r - 2, Y - r + 2), (z0 - 0.75, z0 + 0.75)))
    out = out.union(cyl("z", (0, Y, 0), NECK_R, (nk.PAN_Z[0] - 1, nk.DISC_Z[0])))
    out = out.union(box((0, 33), (Y - 19.5, Y + 13.5), nk.SHELF_Z)).union(collar(_servo("pan"), nk.SHELF_Z[1]))
    out = out.cut(cyl("z", (0, Y, 0), BORE_R, (nk.MOUNT_Z[1], BORE_TOP)))
    for z in ((nk.MOUNT_Z[1], nk.MOUNT_Z[1] + 8), WINDOW_Z):  # the cable in over the foot, out over the shelf
        out = out.cut(box((-BORE_R, BORE_R), (Y - nk.POST_R - 1, Y), z))
    return out.cut(cyl("z", (0, Y, 0), TAP_R, (BORE_TOP, nk.DISC_Z[0])))


def strut(a, b, head, waist):
    """A round Bone from a to b, flat at both ends (bone.bone round, heads False)."""
    up = (1, 0, 0) if abs(b[0] - a[0]) < 1e-9 else (0, 0, 1)
    return bone.bone(a, b, head, waist, up=up, round=True, heads=False)


@bone.carved
def yoke(mechanical=False):
    """The pan yoke (printed upright), a spine (#838): a disc on the neck mount's post under the head (#858; the pan
    shank's bore) with the pan lever back from it and the pan span's upper clamp in front; the top floor on it under the
    tilt servo (a pocket through it where the tilt horn and bar swing); the cheeks up from that to the tilt axis (the
    tilt shanks' tapping holes), the tilt servo's collar and the tilt span's clamp on a post outside the R cheek. As
    Bones (#708): each cheek, the clamp's post and its arm Bones."""
    lever = Y + nk.PAN_LEVER
    out = cyl("z", (0, Y, 0), nk.DISC_R, nk.DISC_Z).union(box((-3, 3), (Y, lever), nk.DISC_Z))
    out = out.union(cyl("z", (0, lever, 0), 3.0, nk.DISC_Z))
    out = out.union(box((nk.LOOP_X[0], 38), (Y - nk.BOSS_R - 1, Y + FLOOR_D), nk.TOP_Z))
    r, (_, z1) = nk.PAN_SPAN
    rho, _ = nk.TILT_SPAN
    cy, cz = Y + rho * 0.7071, Z - rho * 0.7071  # the clamp 45 deg down behind the axis
    if mechanical:
        out = out.union(box((-3, 3), (Y - r - 3, Y - nk.DISC_R + 1), nk.DISC_Z))
        for s in (-1, 1):
            out = out.union(box(sorted(s * c for c in nk.CHEEK_X), (Y - nk.BOSS_R, Y + nk.BOSS_R), (nk.TOP_Z[1], Z)))
        out = out.union(box(nk.LOOP_X, (cy - 2, cy + 2), (nk.TOP_Z[1], cz - 2)))
    else:
        arm = bone.bone((0, Y - nk.DISC_R + 3, nk.DISC_Z[0]), (0, Y - r, nk.DISC_Z[0]), (3.0, 3.9), (2.2, 3.0))
        out = out.union(arm).union(box((-3, 3), (Y - r - 3, Y - r + 3), nk.DISC_Z))
        cheek = (nk.BOSS_R, 3.5), (nk.BOSS_R - 1, 3.0)  # within the cheek's 4 mm, its boss the head's size
        for s in (-1, 1):
            xs = tuple(sorted(s * c for c in nk.CHEEK_X))
            out = out.union(lid_bone([(Y, nk.TOP_Z[1] - 0.5), (Y, Z)], xs, cheek))
        out = out.union(lid_bone([(cy, nk.TOP_Z[1] - 0.5), (cy, cz - 2)], nk.LOOP_X, ((2.5, 3.5), (2.0, 3.0))))
    out = out.cut(box((-3, 3), (Y - r - 2, Y - r + 2), (z1 - 0.75, z1 + 0.75)))
    for s in (-1, 1):
        xs = sorted(s * c for c in nk.CHEEK_X)
        out = out.union(cyl("x", (0, Y, Z), nk.BOSS_R, xs)).cut(cyl("x", (0, Y, Z), TAP_R, xs))
    out = out.union(tie(sum(nk.LOOP_X) / 2, cy, cz))
    out = out.union(collar(_servo("tilt"), nk.TOP_Z[1]))
    out = out.cut(cyl("z", (0, Y, 0), gm.PIN_R, (nk.DISC_Z[0], nk.TOP_Z[1]))).cut(box(*POCKET, nk.TOP_Z))  # from on top
    return out.cut(cyl("z", (0, lever, 0), TAP_R, nk.DISC_Z))


def cervical_carrier():
    """Fixed split lateral load path into the Torso; the centre remains open for the anatomical wire canal."""
    _, y, z = nk.HEAD_AXES["tilt"][0]
    out = box((-20, 20), (91, 101), nk.MOUNT_Z)
    for sign in (-1, 1):
        xs = sorted(sign * x for x in (14, 18))
        rail = box(xs, (y - 3, 97), (nk.MOUNT_Z[1] - 1, nk.MOUNT_Z[1] + 5))
        rail = rail.union(strut((sign * 16, 94, nk.MOUNT_Z[1]), (sign * 16, y, z), (4, 2), (3, 1.6)))
        rail = rail.union(cyl("x", (0, y, z), 5, xs)).cut(cyl("x", (0, y, z), TAP_R, xs))
        out = out.union(rail)
    out = out.union(box((14, 26), (y + 3, y + 11), (z - 5, z + 5)))
    out = out.union(box((23, 26), (y - 10, y + 11), (z - 10, z + 10)))
    return out.cut(cyl("x", (0, y, z), 3.1, (22, 27)))


def nod_plate():
    """The tilting plate, lateral trunnions and the two servo case seats; no load passes through a spline."""
    _, y, z = nk.HEAD_AXES["tilt"][0]
    out = box(nk.NOD_X, nk.NOD_Y, nk.NOD_Z)
    for sign in (-1, 1):
        xs = sorted(sign * x for x in (18.4, 22.4))
        out = out.union(box(xs, (y - 5, y + 5), (z, nk.NOD_Z[0] + 1)))
        out = out.union(cyl("x", (0, y, z), 5, xs)).cut(cyl("x", (0, y, z), gm.PIN_R, xs))
    py = nk.HEAD_AXES["pan"][0][1]
    out = out.cut(cyl("z", (0, py, 0), 4.2, nk.NOD_Z))
    face = (0, py, nk.PAN_HORN_Z)
    matrix = gm.servo_matrix(face, (0, 0, 1), (1, 0, 0))
    out = out.union(collar(matrix, nk.NOD_Z[0]))
    out = out.union(box((26, 69), (y - 17, y + 38), (z - 12.85, z - 9.85)))
    for hy in (y - 13.4, y + 34.1):
        out = out.union(box((26, 39.4), (hy - 2.5, hy + 2.5), (z - 12.85, nk.NOD_Z[0] + 1)))
        for hz in (z - 5, z + 5):
            out = out.cut(cyl("x", (0, hy, hz), 2.0, (35, 40)))
    return out


def head_mount():
    """Upper bearing seat and gimbal bridge, with a torque-only quill and keyed foot on the micro servo's horn."""
    py = nk.HEAD_AXES["pan"][0][1]
    bottom = nk.BEARING_Z[1]
    out = cyl("z", (0, py, 0), 10, (bottom, bottom + 3))
    for x, y in nk.HEAD_SCREWS:
        out = out.union(_flat([(0, py), (x, y)], 6, (bottom + 1.3, bottom + 4.3)))
        out = out.union(cyl("z", (x, y, 0), 3.5, (gm.PLATE_Z[1], bottom + 4.3)))
        out = out.cut(cyl("z", (x, y, 0), 1.7, (gm.PLATE_Z[1], bottom + 4.3)))
    out = out.union(cyl("z", (0, py, 0), 3.5, (nk.PAN_HORN_Z, bottom + 1)))
    out = out.union(_flat([(0, py), (nk.CRANK, py)], 5, (nk.PAN_HORN_Z, nk.PAN_HORN_Z + 1.5)))
    out = out.cut(cyl("z", (0, py, 0), 1.1, (nk.PAN_HORN_Z, bottom + 3)))
    return out.cut(cyl("z", (nk.CRANK, py, 0), 0.6, (nk.PAN_HORN_Z, nk.PAN_HORN_Z + 1.5)))


@bone.carved
def jaw(mechanical=False):
    """The jaw (printed on its side): a boss outside each of the frame's lugs at the condyles (the jaw shanks turn in
    them), an arm down from each (the mandible's ramus) to the body, which runs forward round to the chin as the
    mandible's (#838), and a boss down the L arm round the jaw bar's pin. As Bones (#708): each arm a strut, the body
    and the chin one chain of Bones flat on its underside."""
    jy, jz = nk.JAW
    x0, x1 = nk.JAW_X
    x, (z0, _) = (x0 + x1) / 2, nk.JAW_ARM_Z
    half = [(x, jy), *nk.JAW_BODY]
    points = [*half, (0.0, nk.CHIN_Y + 2.0), *((-px, py) for px, py in reversed(half))]
    if mechanical:
        out = _flat(points, x1 - x0, nk.JAW_ARM_Z)
        for s in (-1, 1):
            out = out.union(box(sorted((s * x0, s * x1)), (jy - nk.BOSS_R, jy + nk.BOSS_R), (z0, jz)))
    else:
        out = bone.chain(points, *JAW_BONE, z=z0)
        for s in (-1, 1):  # from inside the body's Bones up into the boss, inside its faces
            out = out.union(strut((s * x, jy, z0 + 1), (s * x, jy, jz - 1), (3.0, 1.8), (2.4, 1.5)))
    pin = (0, jy, jz - nk.JAW_LEVER)
    out = out.union(cyl("x", pin, 3.0, (x0, x1)))
    for s in (-1, 1):
        xs = sorted((s * x0, s * x1))
        out = out.union(cyl("x", (0, jy, jz), nk.BOSS_R, xs)).cut(cyl("x", (0, jy, jz), gm.PIN_R, xs))
    return out.cut(cyl("x", pin, TAP_R, (x0, x1)))


def _flat(points, w, zs):
    """Flat bars `w` wide through the (x, y) `points` in turn, from zs[0] to zs[1], round at every joint."""
    out = cyl("z", (*points[0], 0), w / 2, zs)
    for a, b in zip(points, points[1:]):
        side = np.array([a[1] - b[1], b[0] - a[0]]) * w / 2 / math.dist(a, b)
        outline = [tuple(map(float, p)) for p in (a + side, b + side, b - side, a - side)]
        bar = cq.Workplane("XY", origin=(0, 0, zs[0])).polyline(outline).close().extrude(zs[1] - zs[0])
        out = out.union(bar).union(cyl("z", (*b, 0), w / 2, zs))
    return out


@bone.carved
def pan_bar(mechanical=False):
    """The pan bar, flat under the yoke's floor: the yoke's lever pin to the pan horn's; mechanical or a Bone (#708)."""
    y = Y + nk.PAN_LEVER
    if mechanical:
        out = box((0, nk.PAN_BAR), (y - 3, y + 3), nk.PAN_Z)
        for x in (0, nk.PAN_BAR):
            out = out.union(cyl("z", (x, y, 0), 3.0, nk.PAN_Z))
    else:
        out = bone.chain([(0.0, y), (nk.PAN_BAR, y)], *LID_BONE, z=nk.PAN_Z[0])
    for x in (0, nk.PAN_BAR):
        out = out.cut(cyl("z", (x, y, 0), gm.PIN_R, nk.PAN_Z))
    return out


@bone.carved
def tilt_bar(mechanical=False):
    y = Y + nk.TILT_LEVER
    return link((y, Z - nk.TILT_BAR), (y, Z), nk.TILT_BAR_X, mechanical, BAR_BONE)


@bone.carved
def jaw_bar(mechanical=False):
    """The jaw bar: the jaw's lever pin back to the mouth horn's (#838)."""
    jy, jz = nk.JAW
    hy, hz = nk.MOUTH_HORN
    return link((jy, jz - nk.JAW_LEVER), (hy, hz + nk.CRANK), nk.JAW_BAR_X, mechanical, BAR_BONE)
