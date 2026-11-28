"""The Mech's eye gimbal (#630) as CadQuery parts, every size from model/gimbal.py (its frame and its design).
Parts at one eye are drawn about the L eye's centre (the R one's mirror where it differs); the rest in the gimbal's
frame. Bores take the busy pivots' M3 steel shanks; each push-rod's cups close on a ball under its equator."""

import functools
import itertools
import math

import cadquery as cq
import mujoco
import numpy as np
from OCP.gp import gp_Trsf
from scipy.spatial import ConvexHull

from model import envelopes, fits, gates, linkage, neck
from model import gimbal as gm
from model import skin as sk
from model.envelopes import box
from model.printed import bone

LEVER_R, NECK_R, CUP_R, ARM = 2.5, 1.2, gm.BALL_R + 1.5, 6.0  # ARM: every printed arm's width
# the Bones' (head, waist) as (semi-width, height): each push-rod's inside its cups and within CUP_R of the line
# between the balls (the lids' clearance, gimbal.report, reads it so); the lid drives' (#698) low enough to lie within
# their 3 mm slabs
ROD_BONE, LID_BONE = ((3.6, 5.5), (2.4, 4.0)), ((4.0, 2.9), (3.0, 2.6))
TIE_BOSS = ARM / 2  # the tie-bar's bosses' radius, round each pin's bore
# The tie-bar's Bones (#1052): each finger's and the tail's lie in their slabs as the lid drives' do, and are as wide in
# the slab's plane as the flat arm at its thickest, so the arm's own sides cut them and no Bone's flank hangs past the
# arm's 44 deg on the tie-bar's bed; the cross-bar's lies on that bed, as wide as the bar, domed up to the fingers
TIE_BONE, CROSS_BONE = ((2.4, 5.0), (2.2, 3.6)), ((2.4, 7.6), (2.2, 5.6))
# (#704) the yoke's crank in its 3 mm slab, stiff in the bed for its bending, its waist 0.5 mm over the slab so the
# slab's top cuts it flat (a crown grazing it, 2.9, fused invalid on aarch64's OCCT, #890); the bail's rod flat-bottomed
# with the shanks' bores at its middle height, each arm a strut round in section, the input arm's tip round the pitch
# bar's pin
CRANK_BONE, BAIL_ROD, BAIL_ARM, BAIL_INPUT = (
    ((4.5, 4.2), (3.0, 3.5)),
    ((4.0, 7.0), (3.0, 6.0)),
    ((2.4, 3.7), (2.2, 3.6)),
    ((3.5, 6.5), (3.0, 5.0)),
)
# The lid drives' Bones' longest span, mm (#967): one of their sizes 30 to 36 mm long comes out of OCCT invalid at
# most of bone.chain's tries, at any angle (the lid bar's carved empty on macOS; all eight of a 32.2 mm spoke's failed
# on Linux), and one 28 mm or shorter at none. Not lower: the upper lid's 31.5 mm spoke builds as one on both, and
# as two it carved in pieces
LID_SPAN = 32.0
MM = 0.001  # MuJoCo's metres per mm
NECK = gm.BALL_R + 1.2  # a ball's centre from what its neck stands on
# Each push-rod's cup closes on its ball this far past the ball's centre. Its mouth turns round the neck the ball
# stands on, up to 21 deg off its own axis at the lever's (the pitch up with the yaw at an end): at 1.85 its rim keeps
# the lids' room from that neck, 0.54 mm there (at 2.0, 0.36 at the lever's and 0.48 at the bail's, #967), and the ball
# still snaps in past a lip 0.51 mm proud (0.63)
CUP_MOUTH = 1.85
# The push-rod leans (#967), so it lies on its own bed, the plane under both its cups: the lever's cup's mouth on it,
# CUP_MOUTH under that ball's centre, and the bail's cup standing on it mouth up, its socket's floor 0.8 mm thick
ROD_BED = (CUP_MOUTH, gm.BALL_R + 0.1 + 0.8)
# each bail arm's way down from the axis, deg from +y toward +z: steeper than the line to its ball, so it passes its
# lid servo's top front corner at the pitch's upper end; its ball stands off the arm's round end on its neck
BAIL_ARM_DEG = -128.0
# the bail's arms' width in their planes, the input arm's too (ARM before): the leaned bar loads the input arm 1.3
# times the horn's stall, the leaned rod its arm 1.5 times
BAIL_ARM_W = 7.0
CAP_BACK = gm.CAP_R * math.cos(math.radians(gm.CAP_HALF))  # the cap's flat back, on the core's seat


def cyl(axis, centre, r, span):
    """A cylinder along x, y or z through `centre` (the other two coordinates), from span[0] to span[1]."""
    i = "xyz".index(axis)
    lo = list(centre)
    lo[i] = span[0]
    d = [0, 0, 0]
    d[i] = 1
    return cq.Workplane().add(cq.Solid.makeCylinder(r, span[1] - span[0], cq.Vector(*lo), cq.Vector(*d)))


def ball(r, at=(0, 0, 0)):
    return cq.Workplane().add(cq.Solid.makeSphere(r, cq.Vector(*at), angleDegrees1=-90, angleDegrees2=90))


def rod(a, b, r):
    """A round rod of radius r from a to b."""
    a, b = cq.Vector(*map(float, a)), cq.Vector(*map(float, b))
    return cq.Workplane().add(cq.Solid.makeCylinder(r, (b - a).Length, a, b - a))


def ball_on(foot, at):
    """A ball on a neck from `foot` to its centre `at`: the push-rod's cup closes round it from the far side."""
    return ball(gm.BALL_R, at).union(rod(foot, at, NECK_R))


def rod_bed():
    """4x4 from the push-rod's print frame (its bed z 0, the lever's ball over the origin, the bail's along +y) to
    where it is drawn: at x 0 about its eye's centre, leaning from the lever's ball down to the bail's (#967)."""
    a, b = np.array([0.0, 0.0, gm.LEVER]), np.array([0.0, *gm.BAIL_BALL])
    lean = math.atan2(b[2] - a[2], b[1] - a[1]) - math.asin((ROD_BED[1] - ROD_BED[0]) / math.dist(a, b))
    m = linkage.rotation((1, 0, 0), math.degrees(lean))
    m[:3, 3] = a - m[:3, :3] @ (0, 0, ROD_BED[0])
    return m


def bail_bed():
    """4x4 from the bail's print frame (its axis x through the origin, its input arm along -y on the bed under its
    rod, its arms rising) to the gimbal's: turned about its axis, the input arm on gm.BAIL_IN_DEG (#967)."""
    m = linkage.rotation((1, 0, 0), gm.BAIL_IN_DEG - 180.0)
    m[:3, 3] = (0, *gm.BAIL)
    return m


def bail_foot():
    """(y, z) of each bail arm's round end's centre, in the gimbal's frame: BAIL_ARM_DEG from the axis, its round and
    its ball's neck from the ball's centre."""
    u = np.array([math.cos(math.radians(BAIL_ARM_DEG)), math.sin(math.radians(BAIL_ARM_DEG))])
    ball_at = np.subtract(gm.BAIL_BALL, gm.BAIL)
    along = float(ball_at @ u)
    d = along - math.sqrt((NECK + BAIL_ARM_W / 2) ** 2 - float(ball_at @ ball_at) + along**2)  # the nearer crossing
    return tuple(np.add(gm.BAIL, d * u))


# the relief on the core's top (#967): pitched down 15 deg, the leaned push-rod's underside passes 16.1 mm from the
# core's centre, 0.8 mm inside its ball, and the rod swings about the yaw axis over the yaw; the ball is cut to a cone
# round the lever's axis, its side this far from the centre and facing (out, up) this way, 2 mm under the rod's bar
# wherever the eye turns (fitted to its underside over the pitch and the yaw)
CORE_RELIEF = (14.0, (0.649, 0.760))


