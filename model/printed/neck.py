"""The Mech's neck and jaw (#641) as CadQuery parts, every size from model/neck.py (its frame and its design), each
drawn where it sits at rest. Turning bores take the busy pivots' M3 shanks (model/gimbal.py PIN_R); the part a shank
is fixed in has a tapping hole instead. A tie slot through a tab clamps each end of a flexing span."""

import math

import cadquery as cq
import numpy as np

from model import gimbal as gm
from model import neck as nk
from model.envelopes import box, hull
from model.printed import bone
from model.printed.gimbal import LID_BONE, collar, cyl, lid_bone, link, passes

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
        xs = sorted(sign * x for x in (5.8, 10.2))
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
    for a, b in ((root, elbow), (elbow, (-6.8, anchor[1], anchor[2]))):
        out = out.union(strut(a, b, (4, 3), (3.5, 2.5)))
    out = out.union(cq.Workplane().sphere(2.8).translate(elbow))
    out = out.union(cyl("x", (0, anchor[1], anchor[2]), 3.5, (-8.3, -1.8)))
    out = out.cut(cyl("x", (0, anchor[1], anchor[2]), TAP_R, (-8.3, -1.8)))
    for x, fy in nk.CARRIER_FEET:
        out = out.cut(cyl("z", (x, fy, 0), 1.7, nk.MOUNT_Z))
    return out


def nod_plate():
    """The tilting plate, lateral trunnions and the two servo case seats; no load passes through a spline."""
    _, y, z = nk.HEAD_AXES["tilt"][0]
    py = nk.HEAD_AXES["pan"][0][1]
    out = hull("XY", [(0, py, 10), (-12.8, y, 3.6), (12.8, y, 3.6)], nk.NOD_Z[1] - nk.NOD_Z[0], (0, 0, nk.NOD_Z[0]))
    for sign in (-1, 1):
        xs = sorted(sign * x for x in (10.8, 14.8))
        out = out.union(box(xs, (y - 5, y + 5), tuple(sorted((z, nk.NOD_Z[0] + 1)))))
        out = out.union(cyl("x", (0, y, z), 3.6, xs)).cut(cyl("x", (0, y, z), gm.PIN_R, xs))
    out = out.cut(cyl("z", (0, py, 0), 4.2, nk.NOD_Z))
    face = (0, py, nk.PAN_HORN_Z)
    matrix = gm.servo_matrix(face, (0, 0, 1), (1, 0, 0))
    floor = nk.PAN_HORN_Z - 19
    out = out.union(collar(matrix, floor))
    for start, x in (((-21, py + 6), -23), ((11, py + 6), 23)):
        out = out.union(_flat([start, (x, 72)], 4, (floor, floor + 3)).cut(passes(matrix)))
        out = out.union(box((x - 1.5, x + 1.5), (69.5, 74.5), (floor, nk.NOD_Z[0] + 1)))
        out = out.union(_flat([(x, 72), (math.copysign(12.8, x), y)], 4, (nk.NOD_Z[0], nk.NOD_Z[0] + 3)))
    # Upper-head saddle on the actual standard-servo tabs; rear posts clear the complete tray/PCB pan sweep.
    sx, sy, sz = nk.TILT_SHAFT
    tab_x = (sx + 10.4, sx + 13.4)
    ceiling, rear = sz + 20, sy
    out = out.union(box((-10, 10), (y, 98), nk.NOD_Z)).union(box((-15, 15), (98, 115), nk.NOD_Z))
    # One positive-X mast leaves the negative-X reaction standoff free. Its low dogleg bypasses the rotating plate;
    # its top leans forward from the hair groove, preserving the continuous skull-wall stack.
    mast = [
        (10, 112, nk.NOD_Z[0]),
        (24.5, 132, -40),
        (24.5, 132, -26),
        (24.5, 112, -14),
        (24.5, 112, 60),
        (24.5, rear, ceiling - 4),
    ]
    for a, b in zip(mast, mast[1:]):
        out = out.union(strut(a, b, (4, 4), (4, 4)))
    for point in mast:
        out = out.union(cq.Workplane().sphere(3.8).translate(point))
    out = out.union(box((-15, 28.5), (rear - 3, rear + 3), (ceiling - 8, ceiling)))
    for hy in (sy - 13.4, sy + 34.1):
        out = out.union(box(tab_x, (hy - 3.2, hy + 3.2), (sz - 10.8, ceiling)))
        for hz in (sz - 5, sz + 5):
            out = out.cut(cyl("x", (0, hy, hz), 1.1, tab_x))
    out = out.union(box(tab_x, (sy - 16.6, max(rear + 3, sy + 37.3)), (ceiling - 8, ceiling)))
    out = out.cut(cyl("z", (0, y, 0), nk.WIRE_R + 0.3, nk.NOD_Z))
    out = out.cut(box((-3.2, 3.2), (95, 116), nk.NOD_Z))  # the reaction bar crosses the rear edge at full tilt
    # Cylindrical reliefs stay clear at every tilt, not only a few sampled angles.
    for xs, radius in (
        ((5.5, 10.5), 5.1),
        ((-10.5, -5.5), 5.1),
        ((-34.2, -25.8), 8.5),
    ):
        out = out.cut(cyl("x", (0, y, z), radius, xs))
    return out


