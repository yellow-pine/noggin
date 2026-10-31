"""Our eyes wire keeper: an independent parametric design (never traced from the designer's mesh) in the designer's eyes
base frame. A 30 x 6 strap with round ends, y -22.6..-19.6, dropped over the base's cable holder posts at x 29.5,
z 51 and 75 through r 1.35 holes along Y. Measured numbers: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

X, POSTS_Z = 29.5, (51.0, 75.0)
Y = (-22.6, -19.6)
WIDTH, HOLE_R = 6.0, 1.35


def build():
    # local x along world Z, extruded along +Y
    plane = cq.Plane(origin=(X, Y[0], sum(POSTS_Z) / 2), xDir=(0, 0, 1), normal=(0, 1, 0))
    strap = cq.Workplane(plane).slot2D(POSTS_Z[1] - POSTS_Z[0] + WIDTH, WIDTH).extrude(Y[1] - Y[0])
    holes = cq.Workplane(plane).pushPoints([(z - sum(POSTS_Z) / 2, 0) for z in POSTS_Z]).circle(HOLE_R)
    return strap.cut(holes.extrude(Y[1] - Y[0]))