def core():
    """The eyeball core: a ball, the seat its cap sits on (forward), the lever up the yaw axis to its ball, whose neck
    leans forward, square to the push-rod's bed (#967), a cone round the lever cut from its top where that rod passes,
    and the pitch axle's bores along x."""
    up = rod_bed()[:3, 2]  # the push-rod's bed's normal: its lever cup's mouth faces down it
    at = np.array([0.0, 0.0, gm.LEVER])
    foot = at - NECK * up
    d, (ny, nz) = CORE_RELIEF
    far = gm.CORE_R + 1  # the cone's section (out, z), past the ball
    section = [(0.0, d / nz), (far, (d - ny * far) / nz), (far, far), (0.0, far)]
    relief = cq.Workplane("YZ").polyline(section).close().revolve(360, (0, 0, 0), (0, 1, 0))
    out = ball(gm.CORE_R).cut(relief)
    out = out.union(cyl("y", (0, 0, 0), gm.SEAT_R, (-CAP_BACK, -gm.CORE_R + 3)))
    out = out.union(rod(foot - 12.0 * up, foot, LEVER_R)).union(ball_on(foot, at))  # the lever, rooted in the cone
    for s in (-1, 1):
        out = out.cut(cyl("x", (0, 0, 0), gm.PIN_R, sorted((s * 8.0, s * (gm.CORE_R + 1)))))
    return out


@bone.grown
def yoke(mechanical=False):
    """The yaw yoke: a U from below round the core, the pitch axle's bores through its arms, its crank back from its
    bottom bar, at the bar's level, to the tie-bar's finger under it (#967: no stem, the yaw shank's bore through the
    bar, which turns on the frame's post). As Bones (#704): the U a cradle round the core, its underside flaring at
    40 deg from its flat foot, the crank a Bone in its slab; printed as drawn, on the foot and the crank."""
    y = gm.YOKE
    x0, x1, h = y["inner"], y["inner"] + y["wall"], y["half_y"]
    z = gm.YAW_CRANK_Z
    if not mechanical:
        r = math.hypot(x1, h)  # round the bosses' corners
        # the cone tangent to the cradle 40 deg under its equator: the overhang no more than that on either
        rt, zt = r * math.cos(math.radians(40)), -r * math.sin(math.radians(40))
        foot = rt - (zt - z[0]) * math.tan(math.radians(40))  # its radius on the bed
        cone = cq.Solid.makeCone(foot, rt, zt - z[0], cq.Vector(0, 0, z[0]))
        out = ball(r).union(cq.Workplane().add(cone))
        out = out.intersect(box((-x1, x1), (-h, h), (z[0], 0))).cut(ball(x0))
        crank = bone.bone((0, 0, z[0]), (0, gm.CRANK, z[0]), *CRANK_BONE).intersect(box((-9, 9), (-9, 20), z))
        out = out.union(crank)
    else:
        out = box((-x1, x1), (-h, h), (-x1, -x0))
        for s in (-1, 1):
            out = out.union(box(sorted((s * x0, s * x1)), (-h, h), (-x1, 0)))
        for s in (-1, 1):  # the U's lower corners cut back: yawed, a square one nears the cheek's Skin (#967)
            corner = [(s * (x1 - gm.YOKE_CUT), -x1), (s * x1, -x1), (s * x1, -x1 + gm.YOKE_CUT)]
            out = out.cut(cq.Workplane("XZ", origin=(0, h, 0)).polyline(corner).close().extrude(2 * h))
        out = out.union(box((-ARM / 2, ARM / 2), (0, gm.CRANK), z)).union(cyl("z", (0, gm.CRANK, 0), ARM / 2, z))
    for s in (-1, 1):
        xs = sorted((s * x0, s * x1))
        out = out.union(cyl("x", (0, 0, 0), h, xs)).cut(cyl("x", (0, 0, 0), gm.PIN_R, xs))
    return out.cut(cyl("z", (0, gm.CRANK, 0), gm.PIN_R, z)).cut(cyl("z", (0, 0, 0), gm.PIN_R, z))


def tie_bed():
    """4x4 from the tie-bar's print frame (its bed z 0: the cross-bar's back edge on it, the fingers and the tail
    rising) to the gimbal's: the gimbal's -y up."""
    m = linkage.rotation((1, 0, 0), 90.0)
    m[:3, 3] = (0, gm.CROSS_Y[1], 0)
    return m


@bone.carved
def tie_bar(mechanical=False):
    """The tie-bar (#967): a finger under each yoke's crank from its pin, back and up inside the lids' shell and out
    through the belt behind the eye to the cross-bar behind the eyes, and a tail from that bar's back edge down the
    midline to the yaw horn's pin: one parallelogram with both yokes' cranks and the horn. Mechanical: flat arms. As
    Bones (#1052): the cross-bar a Bone on the bed, each finger a chain of three in its slab and the tail one in its,
    the pins' bosses as they are. Printed on the cross-bar's back edge (tie_bed), so each finger and the tail rise
    within 45 deg of upright, a wedge under each pin's boss."""
    c, t, thick = gm.EYE["L"][0], gm.FINGER_Z[1] - gm.FINGER_Z[0], gm.CROSS_Z[1] - gm.CROSS_Z[0]
    pin, horn = (gm.CRANK, sum(gm.FINGER_Z) / 2), (gm.YAW_Y + gm.CRANK, sum(gm.TIE_Z) / 2)
    reach, slab = c + gm.FINGER_X[1], (c + gm.FINGER_X[0], c + gm.FINGER_X[1])  # the L finger's, drawn then mirrored
    back = (gm.CROSS_Y[1] - t / 2, sum(gm.CROSS_Z) / 2)
    if mechanical:
        out = box((-reach, reach), gm.CROSS_Y, gm.CROSS_Z)
        # out through the belt as thick as the cross-bar
        finger = lid_mechanical([pin, *gm.FINGER[:2]], slab, t).union(lid_mechanical(gm.FINGER[1:], slab, thick))
        tail = lid_mechanical([horn, back], (-TIE_BOSS, TIE_BOSS), t)
    else:  # the cross-bar's ends flat on the slabs' outer faces
        z = sum(gm.CROSS_Z) / 2
        out = _placed(bone.bone((-reach, z, 0), (reach, z, 0), *CROSS_BONE, heads=False), tie_bed())
        finger = lid_bone([pin, *gm.FINGER], slab, TIE_BONE)
        tail = lid_bone([horn, back], (-TIE_BOSS, TIE_BOSS), TIE_BONE)
    out = out.union(finger).union(finger.mirror("YZ")).union(tail)
    # the tangent under the boss 45 deg off the bed's normal, down to the finger's inboard face
    k = TIE_BOSS * math.sqrt(0.5)
    wedge = [(-k, pin[0] + k), (0.0, pin[0] + 2 * k), (0.0, pin[0])]
    for s in (-1, 1):
        out = out.union(cyl("z", (s * c, pin[0], 0), TIE_BOSS, gm.FINGER_Z))
        gusset = [(s * (c + u), y) for u, y in wedge]
        out = out.union(cq.Workplane("XY", origin=(0, 0, gm.FINGER_Z[0])).polyline(gusset).close().extrude(t))
        out = out.cut(cyl("z", (s * c, pin[0], 0), gm.PIN_R, (gm.FINGER_Z[0] - 1, gm.FINGER_Z[1] + 1)))
    out = out.union(cyl("z", (0, horn[0], 0), TIE_BOSS, gm.TIE_Z))
    drop = [(-k, horn[0] + k), (0.0, horn[0] + 2 * k), (k, horn[0] + k)]  # the horn's boss a teardrop on that bed
    out = out.union(cq.Workplane("XY", origin=(0, 0, gm.TIE_Z[0])).polyline(drop).close().extrude(t))
    return out.cut(cyl("z", (0, horn[0], 0), gm.PIN_R, (gm.TIE_Z[0] - 1, gm.TIE_Z[1] + 1)))


