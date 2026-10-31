"""Our regular pupil: an independent parametric design (never traced from the designer's mesh) in the designer's frame
(the R eye, model/geometry.py EYE_R; the L pupil is the same part placed 59 mm left). The cap of the eyeball's r 20.5
sphere in front of the eyeball's flat face at z -18.5."""

import cadquery as cq

from model import geometry as g
from model.printed.lid import ball

R, FACE_Z = 20.5, -18.5


def build():
    front = cq.Workplane("XY").box(2 * R, 2 * R, FACE_Z + R, centered=(True, True, False)).translate((0, 0, -R))
    return ball(R).intersect(front).translate(g.EYE_R)
