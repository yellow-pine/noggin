"""Our PandT upright v2: an independent parametric design (never traced from the designer's mesh) in the PT frame
(Z up, pan axis Z through the origin). A wall (x -11..11, y -15.5..-10.5) standing in the pan base's slot down to its
underside, round-topped about the tilt pivot; a shelf behind it resting on the plate over the pan base's pin hole; and
the pan lever (x -8..-3) reaching back and stepping up to the pan bar's screw hole. Interfaces exact, envelope within
1 mm, cosmetic fillets dropped. Measured numbers: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

from model import fits
from model.printed.pan_base import box

WALL = {"x": (-11.0, 11.0), "y": (-15.5, -10.5), "z": (3.5, 33.4)}
TILT = {"y": -13.0, "z": 33.4, "r": 1.1}  # the tilt pivot along X; the wall's top is round about it
SHELF = {"y": (-10.5, -5.5), "z": (8.5, 12.5), "corner_r": 2.0}
PIN = {"xy": (0.0, -8.0), "r": 1.35}  # over the pan base's pin hole
LEVER_X = (-8.0, -3.0)
# The lever's YZ profile: z 17.5..22.5 off the wall, up at about 42 degrees to z 20.5..26.8 under the pan bar
LEVER_YZ = [(-10.5, 17.5), (15.2, 17.5), (18.6, 20.5), (25.5, 20.5), (25.5, 26.8), (17.3, 26.8), (12.5, 22.5)]
LEVER_YZ += [(-10.5, 22.5)]
PAN_LEVER = {"xy": (-5.5, 25.5), "r": 1.1, "end_r": 2.5}  # the pan bar's screw along Z; the lever end round about it


def build():
    y1, half = WALL["y"][1], (WALL["y"][1] - WALL["y"][0]) / 2
    out = box(WALL["x"], WALL["y"], WALL["z"])
    out = out.union(rod_x(WALL["x"], (TILT["y"], TILT["z"]), half))
    shelf = box(WALL["x"], (y1 - 1, SHELF["y"][1]), SHELF["z"])
    out = out.union(shelf.edges("|Z").edges(">Y").fillet(SHELF["corner_r"]))
    out = out.union(cq.Workplane("YZ", origin=(LEVER_X[0], 0, 0)).polyline(LEVER_YZ).close().extrude(5.0))
    (px, py), (bottom, top) = PAN_LEVER["xy"], (LEVER_YZ[2][1], LEVER_YZ[4][1])
    out = out.union(cq.Workplane("XY", origin=(px, py, bottom)).circle(PAN_LEVER["end_r"]).extrude(top - bottom))
    out = out.cut(cq.Workplane("XY", origin=(px, py, bottom - 1)).circle(PAN_LEVER["r"]).extrude(top - bottom + 2))
    out = out.cut(cq.Workplane("XY", origin=(*PIN["xy"], 0)).circle(PIN["r"]).extrude(SHELF["z"][1] + 1))
    return out.cut(rod_x((WALL["x"][0] - 1, WALL["x"][1] + 1), (TILT["y"], TILT["z"]), TILT["r"]))


def rod_x(x, yz, r):
    return cq.Workplane("YZ", origin=(x[0], *yz)).circle(r).extrude(x[1] - x[0])


def features():
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/engine/mating.py)."""
    screw_z, screw_half = fits.slab(*SHELF["z"])
    lever_z, lever_half = fits.slab(LEVER_YZ[2][1], LEVER_YZ[4][1])
    x, half = fits.slab(*WALL["x"])
    return {
        "pan base screw": ((*PIN["xy"], screw_z), "z", PIN["r"], screw_half),
        "lever": ((*PAN_LEVER["xy"], lever_z), "z", PAN_LEVER["r"], lever_half),
        "tilt pivot": ((x, TILT["y"], TILT["z"]), "x", TILT["r"], half),
    }