@bone.grown
def bail(mechanical=False):
    """The bail (#967): its rod on an x axis up behind the eyes, an arm down and forward from it to a ball on a neck
    behind each eye, the input arm back to the pitch bar's pin, the shanks' bores in its ends. Drawn in its print
    frame (bail_bed): the rod on the bed, the input arm along it, the arms rising. As Bones (#704): the rod and the
    input arm flat on the bed under the rod, each arm a round strut; printed as drawn (its bores across the layers)."""
    to_bed = np.linalg.inv(bail_bed())
    end = gm.EYE["L"][0] + gm.BAIL_END
    (_, fy, fz), (_, by, bz) = ((to_bed @ (0, *p, 1))[:3] for p in (bail_foot(), gm.BAIL_BALL))
    x0, x1 = gm.BAIL_INPUT_X
    ix, tip = (x0 + x1) / 2, -gm.BAIL_IN
    if not mechanical:
        bed = -3.0
        out = bone.bone((-end, 0, bed), (end, 0, bed), *BAIL_ROD, heads=False)  # its ends flat on the uprights
        out = out.union(
            bone.bone((ix, 0, bed), (ix, tip, bed), *BAIL_INPUT).intersect(box((x0, x1), (-99, 99), (bed, 99)))
        )
    else:
        out = cyl("x", (0, 0, 0), 3.0, (-end, end)).union(lid_mechanical([(0, 0), (tip, 0)], (x0, x1), BAIL_ARM_W))
    for s in (-1, 1):
        x = s * gm.EYE["L"][0]
        if (
            not mechanical
        ):  # its foot's head inside the rod, clear of its bed and its bore's end (#704: flush, Linux's fuse fails)
            reach = math.hypot(fy, fz)
            start = (x, 0.5 * fy / reach, 0.5 * fz / reach)
            out = out.union(bone.bone(start, (x, fy, fz), *BAIL_ARM, up=(0, 1, 0), round=True))
        else:
            out = out.union(lid_mechanical([(0, 0), (fy, fz)], (x - 1.5, x + 1.5), BAIL_ARM_W))
        out = out.union(ball_on((x, fy, fz), (x, by, bz)))
        out = out.cut(cyl("x", (0, 0, 0), gm.PIN_R, sorted((s * end, s * (end - 8)))))
    out = out.cut(cyl("x", (0, tip, 0), gm.PIN_R, (x0, x1)))
    return _placed(out, bail_bed())


@bone.carved
def push_rod(mechanical=False):
    """One push-rod (drawn at x 0): a rod leaning back from the lever's ball down to the bail arm's (#967), a cup round
    each ball. Drawn on its bed (rod_bed): the lever's cup's mouth on it, the bail's cup standing on it on a skirt, its
    mouth up to the bail's neck. Mechanical: a flat bar round the Bone's waist (#809); as a Bone (#703), carved from
    it."""
    at = rod_bed()
    lo, hi = ROD_BED
    back = math.sqrt(math.dist((0, gm.LEVER), gm.BAIL_BALL) ** 2 - (hi - lo) ** 2)
    bar = box((-2.5, 2.5), (0, back), (0, 4.5))
    # as two Bones, each within bone.LONG: one Bone this long carved from its bar empty (#901)
    out = bar if mechanical else bone.chain([(0, 0), (0, back / 2), (0, back)], *ROD_BONE)
    # the skirt: a cone 40 deg off upright from the bed up to where the cup's ball is as steep
    lean = math.radians(40.0)
    rise = hi - CUP_R * math.sin(lean)
    flare = CUP_R * math.cos(lean)
    skirt = cq.Solid.makeCone(flare - rise * math.tan(lean), flare, rise, cq.Vector(0, back, 0))
    out = out.union(ball(CUP_R, (0, 0, lo))).union(ball(CUP_R, (0, back, hi))).union(cq.Workplane().add(skirt))
    out = out.cut(box((-CUP_R, CUP_R), (-CUP_R, back + CUP_R), (-CUP_R, 0)))  # the bed
    # the bail's cup's mouth, CUP_MOUTH past its ball's centre toward the bail's neck
    neck = np.linalg.inv(at)[:3, :3] @ (0, *np.subtract(bail_foot(), gm.BAIL_BALL))
    turn = linkage.rotation((1, 0, 0), math.degrees(math.atan2(neck[2], neck[1])) - 90.0, (0, back, hi))
    out = out.cut(_placed(box((-CUP_R, CUP_R), (back - CUP_R, back + CUP_R), (hi + CUP_MOUTH, hi + CUP_R + 1)), turn))
    for y, z in ((0.0, lo), (back, hi)):
        out = out.cut(ball(gm.BALL_R + 0.1, (0, y, z)))
    return _placed(out, at)


def link(a, b, x, mechanical=False, sizes=LID_BONE):
    """A flat bar in the slab `x` with pin holes along x at the (y, z) points a and b: mechanical or a Bone (#704) of
    `sizes`."""
    return holes(lid_arms([a, b], x, mechanical, sizes), (a, b), x)


def holes(out, pins, x, r=ARM / 2):
    """`out` with the M3 shank's bore along x through the slab `x` at each (y, z) of `pins`, in a boss `r` in radius
    the slab's full thickness: a Bone's dome stops short of its far face, and the part pinned there meets this one face
    to face."""
    for y, z in pins:
        out = out.union(cyl("x", (0, y, z), r, x))
        out = out.cut(cyl("x", (0, y, z), gm.PIN_R, (x[0] - 1, x[1] + 1)))  # past the faces: no slivers on them
    return out


def lid_arms(points, x, mechanical=False, sizes=LID_BONE):
    """The lid drives' bars, links and spokes through the (y, z) `points` in turn, in the slab `x`: mechanical or as Bones
    of `sizes`."""
    return lid_mechanical(points, x) if mechanical else lid_bone(points, x, sizes)


def lid_mechanical(points, x, w=ARM):
    """Mechanical flat arms `w` wide through the (y, z) `points` in turn, filling the slab `x`, round at every joint."""
    out = cyl("x", (0, *points[0]), w / 2, x)
    for a, b in zip(points, points[1:]):
        side = np.array([a[1] - b[1], b[0] - a[0]]) * w / 2 / math.dist(a, b)
        outline = [tuple(map(float, p)) for p in (a + side, b + side, b - side, a - side)]
        arm = cq.Workplane("YZ", origin=(x[0], 0, 0)).polyline(outline).close().extrude(x[1] - x[0])
        out = out.union(arm).union(cyl("x", (0, *b), w / 2, x))
    return out


def lid_bone(points, x, sizes=LID_BONE):
    """Bones (model/printed/bone.py, #704) through the (y, z) `points` in turn, each lying in the slab `x` on its lower
    face, its joints' pins along x, as low as the slab (unclipped: OCCT's clip of one came out empty one way round): the
    lid drives' bars, links and spokes. Every other span's heads, from the first, are 5% smaller, inside its neighbours'
    where they meet: two identical heads fused made an invalid solid, and on Linux so did the bent bar's other way.
    A span longer than LID_SPAN is drawn as two Bones, each half as long."""
    assert sizes[0][1] < x[1] - x[0]
    halved = [points[0]]
    for a, b in zip(points, points[1:]):
        halved += [tuple(np.add(a, b) / 2)] * (math.dist(a, b) > LID_SPAN) + [b]
    out = bone.chain(halved, *sizes, swell=1.0)
    # the bed's z onto x, its x and y onto the gimbal's y and z: a turn about (1, 1, 1), then into the slab
    return cq.Workplane().add(out.val().moved(_at([[0, 0, 1, x[0]], [1, 0, 0, 0], [0, 1, 0, 0]])))


@bone.carved
def pitch_bar(mechanical=False):
    """The pitch bar: the pitch horn's pin up to the bail's input arm, mechanical or a Bone (#708)."""
    hy, hz = gm.PITCH_HORN
    return link((hy + gm.CRANK, hz), gm.BAIL_TIP, gm.PITCH_BAR_X, mechanical)


# The lid drives' arms (#967): LID_ARM wide, and LID_BOSS round a pin where two of them or the cap's shell pass close
# (the lid horn's two pins are 6 mm apart; the link's end is 7.6 mm from the eye line, the lids' sleeves on it).
# The bar and the link lie side by side on the horn's face, so each leaves the horn by a jog (the bar up, the link
# down), which keeps it LID_CLEAR_MM off the other's boss as the horn's arm swings between them
LID_ARM, LID_BOSS = 5.0, 2.5
BAR_JOG, LINK_JOG = (-8.0, 4.5), (-8.0, -2.5)  # (y, z) from each one's pin on the horn to its bend


