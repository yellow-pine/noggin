"""Our base plate: an independent parametric design (never traced from the designer's mesh) in the PT frame (Z up, pan
axis Z through the origin). A z -2..3 plate (corners r 5, its front sides slanting in to the 54 wide front edge) with
the pan pivot and bearing recess, three cut-outs and a slot; the r 3 standoffs of both receiver shields, the switch
boards and the wire keeper; the battery box on the left and a U-shaped holder at the back right. Interfaces exact,
envelope within 1 mm, the underside lettering dropped. Measured numbers: docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

from model import fits
from model.printed.pan_turntable import box

PLATE_Z = (-2.0, 3.0)
OUTLINE = [(-27, -25), (27, -25), (60, 33), (60, 135), (-60, 135), (-60, 33)]  # corners r 5
CORNER_R = 5.0
# Through cut-outs (corners r 2): the two triangles 10 inside the slanted sides, under the pan servo, the front slot
TRIANGLES = [[(27, -4.778), (48.494, 33), (27, 33)], [(-27, -4.778), (-27, 23.221), (-42.93, 23.221)]]
CUT_R = 2.0
RECTS = [((-26.5, -14.5), (32.0, 54.9)), ((-6.0, 6.0), (-19.0, -14.0))]
PIVOT_R = 1.3
RECESS = {"r": 9.0, "floor": 0.0}  # the bearing's
BOSS = {"r": 4.75, "top": 5.0}
MOUNT_HOLES = [(-32.5, 29.5), (-8.5, 29.5), (-32.5, 57.4), (-8.5, 57.4)]  # the pan servo mounts' screws
POST_R, HOLE_R = 3.0, 1.1
RECEIVERS = [
    (26.0, 40.5),
    (50.0, 40.5),
    (26.0, 63.5),
    (50.0, 63.5),
    (26.0, 73.5),
    (50.0, 73.5),
    (26.0, 96.5),
    (50.0, 96.5),
]
PINNED = [(50.0, 40.5), (26.0, 63.5), (50.0, 73.5), (26.0, 96.5)]  # each shield's diagonal pair: pins, not holes
RECEIVER_TOP, PIN_TOP = 16.0, 18.0
POSTS = [(6.0, 68.5, 13.0), (6.0, 92.5, 13.0), (34.5, 108.5, 9.0), (-7.5, 40.5, 9.0), (7.5, 40.5, 9.0)]  # (x, y, top)
BATTERY = {"x": (-53.0, -18.5), "y": (70.0, 128.0), "top": 13.0, "wall": 3.0, "floor_r": 8.0}
HOLDER = {"x": (16.0, 53.0), "y": (111.5, 128.0), "top": 11.0, "wall": 2.0, "step": 9.0, "gap_x": (26.0, 43.0)}


def build():
    top = PLATE_Z[1]
    out = rounded(OUTLINE, CORNER_R, PLATE_Z)
    for tri in TRIANGLES:
        out = out.cut(rounded(tri, CUT_R, (PLATE_Z[0] - 1, top + 1)))
    for x, y in RECTS:
        out = out.cut(box(x, y, (PLATE_Z[0] - 1, top + 1)))
    out = out.cut(cyl((0, 0), RECESS["r"], (RECESS["floor"], top + 1))).union(cyl((0, 0), BOSS["r"], (0, BOSS["top"])))
    out = out.cut(cyl((0, 0), PIVOT_R, (PLATE_Z[0] - 1, BOSS["top"] + 1)))
    for xy in MOUNT_HOLES:
        out = out.cut(cyl(xy, HOLE_R, (PLATE_Z[0] - 1, top + 1)))
    for xy in RECEIVERS:
        out = out.union(cyl(xy, POST_R, (top - 1, RECEIVER_TOP)))
        out = out.union(cyl(xy, HOLE_R, (RECEIVER_TOP - 1, PIN_TOP))) if xy in PINNED else hole(out, xy, RECEIVER_TOP)
    for x, y, post_top in POSTS:
        out = hole(out.union(cyl((x, y), POST_R, (top - 1, post_top))), (x, y), post_top)
    return out.union(battery_box()).union(holder())


def battery_box():
    """Walls to z 13 round a pocket floored on the plate top, its long bottom edges filleted r 8 (the pack's cradle)."""
    (x0, x1), (y0, y1), w = BATTERY["x"], BATTERY["y"], BATTERY["wall"]
    pocket = box((x0 + w, x1 - w), (y0 + w, y1 - w), (PLATE_Z[1], BATTERY["top"] + 1))
    pocket = pocket.edges("|Y and <Z").fillet(BATTERY["floor_r"])
    return box(BATTERY["x"], BATTERY["y"], (PLATE_Z[1] - 1, BATTERY["top"])).cut(pocket)


def holder():
    """A U open to the front: back and side walls to z 11, lower blocks to z 9 either side of the x 26..43 gap."""
    (x0, x1), (y0, y1), w, z = HOLDER["x"], HOLDER["y"], HOLDER["wall"], HOLDER["top"]
    out = box(HOLDER["x"], HOLDER["y"], (PLATE_Z[1] - 1, z))
    out = out.cut(box((x0 + w, x1 - w), (y0 - 1, y1 - w), (HOLDER["step"], z + 1)))
    return out.cut(box(HOLDER["gap_x"], (y0 - 1, y1 - w), (PLATE_Z[1], z + 1)))


def hole(out, xy, top):
    """An r 1.1 screw hole down a post to the plate top."""
    return out.cut(cyl(xy, HOLE_R, (PLATE_Z[1], top + 1)))


def rounded(pts, r, z):
    """The polygon extruded over z with every vertical edge filleted r."""
    return cq.Workplane("XY", origin=(0, 0, z[0])).polyline(pts).close().extrude(z[1] - z[0]).edges("|Z").fillet(r)


def cyl(xy, r, z):
    return cq.Workplane("XY", origin=(*xy, z[0])).circle(r).extrude(z[1] - z[0])


def features():
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/engine/mating.py)."""
    z, half = fits.slab(*PLATE_Z)
    names = ("near foot outer", "near foot inner", "far foot outer", "far foot inner")
    feet = {k: ((*xy, z), "z", HOLE_R, half) for k, xy in zip(names, MOUNT_HOLES)}
    pivot_z, pivot_half = fits.slab(PLATE_Z[0], BOSS["top"])
    return {**feet, "pan pivot": ((0.0, 0.0, pivot_z), "z", PIVOT_R, pivot_half)}
