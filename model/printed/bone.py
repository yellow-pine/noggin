"""A Bone (GLOSSARY): a Skeleton link between two joints drawn organic, for the parts in model/printed to share (#703).
It lies on the print bed (the joints' z), so its pins stand along Z: flat underneath and domed on top, every face
within 45 deg of upright or facing up (overhang_deg reads it)."""

import itertools
import math

import cadquery as cq
import numpy as np
import trimesh

SECTIONS = 9  # the loft's sections along the span
SWELL = 1.02  # chain()'s heads over its spans' ends: none of their faces on another


def bone(a, b, head, waist, up=(0, 0, 1), round=False, heads=True, swell=1.0):
    """A Bone from joint a to joint b (x, y, z; one z, the bed): half-ellipse sections (semi-width, height) lofted from
    `head` at each joint to `waist` mid-span, easing in as cos^2, with a half-ellipsoid head on each joint of the same
    size, so the shaft leaves it tangent. The caller cuts the joint's bore, socket or flat. `round`: whole ellipses,
    their height along `up` (square to the span; a strut off the bed, a and b anywhere), the heads in the same loft.
    `heads` False: flat at both joints (a span the caller ends there). `swell`: the heads that much larger than the
    span's ends, so no face of one lies on the other (OCCT fused some such pairs wrong, #708)."""
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
            m = np.c_[side * head[0] * swell, along * head[0] * swell, top * head[1] * swell, p]
            dome = cq.Solid.makeSphere(1, angleDegrees1=0, angleDegrees2=90)
            out = out.union(cq.Workplane().add(dome.transformGeometry(cq.Matrix([list(map(float, r)) for r in m]))))
    return out


def chain(points, head, waist, z=0.0, down=False, swell=SWELL):
    """Bones through the (x, y) `points` in turn on the bed z, domed up (`down`: domed down, flat on top): a bar, a
    link or a frame's members (`points` closing on its first for a ring). Every other span's heads, from the first, are
    5% smaller, inside its neighbours' where they meet: two identical heads fused made an invalid solid, and on Linux
    so did a bent bar's other way. Drawn on z 0 domed up and then moved, the one way OCCT fused a ring of them; the
    heads `swell` over the spans' ends (bone())."""
    if down:  # drawn mirrored in y, turned half round x onto the points
        flipped = chain([(x, -y) for x, y in points], head, waist, swell=swell)
        return cq.Workplane().add(flipped.val().moved(cq.Location(cq.Vector(0, 0, z), cq.Vector(1, 0, 0), 180)))
    if z:
        return cq.Workplane().add(chain(points, head, waist, swell=swell).val().moved(cq.Location(cq.Vector(0, 0, z))))

    # shortcut: retries each span at 4 sizes x 2 ways for OCCT's union bugs (#708); drop the retries once OCCT unites
    # them first time on macOS and Linux
    def span(a, b, k, onto=None):
        """The span a-b at k of the sizes, fused onto `onto`: OCCT can fail to fuse a head to a span one way, or leave
        it or the union invalid (or drop a span), at one size and not at a hair under it."""
        for f, (p, q) in itertools.product((1.0, 0.99, 0.98, 0.97), ((a, b), (b, a))):
            size = [tuple(f * k * v for v in s) for s in (head, waist)]
            try:
                out = bone((*p, 0), (*q, 0), *size, swell=swell)
            except ValueError:
                continue
            if not _headed(out.val(), a, b, size[0][0]):  # a head fused away
                continue
            if out.val().isValid() and onto is not None:
                fused = onto.union(out)
                grew = fused.val().Volume() > max(onto.val().Volume(), out.val().Volume())  # kept both
                out = fused if grew else fused.newObject([])
            if out.vals() and out.val().isValid():
                return out
        raise ValueError(f"the Bones through {points}: no valid union of {a} to {b}")

    out = span(*points[:2], 0.95)
    for i, (a, b) in enumerate(zip(points[1:], points[2:])):
        out = span(a, b, 1.0 if i % 2 == 0 else 0.95, out)
    return out


def _headed(shape, a, b, reach):
    """Whether `shape` holds a point half `reach` past each joint a and b ((x, y) on the bed) along its span, just over
    the bed: both heads there."""
    along = np.subtract(b, a) / math.dist(a, b)
    ends = (np.subtract(a, along * reach / 2), np.add(b, along * reach / 2))
    return all(shape.isInside(cq.Vector(*map(float, e), 0.1)) for e in ends)


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
