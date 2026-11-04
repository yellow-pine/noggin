"""The Mech's eye gimbal (#630) as CadQuery parts, every size from model/gimbal.py (its frame and its design).
Parts at one eye are drawn about the L eye's centre (the R one's mirror where it differs); the rest in the gimbal's
frame. Bores take the busy pivots' M3 steel shanks; each push-rod's cups close on a ball under its equator."""

import functools
import itertools
import math

import cadquery as cq
import mujoco
import numpy as np
from OCP.gp import gp_Trsf
from scipy.spatial import ConvexHull

from model import envelopes, fits, gates, neck
from model import gimbal as gm
from model.envelopes import box
from model.printed import bone

LEVER_R, NECK_R, CUP_R, ARM = 2.5, 1.2, gm.BALL_R + 1.5, 6.0  # ARM: every printed arm's width
# the Bones' (head, waist) as (semi-width, height): the tie-bar's heads flattened to its 3 mm slab, each push-rod's
# inside its cups and within CUP_R of the line between the balls (the lids' clearance, gimbal.report, reads it so); the
# lid drives' (#698) low enough to lie within their 3 mm slabs
TIE_BONE, ROD_BONE, LID_BONE = ((4.5, 4.2), (2.2, 2.6)), ((3.6, 5.5), (2.4, 4.0)), ((4.0, 2.9), (3.0, 2.6))
# (#704) the yoke's crank in its 3 mm slab, stiff in the bed for its bending, its waist 0.5 mm over the slab so the
# slab's top cuts it flat (a crown grazing it, 2.9, fused invalid on aarch64's OCCT, #890); the bail's rod flat-bottomed
# with the shanks' bores at its middle height, each arm a strut round in section, the input arm's tip round the pitch
# bar's pin
CRANK_BONE, BAIL_ROD, BAIL_ARM, BAIL_INPUT = (
    ((4.5, 4.2), (3.0, 3.5)),
    ((4.0, 7.0), (3.0, 6.0)),
    ((2.4, 3.3), (2.2, 3.2)),
    ((3.5, 6.5), (3.0, 5.0)),
)
MM = 0.001  # MuJoCo's metres per mm
CAP_BACK = gm.CAP_R * math.cos(math.radians(gm.CAP_HALF))  # the cap's flat back, on the core's seat


def cyl(axis, centre, r, span):
    """A cylinder along x, y or z through `centre` (the other two coordinates), from span[0] to span[1]."""
    i = "xyz".index(axis)
    lo = list(centre)
    lo[i] = span[0]
    d = [0, 0, 0]
    d[i] = 1
    return cq.Workplane().add(cq.Solid.makeCylinder(r, span[1] - span[0], cq.Vector(*lo), cq.Vector(*d)))


def ball(r, at=(0, 0, 0)):
    return cq.Workplane().add(cq.Solid.makeSphere(r, cq.Vector(*at), angleDegrees1=-90, angleDegrees2=90))


def ball_on(base, at):
    """A ball on a neck up from z `base` to its centre `at`: the push-rod's cup closes round it from above."""
    x, y, z = at
    return ball(gm.BALL_R, at).union(cyl("z", (x, y, 0), NECK_R, (base, z)))


def core():
    """The eyeball core: a ball, the seat its cap sits on (forward), the lever up the yaw axis to its ball, and the
    pitch axle's bores along x."""
    top = gm.LEVER - gm.BALL_R - 1.2
    out = ball(gm.CORE_R).union(cyl("y", (0, 0, 0), gm.SEAT_R, (-CAP_BACK, -gm.CORE_R + 3)))
    out = out.union(cyl("z", (0, 0, 0), LEVER_R, (gm.CORE_R - 3, top))).union(ball_on(top, (0, 0, gm.LEVER)))
    for s in (-1, 1):
        out = out.cut(cyl("x", (0, 0, 0), gm.PIN_R, sorted((s * 8.0, s * (gm.CORE_R + 1)))))
    return out


