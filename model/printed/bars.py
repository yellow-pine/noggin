"""Our tilt bar and pan bar: independent parametric designs (never traced from the designer's meshes) in the designer's
local frame (geometry.STL_LOCAL: holes along Z, horn end +x). A 5 x 3 bar with round ends about its two holes: r 1.1
for the M2 horn screw, r 1.35 for the M2.5 lever screw. Measured numbers: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

from model import fits

WIDTH, THICK = 5.0, 3.0
HORN_R, LEVER_R = 1.1, 1.35
TILT_PITCH, PAN_PITCH = 20.0, 15.0  # the holes apart


def tilt():
    return bar(TILT_PITCH)


def pan():
    return bar(PAN_PITCH)


def bar(pitch):
    h = pitch / 2
    out = cq.Workplane("XY").slot2D(pitch + WIDTH, WIDTH).extrude(THICK)
    return out.cut(cq.Workplane("XY").pushPoints([(h, 0)]).circle(HORN_R).extrude(THICK)).cut(
        cq.Workplane("XY").pushPoints([(-h, 0)]).circle(LEVER_R).extrude(THICK)
    )


def features(pitch):
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/engine/mating.py)."""
    z, half = fits.slab(0, THICK)
    return {"horn hole": ((pitch / 2, 0, z), "z", HORN_R, half), "lever hole": ((-pitch / 2, 0, z), "z", LEVER_R, half)}
