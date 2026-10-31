"""Our bearing block: an independent parametric design (never traced from the designer's mesh) in the PT frame
(Z up, pan axis Z through the origin). An 18 x 5.5 ring, bore r 5, in the base's r 9 recess over its r 4.75 boss.
Measured numbers: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

R, BORE_R, HEIGHT = 9.0, 5.0, 5.5


def build():
    return cq.Workplane("XY").circle(R).circle(BORE_R).extrude(HEIGHT)