@bone.grown
def yoke(mechanical=False):
    """The yaw yoke: a U from below round the core, the pitch axle's bores through its arms, the stem down the yaw axis
    with its crank (back) on the tie-bar. As Bones (#704): the U a cradle round the core, its underside flaring at 45
    deg into the stem, the crank a Bone in its slab; printed as drawn, on the stem and the crank."""
    y = gm.YOKE
    x0, x1, h = y["inner"], y["inner"] + y["wall"], y["half_y"]
    z = gm.YAW_CRANK_Z
    if not mechanical:
        r = math.hypot(x1, h)  # round the bosses' corners
        # the cone tangent to the cradle 40 deg under its equator: the overhang no more than that on either
        rt, zt = r * math.cos(math.radians(40)), -r * math.sin(math.radians(40))
        flare = zt - (rt - y["stem_r"]) / math.tan(math.radians(40))
        cone = cq.Solid.makeCone(y["stem_r"], rt, zt - flare, cq.Vector(0, 0, flare))
        out = ball(r).union(cq.Workplane().add(cone))
        if flare > y["stem_z"]:  # else the cone flares from under the stem's foot (#901: the bigger core)
            out = out.union(cyl("z", (0, 0, 0), y["stem_r"], (y["stem_z"], flare)))
        out = out.intersect(box((-x1, x1), (-h, h), (y["stem_z"], 0))).cut(ball(x0))
        crank = bone.bone((0, 0, z[0]), (0, gm.CRANK, z[0]), *CRANK_BONE).intersect(box((-9, 9), (-9, 20), z))
        out = out.union(crank)
    else:
        out = box((-x1, x1), (-h, h), (-x1, -x0))
        for s in (-1, 1):
            out = out.union(box(sorted((s * x0, s * x1)), (-h, h), (-x1, 0)))
        out = out.union(cyl("z", (0, 0, 0), y["stem_r"], (y["stem_z"], -x1)))
        out = out.union(box((-ARM / 2, ARM / 2), (0, gm.CRANK), z)).union(cyl("z", (0, gm.CRANK, 0), ARM / 2, z))
    for s in (-1, 1):
        xs = sorted((s * x0, s * x1))
        out = out.union(cyl("x", (0, 0, 0), h, xs)).cut(cyl("x", (0, 0, 0), gm.PIN_R, xs))
    out = out.cut(cyl("z", (0, gm.CRANK, 0), gm.PIN_R, z))
    return out.cut(cyl("z", (0, 0, 0), gm.PIN_R, (y["stem_z"], y["stem_z"] + 8)))


@bone.grown
def tie_bar(mechanical=False):
    """The tie-bar under the yokes' cranks: both eyes' pins and the yaw horn's, one parallelogram. Mechanical: a bar across
    both eyes' pins and a tail back from its middle to the horn's. As Bones (#703): a Bone (model/printed/bone.py) from
    each eye's pin back to the yaw horn's, one chain, flat on top within its slab where the cranks ride on it."""
    c, horn = gm.EYE["L"][0], (0.0, gm.YAW_Y + gm.CRANK, gm.TIE_Z[0])
    if mechanical:
        out = box((-c - ARM / 2, c + ARM / 2), (gm.CRANK - ARM / 2, gm.CRANK + ARM / 2), gm.TIE_Z)
        out = out.union(box((-ARM / 2, ARM / 2), (gm.CRANK, horn[1]), gm.TIE_Z))
        out = out.union(cyl("z", (0, horn[1], 0), ARM / 2, gm.TIE_Z))
    else:
        slab = box(
            (-c - ARM, c + ARM), (0, horn[1] + ARM), (gm.TIE_Z[0] - 1, gm.TIE_Z[1])
        )  # past the bed: no shared face
        # one chain through the horn's pin, its two heads there unalike: two identical ones fused invalid (#838)
        out = bone.chain([(-c, gm.CRANK), horn[:2], (c, gm.CRANK)], *TIE_BONE, z=gm.TIE_Z[0]).intersect(slab)
    for x, y, _ in ((-c, gm.CRANK, 0), (c, gm.CRANK, 0), horn):
        out = out.cut(cyl("z", (x, y, 0), gm.PIN_R, (gm.TIE_Z[0] - 1, gm.TIE_Z[1] + 1)))
    return out


@bone.grown
def bail(mechanical=False):
    """The bail: its rod on an x axis behind the eyes, an arm up to a ball behind each eye, the input arm back to the
    pitch bar's pin, the shanks' bores in its ends. As Bones (#704): the rod and the input arm flat on the bed under
    the rod, each arm a round strut; printed as drawn (its bores across the layers)."""
    by, bz = gm.BAIL
    end, top, tip = gm.EYE["L"][0] + gm.BAIL_END, gm.LEVER - gm.BALL_R - 1.2, by + gm.BAIL_IN
    if not mechanical:
        bed = bz - 3
        out = bone.bone((-end, by, bed), (end, by, bed), *BAIL_ROD, heads=False)  # its ends flat on the uprights
        out = out.union(bone.bone((0, by, bed), (0, tip, bed), *BAIL_INPUT).intersect(box((-2, 2), (0, 99), (bed, 99))))
    else:
        out = cyl("x", (0, by, bz), 3.0, (-end, end))
        out = out.union(box((-2, 2), (by, tip), (bz - 3, bz + 3))).union(cyl("x", (0, tip, bz), 3.0, (-2, 2)))
    for s in (-1, 1):
        x = s * gm.EYE["L"][0]
        if (
            not mechanical
        ):  # its foot's head inside the rod, clear of its bed and its bore's end (#704: flush, Linux's fuse fails)
            arm = bone.bone((x, by, bz + 0.5), (x, by, top - BAIL_ARM[0][0]), *BAIL_ARM, up=(0, 1, 0), round=True)
            out = out.union(arm).union(ball_on(top - BAIL_ARM[0][0], (x, by, gm.LEVER)))
        else:
            out = out.union(box((x - 1.5, x + 1.5), (by - ARM / 2, by + ARM / 2), (bz, top)))
            out = out.union(ball_on(top, (x, by, gm.LEVER)))
        out = out.cut(cyl("x", (0, by, bz), gm.PIN_R, sorted((s * end, s * (end - 8)))))
    return out.cut(cyl("x", (0, tip, bz), gm.PIN_R, (-2, 2)))


