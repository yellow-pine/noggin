"""A Bone (GLOSSARY): a Skeleton link between two joints drawn organic, for the parts in model/printed to share (#703).
It lies on the print bed (the joints' z), so its pins stand along Z: flat underneath and domed on top, every face
within 45 deg of upright or facing up (overhang_deg reads it)."""

import math

import cadquery as cq
import numpy as np
import trimesh

SECTIONS = 9  # the loft's sections along the span


def bone(a, b, head, waist):
    """A Bone from joint a to joint b (x, y, z; one z, the bed): half-ellipse sections (semi-width, height) lofted from
    `head` at each joint to `waist` mid-span, easing in as cos^2, with a half-ellipsoid head on each joint of the same
    size, so the shaft leaves it tangent. The caller cuts the joint's bore, socket or flat."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    along = (b - a) / np.linalg.norm(b - a)
    side = cq.Vector(*np.cross(along, (0, 0, 1)))
    wires = []
    for t in np.linspace(0, 1, SECTIONS):
        k = math.cos(math.pi * t) ** 2  # 1 at the joints, 0 mid-span, flat at both
        w, h = (wa + (ha - wa) * k for ha, wa in zip(head, waist))
        c = cq.Vector(*(a + (b - a) * t))
        # its normal -along, so the arc runs from +side up over the top to -side
        arc = cq.Edge.makeEllipse(w, h, c, cq.Vector(*-along), side, 0, 180)
        wires.append(cq.Wire.assembleEdges([arc, cq.Edge.makeLine(c - side * w, c + side * w)]))
    out = cq.Workplane().add(cq.Solid.makeLoft(wires))
    for p in (a, b):
        dome = cq.Solid.makeSphere(1, angleDegrees1=0, angleDegrees2=90)  # a unit half-ball on z 0
        dome = dome.transformGeometry(cq.Matrix([[head[0], 0, 0, p[0]], [0, head[0], 0, p[1]], [0, 0, head[1], p[2]]]))
        out = out.union(cq.Workplane().add(dome))
    return out


def overhang_deg(shape, keep=lambda centre: True):
    """The worst overhang on `shape` printed as it lies, deg past upright (90: a ceiling), over its faces but the bed's
    (its lowest z) and those whose centre `keep` turns down (an exact interface, a socket's crown)."""
    v, f = shape.tessellate(0.01, 0.1)
    mesh = trimesh.Trimesh([p.toTuple() for p in v], f)
    bed = mesh.vertices[:, 2].min()
    on_bed = (np.abs(mesh.vertices[mesh.faces][:, :, 2] - bed) < 1e-6).all(axis=1)
    down = [n[2] for n, c, flat in zip(mesh.face_normals, mesh.triangles_center, on_bed) if not flat and keep(c)]
    return round(math.degrees(math.asin(max(0.0, -min(down, default=0.0)))), 1)
