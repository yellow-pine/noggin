"""The Mech's neck and jaw (#641) as CadQuery parts, every size from model/neck.py (its frame and its design), each
drawn where it sits at rest. Turning bores take the busy pivots' M3 shanks (model/gimbal.py PIN_R); the part a shank
is fixed in has a tapping hole instead. A tie slot through a tab clamps each end of a flexing span."""

import functools
import math

import cadquery as cq
import numpy as np

from model import envelopes
from model import gimbal as gm
from model import neck as nk
from model.envelopes import box, hull
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
    out = box((-20, 20), (56, 72), nk.MOUNT_Z)
    for sign in (-1, 1):
        xs = sorted(sign * x for x in (18.0, 22.4))
        rail = box(sorted(sign * x for x in (14, 18)), (60, 68), (nk.MOUNT_Z[0] + 1, nk.MOUNT_Z[1] + 1))
        points = [(sign * x, *point) for x, point in zip(nk.CERVICAL_X, nk.CERVICAL_PATH)]
        for a, b in zip(points, points[1:]):
            rail = rail.union(strut(a, b, (4, 2), (3, 1.6)))
        rail = rail.union(cyl("x", (0, y, z), 3.5, xs)).cut(cyl("x", (0, y, z), TAP_R, xs))
        out = out.union(rail)
    # A passive bar reacts the elevated moving-case motor at a pin behind the actual wire canal.
    anchor = nk.TILT_ANCHOR
    root = (-10.5, *nk.CERVICAL_PATH[-2])
    elbow = (-10.5, 90.0, -78.0)
    for a, b in ((root, elbow), (elbow, (-9.8, anchor[1], anchor[2]))):
        out = out.union(strut(a, b, (4, 3), (3.5, 2.5)))
    out = out.union(cq.Workplane().sphere(2.8).translate(elbow))
    out = out.union(cyl("x", (0, anchor[1], anchor[2]), 3.5, (-11.3, nk.REACTION_TAP_X[1])))
    out = out.cut(cyl("x", (0, anchor[1], anchor[2]), TAP_R, (-11.3, nk.REACTION_TAP_X[1])))
    out = out.union(tie(20.0, 78.5, -65.7))
    for x, fy in nk.CARRIER_FEET:
        out = out.cut(cyl("z", (x, fy, 0), 1.7, nk.MOUNT_Z))
    return out


def nod_plate():
    """Tilting cervical carrier, hollow pan spindle and the two real standard-servo tab cradles."""
    _, y, z = nk.HEAD_AXES["tilt"][0]
    out = hull("XY", [(0, y, 12), (-13.8, y, 3.6), (13.8, y, 3.6)], 5, (0, 0, nk.NOD_Z[0]))
    for sign in (-1, 1):
        xs = sorted(sign * x for x in (13.4, 17.4))
        out = out.union(box(xs, (y - 3.6, y + 3.6), tuple(sorted((z, nk.NOD_Z[0] + 1)))))
        out = out.union(cyl("x", (0, y, z), 3.6, xs)).cut(cyl("x", (0, y, z), gm.PIN_R, xs))
        for fy in (y - 12, y + 12):
            out = out.union(_flat([(0, fy), (sign * 14, fy)], 5, nk.NOD_Z))
        out = out.union(_flat([(sign * 14, y - 12), (sign * 14, y + 12)], 4, nk.NOD_Z))
    out = out.cut(box((-3, 3), (y - 13.5, y - 9.5), (nk.NOD_Z[0] + 1.75, nk.NOD_Z[0] + 3.25)))
    # The tube is integral with the nod carrier: head weight never reaches either servo spline.
    out = out.union(pan_wire_candidate()["spindle"])
    out = out.cut(cyl("z", (0, y, 0), nk.WIRE_R, (nk.NOD_Z[0], nk.PAN_STUDY_Z[1])))
    # Low rear tilt cradle: actual tab faces, four M2 tapping bores, an upper header clear of the case and rear Skin.
    sx, sy, sz = nk.TILT_SHAFT
    tabs = (sx + 10.4, sx + 13.4)
    front, rear = sy - 13.4, sy + 34.1
    for fy in (front, rear):
        out = out.union(box(tabs, (fy - 3.1, fy + 3.1), (sz - 8.1, sz + 22.0)))
        for fz in (sz - 5, sz + 5):
            out = out.cut(cyl("x", (0, fy, fz), 0.8, tabs))
    out = out.union(box((sx + 10.4, sx + 16.9), (front - 3.1, rear + 3.1), (sz + 11.5, sz + 22.0)))
    out = out.union(box((sx + 10.4, 25.0), (sy - 10.0, sy + 2.0), (sz + 11.5, sz + 22.0)))
    # Crown pan cradle: a rear dogleg bypasses the entire rotating frame and the electronics tray.
    mast = [
        (13.8, y + 2.5, nk.NOD_Z[0] + 2.5),
        (26, 127, -40),
        (25, 126, 31),
        (18, 110, 65),
        (18, nk.PAN_SHAFT[1] + 34.1, nk.PAN_SHAFT[2] + 9.4),
    ]
    out = out.union(_flat([tuple(mast[0][:2]), tuple(mast[1][:2])], 15, nk.NOD_Z))
    for u, v in zip(mast[1:], mast[2:]):
        out = out.union(strut(u, v, (6.8, 6.8), (6.8, 6.8)))
    for v in mast[1:]:
        out = out.union(cq.Workplane().sphere(6.6).translate(v))
    fore, aft = nk.PAN_SHAFT[1] - 13.4, nk.PAN_SHAFT[1] + 34.1
    plate = (nk.PAN_SHAFT[2] + 5.4, nk.PAN_SHAFT[2] + 13.4)
    out = out.union(_flat([(18, fore), (18, aft)], 6.2, plate))
    for fy in (fore, aft):
        out = out.union(_flat([(-5, fy), (18, fy)], 6.2, plate))
        for x in (-5, 5):
            out = out.cut(cyl("z", (x, fy, 0), 0.8, plate))
    for xs in ((17.7, 26), (-26, -17.7)):
        out = out.cut(cyl("x", (0, y, z), 8.5, xs))
    return out


