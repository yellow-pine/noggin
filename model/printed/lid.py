"""Our inside (top) and outside (bottom) lids: independent parametric designs (never traced from the designer's
meshes) in their own frame (the L eye centre at the origin, the lid pivot along X; geometry.py). A spherical shell
(r 21..24, half a millimetre clear of the r 20.5 eyeball) from the back plane z 5 round to the lip, a plane through
the pivot axis; an ear each side, |x| 22.5..24 and inward to the shell, the lid bar's lobe out to |y| 14.5 with its
r 1 screw hole. The two lids nest on the same bracket pins: each ear is a boss round the r 1.95 pivot hole on one
layer and a clearance round the other lid's boss on the other (the inside lid's boss inboard, the outside lid's
outboard)."""

import math

import cadquery as cq

R_IN, R_OUT, BACK_Z = 21.0, 24.0, 5.0
BROW = 3.0  # the shell stops at the 45 deg plane z - side * y = 3, the one the ears' top chamfer lies on
SQRT2 = math.sqrt(2)
LIP_DEG = {"inside": 52.4, "outside": 57.6}  # the lip below the lid's side of the Y axis
SIDE = {"inside": 1, "outside": -1}  # the lid's side of Y: the lid bar pins sit at y +-12
OUTBOARD = {"inside": False, "outside": True}  # which ear layer carries the boss
EAR_X = (15.0, 22.5, 24.0)  # |x|: from inside the shell to the layer split to the ear's outer face
LOBE = [(0, 3.5), (0.5, 3.5), (2, 5), (11.5, 5), (14.5, 2), (14.5, -2.5), (0, -2.5)]  # y, z on the +y side
LOBE_ROUND = 2.5  # the lobe's bottom outer corner, about the lid bar hole
BOSS_R, CLEAR_R, PIVOT_R = 3.5, 4.5, 1.95
BAR_HOLE = (12.0, 0.0, 1.0)  # |y|, z, r


def build(which):
    s, a = SIDE[which], math.radians(LIP_DEG[which])
    shell = ball(R_OUT).cut(ball(R_IN)).intersect(halfplane((-s * math.sin(a), -math.cos(a)), 0))  # above the lip
    shell = shell.intersect(halfplane((0, 1), BACK_Z)).intersect(halfplane((-s / SQRT2, 1 / SQRT2), BROW / SQRT2))
    corner = LOBE[5]
    lobe = yz_prism([(s * y, z) for y, z in LOBE])
    lobe = lobe.edges(cq.selectors.NearestToPointSelector((0, s * corner[0], corner[1]))).fillet(LOBE_ROUND)
    lip_y = s * BOSS_R / math.tan(a)  # where the lip meets the boss's flat bottom
    boss = yz_prism([(0, 0), (0, -BOSS_R), (lip_y, -BOSS_R)]).union(rod(BOSS_R))
    inner, split, outer = EAR_X
    layers = {True: (split, outer), False: (inner, split)}
    out = shell
    for sx in (-1, 1):
        out = out.union(clip(lobe, sx, inner, outer).cut(ball(R_IN)))
        out = out.cut(clip(rod(CLEAR_R), sx, *layers[not OUTBOARD[which]]))
        out = out.union(clip(boss, sx, *layers[OUTBOARD[which]]).cut(ball(R_IN)))
    y, z, r = BAR_HOLE
    return out.cut(rod(PIVOT_R)).cut(rod(r, (s * y, z)))


def halfplane(n, c):
    """The YZ points p with n . p <= c (n a unit vector), through x -30..30."""
    (ny, nz), t = n, (-n[1], n[0])
    o = (c * ny, c * nz)
    return yz_prism(
        [
            (o[0] + k * 60 * t[0] - m * 60 * ny, o[1] + k * 60 * t[1] - m * 60 * nz)
            for k, m in ((-1, 0), (1, 0), (1, 1), (-1, 1))
        ]
    )


def ball(r):
    """A sphere about the eye centre with its poles along Y (OCCT's inside test misreads points near a pole)."""
    return cq.Workplane("XY").add(cq.Solid.makeSphere(r, cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), -90, 90, 360))


def yz_prism(yz):
    """A YZ polygon through x -30..30."""
    return cq.Workplane("YZ", origin=(-30, 0, 0)).polyline(yz).close().extrude(60)


def rod(r, yz=(0, 0)):
    return cq.Workplane("YZ", origin=(-30, *yz)).circle(r).extrude(60)


def clip(part, sx, x0, x1):
    """The part between |x| x0 and x1 on the sx side."""
    return part.intersect(cq.Workplane("XY").box(x1 - x0, 60, 60).translate((sx * (x0 + x1) / 2, 0, 0)))
