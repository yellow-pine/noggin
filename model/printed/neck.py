"""The next Mech's neck and jaw (#641) as CadQuery parts, every size from model/neck.py (its frame and its design), each
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
COLUMN_R = 10.0  # the neck mount's column: its top is the yoke's thrust face, inside the pan bar's sweep
NECK_R = 5.0  # the column's top, in the pan bar's layer: the bar swings to 6.8 mm of the axis at pan 45 (#642)
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
    """The neck mount (static, printed upright): a foot for the base, a column whose top the yoke turns on (the pan
    shank's tapping hole down its axis; narrowed where the pan bar swings past), the pan servo's collar and the pan
    span's lower clamp in front. As Bones (#708): the column waisted, the clamp's arm a strut."""
    foot = box((-14, 42), (Y - 22, Y + 16), nk.MOUNT_Z)
    r, (z0, _) = nk.PAN_SPAN
    if mechanical:
        out = foot.union(cyl("z", (0, Y, 0), COLUMN_R, (nk.MOUNT_Z[1], nk.PAN_Z[0] - 1)))  # 1 mm under the bar
        out = out.union(box((-3, 3), (Y - r - 3, Y - COLUMN_R + 1), (z0 - 2, z0 + 2)))
    else:
        column = (COLUMN_R, COLUMN_R), (COLUMN_R - 3, COLUMN_R - 3)  # into the foot, no face shared with it
        out = foot.union(strut((0, Y, nk.MOUNT_Z[1] - 1), (0, Y, nk.PAN_Z[0] - 1), *column))
        out = out.union(strut((0, Y - COLUMN_R + 3, z0), (0, Y - r, z0), (2.0, 2.0), (1.6, 1.6)))
        out = out.union(box((-3, 3), (Y - r - 3, Y - r + 3), (z0 - 2, z0 + 2)))
    out = out.cut(box((-3, 3), (Y - r - 2, Y - r + 2), (z0 - 0.75, z0 + 0.75)))
    out = out.union(cyl("z", (0, Y, 0), NECK_R, (nk.PAN_Z[0] - 1, nk.DISC_Z[0])))
    out = out.union(collar(_servo("pan"), nk.MOUNT_Z[1]))
    return out.cut(cyl("z", (0, Y, 0), TAP_R, (nk.MOUNT_Z[1], nk.DISC_Z[0])))


def strut(a, b, head, waist):
    """A round Bone from a to b, flat at both ends (bone.bone round, heads False)."""
    up = (1, 0, 0) if abs(b[0] - a[0]) < 1e-9 else (0, 0, 1)
    return bone.bone(a, b, head, waist, up=up, round=True, heads=False)


@bone.carved
def yoke(mechanical=False):
    """The pan yoke (printed upright), a spine (#838): a disc on the column under the Torso's lid (the pan shank's bore)
    with the pan lever back from it and the pan span's upper clamp in front; the post up from it through the lid to the
    top floor under the tilt servo (a pocket through it where the tilt horn and bar swing); the cheeks up from that to
    the tilt axis (the tilt shanks' tapping holes), the tilt servo's collar and the tilt span's clamp on a post outside
    the R cheek. As Bones (#708): the post a strut, each cheek, the clamp's post and its arm Bones."""
    lever = Y + nk.PAN_LEVER
    out = cyl("z", (0, Y, 0), nk.DISC_R, nk.DISC_Z).union(box((-3, 3), (Y, lever), nk.DISC_Z))
    out = out.union(cyl("z", (0, lever, 0), 3.0, nk.DISC_Z))
    out = out.union(box((nk.LOOP_X[0], 38), (Y - nk.BOSS_R - 1, Y + FLOOR_D), nk.TOP_Z))
    r, (_, z1) = nk.PAN_SPAN
    rho, _ = nk.TILT_SPAN
    cy, cz = Y + rho * 0.7071, Z - rho * 0.7071  # the clamp 45 deg down behind the axis
    if mechanical:
        out = out.union(cyl("z", (0, Y, 0), nk.POST_R, (nk.DISC_Z[1], nk.TOP_Z[0])))
        out = out.union(box((-3, 3), (Y - r - 3, Y - nk.DISC_R + 1), nk.DISC_Z))
        for s in (-1, 1):
            out = out.union(box(sorted(s * c for c in nk.CHEEK_X), (Y - nk.BOSS_R, Y + nk.BOSS_R), (nk.TOP_Z[1], Z)))
        out = out.union(box(nk.LOOP_X, (cy - 2, cy + 2), (nk.TOP_Z[1], cz - 2)))
    else:
        out = out.union(strut((0, Y, nk.DISC_Z[1] - 1), (0, Y, nk.TOP_Z[0] + 1), (nk.POST_R, nk.POST_R), (4.0, 4.0)))
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
    out = out.cut(cyl("z", (0, Y, 0), gm.PIN_R, nk.DISC_Z)).cut(box(*POCKET, nk.TOP_Z))
    return out.cut(cyl("z", (0, lever, 0), TAP_R, nk.DISC_Z))


@bone.carved
def head_mount(mechanical=False):
    """The head mount (printed on its side, its bores along Z): a flange screwed under the gimbal frame's plate's back,
    behind the mouth servo, the tilt lugs outside the cheeks (the tilt shanks turn in them; the cheeks' bosses rise into
    slots in the flange), the tilt lever behind, and the tilt span's head clamp straight behind the tilt axis, under the
    flange (#708, #838). As Bones (#708): the flange a frame of Bones flat on the plate from screw to screw round the
    back, the lever a Bone."""
    f0, top = nk.FLANGE_Z
    rho, _ = nk.TILT_SPAN
    ly = Y + nk.TILT_LEVER
    (x0, y0), (x1, y1) = (nk.HEAD_SCREWS[1], nk.HEAD_SCREWS[2])
    if mechanical:
        out = box((nk.LOOP_X[0], -nk.LOOP_X[0]), (y0 - 2.5, ly + 3), nk.FLANGE_Z)
        hang = f0
    else:  # the Bones flat on the plate's underside, domed down within the flange's 3 mm
        flat = dict(z=top, down=True)
        out = bone.chain([(x0, y0), (x0, y1), (x1, y1), (x1, y0)], *FLANGE_BONE, **flat)  # OCCT fuses no ring of them
        out = out.union(bone.chain([(0.0, y1), (0.0, ly)], *FLANGE_BONE, **flat))
        hang = top - 1  # the lugs and the lever up into the Bones
    for x, y in nk.HEAD_SCREWS:
        out = out.cut(cyl("z", (x, y, 0), 1.7, nk.FLANGE_Z))
    for s in (-1, 1):
        xs = sorted(s * c for c in nk.LUG_X)
        out = out.union(box(xs, (Y - nk.BOSS_R, Y + nk.BOSS_R), (Z, hang))).union(cyl("x", (0, Y, Z), nk.BOSS_R, xs))
        out = out.cut(cyl("x", (0, Y, Z), gm.PIN_R, xs))
    out = out.union(box((-1.5, 1.5), (ly - 3, ly + 3), (Z, hang))).union(cyl("x", (0, ly, Z), 3.0, (-1.5, 1.5)))
    out = out.cut(cyl("x", (0, ly, Z), TAP_R, (-1.5, 1.5))).cut(_clear())
    return out.union(tie(sum(nk.LOOP_X) / 2, Y + rho, Z))


def _clear():
    """What the flange leaves open: a slot round each cheek's boss and one round the tilt bar's top end."""
    x0, x1 = nk.TILT_BAR_X
    out = box((x0, x1 + 0.5), _around(Y + nk.TILT_LEVER), nk.FLANGE_Z)
    for s in (-1, 1):
        out = out.union(box(sorted(s * c for c in (nk.CHEEK_X[0] - 0.5, nk.CHEEK_X[1])), (Y - 6, Y + 6), nk.FLANGE_Z))
    return out


def _around(y, r=nk.BOSS_R + 0.5):
    return (y - r, y + r)


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