def tilt_lever():
    """Adapter on the supplied round horn, with an outboard standoff clear of the actual case and tabs."""
    x, y, z = nk.TILT_SHAFT
    outer = x + envelopes.STANDARD_HORN["face"]
    span = (outer - 5, outer)  # counterbore leaves a full 2 mm printed floor over the stock retaining screw
    out = cyl("x", (0, y, z), 11.5, span)
    out = out.union(hull("YZ", [(y, z, 7), (*nk.TILT_PIN[1:], 7)], span[1] - span[0], (span[0], 0, 0)))
    out = out.union(cyl("x", (0, *nk.TILT_PIN[1:]), 4.5, (span[0], nk.REACTION_TAP_X[1])))
    out = out.cut(cyl("x", (0, y, z), 1.6, span))
    out = out.cut(cyl("x", (0, y, z), 2.8, (outer - 3, outer)))
    for dy, dz in envelopes.STANDARD_HORN["mounts"]:
        out = out.cut(cyl("x", (0, y + dy, z + dz), 1.1, span))
    return out.cut(cyl("x", (0, *nk.TILT_PIN[1:]), TAP_R, nk.REACTION_TAP_X))


def tilt_reaction_bar():
    """A rigid bent bar around the electronics; endpoint geometry, not the shape between them, closes the parallelogram."""
    from model.printed.gimbal import lid_mechanical

    pins = [tuple(point[1:]) for point in nk.TILT_BAR_PATH]
    out = lid_mechanical(pins, nk.REACTION_BAR_X)
    for point in (nk.TILT_ANCHOR, nk.TILT_PIN):
        out = out.union(cyl("x", (0, *point[1:]), 3.8, nk.REACTION_BAR_X)).cut(
            cyl("x", (0, *point[1:]), gm.PIN_R, nk.REACTION_BAR_X)
        )
    return out


def head_mount():
    """Bearing-supported rotating head carrier, including its real pan rocker post."""
    return pan_wire_candidate()["head carrier"]


def pan_fixed_cap():
    return pan_wire_candidate()["fixed cap"]


def pan_moving_cap():
    return pan_wire_candidate()["moving cap"]


def pan_lever():
    """Printed adapter on the standard round horn; the bar shares the head post's horizontal pin plane."""
    x, y, _ = nk.PAN_SHAFT
    pin = nk.PAN_PIN[:2]
    mounts = [(x + dx, y + dy, 2.2 if dy < 0 else 3.2) for dx, dy in envelopes.STANDARD_HORN["mounts"]]
    out = hull("XY", [*mounts, (*pin, 4.5)], nk.PAN_LEVER_Z[1] - nk.PAN_LEVER_Z[0], (0, 0, nk.PAN_LEVER_Z[0]))
    out = out.union(cyl("z", (*pin, 0), 4.5, (nk.PAN_LEVER_Z[0], nk.PAN_TAP_Z[1])))
    out = out.cut(cyl("z", (*pin, 0), TAP_R, nk.PAN_TAP_Z))
    out = out.cut(cyl("z", (x, y, 0), 2.8, nk.PAN_LEVER_Z))
    for dx, dy in envelopes.STANDARD_HORN["mounts"]:
        out = out.cut(cyl("z", (x + dx, y + dy, 0), 1.1, nk.PAN_LEVER_Z))
    return out