@bone.carved
def push_rod(mechanical=False):
    """One push-rod (drawn at x 0): a rod back from the lever's ball to the bail arm's on its cups' rims, a cup round
    each ball. Mechanical: a flat bar round the Bone's waist (#809); as a Bone (#703), carved from it."""
    z, back = gm.LEVER, gm.BAIL[0]
    rod = box((-2.5, 2.5), (0, back), (z - 2, z + 2.5))
    # as two Bones, each within bone.LONG: one Bone this long carved from its bar empty (#901)
    out = rod if mechanical else bone.chain([(0, 0), (0, back / 2), (0, back)], *ROD_BONE, z=z - 2)
    for y in (0.0, back):
        out = out.union(ball(CUP_R, (0, y, z)).cut(box((-CUP_R, CUP_R), (y - CUP_R, y + CUP_R), (z - CUP_R, z - 2))))
    for y in (0.0, back):
        out = out.cut(ball(gm.BALL_R + 0.1, (0, y, z)))
    return out


def link(a, b, x, mechanical=False, sizes=LID_BONE):
    """A flat bar in the slab `x` with pin holes along x at the (y, z) points a and b: mechanical or a Bone (#704) of
    `sizes`."""
    return holes(lid_arms([a, b], x, mechanical, sizes), (a, b), x)


def holes(out, pins, x):
    """`out` with the M3 shank's bore along x through the slab `x` at each (y, z) of `pins`, in a boss the slab's full
    thickness: a Bone's dome stops short of its far face, and the part pinned there meets this one face to face."""
    for y, z in pins:
        out = out.union(cyl("x", (0, y, z), ARM / 2, x))
        out = out.cut(cyl("x", (0, y, z), gm.PIN_R, (x[0] - 1, x[1] + 1)))  # past the faces: no slivers on them
    return out


def lid_arms(points, x, mechanical=False, sizes=LID_BONE):
    """The lid drives' bars, links and spokes through the (y, z) `points` in turn, in the slab `x`: mechanical or as Bones
    of `sizes`."""
    return lid_mechanical(points, x) if mechanical else lid_bone(points, x, sizes)


def lid_mechanical(points, x):
    """Mechanical flat arms ARM wide through the (y, z) `points` in turn, filling the slab `x`, round at every joint."""
    out = cyl("x", (0, *points[0]), ARM / 2, x)
    for a, b in zip(points, points[1:]):
        side = np.array([a[1] - b[1], b[0] - a[0]]) * ARM / 2 / math.dist(a, b)
        outline = [tuple(map(float, p)) for p in (a + side, b + side, b - side, a - side)]
        arm = cq.Workplane("YZ", origin=(x[0], 0, 0)).polyline(outline).close().extrude(x[1] - x[0])
        out = out.union(arm).union(cyl("x", (0, *b), ARM / 2, x))
    return out


def lid_bone(points, x, sizes=LID_BONE):
    """Bones (model/printed/bone.py, #704) through the (y, z) `points` in turn, each lying in the slab `x` on its lower
    face, its joints' pins along x, as low as the slab (unclipped: OCCT's clip of one came out empty one way round): the
    lid drives' bars, links and spokes. Every other span's heads, from the first, are 5% smaller, inside its neighbours'
    where they meet: two identical heads fused made an invalid solid, and on Linux so did the bent bar's other way."""
    assert sizes[0][1] < x[1] - x[0]
    out = bone.chain(points, *sizes, swell=1.0)
    # the bed's z onto x, its x and y onto the gimbal's y and z: a turn about (1, 1, 1), then into the slab
    return cq.Workplane().add(out.val().moved(_at([[0, 0, 1, x[0]], [1, 0, 0, 0], [0, 1, 0, 0]])))


@bone.carved
def pitch_bar(mechanical=False):
    """The pitch bar: the pitch horn's pin up to the bail's input arm, mechanical or a Bone (#708)."""
    hy, hz = gm.PITCH_HORN
    return link((hy + gm.CRANK, hz), (gm.BAIL[0] + gm.BAIL_IN, gm.BAIL[1]), gm.PITCH_BAR_X, mechanical)


