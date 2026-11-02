"""The next Mech's eye gimbal (#630) as CadQuery parts, every size from model/gimbal.py (its frame and its design).
Parts at one eye are drawn about the L eye's centre (the R one's mirror where it differs); the rest in the gimbal's
frame. Bores take the busy pivots' M3 steel shanks; each push-rod's cups close on a ball under its equator."""

import math

import cadquery as cq
import numpy as np

from model import envelopes
from model import gimbal as gm
from model.envelopes import box

LEVER_R, NECK_R, CUP_R, ROD_R, ARM = 2.5, 1.2, gm.BALL_R + 1.5, 2.0, 6.0  # ARM: every printed arm's width
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


def ball_on(base, at):
    """A ball on a neck up from z `base` to its centre `at`: the push-rod's cup closes round it from above."""
    x, y, z = at
    return ball(gm.BALL_R, at).union(cyl("z", (x, y, 0), NECK_R, (base, z)))


def core():
    """The eyeball core: a ball, the seat its cap sits on (forward), the lever up the yaw axis to its ball, and the
    pitch axle's bores along x."""
    top = gm.LEVER - gm.BALL_R - 1.2
    out = ball(gm.CORE_R).union(cyl("y", (0, 0, 0), gm.SEAT_R, (-CAP_BACK, -gm.CORE_R + 3)))
    out = out.union(cyl("z", (0, 0, 0), LEVER_R, (gm.CORE_R - 3, top))).union(ball_on(top, (0, 0, gm.LEVER)))
    for s in (-1, 1):
        out = out.cut(cyl("x", (0, 0, 0), gm.PIN_R, sorted((s * 8.0, s * (gm.CORE_R + 1)))))
    return out


def cap(side):
    """The largest eyeball cap (a Shell): the sphere segment within CAP_HALF of the gaze, flat on its seat, with the
    pupil's seat 1 mm deep, its centre turned TOE_IN toward the other eye."""
    r = gm.CAP_R
    out = ball(r).intersect(box((-r, r), (-r - 1, -CAP_BACK), (-r, r)))
    inward = -1 if side == "L" else 1
    seat_r = r * math.sin(math.radians(gm.PUPIL_DEG))
    seat = cyl("y", (inward * r * math.sin(math.radians(gm.TOE_IN)), 0, 0), seat_r, (-r - 1, -r + 1))
    return out.cut(seat)


def yoke():
    """The yaw yoke: a U from below round the core, the pitch axle's bores through its arms, the stem down the yaw axis
    with its crank (back) on the tie-bar."""
    y = gm.YOKE
    x0, x1, h = y["inner"], y["inner"] + y["wall"], y["half_y"]
    out = box((-x1, x1), (-h, h), (-x1, -x0))
    for s in (-1, 1):
        xs = sorted((s * x0, s * x1))
        out = out.union(box(xs, (-h, h), (-x1, 0))).union(cyl("x", (0, 0, 0), h, xs))
        out = out.cut(cyl("x", (0, 0, 0), gm.PIN_R, xs))
    out = out.union(cyl("z", (0, 0, 0), y["stem_r"], (y["stem_z"], -x1)))
    z = gm.YAW_CRANK_Z
    out = out.union(box((-ARM / 2, ARM / 2), (0, gm.CRANK), z)).union(cyl("z", (0, gm.CRANK, 0), ARM / 2, z))
    out = out.cut(cyl("z", (0, gm.CRANK, 0), gm.PIN_R, z))
    return out.cut(cyl("z", (0, 0, 0), gm.PIN_R, (y["stem_z"], y["stem_z"] + 8)))


def tie_bar():
    """The tie-bar under the yokes' cranks: both eyes' and the yaw horn's pins, one parallelogram."""
    c = gm.EYE["L"][0]
    out = box((-c - ARM / 2, c + ARM / 2), (gm.CRANK - ARM / 2, gm.CRANK + ARM / 2), gm.TIE_Z)
    for x in (-c, 0.0, c):
        out = out.cut(cyl("z", (x, gm.CRANK, 0), gm.PIN_R, gm.TIE_Z))
    return out


def bail():
    """The bail: its rod on an x axis behind the eyes, an arm up to a ball behind each eye, the input arm back to the
    pitch bar's pin, the shanks' bores in its ends."""
    by, bz = gm.BAIL
    end, top = gm.EYE["L"][0] + 8.0, gm.LEVER - gm.BALL_R - 1.2
    out = cyl("x", (0, by, bz), 3.0, (-end, end))
    for s in (-1, 1):
        x = s * gm.EYE["L"][0]
        out = out.union(box((x - 1.5, x + 1.5), (by - ARM / 2, by + ARM / 2), (bz, top)))
        out = out.union(ball_on(top, (x, by, gm.LEVER)))
        out = out.cut(cyl("x", (0, by, bz), gm.PIN_R, sorted((s * end, s * (end - 8)))))
    tip = by + gm.BAIL_IN
    out = out.union(box((-2, 2), (by, tip), (bz - 3, bz + 3))).union(cyl("x", (0, tip, bz), 3.0, (-2, 2)))
    return out.cut(cyl("x", (0, tip, bz), gm.PIN_R, (-2, 2)))


def push_rod():
    """One push-rod (drawn at x 0): a rod back from the lever's ball to the bail arm's, a cup round each ball."""
    z, back = gm.LEVER, gm.BAIL[0]
    out = cyl("y", (0, 0, z), ROD_R, (0, back))
    for y in (0.0, back):
        out = out.union(ball(CUP_R, (0, y, z)).cut(box((-CUP_R, CUP_R), (y - CUP_R, y + CUP_R), (z - CUP_R, z - 2))))
    for y in (0.0, back):
        out = out.cut(ball(gm.BALL_R + 0.1, (0, y, z)))
    return out


