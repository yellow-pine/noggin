"""Our top jaw plain: an independent parametric design (never traced from the designer's mesh) in the eyes frame
(model/geometry.py). The lip, the same 5 mm U as the bottom jaw's, two flanges screwed to the front of the main
bracket's bottom rail either side of its stem, and cheeks forward to the jaw hinge carrying the pins the bottom jaw's
ears turn on. Interfaces exact, envelope within 1 mm. Measured numbers:
docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

from model import fits
from model.printed.bottom_jaw import HINGE, arms, lip
from model.printed.main_bracket import box, rod

LIP_Y = (-40.6, -30.6)
FLANGE = {"z": (10.0, 13.0), "x": [(-11.42, 19.58), (39.42, 70.42)], "end_r": 2.0}  # the stem passes between them
HOLES = {"xy": [(x, -35.6) for x in (6.5, 16.5, 42.5, 52.5)], "r": 1.35}  # along Z into the bracket rail
# The cheeks: 3 thick outside the lip's arms, y -54.6..-30.6, z 3..13, round r 5 (HINGE ear_r) about the hinge in
# front and chamfered 3 at 45 degrees under their outer edge.
CHEEK = {"t": 3.0, "y": (-54.6, -30.6), "z": (3.0, 13.0), "chamfer": 3.0}
# The pins, from the cheeks in along the hinge: full radius for `full`, then domed (a sphere r `dome` on the hinge) to
# a flat tip at `length`, flush with the bottom jaw ears' inner faces.
PIN = {"r": 1.75, "full": 4.17, "length": 5.0, "dome": 2.06}


def build():
    (y0, z0), (left, right) = HINGE["yz"], arms()
    out = lip(LIP_Y, FLANGE["z"][0])
    for x, end in zip(FLANGE["x"], (">X", "<X")):
        out = out.union(box(x, LIP_Y, FLANGE["z"]).edges(f"|Z and {end}").fillet(FLANGE["end_r"]))
    (cy0, cy1), (cz0, cz1), r, t, c = CHEEK["y"], CHEEK["z"], HINGE["ear_r"], CHEEK["t"], CHEEK["chamfer"]
    for inner, s in ((left[0], -1), (right[1], 1)):  # s: outward along X
        x = tuple(sorted((inner, inner + s * t)))
        out = out.union(box(x, (y0, cy1), (cz0, cz1))).union(box(x, (cy0, y0), (cz0, z0))).union(rod(*x, r, (y0, z0)))
        wedge = [(inner, cz0), (inner + s * (c + 1), cz0 + c + 1), (inner + s * (c + 1), cz0 - 1), (inner, cz0 - 1)]
        out = out.cut(cq.Workplane("XZ", origin=(0, cy1 + 1, 0)).polyline(wedge).close().extrude(cy1 - cy0 + 2))
        out = out.union(rod(*sorted((inner, inner - s * PIN["length"])), PIN["r"], (y0, z0)).intersect(dome(inner, s)))
    depth = FLANGE["z"][1] - FLANGE["z"][0] + 2
    return out.cut(
        cq.Workplane("XY", origin=(0, 0, FLANGE["z"][0] - 1)).pushPoints(HOLES["xy"]).circle(HOLES["r"]).extrude(depth)
    )


def dome(inner, s):
    """The pin's envelope from the cheek at x `inner` (s: outward along X): its full-radius length, then the sphere."""
    (y0, z0), r, R = HINGE["yz"], PIN["r"], PIN["dome"]
    centre = inner - s * (PIN["full"] - (R * R - r * r) ** 0.5)
    sphere = cq.Workplane("XY").sphere(R).translate((centre, y0, z0))
    return rod(*sorted((inner + s, centre)), r + 1, (y0, z0)).union(sphere)


def features():
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/engine/mating.py)."""
    (left, _), (_, right) = arms()
    full = PIN["full"]  # the pin's full-radius length in from its cheek, before the dome
    spans = {"L pin": (left, left + full), "R pin": (right - full, right)}
    return {k: ((fits.slab(*x)[0], *HINGE["yz"]), "x", PIN["r"], fits.slab(*x)[1]) for k, x in spans.items()}
