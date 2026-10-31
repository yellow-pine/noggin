"""Our L and R regular eyeballs: independent parametric designs (never traced from the designer's meshes) in the eyes
frame (model/geometry.py); drawn about the L eye centre, the R eyeball its mirror about x=29.5. An r 20.5 ball, 3 mm
thick, flat at the front (z -18.5, the pupil's seat) and the back (z 5), solid in its lower inboard-back quadrant
(x <= 5, y <= 0) where the main bracket's M3 pivot screw (r 1.3 along Y) and the eyeball bar's pin (an r 3 boss up to
the bar at y 2.5, its screw r 1.1) go in; the top screw's r 3 hole through the top."""

import cadquery as cq

from model import geometry as g
from model.printed.lid import ball
from model.printed.main_bracket import box

R, WALL, Z, TOP_Y = 20.5, 3.0, (-18.5, 5.0), 20.28
QUADRANT = {"x": 5.0, "y": 0.0}
PIVOT_R, HOLE_FLOOR_Y = 1.3, -14.0  # both screw holes along Y start at y -14
TOP_HOLE_R = 3.0
BOSS = {"r": 3.0, "top": 2.5, "hole_r": 1.1}


def build(side):
    body = left()
    return body if side == "L" else body.mirror("YZ", (g.CENTRE_X, 0, 0))


def left():
    hollow = ball(R - WALL).cut(box((-R, QUADRANT["x"]), (-R, QUADRANT["y"]), Z))
    bx, _, bz = g.EYEBALL_BAR_PINS[1]
    out = ball(R).intersect(box((-R, R), (-R, TOP_Y), Z)).cut(hollow)
    out = out.union(along_y(bx, bz, BOSS["r"], (-2, BOSS["top"])))
    out = out.cut(along_y(0, 0, PIVOT_R, (HOLE_FLOOR_Y, 1))).cut(along_y(bx, bz, BOSS["hole_r"], (HOLE_FLOOR_Y, 3)))
    return out.cut(along_y(0, 0, TOP_HOLE_R, (R - WALL - 1, R + 1)))


def along_y(x, z, r, y):
    """A cylinder along Y from y[0] to y[1] through (x, z)."""
    return cq.Workplane("XZ", origin=(x, y[1], z)).circle(r).extrude(y[1] - y[0])
