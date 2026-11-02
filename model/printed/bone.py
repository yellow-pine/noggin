"""A Bone (GLOSSARY): a Skeleton link between two joints drawn organic, for the parts in model/printed to share (#703).
It lies on the print bed (the joints' z), so its pins stand along Z: flat underneath and domed on top, every face
within 45 deg of upright or facing up (overhang_deg reads it)."""

import math

import cadquery as cq
import numpy as np
import trimesh

SECTIONS = 9  # the loft's sections along the span


def bone(a, b, head, waist, up=(0, 0, 1), round=False, heads=True):
    """A Bone from joint a to joint b (x, y, z; one z, the bed): half-ellipse sections (semi-width, height) lofted from
    `head` at each joint to `waist` mid-span, easing in as cos^2, with a half-ellipsoid head on each joint of the same
    size, so the shaft leaves it tangent. The caller cuts the joint's bore, socket or flat. `round`: whole ellipses,
    their height along `up` (square to the span; a strut off the bed, a and b anywhere), the heads in the same loft.
    `heads` False: flat at both joints (a span the caller ends there)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    span = np.linalg.norm(b - a)
    along = (b - a) / span
    side = np.cross(along, up)
    side /= np.linalg.norm(side)
    top = np.cross(side, along)
    # round: the heads are the loft's own sections past each joint, an ellipsoid's out to near its tip, so the Bone is
    # one loft: an ellipsoid fused on fails on Linux (#737)
    caps = np.radians([75, 55, 30]) if round and heads else []
    stations = [(-head[0] * math.sin(q) / span, math.cos(q)) for q in caps]
    stations += [(t, 1.0) for t in np.linspace(0, 1, SECTIONS)]
    stations += [(1 + head[0] * math.sin(q) / span, math.cos(q)) for q in reversed(caps)]
    wires = []
    for t, f in stations:
        k = math.cos(math.pi * min(max(t, 0), 1)) ** 2  # 1 at the joints, 0 mid-span, flat at both
        w, h = ((wa + (ha - wa) * k) * f for ha, wa in zip(head, waist))
        c, s = cq.Vector(*(a + (b - a) * t)), cq.Vector(*side)
        # its normal -along, so the arc runs from +side up over the top to -side
        arc = cq.Edge.makeEllipse(w, h, c, cq.Vector(*-along), s, 0, 360 if round else 180)
        wires.append(cq.Wire.assembleEdges([arc] if round else [arc, cq.Edge.makeLine(c - s * w, c + s * w)]))
    out = cq.Workplane().add(cq.Solid.makeLoft(wires))
    if heads and not round:
        for p in (a, b):  # a unit half-ball scaled
            m = np.c_[side * head[0], along * head[0], top * head[1], p]
            dome = cq.Solid.makeSphere(1, angleDegrees1=0, angleDegrees2=90)
            out = out.union(cq.Workplane().add(dome.transformGeometry(cq.Matrix([list(map(float, r)) for r in m]))))
    return out


def overhang_deg(shape, keep=lambda centre: True):
    """The worst overhang on `shape` printed as it lies, deg past upright (90: a ceiling), over its faces but the bed's
    (its lowest z), the slivers under 0.01 mm2 a tessellation leaves on a seam, and those whose centre `keep` turns down
    (an exact interface, a socket's crown)."""
    v, f = shape.tessellate(0.01, 0.1)
    mesh = trimesh.Trimesh([p.toTuple() for p in v], f)
    bed = mesh.vertices[:, 2].min()
    on_bed = (np.abs(mesh.vertices[mesh.faces][:, :, 2] - bed) < 1e-6).all(axis=1) | (mesh.area_faces < 0.01)
    down = [n[2] for n, c, flat in zip(mesh.face_normals, mesh.triangles_center, on_bed) if not flat and keep(c)]
    return round(math.degrees(math.asin(max(0.0, -min(down, default=0.0)))), 1)
