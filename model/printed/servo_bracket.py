"""Our L and R servo brackets: independent parametric designs (never traced from the designer's meshes) in the eyes
frame (model/geometry.py). Drawn for the L side; the R bracket is its mirror about x=29.5 but for the stem tab, which
sits 10 mm higher so the two tabs stack side by side on the main bracket's stem. A plate (z 18..21) screwed onto the
main bracket; the eye servo's two walls (tab holes along Y); the lid servo's two tongues (tab holes along X): the
post at the front, the block at the back. Interfaces exact, envelope within 1 mm, fillets dropped. Measured:
docs/research/2026-10-31-model.md [M]."""

import cadquery as cq

from model import fits
from model import geometry as g
from model.printed.main_bracket import box, mirrored

PLATE_Z = (18.0, 21.0)
PLATE = [(-3.42, -35.6), (19.24, -35.6), (19.24, -16.5), (24.24, -11.5), (25.16, -11.5), (25.16, -6.5), (24.24, -6.5)]
PLATE += [(15.24, 2.5), (-1.92, 2.5), (-8.42, -4.0), (-17.42, -4.0), (-17.42, -11.5), (-8.42, -11.5), (-3.42, -16.5)]
TAB = {"x": (19.24, 35.24), "L": (-35.6, -27.6), "R": (-25.6, -17.6)}  # the stem tab, its foot on the centreline
FOOT_R = 1.35
FEET = [(-13.42, -7.75), (10.24, -0.5)]
WALL_Y = (-11.5, -6.5)  # the eye servo walls; the outer one runs on to y -4 below the lid post
WALL_X = {"inner": (19.24, 25.16), "outer": (-9.34, -3.42)}
WALL_TOP = 32.76
OUTER_YZ = [(-11.5, 21.0), (-4.0, 21.0), (-4.0, 30.16), (-1.4, 32.76), (-11.5, 32.76)]  # the outer wall, up to the post
ROUND = 2.0  # off the outer edges: the plate's corners, the walls' and tongues' tops
POST = {"x": (-7.34, -2.38), "y": (-6.9, -1.4), "z": (32.76, 46.0)}  # the lid servo's front tongue
BLOCK_XZ = [(-3.42, 21.0), (19.24, 21.0), (19.24, 33.0), (8.24, 46.0), (-7.42, 46.0), (-7.42, 34.0), (-3.42, 30.0)]
BLOCK_Y, BLOCK_STEP = (-35.6, -30.1), (-31.6, 34.0)  # the back tongue; y -31.6..-30.1 starts 45 deg up from z 34
TONGUE_X = (-7.42, -3.42)
TAB_R = 1.1


def build(side):
    body = left(TAB[side])
    return body if side == "L" else body.mirror("YZ", (g.CENTRE_X, 0, 0))


def left(tab_y):
    mid = sum(PLATE_Z) / 2
    out = cq.Workplane("XY", origin=(0, 0, PLATE_Z[0])).polyline(PLATE).close().extrude(PLATE_Z[1] - PLATE_Z[0])
    for x, y in (PLATE[7], PLATE[8], PLATE[10], PLATE[11]):
        out = rounded(out, (x, y, mid))
    tab = box(TAB["x"], tab_y, PLATE_Z)
    out = out.union(rounded(rounded(tab, (TAB["x"][1], tab_y[0], mid)), (TAB["x"][1], tab_y[1], mid)))
    inner, outer, y = WALL_X["inner"], WALL_X["outer"], sum(WALL_Y) / 2
    out = out.union(rounded(box(inner, WALL_Y, (PLATE_Z[1], WALL_TOP)), (inner[1], y, WALL_TOP)))
    out = out.union(rounded(prism_x(OUTER_YZ, outer), (outer[0], y, WALL_TOP)))
    out = out.union(rounded(box(POST["x"], POST["y"], POST["z"]), (sum(POST["x"]) / 2, POST["y"][1], POST["z"][1])))
    block = cq.Workplane("XZ", origin=(0, BLOCK_Y[1], 0)).polyline(BLOCK_XZ).close().extrude(BLOCK_Y[1] - BLOCK_Y[0])
    block = rounded(block, (0, BLOCK_Y[0], BLOCK_XZ[4][1]))
    (y0, z0), y1 = BLOCK_STEP, BLOCK_Y[1]
    out = out.union(block.cut(prism_x([(y0, 0), (y1, 0), (y1, z0 + y1 - y0), (y0, z0)], (-20, 40))))
    feet = FEET + [(g.CENTRE_X, sum(tab_y) / 2)]
    depth = PLATE_Z[1] - PLATE_Z[0] + 2
    out = out.cut(cq.Workplane("XY", origin=(0, 0, PLATE_Z[0] - 1)).pushPoints(feet).circle(FOOT_R).extrude(depth))
    for x, _, z in g.SERVOS["l_eye"]["tab_holes"]:
        out = out.cut(cq.Workplane("XZ", origin=(x, 0, z)).circle(TAB_R).extrude(15, both=True))
    x0, x1 = TONGUE_X
    for _, y, z in g.SERVOS["l_lid"]["tab_holes"]:
        out = out.cut(cq.Workplane("YZ", origin=(x0 - 1, y, z)).circle(TAB_R).extrude(x1 - x0 + 1))
    return out


def rounded(part, near):
    """The part with its edge nearest `near` rounded to r ROUND."""
    return part.edges(cq.selectors.NearestToPointSelector(near)).fillet(ROUND)


def prism_x(yz, x):
    """A YZ polygon extruded along X from x[0] to x[1]."""
    return cq.Workplane("YZ", origin=(x[0], 0, 0)).polyline(yz).close().extrude(x[1] - x[0])


def features(side):
    """{feature: (centre, axis, r, half[, band])} the mating check fits on our mesh (model/engine/mating.py)."""
    z, half = fits.slab(*PLATE_Z)
    lid_x, lid_half = fits.slab(*TONGUE_X)
    eye_y, eye_half = fits.slab(*WALL_Y)
    (_, far_y, lid_z), (_, near_y, _) = g.SERVOS["l_lid"]["tab_holes"]
    (near_x, _, eye_z), (far_x, _, _) = g.SERVOS["l_eye"]["tab_holes"]
    left = {
        "lid near": ((lid_x, near_y, lid_z), "x", TAB_R, lid_half),
        "lid far": ((lid_x, far_y, lid_z), "x", TAB_R, lid_half),
        "eye near": ((near_x, eye_y, eye_z), "y", TAB_R, eye_half),
        "eye far": ((far_x, eye_y, eye_z), "y", TAB_R, eye_half),
        "foot outer": ((*FEET[0], z), "z", FOOT_R, half),
        "foot inner": ((*FEET[1], z), "z", FOOT_R, half),
        "foot stem": ((g.CENTRE_X, sum(TAB[side]) / 2, z), "z", FOOT_R, half),
    }
    return left if side == "L" else mirrored(left)
