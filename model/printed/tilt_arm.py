"""Our PandT tilt arm: an independent parametric design (never traced from the designer's mesh) in the designer's STL
frame (the PT frame with the arm at the v1 height; geometry.TILT_ARM_SHIFT_Z raises it 5 onto upright v2). A z 30.9..35.9
frame with a window, hung by two side ears on the tilt pivot screws, and the lever (x 3..8) reaching back to the tilt
bar's screw. Interfaces exact, envelope within 1 mm. Measured numbers: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

from model.printed.pan_base import box
from model.printed.upright import rod_x

PLATE_Z = (30.9, 35.9)
FRAME = {"x": (-14.0, 14.0), "y": (-20.5, -5.5)}
WINDOW = {"x": (-6.0, 6.0), "y": (-15.5, -10.5)}
LEVER = {"x": (3.0, 8.0), "end": 29.5}
CORNER_R = 2.0  # the frame's corners, the lever's root and its end
EARS = {"x": [(-14.0, -11.0), (11.0, 14.0)], "y": (-16.5, -9.5), "bottom": 25.9, "corner_r": 2.5}
PIVOT = {"y": -13.0, "z": 28.4, "r": 1.35}  # the tilt pivot screws along X
LEVER_HOLE = {"y": 26.5, "z": 33.4, "r": 1.1}  # the tilt bar's screw along X


def build():
    out = box(FRAME["x"], FRAME["y"], PLATE_Z).union(box(LEVER["x"], (FRAME["y"][1] - 1, LEVER["end"]), PLATE_Z))
    (x0, x1), (y0, y1), (lx0, lx1), mid = FRAME["x"], FRAME["y"], LEVER["x"], sum(PLATE_Z) / 2
    for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1), (lx0, y1), (lx1, y1)):
        out = out.edges("|Z").edges(cq.selectors.NearestToPointSelector((x, y, mid))).fillet(CORNER_R)
    out = out.edges("|X").edges(cq.selectors.BoxSelector((lx0 - 1, LEVER["end"] - 0.1, 0), (lx1 + 1, 99, 99)))
    out = out.fillet(CORNER_R)
    out = out.cut(box(WINDOW["x"], WINDOW["y"], (PLATE_Z[0] - 1, PLATE_Z[1] + 1)))
    for x in EARS["x"]:
        ear = box(x, EARS["y"], (EARS["bottom"], PLATE_Z[0] + 1)).edges("|X and <Z").fillet(EARS["corner_r"])
        out = out.union(ear)
    out = out.cut(rod_x((x0 - 1, x1 + 1), (PIVOT["y"], PIVOT["z"]), PIVOT["r"]))
    return out.cut(rod_x((lx0 - 1, lx1 + 1), (LEVER_HOLE["y"], LEVER_HOLE["z"]), LEVER_HOLE["r"]))
