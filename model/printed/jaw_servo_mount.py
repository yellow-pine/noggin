"""Our jaw servo mount: an independent parametric design (never traced from the designer's mesh) in the eyes frame
(model/geometry.py). A wall the jaw servo's tabs screw onto, the servo body in a window below its back edge, and a foot
screwed onto the eye bracket's bottom rail. Interfaces exact, envelope within 1 mm. Measured numbers:
docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

from model import fits
from model.printed.eye_bracket import box

WALL = {"x": (73.42, 78.42), "y": (-52.6, -30.6), "z": (12.0, 44.66)}
WINDOW = {"y": -42.1, "z": (17.0, 39.66)}  # the servo body sits below y -42.1 between the tabs
TABS = {"yz": [(-48.6, 14.43), (-48.6, 42.23)], "r": 1.1}  # the servo's tab screws, along X
FOOT = {"x": (63.42, 73.42), "y": (-40.6, -30.6), "z": (18.0, 21.0)}
FEET = {"xy": [(65.92, -35.6), (70.92, -35.6)], "r": 1.35}  # M2.5 into the bracket rail, along Z
CORNER_R = 1.91


def build():
    (x0, x1), (y0, y1), (z0, z1) = WALL["x"], WALL["y"], WALL["z"]
    (wz0, wz1), wy = WINDOW["z"], WINDOW["y"]
    out = box((x0, x1), (wy, y1), (z0 + 2, z1 - 2))  # the wall's back, the window below it
    for z in ((z0, wz0), (wz1, z1)):  # the tab ears, round at their corners
        out = out.union(box((x0, x1), (y0, y1), z).edges("|X").fillet(CORNER_R))
    out = out.union(box(FOOT["x"], FOOT["y"], FOOT["z"]).edges("|Z and <X").fillet(CORNER_R))
    out = out.cut(
        cq.Workplane("YZ", origin=(x0 - 1, 0, 0)).pushPoints(TABS["yz"]).circle(TABS["r"]).extrude(x1 - x0 + 2)
    )
    depth = FOOT["z"][1] - FOOT["z"][0] + 2
    return out.cut(
        cq.Workplane("XY", origin=(0, 0, FOOT["z"][0] - 1)).pushPoints(FEET["xy"]).circle(FEET["r"]).extrude(depth)
    )


def features():
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/engine/mating.py)."""
    x, half = fits.slab(*WALL["x"])
    z, foot_half = fits.slab(*FOOT["z"])
    (far, near), r = TABS["yz"], TABS["r"]
    tabs = {"near tab hole": ((x, *near), "x", r, half), "far tab hole": ((x, *far), "x", r, half)}
    return {**tabs, **{f"foot {s}": ((*xy, z), "z", FEET["r"], foot_half) for s, xy in zip("LR", FEET["xy"])}}