def _slab(name, side=1):
    """The LID_X slab outboard (side 1) or inboard (-1) of the L eye's centre, as an x span."""
    return tuple(sorted(side * u for u in gm.LID_X[name]))


@bone.carved
def lid_bar(mechanical=False):
    """One lid's bar (drawn centred on x 0): the upper lid's crank pin back over the link's pin (#698), bent there, to its
    horn's behind the eye (#838). Mechanical or as Bones (#704)."""
    w = (gm.LID_X["bar"][1] - gm.LID_X["bar"][0]) / 2
    horn = tuple(np.add(gm.LID_HORN, gm.LID_PIN))
    out = lid_arms([gm.LID_PIN, gm.LINK_PIN, horn], (-w, w), mechanical)
    return holes(out, (gm.LID_PIN, gm.LINK_PIN, horn), (-w, w))


@bone.carved
def lid_link(mechanical=False):
    """One lower lid's link (drawn centred on x 0): from its pin on the lid bar to the lower lid's crank pin (#698).
    Mechanical or as Bones (#704)."""
    w, pins = (gm.LID_X["link"][1] - gm.LID_X["link"][0]) / 2, (gm.LINK_PIN, gm.LOWER_PIN)
    # its heads 0.2 mm lower than LID_BONE's: a crown 0.1 mm under the slab's face fused invalid on aarch64's OCCT (#890)
    return holes(lid_arms(pins, (-w, w), mechanical, ((4.0, 2.7), LID_BONE[1])), pins, (-w, w))


def _lid(radii, span, spokes, boss, pin, mechanical):
    """An L lid: its shell wedge about x from `span` (deg from forward toward up) between the caps' sides, and in two
    slabs a spoke out to the shell at `spokes` deg (outboard, inboard), the shell reaching round to it there: outboard
    from the `boss` on the frame's shank, inboard from its crank `pin` (#698), `mechanical` or as Bones (#704). The outboard
    spoke stays behind (or under) the cap yawed out and pitched over the lid's whole range; the inboard one is past the
    cap's reach. Everything within the outer radius."""
    ri, ro = radii

    def wedge(a, b, x):
        arc = np.radians(np.linspace(a, b, 24))
        fan = [(0.0, 0.0)] + [(-(ro + 5) * math.cos(t), (ro + 5) * math.sin(t)) for t in arc]
        return cq.Workplane("YZ", origin=(x[0], 0, 0)).polyline(fan).close().extrude(x[1] - x[0])

    shell, outer, inner = ball(ro).cut(ball(ri)), _slab(boss), _slab("ear", -1)
    out = shell.intersect(wedge(*span, (inner[1], outer[1])))  # into the ears' slab only round its own (the other's)
    for x, spoke in zip((outer, inner), spokes):
        reach = (min(spoke - 10, span[1] - 1), spoke + 10) if spoke > 0 else (spoke - 10, max(spoke + 10, span[0] + 1))
        r = math.sqrt(((ri + ro) / 2) ** 2 - (sum(x) / 2) ** 2)  # the shell's middle in the slab
        end = (-r * math.cos(math.radians(spoke)), r * math.sin(math.radians(spoke)))
        out = out.union(shell.intersect(wedge(*reach, x))).union(
            lid_arms([pin if x == inner else (0, 0), end], x, mechanical)
        )
    out = out.union(cyl("x", (0, 0, 0), 4.0, outer)).intersect(ball(ro))
    return holes(out, [pin], inner).cut(cyl("x", (0, 0, 0), gm.PIN_R, outer))


@bone.carved
def upper_lid(side, mechanical=False):
    """The `side` upper lid (drawn for L, the R its mirror): its edge at LID_REST, LID_SPAN up; its boss on the shank
    nearer the eye, its crank pin LID_PIN on the lid bar."""
    out = _lid(gm.LID_R, (gm.LID_REST, gm.LID_REST + gm.LID_SPAN), (112.0, 90.0), "upper boss", gm.LID_PIN, mechanical)
    return out if side == "L" else out.mirror("YZ")


@bone.grown  # carved, Linux's OCCT broke its Bones' intersect (#901): the mechanical lid takes them in
def lower_lid(side, mechanical=False):
    """The `side` lower lid (drawn for L, the R its mirror): its edge at LOWER_REST, LOWER_SPAN down, outside the upper
    lid; its boss on the shank beside the upper's, its crank pin LOWER_PIN on the link."""
    span = (gm.LOWER_REST - gm.LOWER_SPAN, gm.LOWER_REST)
    # its outboard spoke forward of the yoke's bearing under the eye over the lid's whole range (#901)
    out = _lid(gm.LOWER_R, span, (-65.0, -90.0), "lower boss", gm.LOWER_PIN, mechanical)
    return out if side == "L" else out.mirror("YZ")