def _bar(points, bosses):
    """A lid drive's arm through the (y, z) `points` in turn, centred on x 0 in its slab, a pin's boss `bosses` in
    radius at its first point and at its last."""
    w = (gm.LID_X["bar"][1] - gm.LID_X["bar"][0]) / 2
    out = lid_mechanical(points, (-w, w), LID_ARM)
    for pin, r in zip((points[0], points[-1]), bosses, strict=True):
        out = holes(out, [pin], (-w, w), r)
    return out


def lid_bar():
    """One upper lid's bar (drawn centred on x 0): its crank's pin back to the lid horn's, with the horn's arm a
    parallelogram (#698); bent up by the horn, over the link's pin on it (#967)."""
    horn = tuple(np.add(gm.LID_HORN, gm.LID_PIN))
    return _bar([gm.LID_PIN, tuple(np.add(horn, BAR_JOG)), horn], (ARM / 2, LID_BOSS))


def lid_link():
    """One lower lid's link (drawn centred on x 0): its crank's pin, under the eye line, back to the lid horn's inner
    hole (#967); bent down by the horn, under the bar's pin on it."""
    return _bar([gm.LOWER_PIN, tuple(np.add(gm.LINK_PIN, LINK_JOG)), gm.LINK_PIN], (LID_BOSS, LID_BOSS))


@functools.cache
def opening(side):
    """The `side` eye opening seen from the front: its outline (n, 2), (x, z) about its eye's centre as the L eye's
    (the R eye's mirrored), mm. The eye white's cut on Morty's Sculpt (model/skin.py cuts()): the opening in his face is
    the Sculpt's own (#893)."""
    view, region = sk.cuts()[f"{side} eye white"]
    assert view == "front"
    return (np.asarray(region, float) - (gm.EYE[side][0], 0.0)) * ((1, 1) if side == "L" else (-1, 1))


def _offset(outline, by):
    """`outline` (closed, smooth, its middle inside it) with each point moved `by` mm (one size, or one a point) out
    along its normal."""
    t = np.roll(outline, -1, axis=0) - np.roll(outline, 1, axis=0)
    n = np.stack([t[:, 1], -t[:, 0]], axis=1) / np.linalg.norm(t, axis=1)[:, None]
    n *= np.sign(((outline - outline.mean(axis=0)) * n).sum(axis=1))[:, None]
    return outline + n * np.reshape(by, (-1, 1))


def prism(outline, depth=60.0):
    """All the front sees inside `outline` (x, z): it swept forward from the eyes' plane."""
    return cq.Workplane("XZ").polyline([tuple(map(float, p)) for p in outline]).close().extrude(depth)


def cone(outline):
    """Every way out from the eye's centre that the front sees inside `outline` (x, z) on Morty's eyeball
    (gm.MORTY_BALL_R): a solid out past the lids' band, its apex the centre, its sides flat between the outline's
    points. A lid's hidden edges are cut along it, so each lies at one lid angle through the band's depth (the prism,
    cut along the view, lies 5 deg further round on the band's inside at the top rim)."""
    x, z = outline.T
    p = np.stack([x, -np.sqrt(gm.MORTY_BALL_R**2 - x**2 - z**2), z], axis=1) * (60.0 / gm.MORTY_BALL_R)
    far = p.mean(axis=0) * (60.0 / np.linalg.norm(p.mean(axis=0)))

    def face(*corners):
        return cq.Face.makeFromWires(cq.Wire.makePolygon([cq.Vector(*map(float, c)) for c in corners], close=True))

    faces = [
        f for a, b in zip(p, np.roll(p, -1, axis=0), strict=True) for f in (face((0, 0, 0), a, b), face(far, b, a))
    ]
    return cq.Workplane().add(cq.Solid.makeSolid(cq.Shell.makeShell(faces)))


def _up(shape, deg):
    """`shape` turned `deg` up about the eye line, as a lid turns."""
    return _placed(shape, linkage.rotation((1, 0, 0), -deg))


def _wedge(deg, x, r=45.0):
    """The lid angles `deg` (from, to: from forward toward up) out to `r` from the eye line, between the planes `x`."""
    arc = np.radians(np.linspace(*deg, 24))
    fan = [(0.0, 0.0)] + [(-r * math.cos(t), r * math.sin(t)) for t in arc]
    return cq.Workplane("YZ", origin=(x[0], 0, 0)).polyline(fan).close().extrude(x[1] - x[0])


def _spoke(deg, back, x, w):
    """A lid's spoke in the slab `x`, `w` wide: one edge on the line from the eye line at `deg`, the other
    `back` (1 or -1: toward greater lid angles, or lesser) of it, out to the band's outer face."""
    e, n = (np.array([-math.cos(math.radians(d)), math.sin(math.radians(d))]) for d in (deg, deg + back * 90.0))
    arm = [(0.0, 0.0), 45.0 * e, 45.0 * e + w * n, w * n]
    arm = cq.Workplane("YZ", origin=(x[0], 0, 0)).polyline([tuple(map(float, q)) for q in arm]).close()
    return arm.extrude(x[1] - x[0]).intersect(ball(gm.LID_R[1]))


# Each lid's tail (#967): its band running on behind its inner end to its spoke, under his skin. Between the planes
# TAIL_X (from the eye's centre: the upper's from its spoke's slab, 0.2 mm off the bar's and the link's, which cross
# the band's radius beside it, out to short of the yaw bearing's neck; the lower's from its spoke's slab out to its band) and
# the lid angles TAIL_DEG (shut)
TAIL_X = {"upper": (-gm.LID_X["upper"][1], -21.5), "lower": (-gm.LID_X["lower"][1] + 0.05, -31.0)}
TAIL_DEG = {"upper": (20.0, 138.0), "lower": (-134.0, 28.0)}
CRANK_W = {"upper": 8.0, "lower": 7.0}  # each lid's crank's width, for its servo's stall at SF 2 (a hand sum)
# A lid's edges follow every third point of its opening's outline, 6 mm apart, straight between them (0.13 mm inside
# the outline at most): each point is a face on the lid, and the lid drives' sweep reads every face (#1053)
RIM_EVERY = 3


@functools.cache
def _bands(side):
    """(upper, lower): the `side` eye's two lids' bands, shut, about the L eye's centre (gm.LID_R), between two cones
    about the eye line (gm.LID_ENDS). Shut, the two fill their opening as the front sees it, and each runs on
    gm.LID_COVER deg past the rim it hides behind (the upper not along the top rim's middle, gm.COVER_FREE) and
    gm.LID_TIPS past the opening's inner corner. The opening's outline, its lower half drawn in to the cap's bottom edge
    (gm.CAP_LOW) and all of it lifted gm.LOWER_TRAVEL about the eye line, parts them: the lower lid under it (its edge
    is the bottom rim's own curve), the upper inside it, gm.LID_SLIT in. Each has its tail."""
    rim = opening(side)[::RIM_EVERY]
    band = ball(gm.LID_R[1]).cut(ball(gm.LID_R[0]))
    ended = band
    for deg, way in zip(gm.LID_ENDS, (-1, 1), strict=True):
        reach = 45.0 / math.tan(math.radians(abs(deg)))
        ended = ended.cut(
            cq.Workplane().add(cq.Solid.makeCone(0.0, reach, 45.0, cq.Vector(0, 0, 0), cq.Vector(way, 0, 0)))
        )
    seen, (past, height) = cone(rim), gm.LID_TIPS
    tips = prism(_offset(rim, past)).intersect(box((-60, 0), (-70, 1), (-height, height)))  # the outer one is a pole
    over = _up(seen, gm.LID_COVER).cut(box((-gm.COVER_FREE, gm.COVER_FREE), (-70, 70), (-70, 70)))
    # the two lids' edges that show are cut as the front sees them, along the view, when the lower lid is open: along
    # the cap's bottom edge
    low = np.where(rim[:, 1:] < 0, rim * gm.CAP_LOW, rim)
    lifted, inside = _up(prism(low), gm.LOWER_TRAVEL), _up(prism(_offset(low, -gm.LID_SLIT)), gm.LOWER_TRAVEL)
    tails = {k: band.intersect(_wedge(TAIL_DEG[k], TAIL_X[k])) for k in TAIL_X}
    upper = ended.intersect(seen.union(tips).union(over)).union(tails["upper"]).intersect(inside)
    upper = upper.union(tails["upper"].cut(seen))  # on past its own back edge, over the top rim
    lower = ended.intersect(seen.union(tips).union(_up(seen, -gm.LID_COVER))).union(tails["lower"]).cut(lifted)
    return upper, lower


