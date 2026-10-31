"""Our jaw bar: an independent parametric design (never traced from the designer's mesh) in the designer's
local frame (model/geometry.py STL_LOCAL places it). A 5 mm thick Z: two 3 mm end tabs a 12.5 mm step apart, joined
by a straight band, each tab with its screw hole along Z; the bends' cosmetic radii dropped. Measured numbers:
docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

Y = (-5.0, 0.0)
# The XZ profile: the -x tab (z 4.75..7.75) to x -13, the band, the +x tab (z -7.75..-4.75) from x 16.
PROFILE_XZ = [(-25, 4.75), (-25, 7.75), (-13, 7.75), (16, -4.75), (25, -4.75), (25, -7.75), (16, -7.75), (-13, 4.75)]
END_R = 2.0  # the ends round in plan
HOLES = [((-22.05, -2.5), 1.1), ((22.05, -2.5), 1.35)]  # (x, y), r: along Z through the tabs


def build():
    out = cq.Workplane("XZ", origin=(0, Y[1], 0)).polyline(PROFILE_XZ).close().extrude(Y[1] - Y[0])
    out = out.edges("|Z and (<X or >X)").fillet(END_R)
    for xy, r in HOLES:
        out = out.cut(cq.Workplane("XY", origin=(*xy, -10)).circle(r).extrude(20))
    return out
