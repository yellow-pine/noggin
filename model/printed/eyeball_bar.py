"""Our eyeball bar: an independent parametric design (never traced from the designer's mesh) in the eyes frame
(model/geometry.py; L side). A 5 wide slot in the XZ plane, y 2.5..5.5, between its two pin holes along Y at x=-10:
r 1.25 on the eyeball's pin (z 0), r 1.05 on the eye-horn screw (z 27). Measured: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

X, Y, WIDTH = -10.0, (2.5, 5.5), 5.0
HOLES = {0.0: 1.25, 27.0: 1.05}  # z: r


def build():
    z0, z1 = min(HOLES), max(HOLES)
    bar = cq.Workplane("XZ", origin=(X, Y[1], (z0 + z1) / 2)).slot2D(z1 - z0 + WIDTH, WIDTH, angle=90)
    bar = bar.extrude(Y[1] - Y[0])
    for z, r in HOLES.items():
        bar = bar.cut(cq.Workplane("XZ", origin=(X, Y[1] + 1, z)).circle(r).extrude(Y[1] - Y[0] + 2))
    return bar