@bone.grown
def frame(mechanical=False):
    """The gimbal frame (Skeleton): a plate under the eyes' drives, up between the realistic skull's coronoids and condyles
    (#838, model/gimbal.py PLATE_Z), with the yaw bearings reaching forward under the yokes' stems, the bail's and the
    lids' uprights with the shanks' bores (the lids' feet hanging a beam under the lower lids' sweep, #901, the face's
    Seats flush in its front, #852), the
    jaw's lugs on risers at the condyles (model/neck.py JAW, their shanks' tapping holes), a collar on posts round each
    servo at its tab plate (the yaw and the mouth servo hanging under the plate, through it where they pass), and the
    holes the head mount
    (model/printed/neck.py) is screwed up through. As Bones (#708): each bearing a waisted strut, each upright and riser a
    waisted strut up from the plate in its slab to a round boss round the shank's bore; the mechanical frame takes them
    in (bone.grown: OCCT carved the Bones out of it empty or broken, #838)."""
    from model.printed.neck import TAP_R, strut  # here: model.printed.neck imports this module

    c, (bottom, top) = gm.EYE["L"][0], gm.PLATE_Z
    by, bz = gm.BAIL
    (y0, y1), edge, stem = gm.PLATE_Y, c + gm.LID_X["upright"][1], gm.YOKE["stem_z"]
    jy, jz = neck.JAW
    out = box((-gm.PLATE_X, gm.PLATE_X), (y0, gm.BACK_Y), gm.PLATE_Z)
    out = out.union(box((-gm.BACK_X, gm.BACK_X), (gm.BACK_Y, y1), gm.PLATE_Z))
    out = out.union(box((-edge, edge), (y0, y0 + 4), gm.PLATE_Z))  # its front out to the lids' uprights
    out = out.union(box((-edge, edge), gm.CHEEK_Y, gm.BEAM_Z))  # the bar, a beam (#852) under the lids (#901)
    for s in (-1, 1):
        bx = sorted((s * (c + gm.BAIL_END), s * (c + gm.BAIL_END + 4)))
        ux = sorted(s * (c + u) for u in gm.LID_X["upright"])
        lx = sorted(s * u for u in neck.JAW_LUG_X)
        # the lid upright's foot, hanging the bar, and its rail on the plate's level back to the plate's front
        out = out.union(box(ux, (gm.CHEEK_Y[0], 4), (gm.BEAM_Z[0], top))).union(box(ux, (4, y0 + 4), gm.PLATE_Z))
        # each yoke's bearing reaching forward from the plate's front, under the tie-bar (#901): both styles
        out = out.union(cyl("z", (s * c, 0, 0), 5.0, (top, stem)))
        out = out.union(box((s * c - 5, s * c + 5), (0, y0 + 1), (top, gm.TIE_Z[0] - 2.0)))
        if mechanical:
            out = out.union(box(bx, (by - 4, by + 4), (top, bz + 4))).union(box(ux, (-4, 4), (top, 4)))
            out = out.union(box(lx, (jy - neck.BOSS_R, jy + neck.BOSS_R), (top, jz))).union(
                cyl("x", (0, jy, jz), neck.BOSS_R, lx)
            )
        else:  # from inside the plate, flat on top under the yoke's stem; each upright and riser up its slab's middle
            for xs, y, z, r in ((bx, by, bz, 4.0), (ux, 0.0, 0.0, 4.0), (lx, jy, jz, neck.BOSS_R)):
                # a waisted strut, a round boss at its top (a light mesh); its sides 0.25 mm in from its slab's, as a
                # strut's flush on the plate's edge reads back from Linux's STEP crossing the plate's (#851)
                x, h = sum(xs) / 2, (xs[1] - xs[0]) / 2 - 0.25
                out = out.union(strut((x, y, top - 1), (x, y, z), (r, h), (r - 1.0, h))).union(
                    cyl("x", (0, y, z), r, xs)
                )
        out = out.cut(cyl("z", (s * c, 0, 0), gm.PIN_R, (stem - 8, stem)))
        out = holes(holes(out, [(by, bz)], bx), [(0, 0)], ux).cut(cyl("x", (0, jy, jz), TAP_R, lx))
    for x, y in neck.HEAD_SCREWS:  # the head mount's screws (model/printed/neck.py)
        out = out.cut(cyl("z", (x, y, 0), 1.7, gm.PLATE_Z))
    servos = [gm.servo_matrix(face, shaft, tab) for face, shaft, tab, _ in gm.drives().values()]
    servos.append(gm.servo_matrix(*neck.drives()["mouth"][:3]))  # the mouth's, hanging behind the jaw (#838)
    for m in servos:
        out = out.cut(passes(m))
    for m in servos:  # on the plate's top, or hanging from its underside
        out = out.union(collar(m, top if (m @ (0, 0, 0, 1))[2] > top else bottom))
    for s in (-1, 1):  # room for each yoke's crank to turn: the lid servo's collar comes down beside it
        reach = gm.CRANK + CRANK_BONE[0][0] + 0.5  # its Bone's head, which the yoke grows into its mechanical one
        out = out.cut(cyl("z", (s * c, 0, 0), reach, (gm.YAW_CRANK_Z[0], gm.YAW_CRANK_Z[1] + 0.5)))
    return out


