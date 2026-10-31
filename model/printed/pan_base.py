"""Our PandT pan base: an independent parametric design (never traced from the designer's mesh) in the PT frame (Z up,
pan axis Z through the origin). A z 3.5..8.5 plate turning on the M3 pan pivot (r 1.75, with a boss on top) over the
bearing (an r 9 recess underneath, to z 5.5), its front-left corner cut at 45 degrees, corners r 5; the upright's slot in front of
the pivot; and the x 20..25 tower on its right edge, two lugs carrying the tilt servo's tab screws along X. Interfaces
exact, envelope within 1 mm, cosmetic fillets dropped. Measured numbers: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

PLATE_Z = (3.5, 8.5)
# the plate outline (z), the 45 degree cut from (-25, -10) to the y 17 back edge; (corner, fillet r)
OUTLINE = [(-25, -25), (25, -25), (25, 26), (20, 26), (20, 17), (2, 17), (-25, -10)]
ROUND = [((-25, -25), 5.0), ((25, -25), 5.0), ((2, 17), 5.0), ((-25, -10), 5.0), ((20, 17), 2.0)]
PIVOT_R, BOSS = 1.75, {"r": 5.0, "top": 11.5}
RECESS = {"r": 9.0, "top": 5.5}  # the bearing's
KEY = {"xy": (0, -8), "r": 1.1}  # the small pin hole in front of the pivot, through the plate
SLOT = {"x": (-11.0, 11.0), "y": (-15.5, -10.5)}  # the upright drops through it
TOWER = {"x": (20.0, 25.0), "y": (-8.5, 26.0), "top": 12.5}
LUGS = {"y": [(-8.5, -2.58), (20.08, 26.0)], "top": 24.26}
TAB = {"y": (-5.04, 22.54), "z": 18.38, "r": 1.1}  # the tilt servo's tab holes along X


def build():
    plate = cq.Workplane("XY", origin=(0, 0, PLATE_Z[0])).polyline(OUTLINE).close().extrude(PLATE_Z[1] - PLATE_Z[0])
    for (x, y), r in ROUND:
        plate = plate.edges("|Z").edges(cq.selectors.NearestToPointSelector((x, y, sum(PLATE_Z) / 2))).fillet(r)
    out = plate
    out = out.union(cq.Workplane("XY", origin=(0, 0, PLATE_Z[1])).circle(BOSS["r"]).extrude(BOSS["top"] - PLATE_Z[1]))
    out = out.union(box(TOWER["x"], TOWER["y"], (PLATE_Z[1] - 1, TOWER["top"])))
    for y in LUGS["y"]:
        out = out.union(box(TOWER["x"], y, (TOWER["top"] - 1, LUGS["top"])))
    out = out.cut(cq.Workplane("XY", origin=(0, 0, PLATE_Z[0])).circle(RECESS["r"]).extrude(RECESS["top"] - PLATE_Z[0]))
    out = out.cut(cq.Workplane("XY").circle(PIVOT_R).extrude(BOSS["top"] + 1))
    out = out.cut(cq.Workplane("XY", origin=(*KEY["xy"], 0)).circle(KEY["r"]).extrude(PLATE_Z[1] + 1))
    out = out.cut(box(SLOT["x"], SLOT["y"], (0, PLATE_Z[1] + 1)))
    tabs = cq.Workplane("YZ", origin=(TOWER["x"][0] - 1, 0, 0)).pushPoints([(y, TAB["z"]) for y in TAB["y"]])
    return out.cut(tabs.circle(TAB["r"]).extrude(TOWER["x"][1] - TOWER["x"][0] + 2))


def box(x, y, z):
    return cq.Workplane("XY").box(x[1] - x[0], y[1] - y[0], z[1] - z[0], centered=False).translate((x[0], y[0], z[0]))