def _lid(band, travel, which, name, pin, side):
    """A lid (#967), at rest (open): its `band` (shut) turned `travel` open, and between the eyes its spoke from the
    band's tail to its sleeve on the lids' shank, and its crank (in the slab `name`'s) to `pin`, whose boss reaches
    the bar's and the link's slab. Drawn for the L eye, the R its mirror."""
    back = 1 if which == "upper" else -1
    slab, sleeve, crank = (tuple(sorted(-u for u in gm.LID_X[k])) for k in (which, which + " sleeve", name))
    out = _up(band, travel).union(_spoke(gm.SPOKES[which] + travel, back, slab, gm.SPOKE_W[which]))
    out = out.union(cyl("x", (0, 0, 0), gm.HUB_R, sleeve)).union(lid_mechanical([(0, 0), pin], crank, CRANK_W[which]))
    reach = (min(crank[0], -gm.LID_X["bar"][0]), max(crank[1], -gm.LID_X["bar"][1]))  # to the bar's, the link's face
    out = holes(out, [pin], reach, CRANK_W[which] / 2)
    out = out.cut(cyl("x", (0, 0, 0), gm.PIN_R, (sleeve[0] - 1, sleeve[1] + 1)))
    return out if side == "L" else out.mirror("YZ")


def upper_lid(side):
    """The `side` upper lid (#967): at rest, open behind its opening's top rim, its crank's pin gm.LID_PIN on the lid bar,
    its spoke behind the eye line."""
    return _lid(_bands(side)[0], gm.UPPER_TRAVEL, "upper", "upper", gm.LID_PIN, side)


def lower_lid(side):
    """The `side` lower lid (#967): open, its edge on its opening's bottom rim; its crank's pin gm.LOWER_PIN on the lid
    link, in its own slab further from the midline than its spoke's."""
    return _lid(_bands(side)[1], -gm.LOWER_TRAVEL, "lower", "crank", gm.LOWER_PIN, side)


# Each yaw bearing (#967, model/gimbal.py RAIL_R), about the plane of the yaw axis and the bearing's way out of the
# sphere: its strip's sides from that plane (RAIL_LAT, - inboard and forward); the web on it, a blade from RAIL_WEB mm
# from the eye's centre out to the strip, its sides WEB_LAT, which keeps RAIL_ROOM from what the yaw swings over it;
# the pad under that sweep, as deep as the sphere leaves and PAD_LAT wide (a 1.5 mm strip alone, as the layout's rough
# CAD drew it, bends at 120 MPa under its post with the eye held and the pitch servo stalled); the neck it leaves the
# lids' shell by, RAIL_NECK deg on from the strip's end and out to RAIL_OUT mm; and the pylon under the neck's tip, its
# sides from that tip in x and y, a buttress forward from PYLON_KNEE (z) down to PYLON_TOE (y from the tip) on the plate
RAIL_LAT, WEB_LAT, PAD_LAT = (-5.0, 3.0), (-3.0, 1.0), (-16.0, 16.0)
RAIL_WEB, RAIL_NECK, RAIL_OUT, RAIL_ROOM = 27.0, 16.0, 39.0, 2.0
# the pad's front corner toward the other eye is cut back to the yaw axis' plane, from PAD_IN inboard of the axis on:
# yawed in and pitched down, the cap's rim, which reaches its opening's bottom rim, swept 0.2 mm from it (#967)
PAD_IN = 6.0
PYLON, PYLON_KNEE, PYLON_TOE = ((-5.0, 1.0), (-2.5, 2.5)), -23.0, -9.0


def rail():
    """The L yaw bearing (#967; the R its mirror): a post under the yoke's bottom bar, the yaw shank's bore down it, on
    a strip of a sphere inside the lids' shell and a web over it, which run back and inboard from under the yoke to the
    belt behind the eye; a neck leaves the shell there, on a pylon on the plate. The web keeps under the sweep of the
    crank and of the tie-bar's boss on its pin."""
    eye, (r0, r1) = np.array(gm.EYE["L"]), gm.RAIL_R
    a, phi = math.radians(-gm.RAIL_EXIT[0]), math.radians(gm.RAIL_EXIT[1])
    down = np.array([0.0, 0.0, -1.0])
    way = np.array([math.sin(a), -math.cos(a) * math.cos(phi), math.cos(a) * math.sin(phi)])  # where it leaves
    n = np.cross(down, way)
    n /= np.linalg.norm(n)
    end, neck = math.acos(float(down @ way)), math.radians(RAIL_NECK)
    plane = cq.Plane(origin=tuple(eye), xDir=tuple(down), normal=tuple(n))

    def fan(t0, t1, lat=RAIL_LAT):
        pts = [(0.0, 0.0)] + [(60 * math.cos(t), 60 * math.sin(t)) for t in np.linspace(t0, t1, 24)]
        return cq.Workplane(plane).polyline(pts).close().extrude(lat[1] - lat[0]).translate(tuple(n * lat[0]))

    def shell(lo, hi):
        return ball(hi, tuple(eye)).cut(ball(lo, tuple(eye)))

    strip = shell(r0, r1)
    out = strip.intersect(fan(0.0, end))
    web = shell(RAIL_WEB, r1).intersect(fan(0.0, end + neck, WEB_LAT))
    # yawed, the tie-bar's boss sweeps under the crank's pin and the crank's head over it: the web keeps RAIL_ROOM
    # under and outside each, and under the boss's sweep a pad as wide as the sphere allows carries the post instead
    # (the boss's wedge on its bed reaches root 2 of its radius from the pin)
    boss, head = (gm.CRANK + r + RAIL_ROOM for r in (TIE_BOSS * math.sqrt(2), CRANK_BONE[0][0]))
    under = gm.FINGER_Z[0] - RAIL_ROOM
    web = web.cut(cyl("z", (eye[0], 0, 0), boss, (under, 0.0)))
    out = out.union(web.cut(cyl("z", (eye[0], 0, 0), head, (gm.YAW_CRANK_Z[0] - RAIL_ROOM, 0.0))))
    pad = ball(r1, tuple(eye)).intersect(fan(0.0, end, PAD_LAT))
    pad = pad.intersect(box((eye[0] - r1, eye[0] + r1), (-gm.POST_R, r1), (-r1, under)))
    out = out.union(pad.cut(box((eye[0] - r1, eye[0] - PAD_IN), (-gm.POST_R - 1.0, 0.0), (-r1, under))))
    out = out.union(shell(r0, RAIL_OUT).intersect(fan(end, end + neck)))
    tip = eye + RAIL_OUT * way
    (x0, x1), (y0, y1) = PYLON
    top, floor = tip[2] + 1.0, gm.PLATE_Z[1]
    side = [(y1, floor), (y1, top), (y0, top), (y0, PYLON_KNEE), (PYLON_TOE, floor)]
    side = [(tip[1] + y, z) for y, z in side]
    out = out.union(cq.Workplane("YZ", origin=(tip[0] + x0, 0, 0)).polyline(side).close().extrude(x1 - x0))
    z = (-math.sqrt(r0**2 - gm.POST_R**2) - 0.2, gm.YAW_CRANK_Z[0])
    out = out.union(cyl("z", (eye[0], 0, 0), gm.POST_R, z))
    return out.cut(cyl("z", (eye[0], 0, 0), gm.PIN_R, (z[1] - 8.0, z[1])))


