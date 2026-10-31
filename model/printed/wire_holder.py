"""Our PandT wire holder: an independent parametric design (never traced from the designer's mesh) in the PT frame
(Z up, pan axis Z through the origin). A 21 x 6 strap with round ends, z 9..12, dropped over the base's two wire keeper
posts at (+-7.5, 40.5) through r 1.35 holes. Measured numbers: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

POSTS = [(-7.5, 40.5), (7.5, 40.5)]
Z = (9.0, 12.0)
WIDTH, HOLE_R = 6.0, 1.35


def build():
    strap = cq.Workplane("XY", origin=(0, POSTS[0][1], Z[0])).slot2D(15.0 + WIDTH, WIDTH).extrude(Z[1] - Z[0])
    return strap.cut(cq.Workplane("XY", origin=(0, 0, Z[0])).pushPoints(POSTS).circle(HOLE_R).extrude(Z[1] - Z[0]))
