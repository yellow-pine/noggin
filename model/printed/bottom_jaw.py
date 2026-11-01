"""Our bottom jaw: an independent parametric design (never traced from the designer's mesh) in the eyes frame
(model/geometry.py), jaws closed. The lip, a 5 mm U round the mouth, its arms ending in ears that turn on the top jaw's
pins about the jaw hinge, and the lug the jaw bar screws to. Interfaces exact, envelope within 1 mm. Measured
numbers: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

from model import fits
from model.printed.eye_bracket import box, rod

# The lip's U in XZ: round below z 3 about x 29.5 between these radii, straight arms above.
U = {"x": 29.5, "z": 3.0, "r": (32.92, 37.92)}
LIP_Y = (-54.6, -44.6)
HINGE = {"yz": (-49.6, 8.0), "ear_r": 5.0, "hole_r": 2.0}  # the ears round about the hinge, on the top jaw's pins
# The lug: this XY outline (chamfered at its +x front corner) through z -12.94..-7.94, round r 2.5 about the
# jaw bar's screw hole (r 1.1 along X).
LUG_XY = [(61.42, -58.1), (70.42, -58.1), (70.42, -51.6), (66.42, -44.6), (61.42, -44.6)]
LUG_Z = (-12.94, -7.94)
LUG_HOLE = {"yz": (-58.1, -10.44), "r": 1.1}


def build():
    (y0, z0), r = HINGE["yz"], HINGE["ear_r"]
    out = lip(LIP_Y, z0)
    for x0, x1 in arms():
        out = out.union(rod(x0, x1, r, (y0, z0)))
    out = out.union(cq.Workplane("XY", origin=(0, 0, LUG_Z[0])).polyline(LUG_XY).close().extrude(LUG_Z[1] - LUG_Z[0]))
    out = out.union(rod(LUG_XY[0][0], LUG_XY[1][0], (LUG_Z[1] - LUG_Z[0]) / 2, LUG_HOLE["yz"]))
    out = out.cut(rod(LUG_XY[0][0] - 1, LUG_XY[1][0] + 1, LUG_HOLE["r"], LUG_HOLE["yz"]))
    return out.cut(rod(arms()[0][0] - 1, arms()[1][1] + 1, HINGE["hole_r"], (y0, z0)))


def arms():
    """The U's arms (x0, x1), left then right."""
    r0, r1 = U["r"]
    return (U["x"] - r1, U["x"] - r0), (U["x"] + r0, U["x"] + r1)


def lip(y, top):
    """The U through y (y0, y1), its arms up to z top."""
    r0, r1 = U["r"]
    ring = cq.Workplane("XZ", origin=(U["x"], y[1], U["z"])).circle(r1).circle(r0).extrude(y[1] - y[0])
    out = ring.cut(box((U["x"] - r1 - 1, U["x"] + r1 + 1), (y[0] - 1, y[1] + 1), (U["z"], U["z"] + r1 + 1)))
    for x in arms():
        out = out.union(box(x, y, (U["z"], top)))
    return out


def features():
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/mating.py)."""
    x, half = fits.slab(LUG_XY[0][0], LUG_XY[1][0])
    hinges = {
        f"{s} hinge": ((fits.slab(*arm)[0], *HINGE["yz"]), "x", HINGE["hole_r"], fits.slab(*arm)[1])
        for s, arm in zip("LR", arms())
    }
    return {"lug": ((x, *LUG_HOLE["yz"]), "x", LUG_HOLE["r"], half), **hinges}
