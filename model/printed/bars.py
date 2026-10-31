"""Our tilt bar and pan bar: independent parametric designs (never traced from the designer's meshes) in the designer's
local frame (geometry.STL_LOCAL: holes along Z, horn end +x). A 5 x 3 bar with round ends about its two holes: r 1.1
for the M2 horn screw, r 1.35 for the M2.5 lever screw. Measured numbers: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

WIDTH, THICK = 5.0, 3.0
HORN_R, LEVER_R = 1.1, 1.35


def tilt():
    return bar(20.0)


def pan():
    return bar(15.0)


def bar(pitch):
    h = pitch / 2
    out = cq.Workplane("XY").slot2D(pitch + WIDTH, WIDTH).extrude(THICK)
    return out.cut(cq.Workplane("XY").pushPoints([(h, 0)]).circle(HORN_R).extrude(THICK)).cut(
        cq.Workplane("XY").pushPoints([(-h, 0)]).circle(LEVER_R).extrude(THICK)
    )
