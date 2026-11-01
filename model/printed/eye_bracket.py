"""Our eye bracket: an independent parametric design (never traced from the designer's mesh) in the eyes frame
(model/geometry.py: L eye centre at the origin, +Y up, -Z front). A plate (z 13..18) behind the eyes: the top band
the servo brackets screw onto, the stem the neck clamps, the bottom rail the jaw servo mount screws onto; and a frame
in front of it at eye height carrying the lid pins and the eyeball forks. Interfaces exact, envelope within 1 mm,
cosmetic detail dropped. Measured numbers: docs/research/2026-10-31-model.md [M]. The desk eye bracket is the
designer's first one, the desk build's (geometry.DESK): no rail and no raised band, its stem 5 mm shorter."""

import cadquery as cq

from model import fits
from model import geometry as g

PLATE_Z = (13.0, 18.0)
BAND = {"x": (-18.0, 77.0), "y": (-12.5, 2.5)}  # the top band; its top edge y=2.5 is the rail the eyeball bars ride
RAISED = {"x": (-4.0, 63.0), "top": 8.5}  # the band between the eyeball forks stands up to y 8.5
STEM = {"x": (23.5, 35.5), "bottom": g.STEM_BOTTOM[1]}
RAIL = {"x": (-3.4, 73.4), "y": (-40.6, -30.6), "r": 3.0}  # the bottom rail the jaw servo mount screws onto
# r 1.1 screw holes along Z through the plate [M]: servo bracket feet (L, R, the shared stem one), the top row, the stem,
# the bottom rail (the jaw servo mount's feet at 65.92 and 70.92)
HOLE_R = 1.1
HOLES = (
    [(-13.42, -7.75), (10.24, -0.5), (48.76, -0.5), (72.42, -7.75)]
    + [(x, 5.5) for x in (1.5, 6.5, 11.5, 24.5, 34.5, 47.5, 52.5, 57.5)]
    + [(29.5, y) for y in (-11.6, -16.6, -21.6, -31.6, -36.6)]
    + [(x, -35.6) for x in (1.5, 6.5, 11.5, 16.5, 42.5, 47.5, 52.5, 57.5, 65.92, 70.92)]
)
# The eye-height frame: this XZ profile through y -2.5..2.5, arms chamfered out to the outer lid posts.
FRAME_Y = 2.5
FRAME_XZ = [(-28, -1.5), (-28, 8), (-18, 18), (77, 18), (87, 8), (87, -1.5)]
FRAME_XZ += [(83, -1.5), (83, 7), (77, 13), (-18, 13), (-24, 7), (-24, -1.5)]
# The lid posts (x0, x1, top z), 4 wide, their bottoms round (r 2.5 along X) down to z -4: the outer ones meet the arms,
# the inner ones the plate. Lid pins r 1.75 along X from the post faces 24 mm either side of each eye centre to 20.93
# (the lid ears are |x| 21..24).
POSTS = [(-28.0, -24.0, 7.0), (24.0, 28.0, 13.0), (31.0, 35.0, 13.0), (83.0, 87.0, 7.0)]
POST_BOTTOM = -4.0
LID_PIN = {"r": 1.75, "x": (24.0, 20.93)}
FORK = {"y": (0.0, 4.0), "r": 4.0, "hole_r": 1.6}  # round about each eyeball pivot, the M3 screw through it


def build(desk=False):
    out = box(BAND["x"], BAND["y"], PLATE_Z)
    stem = g.DESK_STEM_BOTTOM[1] if desk else STEM["bottom"]
    out = out.union(box(STEM["x"], (stem, BAND["y"][0] + 1), PLATE_Z))
    if not desk:
        out = out.union(box(RAISED["x"], (BAND["y"][1] - 1, RAISED["top"]), PLATE_Z))
        out = out.union(box(RAIL["x"], RAIL["y"], PLATE_Z).edges("|Z").fillet(RAIL["r"]))
    out = out.union(cq.Workplane("XZ", origin=(0, FRAME_Y, 0)).polyline(FRAME_XZ).close().extrude(2 * FRAME_Y))
    round_z = POST_BOTTOM + FRAME_Y
    for x0, x1, top in POSTS:
        out = out.union(box((x0, x1), (-FRAME_Y, FRAME_Y), (round_z, top))).union(rod(x0, x1, FRAME_Y, (0, round_z)))
    for x0, y0, z0 in (g.EYE_L, g.EYE_R):  # lid pivots along X and eyeball pivots along Y through the eye centres
        for s in (-1, 1):
            a, b = (x0 + s * x for x in LID_PIN["x"])
            out = out.union(rod(min(a, b), max(a, b), LID_PIN["r"], (y0, z0)))
        r, (ya, yb) = FORK["r"], FORK["y"]
        out = out.union(box((x0 - r, x0 + r), FORK["y"], (z0, PLATE_Z[0])))
        out = out.union(cq.Workplane("XZ", origin=(x0, yb, z0)).circle(r).extrude(yb - ya))
        out = out.cut(cq.Workplane("XZ", origin=(x0, yb + 1, z0)).circle(FORK["hole_r"]).extrude(yb - ya + 2))
    depth = PLATE_Z[1] - PLATE_Z[0] + 2
    return out.cut(cq.Workplane("XY", origin=(0, 0, PLATE_Z[0] - 1)).pushPoints(HOLES).circle(HOLE_R).extrude(depth))


def rod(x0, x1, r, yz):
    """A cylinder along X from x0 to x1 through (y, z)."""
    return cq.Workplane("YZ", origin=(x0, *yz)).circle(r).extrude(x1 - x0)


def box(x, y, z):
    return cq.Workplane("XY").box(x[1] - x[0], y[1] - y[0], z[1] - z[0], centered=False).translate((x[0], y[0], z[0]))


def features(desk=False):
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/engine/mating.py)."""
    z, half = fits.slab(*PLATE_Z)
    x, pin_half = fits.slab(*LID_PIN["x"][::-1])
    fork_y, fork_half = fits.slab(*FORK["y"])
    left = {
        "L foot outer": ((*HOLES[0], z), "z", HOLE_R, half),
        "L foot inner": ((*HOLES[1], z), "z", HOLE_R, half),
        "L outer lid pin": ((g.EYE_L[0] - x, *g.EYE_L[1:]), "x", LID_PIN["r"], pin_half, fits.BORE),
        "L inner lid pin": ((g.EYE_L[0] + x, *g.EYE_L[1:]), "x", LID_PIN["r"], pin_half, fits.BORE),
        "L fork": ((g.EYE_L[0], fork_y, g.EYE_L[2]), "y", FORK["hole_r"], fork_half),
    }
    stem = {f"{s} foot stem": ((g.CENTRE_X, y, z), "z", HOLE_R, half) for s, y in (("L", -31.6), ("R", -21.6))}
    rail = {f"rail {s}": ((x, -35.6, z), "z", HOLE_R, half) for s, x in (("L", 65.92), ("R", 70.92))}
    return {**left, **{"R" + k[1:]: v for k, v in mirrored(left).items()}, **stem, **({} if desk else rail)}


def mirrored(features):
    """Declared features of the L side, mirrored onto the R side (geometry.mirror_x)."""
    return {k: (g.mirror_x(c), *rest) for k, (c, *rest) in features.items()}