@bone.grown
def frame(mechanical=False):
    """The gimbal frame (Skeleton): a plate under the eyes' drives, up between the realistic skull's coronoids and condyles
    (#838, model/gimbal.py PLATE_Z), with a yaw bearing under each yoke, on a pylon behind its eye (#967, rail), the
    bail's uprights with the shanks' bores, a foot behind each cheek hanging a beam under the eyes (#901, its ends and
    the feet inside Morty's cheeks, #967), the lids' carrier, a wall on the midline from their shank between the eyes
    back to a post on the plate (#967, model/gimbal.py WALL_Z), the
    jaw's lugs on risers at the condyles (model/neck.py JAW, their shanks' tapping holes), a collar on posts round each
    servo at its tab plate (the yaw and the mouth servo hanging under the plate, through it where they pass), a window
    either side of the yaw servo's for the realistic skull's maxillae (#967, model/gimbal.py WINDOW_X), and the holes
    the head mount (model/printed/neck.py) is screwed up through. As Bones (#708): each upright and riser a waisted strut
    up from the plate in its slab to a round boss round the shank's bore; the mechanical frame takes them
    in (bone.grown: OCCT carved the Bones out of it empty or broken, #838)."""
    from model.printed.neck import TAP_R, strut  # here: model.printed.neck imports this module

    c, (bottom, top) = gm.EYE["L"][0], gm.PLATE_Z
    by, bz = gm.BAIL
    # each bail upright in section (y, z), mechanical: twice as deep on the plate as at its boss, as it stands half
    # as tall again as it did (#967)
    upright = [(by - 8, top), (by + 8, top), (by + 4, bz), (by + 4, bz + 4), (by - 4, bz + 4), (by - 4, bz)]
    (y0, y1), edge = gm.PLATE_Y, c + gm.FOOT_X[1]
    jy, jz = neck.JAW
    out = box((-gm.PLATE_X, gm.PLATE_X), (y0, gm.BACK_Y), gm.PLATE_Z)
    out = out.union(box((-gm.BACK_X, gm.BACK_X), (gm.BACK_Y, y1), gm.PLATE_Z))
    out = out.union(box((-edge, edge), (y0, y0 + 4), gm.PLATE_Z))  # its front out to the feet
    out = out.union(box((-gm.BEAM_X, gm.BEAM_X), gm.CHEEK_Y, gm.BEAM_Z))  # the bar, a beam (#852) under the lids (#901)
    bearing = rail()
    for s in (-1, 1):
        bx = sorted((s * (c + gm.BAIL_END), s * (c + gm.BAIL_END + 4)))
        ux = sorted(s * (c + u) for u in gm.FOOT_X)
        lx = sorted(s * u for u in neck.JAW_LUG_X)
        # the cheek curves in under the beam's end: its lower outer corner cut back BEAM_CUT, the arm and the foot that
        # far up
        z0, z1 = gm.BEAM_Z[0] + gm.BEAM_CUT, gm.BEAM_Z[1]
        # the foot behind the cheek, and an arm from it to the beam's end (#967)
        out = out.union(box(ux, gm.FOOT_Y, (z0, top)))
        end = [(s * x, y) for x in (gm.BEAM_X - 6.0, gm.BEAM_X) for y in gm.CHEEK_Y]
        arm = np.array(end + [(x, y) for x in ux for y in (gm.FOOT_Y[0], gm.FOOT_Y[0] + 4.0)])
        arm = [tuple(map(float, arm[i])) for i in ConvexHull(arm).vertices]
        corner = [(s * (gm.BEAM_X - gm.BEAM_CUT), gm.BEAM_Z[0]), (s * gm.BEAM_X, gm.BEAM_Z[0]), (s * gm.BEAM_X, z0)]
        depth = gm.CHEEK_Y[1] - gm.CHEEK_Y[0]  # the XZ workplane extrudes toward -y
        out = out.cut(cq.Workplane("XZ", origin=(0, gm.CHEEK_Y[1], 0)).polyline(corner).close().extrude(depth))
        out = out.union(cq.Workplane("XY", origin=(0, 0, z0)).polyline(arm).close().extrude(z1 - z0))
        out = out.union(bearing if s == 1 else bearing.mirror("YZ"))  # each yoke's (#967): both styles
        if mechanical:
            out = out.union(cq.Workplane("YZ", origin=(bx[0], 0, 0)).polyline(upright).close().extrude(bx[1] - bx[0]))
            out = out.union(box(lx, (jy - neck.JAW_FIXED_R, jy + neck.JAW_FIXED_R), tuple(sorted((top, jz))))).union(
                cyl("x", (0, jy, jz), neck.JAW_FIXED_R, lx)
            )
        else:  # from inside the plate, flat on top under the yoke's stem; each upright and riser up its slab's middle
            for xs, y, foot, z, r in ((bx, by, by, bz, 4.0), (lx, jy, jy, jz, neck.JAW_FIXED_R)):
                # a waisted strut, a round boss at its top (a light mesh); its sides 0.25 mm in from its slab's, as a
                # strut's flush on the plate's edge reads back from Linux's STEP crossing the plate's (#851)
                x, h = sum(xs) / 2, (xs[1] - xs[0]) / 2 - 0.25
                out = out.union(strut((x, foot, top - 1), (x, y, z), (r, h), (r - 1.0, h))).union(
                    cyl("x", (0, y, z), r, xs)
                )
        out = holes(out, [(by, bz)], bx).cut(cyl("x", (0, jy, jz), TAP_R, lx))
    # the lids' carrier (#967): both styles, as the yaw bearings
    (wy0, wy1), half = gm.WALL_POST
    wall = box((-gm.WALL_X, gm.WALL_X), (0.0, wy1), gm.WALL_Z).union(
        box((-half, half), (wy0, wy1), (top, gm.WALL_Z[1]))
    )
    wall = wall.union(cyl("x", (0, 0, 0), gm.HUB_R, (-gm.WALL_X, gm.WALL_X)))
    out = out.union(wall).cut(cyl("x", (0, 0, 0), gm.PIN_R, (-gm.WALL_X - 1, gm.WALL_X + 1)))
    for x, y in neck.HEAD_SCREWS:  # the head mount's screws (model/printed/neck.py)
        out = out.cut(cyl("z", (x, y, 0), 1.7, gm.PLATE_Z))
    out = out.cut(cyl("z", (0, neck.HEAD_AXES["pan"][0][1], 0), neck.FRAME_OPEN_R, gm.PLATE_Z))
    # each jaw pivot boss' notch in the plate, from its lug's face to as far past the boss as the boss stands off
    # the lug (#968: the notch was the boss' own width, its walls on the boss' two faces)
    notch = (neck.JAW_LUG_X[1], neck.JAW_X[1] + neck.JAW_X[0] - neck.JAW_LUG_X[1])
    for sign in (-1, 1):
        out = out.cut(cyl("x", (0, jy, jz), neck.BOSS_R + 1.6, sorted(sign * x for x in notch)))
    drives = {label: gm.servo_matrix(face, shaft, tab) for label, (face, shaft, tab, _) in gm.drives().items()}
    lids = [m for label, m in drives.items() if label.endswith(" lid")]
    servos = [*drives.values(), gm.servo_matrix(*neck.drives()["mouth"][:3])]  # the mouth's, behind the jaw (#838)
    tz0 = envelopes.SERVO["tabs"][2][0]
    lo, hi = post(servos[-1], envelopes.SERVO["tab_holes"][0], (tz0 - 3.0, tz0))
    out = out.union(box((lo[0], hi[0]), tuple(sorted((lo[1], y0 + 1))), gm.PLATE_Z))
    # the maxillae's windows (#967) from the yaw servo's collar (its posts stay on the plate) out to WINDOW_X, open in
    # front (a bar closed each to the yoke's old bearing, inside the lids' shell): after the collars and the mouth
    # servo's web, which would fill them
    tabs = envelopes.SERVO["tabs"][0]
    inner = sorted((servos[0] @ (x, 0, 0, 1))[0] for x in (tabs[0] - 2, tabs[1] + 2))
    for m in servos:
        out = out.cut(passes(m))
    for m in servos:  # on the plate's top, or hanging from its underside; a lid servo's on its stand (#967)
        lid = any(m is other for other in lids)
        out = out.union(collar(m, top if (m @ (0, 0, 0, 1))[2] > top else bottom, posts=not lid))
        if lid:
            out = out.union(lid_stand(m, top))
    for s, x in zip((-1, 1), inner, strict=True):
        out = out.cut(box(sorted((x, s * gm.WINDOW_X)), (y0, gm.WINDOW_Y), gm.PLATE_Z))
    for (x0, x1), depth, flare in gm.BACK_POCKETS:  # room for the neck past the pan's ends (#967)
        pocket = [(x0, y1 + 1), (x0, y1 - depth), (x1, y1 - depth), (x1 + flare, y1), (x1 + flare, y1 + 1)]
        out = out.cut(cq.Workplane("XY", origin=(0, 0, bottom)).polyline(pocket).close().extrude(top - bottom))
    return out