def passes(m):
    """Where a servo placed by m passes through the plate: its case, its tab plate and its gear top's bosses with the
    spline over them, 0.3 mm clear."""
    s = envelopes.SERVO
    (x0, x1), (y0, y1), (z0, z1) = s["case"]
    (tx0, tx1), (ty0, ty1), (tz0, tz1) = s["tabs"]
    local = box((x0 - 0.3, x1 + 0.3), (y0 - 0.3, y1 + 0.3), (z0 - 0.3, z1 + 0.3))
    local = local.union(box((tx0 - 0.3, tx1 + 0.3), (ty0 - 0.3, ty1 + 0.3), (tz0 - 0.3, tz1 + 0.3)))
    (bx, by, br), (cx, _, cr) = s["boss"]
    top = box((cx - cr - 0.5, bx + br + 0.5), (by - br - 0.5, by + br + 0.5), (s["tip_z"] - 0.3, z0))
    return _moved(local.union(top), m)


def collar(m, floor):
    """A plate round the servo's case at its tab plate, with its two screw holes, on a post under each hole down (or up)
    to `floor`, but where the servo's case stands between the hole and the floor: under the tabs, or over them when
    the floor is on their side (a servo hanging under the plate)."""
    s = envelopes.SERVO
    (x0, x1), (y0, y1), _ = s["case"]
    (tx0, tx1), (ty0, ty1), (tz0, _) = s["tabs"]
    up = floor > (m @ (0, 0, 0, 1))[2]
    z = (0.0, 3.0) if up == (m[2, 2] > 0) else (tz0 - 3.0, tz0)  # local z runs from the tabs away from the horn
    local = box((tx0 - 2, tx1 + 2), (ty0 - 2, ty1 + 2), z).cut(box((x0 - 0.3, x1 + 0.3), (y0 - 0.3, y1 + 0.3), z))
    for hx, hy in s["tab_holes"]:
        local = local.cut(cq.Workplane("XY").circle(s["tab_r"]).extrude(3).translate((hx, hy, z[0])))
    out = _moved(local, m)
    case = (m @ np.c_[list(itertools.product(*s["case"])), np.ones(8)].T)[:3].T
    clo, chi = case.min(axis=0), case.max(axis=0)
    for hole in s["tab_holes"]:
        lo, hi = post(m, hole, z)
        span = (floor, hi[2]) if floor < lo[2] else (lo[2], floor)
        if (lo[:2] < chi[:2]).all() and (hi[:2] > clo[:2]).all() and span[0] < chi[2] and span[1] > clo[2]:
            continue  # the case stands between: the other post and the plate hold it
        out = out.union(box((lo[0], hi[0]), (lo[1], hi[1]), span))
    return out


def post(m, hole, z=(0, 3)):
    """(lo, hi) corners of the box round a servo's tab hole `hole` (its STEP frame) through the collar (its local z),
    placed by m."""
    hx, hy = hole
    corners = [(hx + a, hy + b, c) for a in (-2.4, 2.4) for b in (-2.4, 2.4) for c in z]
    w = (m @ np.c_[corners, np.ones(8)].T)[:3].T
    return w.min(axis=0), w.max(axis=0)


def _moved(shape, m):
    t = cq.Matrix([list(map(float, row)) for row in m[:3]])
    return cq.Workplane().add(shape.val().transformGeometry(t))


def at_rest(mechanical=False):
    """{eyes part: its solid where model/stages.py places it}, each lid's pivot shank beside them (the M3 steel
    shank from the frame's upright through the lid's boss); `mechanical`: the Skeleton mechanical (#704)."""
    from model import stages
    from model.printed import PARTS, styled  # here: model.printed imports this module

    out = {}
    for name, p in stages.eyes_sub().parts.items():
        stem = styled(stages.stem(p.file), mechanical)
        out[name] = (PARTS.get(stem) or envelopes.ENVELOPES[stem])().val().moved(_at(p.matrix))
    for s, sign in (("L", 1), ("R", -1)):
        x = sorted(gm.EYE[s][0] + sign * u for u in (gm.LID_X["upper boss"][0] + 2, gm.LID_X["upright"][1]))
        out[f"{s} lid shank"] = cyl("x", (0, 0, 0), gm.PIN_R - fits.CLEARANCE[0], x).val()
    return out


# the parts moved() carries by a pin on another moving part: each turns on that part's pin
COUPLED = {
    **{f"{s} lid bar:1": f"{s} lid horn:1" for s in "LR"},
    **{f"{s} lid link:1": f"{s} lid bar:1" for s in "LR"},
    **{f"{s} push-rod:1": "bail:1" for s in "LR"},
    "pitch bar:1": "pitch horn:1",
}