def link(a, b, x):
    """A flat bar in the slab `x` with pin holes along x at the (y, z) points a and b."""
    (ya, za), (yb, zb) = a, b
    assert ya == yb, "the drives' bars stand along z"
    w = ARM / 2
    out = box(x, (ya - w, ya + w), sorted((za, zb)))
    for y, z in (a, b):
        out = out.union(cyl("x", (0, y, z), w, x)).cut(cyl("x", (0, y, z), gm.PIN_R, x))
    return out


def pitch_bar():
    hy, hz = gm.PITCH_HORN
    return link((hy + gm.CRANK, hz), (gm.BAIL[0] + gm.BAIL_IN, gm.BAIL[1]), gm.PITCH_BAR_X)


def lid_bar():
    """One lid's bar (drawn centred on x 0): the lid's crank down to its horn."""
    w = (gm.LID_X["bar"][1] - gm.LID_X["bar"][0]) / 2
    return link((gm.CRANK, 0.0), (gm.LID_HORN[0] + gm.CRANK, gm.LID_HORN[1]), (-w, w))


def lid(side):
    """The `side` lid (drawn for L, the R its mirror): a shell wedge about x through the eye centre, its lower edge at LID_REST and LID_SPAN wide, the boss
    on its outboard pole turning on the frame's shank, and the crank back to its bar."""
    ri, ro = gm.LID_R
    arc = np.radians(np.linspace(gm.LID_REST, gm.LID_REST + gm.LID_SPAN, 24))
    fan = [(0.0, 0.0)] + [(-(ro + 5) * math.cos(a), (ro + 5) * math.sin(a)) for a in arc]
    wedge = cq.Workplane("YZ", origin=(-ro - 1, 0, 0)).polyline(fan).close().extrude(2 * ro + 2)
    out = ball(ro).cut(ball(ri)).intersect(wedge)
    bx, cx = gm.LID_X["boss"], gm.LID_X["crank"]
    out = out.union(cyl("x", (0, 0, 0), 4.0, bx)).union(box(cx, (0, gm.CRANK), (-ARM / 2, ARM / 2)))
    out = out.union(cyl("x", (0, gm.CRANK, 0), ARM / 2, cx))
    out = out.cut(cyl("x", (0, gm.CRANK, 0), gm.PIN_R, cx)).cut(cyl("x", (0, 0, 0), gm.PIN_R, (bx[0] + 2, bx[1])))
    return out if side == "L" else out.mirror("YZ")


def frame():
    """The gimbal frame (Skeleton): a plate under everything, the yaw bearings under the yokes' stems, the bail's and
    the lids' uprights with the shanks' bores, and a collar on posts round each servo at its tab plate."""
    c, top = gm.EYE["L"][0], gm.PLATE_Z[1]
    by, bz = gm.BAIL
    out = box((-c - 58, c + 58), (-25, 70), gm.PLATE_Z)
    for s in (-1, 1):
        stem = gm.YOKE["stem_z"]
        out = out.union(cyl("z", (s * c, 0, 0), 5.0, (top, stem))).cut(
            cyl("z", (s * c, 0, 0), gm.PIN_R, (stem - 8, stem))
        )
        bx = sorted((s * (c + 8), s * (c + 12)))
        out = out.union(box(bx, (by - 4, by + 4), (top, bz + 4))).cut(cyl("x", (0, by, bz), gm.PIN_R, bx))
        ux = sorted(s * (c + u) for u in gm.LID_X["upright"])
        out = out.union(box(ux, (-4, by), (-4, 4))).union(box(ux, (by - 4, by + 4), (top, 4)))
        out = out.cut(cyl("x", (0, 0, 0), gm.PIN_R, ux))
    for face, shaft, tab, _ in gm.drives().values():
        out = out.union(collar(gm.servo_matrix(face, shaft, tab), top))
    return out


def collar(m, floor):
    """A plate round the servo's case under its tab plate, with its two screw holes, on a post under each hole down
    to `floor`."""
    s = envelopes.SERVO
    (x0, x1), (y0, y1), _ = s["case"]
    (tx0, tx1), (ty0, ty1), _ = s["tabs"]
    local = box((tx0 - 2, tx1 + 2), (ty0 - 2, ty1 + 2), (0, 3)).cut(
        box((x0 - 0.3, x1 + 0.3), (y0 - 0.3, y1 + 0.3), (0, 3))
    )
    for hx, hy in s["tab_holes"]:
        local = local.cut(cq.Workplane("XY").circle(s["tab_r"]).extrude(3).translate((hx, hy, 0)))
    out = _moved(local, m)
    for hx, hy in s["tab_holes"]:
        corners = [(hx + a, hy + b, z) for a in (-2.4, 2.4) for b in (-2.4, 2.4) for z in (0, 3)]
        w = (m @ np.c_[corners, np.ones(8)].T)[:3].T
        lo, hi = w.min(axis=0), w.max(axis=0)
        out = out.union(box((lo[0], hi[0]), (lo[1], hi[1]), (floor, hi[2])))
    return out


def _moved(shape, m):
    t = cq.Matrix([list(map(float, row)) for row in m[:3]])
    return cq.Workplane().add(shape.val().transformGeometry(t))