def passes(m):
    """Where a servo placed by m passes through the plate: its case, its tab plate and its gear top's bosses with the
    spline over them, 0.3 mm clear."""
    s = envelopes.SERVO
    (x0, x1), (y0, y1), (z0, z1) = s["case"]
    (tx0, tx1), (ty0, ty1), (tz0, tz1) = s["tabs"]
    local = box((x0 - 0.3, x1 + 0.3), (y0 - 0.3, y1 + 0.3), (z0 - 0.3, z1 + 0.3))
    local = local.union(box((tx0 - 0.3, tx1 + 0.3), (ty0 - 0.3, ty1 + 0.3), (tz0 - 0.3, tz1 + 0.3)))
    (bx, by, br), (cx, _, cr) = s["boss"]
    top = box((cx - cr - 0.5, bx + br + 0.5), (by - br - 0.5, by + br + 0.5), (s["tip_z"] - 0.3, z0))
    return _moved(local.union(top), m)


def lid_stand(m, floor):
    """What a lid servo's collar stands on (#967): behind the belt the R one hangs over the hub on the cranium tray's
    riser, so no post can go down under its tab holes. A shelf under the servo's case, from the collar's lower edge
    out past the case's outer end, on a post down to `floor` (the plate) there, outboard of the hub. Both sides alike."""
    case, tabs = (
        (m @ np.c_[list(itertools.product(*envelopes.SERVO[k])), np.ones(8)].T)[:3].T for k in ("case", "tabs")
    )
    side = np.sign(case[:, 0].sum())  # the case's side of the head
    outer = side * np.abs(case[:, 0]).max()
    inner = side * np.abs(tabs[:, 0]).max()  # the tab plate's face on the case's side: the collar is on it
    foot = tabs[:, 2].min() - 2.0  # the collar's lower edge
    y = (case[:, 1].min() + 2.0, case[:, 1].max() - 2.0)
    shelf = box(sorted((inner, outer + side * 4.0)), y, (foot, foot + 3.0))
    return shelf.union(box(sorted((outer + side * 1.0, outer + side * 4.0)), y, (floor, foot + 3.0)))


def collar(m, floor, posts=True):
    """A plate round the servo's case at its tab plate, with its two screw holes, on a post under each hole down (or up)
    to `floor`, but where the servo's case stands between the hole and the floor: under the tabs, or over them when
    the floor is on their side (a servo hanging under the plate). `posts` False: the plate alone (lid_stand)."""
    s = envelopes.SERVO
    (x0, x1), (y0, y1), _ = s["case"]
    (tx0, tx1), (ty0, ty1), (tz0, _) = s["tabs"]
    up = floor > (m @ (0, 0, 0, 1))[2]
    z = (0.0, 3.0) if up == (m[2, 2] > 0) else (tz0 - 3.0, tz0)  # local z runs from the tabs away from the horn
    local = box((tx0 - 2, tx1 + 2), (ty0 - 2, ty1 + 2), z).cut(box((x0 - 0.3, x1 + 0.3), (y0 - 0.3, y1 + 0.3), z))
    for hx, hy in s["tab_holes"]:
        local = local.cut(cq.Workplane("XY").circle(s["tab_r"]).extrude(3).translate((hx, hy, z[0])))
    out = _moved(local, m)
    case = (m @ np.c_[list(itertools.product(*s["case"])), np.ones(8)].T)[:3].T
    clo, chi = case.min(axis=0), case.max(axis=0)
    for hole in s["tab_holes"] if posts else ():
        lo, hi = post(m, hole, z)
        span = (floor, hi[2]) if floor < lo[2] else (lo[2], floor)
        if (lo[:2] < chi[:2]).all() and (hi[:2] > clo[:2]).all() and span[0] < chi[2] and span[1] > clo[2]:
            continue  # the case stands between: the other post and the plate hold it
        out = out.union(box((lo[0], hi[0]), (lo[1], hi[1]), span))
    return out


def post(m, hole, z=(0, 3)):
    """(lo, hi) corners of the box round a servo's tab hole `hole` (its STEP frame) through the collar (its local z),
    placed by m."""
    hx, hy = hole
    corners = [(hx + a, hy + b, c) for a in (-2.4, 2.4) for b in (-2.4, 2.4) for c in z]
    w = (m @ np.c_[corners, np.ones(8)].T)[:3].T
    return w.min(axis=0), w.max(axis=0)


def _moved(shape, m):
    t = cq.Matrix([list(map(float, row)) for row in m[:3]])
    return cq.Workplane().add(shape.val().transformGeometry(t))


def _placed(shape, m):
    """`shape` moved by the rigid 4x4 m: its geometry stays exact."""
    return cq.Workplane().add(shape.val().moved(_at(m)))


def at_rest(mechanical=False):
    """{eyes part: its solid where model/stages.py places it}, the lids' shank beside them (the M3 steel shank along
    the eye line through the frame's wall and each lid's sleeve); `mechanical`: the Skeleton mechanical (#704)."""
    from model import stages
    from model.printed import PARTS, styled  # here: model.printed imports this module

    out = {}
    for name, p in stages.eyes_sub().parts.items():
        stem = styled(stages.stem(p.file), mechanical)
        out[name] = (PARTS.get(stem) or envelopes.ENVELOPES[stem])().val().moved(_at(p.matrix))
    reach = gm.SPACING / 2 - gm.LID_X["upper"][0]
    out["lid shank"] = cyl("x", (0, 0, 0), gm.PIN_R - fits.CLEARANCE[0], (-reach, reach)).val()
    return out


# the parts moved() carries by a pin on another moving part: each turns on that part's pin
COUPLED = {
    **{f"{s} lid bar:1": f"{s} lid horn:1" for s in "LR"},
    **{f"{s} lid link:1": f"{s} lid horn:1" for s in "LR"},
    **{f"{s} push-rod:1": "bail:1" for s in "LR"},
    "pitch bar:1": "pitch horn:1",
}


def _turn(m):
    """Radians a 4x4 turns about x."""
    return math.atan2(m[2, 1], m[1, 1])