def _turn(m):
    """Radians a 4x4 turns about x."""
    return math.atan2(m[2, 1], m[1, 1])


def skeleton(rest, tol=0.1):
    """The gimbal as hinges for gates.certify (#655), in metres: a body per part in `rest`, its pieces a ball of `tol`
    mm on each corner of its tessellation's hull (the surface strays from it by `tol` at most), each part moved() turns
    hinged about x through the point its turn fixes (a COUPLED part on the part that carries it), the parts that turn
    alike about one line on one hinge; and rows(poses), a qpos row per (lid, pitch). Every move at yaw 0 turns about x."""
    probe = gm.moved(-30.0, 10.0)  # a pose that turns every hinge
    s, bodies, hinged, carrier = mujoco.MjSpec(), {}, {}, {}  # hinged: (carrier, line, turn) -> the hinge's part

    def add(name):
        if name not in bodies:
            parent = COUPLED.get(name)
            host = add(parent) if parent else s.worldbody
            if name in probe:
                rel = np.linalg.inv(probe[parent]) @ probe[name] if parent else probe[name]
                y, z = np.linalg.solve(np.eye(2) - rel[1:3, 1:3], rel[1:3, 3])  # the point the turn fixes
                key = (carrier.get(parent), round(y, 6), round(z, 6), round(_turn(rel), 9), " lid" in name)
                carrier[name] = hinged.setdefault(key, name)
                if carrier[name] != name:  # the hinge of a part that turns alike carries it
                    host = bodies[carrier[name]]
            body = bodies[name] = host.add_body(name=name)
            if carrier.get(name) == name:
                body.add_joint(type=mujoco.mjtJoint.mjJNT_HINGE, axis=[1, 0, 0], pos=[0, y * MM, z * MM])
            v = np.array([p.toTuple() for p in rest[name].tessellate(tol)[0]])
            for corner in v[ConvexHull(v).vertices]:
                body.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[tol * MM, 0, 0], pos=corner * MM)
        return bodies[name]

    for name in rest:
        add(name)
    model = s.compile()
    # a lid part turns with the lid servo alone, every other with the pitch alone (moved())
    lid_m, pitch_m = functools.cache(lambda lid: gm.moved(lid, 0.0)), functools.cache(lambda p: gm.moved(0.0, p))

    def rows(poses):
        qpos = np.zeros((len(poses), model.nq))
        for i, (lid, pitch) in enumerate(poses):
            for name in hinged.values():
                m = lid_m(lid) if " lid" in name else pitch_m(pitch)
                turn = _turn(m[name]) - (_turn(m[COUPLED[name]]) if name in COUPLED else 0.0)
                qpos[i, model.jnt_qposadr[model.body(name).jntadr[0]]] = turn
        return qpos

    return model, rows


def _path(segments, step):
    """(lid, pitch) rows `step` deg apart along the segments in turn, each joined straight to the next."""
    ends = [e for s in segments for e in s]
    rows = [ends[0]]
    for a, b in zip(ends, ends[1:]):
        rows += list(np.linspace(a, b, max(1, math.ceil(np.abs(np.subtract(b, a)).max() / step)) + 1)[1:])
    return np.round(rows, 6)  # a value shared by two lines reads the same