@functools.cache
def pan_wire_candidate():
    """Unaccepted retained C0 bearing study; immediate CAD/STEP evidence, outside the production part registry."""
    y = nk.HEAD_AXES["tilt"][0][1]
    (bore, outside, _), (bottom, top) = nk.PAN_STUDY_BEARING, nk.PAN_STUDY_Z
    bolts = [(7.1 * math.cos(a), y + 7.1 * math.sin(a)) for a in np.radians((0, 120, 240))]
    tube_top = bottom - 6.3
    spindle = cyl("z", (0, y, 0), 6.2, (nk.NOD_Z[1], tube_top))
    flare = cq.Solid.makeCone(6.2, 11.5, 5.3, cq.Vector(0, y, tube_top), cq.Vector(0, 0, 1))
    spindle = spindle.union(cq.Workplane().add(flare)).union(cyl("z", (0, y, 0), 11.5, (bottom - 1, bottom)))
    spindle = spindle.union(cyl("z", (0, y, 0), bore / 2, (bottom, top)))
    spindle = spindle.cut(cyl("z", (0, y, 0), nk.WIRE_R, (nk.NOD_Z[1], top)))
    fixed_cap = cyl("z", (0, y, 0), 11.5, (top, top + 4)).cut(cyl("z", (0, y, 0), nk.WIRE_R, (top, top + 4)))
    for x, fy in bolts:
        spindle = spindle.cut(cyl("z", (x, fy, 0), 0.8, (top - 6.5, top)))
        fixed_cap = fixed_cap.cut(cyl("z", (x, fy, 0), 1.1, (top, top + 4)))
    bearing = cyl("z", (0, y, 0), outside / 2, (bottom, top)).cut(cyl("z", (0, y, 0), bore / 2, (bottom, top)))
    carrier = cyl("z", (0, y, 0), 18.5, (bottom - 2, top)).cut(
        cyl("z", (0, y, 0), 15, (bottom - 2, bottom)).union(cyl("z", (0, y, 0), outside / 2, (bottom, top)))
    )
    moving_cap = cyl("z", (0, y, 0), 18.5, (top, top + 4)).cut(cyl("z", (0, y, 0), 15, (top, top + 4)))
    for a in np.radians((0, 120, 240)):
        x, fy = 20.6 * math.cos(a), y + 20.6 * math.sin(a)
        carrier = carrier.union(cyl("z", (x, fy, 0), 3.2, (bottom - 2, top))).cut(
            cyl("z", (x, fy, 0), 0.8, (top - 6.5, top))
        )
        moving_cap = moving_cap.union(cyl("z", (x, fy, 0), 3.2, (top, top + 4))).cut(
            cyl("z", (x, fy, 0), 1.1, (top, top + 4))
        )
    for x, fy in nk.PAN_STUDY_SCREWS:
        delta = np.array((x, fy - y))
        start = delta / np.linalg.norm(delta) * 19.5 + (0, y)
        feet = gm.PLATE_Z[1]
        carrier = carrier.union(_flat([tuple(start), (x, fy)], 6, (bottom + 1, bottom + 4)))
        carrier = carrier.union(cyl("z", (x, fy, 0), 3.8, (feet, bottom + 4))).cut(
            cyl("z", (x, fy, 0), 1.7, (feet, bottom + 4))
        )
    # The post's lower step joins the rotor below the removable cap, without using cap screws as a beam joint.
    carrier = carrier.union(box((-24.8, -17), (y - 10, y + 10), (bottom + 1, top)))
    carrier = carrier.union(box((-24.8, -18.8), (y - 10, y + 10), (top - 0.5, top + 13)))
    px, py, _ = nk.PAN_ANCHOR
    # The lower column stands behind the crank sweep; its top arm reaches the coupler above the crank plate.
    rear = (px, py + 10)
    carrier = carrier.union(_flat([(-26.3, y), rear], 15, (top + 4, top + 13)))
    carrier = carrier.union(cyl("z", (*rear, 0), 7.5, (top + 4, nk.PAN_TAP_Z[1])))
    arm_z = (nk.PAN_LEVER_Z[1] + 1.5, nk.PAN_TAP_Z[1])
    carrier = carrier.union(hull("XY", [(*rear, 7.5), (px, py, 5.0)], arm_z[1] - arm_z[0], (0, 0, arm_z[0])))
    carrier = carrier.cut(cyl("z", (px, py, 0), TAP_R, nk.PAN_TAP_Z))
    carrier = carrier.cut(box((-24.8, -18.8), (y - 2, y + 2), (top + 6.25, top + 7.75)))
    return {
        "spindle": spindle,
        "fixed cap": fixed_cap,
        "bearing": bearing,
        "head carrier": carrier,
        "moving cap": moving_cap,
    }