def skeleton(rest, tol=0.1):
    """The gimbal as hinges for gates.certify (#655), in metres: a body per part in `rest`, its pieces a ball of `tol`
    mm on each corner of its tessellation's hull (the surface strays from it by `tol` at most), each part moved() turns
    hinged about x through the point its turn fixes (a COUPLED part on the part that carries it), the parts that turn
    alike about one line on one hinge; and rows(poses), a qpos row per (lid, pitch). Every move at yaw 0 turns about x."""
    probe = gm.moved(-30.0, 10.0)  # a pose that turns every hinge
    s, bodies, hinged, carrier = mujoco.MjSpec(), {}, {}, {}  # hinged: (carrier, line, turn) -> the hinge's part

    def add(name):
        if name not in bodies:
            parent = COUPLED.get(name)
            host = add(parent) if parent else s.worldbody
            if name in probe:
                rel = np.linalg.inv(probe[parent]) @ probe[name] if parent else probe[name]
                y, z = np.linalg.solve(np.eye(2) - rel[1:3, 1:3], rel[1:3, 3])  # the point the turn fixes
                key = (carrier.get(parent), round(y, 6), round(z, 6), round(_turn(rel), 9), " lid" in name)
                carrier[name] = hinged.setdefault(key, name)
                if carrier[name] != name:  # the hinge of a part that turns alike carries it
                    host = bodies[carrier[name]]
            body = bodies[name] = host.add_body(name=name)
            if carrier.get(name) == name:
                body.add_joint(type=mujoco.mjtJoint.mjJNT_HINGE, axis=[1, 0, 0], pos=[0, y * MM, z * MM])
            v = np.array([p.toTuple() for p in rest[name].tessellate(tol)[0]])
            for corner in v[ConvexHull(v).vertices]:
                body.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[tol * MM, 0, 0], pos=corner * MM)
        return bodies[name]

    for name in rest:
        add(name)
    model = s.compile()
    # a lid part turns with the lid servo alone, every other with the pitch alone (moved())
    lid_m, pitch_m = functools.cache(lambda lid: gm.moved(lid, 0.0)), functools.cache(lambda p: gm.moved(0.0, p))

    def rows(poses):
        qpos = np.zeros((len(poses), model.nq))
        for i, (lid, pitch) in enumerate(poses):
            for name in hinged.values():
                m = lid_m(lid) if " lid" in name else pitch_m(pitch)
                turn = _turn(m[name]) - (_turn(m[COUPLED[name]]) if name in COUPLED else 0.0)
                qpos[i, model.jnt_qposadr[model.body(name).jntadr[0]]] = turn
        return qpos

    return model, rows


def _path(segments, step):
    """(lid, pitch) rows `step` deg apart along the segments in turn, each joined straight to the next."""
    ends = [e for s in segments for e in s]
    rows = [ends[0]]
    for a, b in zip(ends, ends[1:]):
        rows += list(np.linspace(a, b, max(1, math.ceil(np.abs(np.subtract(b, a)).max() / step)) + 1)[1:])
    return np.round(rows, 6)  # a value shared by two lines reads the same


def sweep(n_lid=9, n_pitch=7, within=5.0, step=0.1):
    """The lid drives' sweep (#650), on the Skeleton mechanical (#809: the Bones carved from it): each lid, its bar, its link, its
    horn and the lids' shank against every other part over the lid x pitch grid (both lid servos together, yaw 0; model/gimbal.py moved()).
    Every pair over LID_CLEAR_MM apart at rest
    is certified to stay so along the grid's lines that turn it (#655, lines(): gates.certify on skeleton()'s hinges,
    reading the exact solids, the bounding boxes' gap past `within` mm), rows `step` deg apart; the closest it read is
    reported. Every pair closer at rest (a pin, a face sliding on a face, the boss on its shank) is checked for overlap
    at the grid's samples: every move here turns about x, so one of two lifts 0.01 mm along x parts a pair that only
    touches."""
    rest = at_rest(mechanical=True)
    names = ("upper lid:1", "lower lid:1", "lid bar:1", "lid link:1", "lid horn:1")
    drives = [f"{s} {n}" for s in "LR" for n in names] + ["lid shank"]
    spline = {(f"{s} lid horn:1", f"{s} lid servo:1") for s in "LR"}  # the horn's hub on its spline
    pairs = [(a, b) for i, a in enumerate(drives) for b in rest if b not in drives[: i + 1] and (a, b) not in spline]
    # a lid's band is LID_CLEAR_MM over its cap by its radii, wherever either turns (gimbal.report): no closer, so
    # checked for overlap with the pairs that touch
    room = gm.LID_CLEAR_MM + 2 * gm.LID_OVER
    near = {(a, b) for a, b in pairs if _gap(rest[a], rest[b]) < room > rest[a].distance(rest[b])}
    lids, pitches = (
        np.linspace(*np.subtract(gm.LID_EDGES, gm.LID_REST), n_lid),
        np.linspace(-gm.PITCH, gm.PITCH, n_pitch),
    )
    lift = [cq.Location(cq.Vector(e, 0, 0)) for e in (-0.01, 0.01)]
    overlaps, seen = [], set()
    for lid in lids:  # the lid servo's range
        for pitch in pitches:
            m = gm.moved(lid, pitch)
            turned = {k for k in m if " lid" in k}
            for a, b in near:
                # each pair once per angle that moves it
                pose = (a, b, lid if {a, b} & turned else None, pitch if {a, b} & set(m) - turned else None)
                if pose in seen:
                    continue
                seen.add(pose)
                sa, sb = (rest[k].moved(_at(m[k])) if k in m else rest[k] for k in (a, b))
                if _gap(sa, sb) < 0 and max(sa.moved(t).distance(sb) for t in lift) < 0.005:
                    overlaps.append(
                        {"pair": [a, b], "at": {"lid_deg": round(float(lid), 1), "pitch_deg": round(float(pitch), 1)}}
                    )
    model, rows = skeleton(rest)
    moving, closest = set(gm.moved(0, 0)), [within, None, None]

    def certify(pairs, path):
        qpos, posed = rows(path), {}
        row_of = {q.tobytes(): i for i, q in enumerate(qpos)}

        def shape(k, data):
            if k not in posed:
                m = np.eye(4)
                m[:3, :3], m[:3, 3] = data.body(k).xmat.reshape(3, 3), data.body(k).xpos / MM
                posed[k] = rest[k].moved(_at(m)) if k in moving else rest[k]
            return posed[k]

        def separation(model, data, pair):
            row = row_of[data.qpos.tobytes()]
            if posed.get("row") != row:
                posed.clear()
                posed["row"] = row
            a, b = (shape(k, data) for k in pair)
            mm = _gap(a, b)  # a lower bound on the gap; the exact one within `within`
            if mm < within:
                mm = a.distance(b)
            if mm < closest[0]:
                lid, pitch = (round(float(d), 1) for d in path[row])
                closest[:] = mm, list(pair), {"lid_deg": lid, "pitch_deg": pitch}
            return mm

        # a reading under LID_CLEAR_MM is the closest one, so closest carries what the gate reads
        gates.certify(model, qpos, dict.fromkeys(pairs, gm.LID_CLEAR_MM), separation=separation)

    def lines(a, b):
        """The grid's lines a pair is certified along, as (the pitches of its lid lines, the lids of its pitch lines):
        those of the servos that turn it."""
        turns = {" lid" in k for k in (a, b) if k in moving}  # True: the lid servo turns it, False: the pitch servo
        if any(k.endswith(" lid:1") for k in (a, b)) and any(" eyeball " in k for k in (a, b)):
            # a lid and an eye turn about one line through the eyes' centres, so their gap follows the turn between
            # them alone: the lid lines at the pitch's two ends sweep all of it, the lid's range being the wider
            assert np.ptp(lids) >= np.ptp(pitches)
            return pitches[[0, -1]], []
        if False not in turns:
            return pitches[:1], []
        return (pitches, lids) if True in turns else ([], lids[:1])

    groups = {}
    for a, b in pairs:
        if (a, b) not in near:
            groups.setdefault(tuple(map(tuple, lines(a, b))), []).append((a, b))
    for (ps, ls), group in groups.items():
        segments = [((lids[0], p), (lids[-1], p)) for p in ps] + [((lid, pitches[0]), (lid, pitches[-1])) for lid in ls]
        certify(group, _path([s[:: (-1) ** i] for i, s in enumerate(segments)], step))
    return {"clearance_mm": round(closest[0], 2), "pair": closest[1], "at": closest[2], "overlaps": overlaps}


def _gap(a, b):
    """mm between the two solids' bounding boxes along the axis they are furthest apart on (negative: they overlap)."""
    ba, bb = a.BoundingBox(), b.BoundingBox()
    return max(
        max(getattr(ba, f"{k}min") - getattr(bb, f"{k}max"), getattr(bb, f"{k}min") - getattr(ba, f"{k}max"))
        for k in "xyz"
    )


def _at(m):
    """A rigid 4x4 as a CadQuery Location: the solid moves, its geometry stays exact."""
    t = gp_Trsf()
    t.SetValues(*map(float, np.asarray(m)[:3].ravel()))
    return cq.Location(t)