def sweep(n_lid=9, n_pitch=7, within=5.0, step=0.1):
    """The lid drives' sweep (#650), on the Skeleton mechanical (#809: the Bones carved from it): each lid, its bar, its horn and its
    shank against every other part over the lid x pitch grid (both lid servos together, yaw 0; model/gimbal.py moved()).
    Every pair at least LID_CLEAR_MM apart at rest
    is certified to stay so along the grid's lines that turn it (#655, lines(): gates.certify on skeleton()'s hinges,
    reading the exact solids, the bounding boxes' gap past `within` mm), rows `step` deg apart; the closest it read is
    reported. Every pair closer at rest (a pin, a face sliding on a face, the boss on its shank) is checked for overlap
    at the grid's samples: every move here turns about x, so one of two lifts 0.01 mm along x parts a pair that only
    touches."""
    rest = at_rest(mechanical=True)
    names = ("upper lid:1", "lower lid:1", "lid bar:1", "lid link:1", "lid horn:1", "lid shank")
    drives = [f"{s} {n}" for s in "LR" for n in names]
    spline = {(f"{s} lid horn:1", f"{s} lid servo:1") for s in "LR"}  # the horn's hub on its spline
    pairs = [(a, b) for i, a in enumerate(drives) for b in rest if b not in drives[: i + 1] and (a, b) not in spline]
    near = {(a, b) for a, b in pairs if _gap(rest[a], rest[b]) < gm.LID_CLEAR_MM > rest[a].distance(rest[b])}
    lids, pitches = (
        np.linspace(*np.subtract(gm.LID_EDGES, gm.LID_REST), n_lid),
        np.linspace(-gm.PITCH, gm.PITCH, n_pitch),
    )
    lift = [cq.Location(cq.Vector(e, 0, 0)) for e in (-0.01, 0.01)]
    overlaps, seen = [], set()
    for lid in lids:  # the lid servo's range
        for pitch in pitches:
            m = gm.moved(lid, pitch)
            turned = {k for k in m if " lid" in k}
            for a, b in near:
                # each pair once per angle that moves it
                pose = (a, b, lid if {a, b} & turned else None, pitch if {a, b} & set(m) - turned else None)
                if pose in seen:
                    continue
                seen.add(pose)
                sa, sb = (rest[k].moved(_at(m[k])) if k in m else rest[k] for k in (a, b))
                if _gap(sa, sb) < 0 and max(sa.moved(t).distance(sb) for t in lift) < 0.005:
                    overlaps.append(
                        {"pair": [a, b], "at": {"lid_deg": round(float(lid), 1), "pitch_deg": round(float(pitch), 1)}}
                    )
    model, rows = skeleton(rest)
    moving, closest = set(gm.moved(0, 0)), [within, None, None]

    def certify(pairs, path):
        qpos, posed = rows(path), {}
        row_of = {q.tobytes(): i for i, q in enumerate(qpos)}

        def shape(k, data):
            if k not in posed:
                m = np.eye(4)
                m[:3, :3], m[:3, 3] = data.body(k).xmat.reshape(3, 3), data.body(k).xpos / MM
                posed[k] = rest[k].moved(_at(m)) if k in moving else rest[k]
            return posed[k]

        def separation(model, data, pair):
            row = row_of[data.qpos.tobytes()]
            if posed.get("row") != row:
                posed.clear()
                posed["row"] = row
            a, b = (shape(k, data) for k in pair)
            mm = _gap(a, b)  # a lower bound on the gap; the exact one within `within`
            if mm < within:
                mm = a.distance(b)
            if mm < closest[0]:
                lid, pitch = (round(float(d), 1) for d in path[row])
                closest[:] = mm, list(pair), {"lid_deg": lid, "pitch_deg": pitch}
            return mm

        # a reading under LID_CLEAR_MM is the closest one, so closest carries what the gate reads
        gates.certify(model, qpos, dict.fromkeys(pairs, gm.LID_CLEAR_MM), separation=separation)

    def lines(a, b):
        """The grid's lines a pair is certified along, as (the pitches of its lid lines, the lids of its pitch lines):
        those of the servos that turn it."""
        turns = {" lid" in k for k in (a, b) if k in moving}  # True: the lid servo turns it, False: the pitch servo
        if any(k.endswith(" lid:1") for k in (a, b)) and any(" eyeball " in k for k in (a, b)):
            # a lid and an eye turn about one line through the eyes' centres, so their gap follows the turn between
            # them alone: the lid lines at the pitch's two ends sweep all of it, the lid's range being the wider
            assert np.ptp(lids) >= np.ptp(pitches)
            return pitches[[0, -1]], []
        if False not in turns:
            return pitches[:1], []
        return (pitches, lids) if True in turns else ([], lids[:1])

    groups = {}
    for a, b in pairs:
        if (a, b) not in near:
            groups.setdefault(tuple(map(tuple, lines(a, b))), []).append((a, b))
    for (ps, ls), group in groups.items():
        segments = [((lids[0], p), (lids[-1], p)) for p in ps] + [((lid, pitches[0]), (lid, pitches[-1])) for lid in ls]
        certify(group, _path([s[:: (-1) ** i] for i, s in enumerate(segments)], step))
    return {"clearance_mm": round(closest[0], 2), "pair": closest[1], "at": closest[2], "overlaps": overlaps}


def bounds(rest):
    """The gimbal's bounding box at `rest` (at_rest()), mm: its width (x), depth (y) and height (z), servos and horns
    included (#684)."""
    b = cq.Compound.makeCompound(list(rest.values())).BoundingBox()
    return [round(b.xlen, 1), round(b.ylen, 1), round(b.zlen, 1)]


def _gap(a, b):
    """mm between the two solids' bounding boxes along the axis they are furthest apart on (negative: they overlap)."""
    ba, bb = a.BoundingBox(), b.BoundingBox()
    return max(
        max(getattr(ba, f"{k}min") - getattr(bb, f"{k}max"), getattr(bb, f"{k}min") - getattr(ba, f"{k}max"))
        for k in "xyz"
    )


def _at(m):
    """A rigid 4x4 as a CadQuery Location: the solid moves, its geometry stays exact."""
    t = gp_Trsf()
    t.SetValues(*map(float, np.asarray(m)[:3].ravel()))
    return cq.Location(t)