@bone.grown
def jaw(mechanical=False):
    """Hidden spatial carrier following the measured mandibular ramus/body, hinged at the actual condyles."""
    from model import skin

    points = {}
    for side, border in nk.MANDIBLE_BORDER.items():
        sign = 1 if side == "L" else -1
        points[side] = [(x - sign * 2.5, y, z + (3 if i >= 4 else 0)) for i, (x, y, z) in enumerate(border)]
        points[side].append(tuple(np.add(nk.MENTON, (0, 0, 3))))
    out = None
    for chain in points.values():
        for a, b in zip(chain, chain[1:]):
            link = strut(a, b, (3.2, 2.2), (2.8, 2))
            out = link if out is None else out.union(link)
    jy, jz = nk.JAW
    for sign in (-1, 1):
        xs = sorted(sign * x for x in nk.JAW_X)
        out = out.union(cyl("x", (0, jy, jz), nk.BOSS_R, xs)).cut(cyl("x", (0, jy, jz), gm.PIN_R, xs))
    # The actual ramus, not a vertical extension of the old L, takes the drive pin.
    x = sum(nk.JAW_X) / 2
    pin = (x, *nk.JAW_PIN)
    out = out.union(strut(points["L"][2], pin, (3, 2.2), (2.5, 1.8)))
    pin_r = 4.0 if mechanical else 3.5
    out = out.union(cyl("x", (0, *nk.JAW_PIN), pin_r, nk.JAW_X)).cut(cyl("x", (0, *nk.JAW_PIN), TAP_R, nk.JAW_X))
    # Keep the existing resting mouth Shell on its actual Seat while the hidden anatomical load path changes.
    seat = next(s for s in skin.SEATS if s.shell == "morty mouth cover")
    at = np.subtract(seat.at, np.multiply(seat.normal, seat.pad / 2))
    out = out.union(strut(points["L"][-1], at, (3.2, 2.4), (2.8, 2)))
    return out


def _flat(points, w, zs):
    """Flat bars `w` wide through the (x, y) `points` in turn, from zs[0] to zs[1], round at every joint."""
    out = cyl("z", (*points[0], 0), w / 2, zs)
    for a, b in zip(points, points[1:]):
        side = np.array([a[1] - b[1], b[0] - a[0]]) * w / 2 / math.dist(a, b)
        outline = [tuple(map(float, p)) for p in (a + side, b + side, b - side, a - side)]
        bar = cq.Workplane("XY", origin=(0, 0, zs[0])).polyline(outline).close().extrude(zs[1] - zs[0])
        out = out.union(bar).union(cyl("z", (*b, 0), w / 2, zs))
    return out


def pan_bar():
    """The real horizontal coupler between the standard horn adapter and the bearing-supported head post."""
    out = _flat([tuple(nk.PAN_PIN[:2]), tuple(nk.PAN_ANCHOR[:2])], 7.6, nk.PAN_LINK_Z)
    for point in (nk.PAN_PIN, nk.PAN_ANCHOR):
        out = out.cut(cyl("z", (*point[:2], 0), gm.PIN_R, nk.PAN_LINK_Z))
    return out


@bone.carved
def tilt_bar(mechanical=False):
    y = Y + nk.TILT_LEVER
    return link((y, Z - nk.TILT_BAR), (y, Z), nk.TILT_BAR_X, mechanical, BAR_BONE)


@bone.carved
def jaw_bar(mechanical=False):
    """The jaw bar: the jaw's lever pin back to the mouth horn's (#838)."""
    solve = nk.LINKAGES["jaw"]
    _, a, b = solve(0)
    return link(tuple(a[1:]), tuple(b[1:]), nk.JAW_BAR_X, mechanical, BAR_BONE)