def tilt_lever():
    """Adapter on the supplied round horn, with an outboard standoff clear of the actual case and tabs."""
    from model.printed.gimbal import lid_mechanical

    x, y, z = nk.TILT_SHAFT
    span = (x - 3, x)
    out = cyl("x", (0, y, z), 11.5, span)
    out = out.union(lid_mechanical([(y, z), tuple(nk.TILT_PIN[1:])], span))
    out = out.union(cyl("x", (0, *nk.TILT_PIN[1:]), 3.5, (x - 3, -1.8)))
    out = out.cut(cyl("x", (0, y, z), 1.6, span))
    for dy, dz in ((8, 0), (-8, 0), (0, 8), (0, -8)):
        out = out.cut(cyl("x", (0, y + dy, z + dz), 1.1, span))
    return out.cut(cyl("x", (0, *nk.TILT_PIN[1:]), TAP_R, (-4.8, -1.8)))


def tilt_reaction_bar():
    """A rigid bent bar around the electronics; endpoint geometry, not the shape between them, closes the parallelogram."""
    from model.printed.gimbal import lid_mechanical

    pins = [tuple(point[1:]) for point in nk.TILT_BAR_PATH]
    out = lid_mechanical(pins, (-1.5, 1.5))
    for point in (nk.TILT_ANCHOR, nk.TILT_PIN):
        out = out.union(cyl("x", (0, *point[1:]), 3.8, (-1.5, 1.5))).cut(
            cyl("x", (0, *point[1:]), gm.PIN_R, (-1.5, 1.5))
        )
    return out


def head_mount():
    """Upper bearing seat and gimbal bridge, with a torque-only quill and keyed foot on the micro servo's horn."""
    py = nk.HEAD_AXES["pan"][0][1]
    bottom = nk.BEARING_Z[1]
    out = cyl("z", (0, py, 0), 8, (bottom, gm.PLATE_Z[1] + 0.3))
    top = gm.PLATE_Z[1] + 3.3
    out = out.union(cyl("z", (0, py, 0), 10, (gm.PLATE_Z[1] + 0.3, top)))
    for x, y in nk.HEAD_SCREWS:
        out = out.union(_flat([(0, py), (x, y)], 6, (gm.PLATE_Z[1] + 0.3, top)))
        out = out.union(cyl("z", (x, y, 0), 3.5, (gm.PLATE_Z[1], top)))
        out = out.cut(cyl("z", (x, y, 0), 1.7, (gm.PLATE_Z[1], top)))
    out = out.union(cyl("z", (0, py, 0), 3.5, (nk.PAN_HORN_Z, bottom + 1)))
    out = out.union(_flat([(0, py), (nk.CRANK, py)], 5.4, (nk.PAN_HORN_Z, nk.PAN_HORN_Z + 1.5)))
    out = out.cut(cyl("z", (0, py, 0), 1.1, (nk.PAN_HORN_Z, top)))
    return out.cut(cyl("z", (nk.CRANK, py, 0), 0.6, (nk.PAN_HORN_Z, nk.PAN_HORN_Z + 1.5)))


@bone.carved
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
            link = strut(a, b, (3.2, 2.2), (2.6, 1.8))
            out = link if out is None else out.union(link)
    jy, jz = nk.JAW
    for sign in (-1, 1):
        xs = sorted(sign * x for x in nk.JAW_X)
        out = out.union(cyl("x", (0, jy, jz), nk.BOSS_R, xs)).cut(cyl("x", (0, jy, jz), gm.PIN_R, xs))
    # The actual ramus, not a vertical extension of the old L, takes the drive pin.
    x = sum(nk.JAW_X) / 2
    pin = (x, *nk.JAW_PIN)
    out = out.union(strut(points["L"][2], pin, (3, 2.2), (2.5, 1.8)))
    out = out.union(cyl("x", (0, *nk.JAW_PIN), 3, nk.JAW_X)).cut(cyl("x", (0, *nk.JAW_PIN), TAP_R, nk.JAW_X))
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
    solve = nk.LINKAGES["jaw"]
    _, a, b = solve(0)
    return link(tuple(a[1:]), tuple(b[1:]), nk.JAW_BAR_X, mechanical, BAR_BONE)
