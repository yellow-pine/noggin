"""Seam: the next Mech's eye gimbal parts (model/printed/gimbal.py) as model/stages.py places them at rest, each lid's
shank beside them: no two overlap, and each cap's pupil seat turns toward the other eye (the toe-in, #630)."""

import itertools
import math

import cadquery as cq
import mujoco
import numpy as np
import pytest

from model import beams
from model import geometry as g
from model import gimbal as gm
from model.printed import bone, gimbal

# a horn's hub on its servo's spline: the Envelopes overlap there by design
ON_SPLINE = {frozenset((f"next {d} servo:1", f"next {d} horn:1")) for d in gm.drives()}


def _overlaps(a, b):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    apart = any(
        getattr(ba, f"{k}max") < getattr(bb, f"{k}min") or getattr(bb, f"{k}max") < getattr(ba, f"{k}min")
        for k in "xyz"
    )
    return 0.0 if apart else a.intersect(b).Volume()


@pytest.mark.build
@pytest.mark.parametrize("plain", [False, True])
def test_no_two_parts_overlap_at_rest(plain):
    shapes = gimbal.at_rest(plain)
    hits = [
        f"{a} / {b}: {v:.2f} mm3"
        for a, b in itertools.combinations(shapes, 2)
        if frozenset((a, b)) not in ON_SPLINE and (v := _overlaps(shapes[a], shapes[b])) > 0.01
    ]
    assert hits == []


@pytest.mark.build
def test_the_block_fits_the_compact_head():
    """#684, #698: the gimbal, servos and horns included, fits a head of at most 124.6 W x 120 D x 150 H: the face as
    wide as the lids' frame and the shell's wall."""
    assert all(b <= h for b, h in zip(gimbal.bounds(), gm.HEAD_MM))


@pytest.mark.parametrize("side, inward", [("L", -1), ("R", 1)])
def test_the_pupil_seat_sits_toward_the_other_eye(side, inward):
    """Just inside the cap's front, 6.6 mm either side of the gaze: the seat (r 7) is cut on the inward side, the cap
    solid on the outward one."""
    cap = gimbal.cap(side).val()
    y = -gm.CAP_R + 0.9
    assert not cap.isInside(cq.Vector(inward * 6.6, y, 0)) and cap.isInside(cq.Vector(-inward * 6.6, y, 0))


@pytest.mark.build
def test_the_skeleton_moves_every_part_as_the_gimbal_does():
    """The hinges gates.certify reads (#655): at each (lid, pitch) row every part sits where gimbal.moved() puts it, the
    parts that turn alike about one line on one hinge."""
    poses = [(-36, -12), (-20, 0), (10, 14)]
    model, rows = gimbal.skeleton(gimbal.at_rest())
    data = mujoco.MjData(model)
    for (lid, pitch), q in zip(poses, rows(poses)):
        data.qpos[:] = q
        mujoco.mj_kinematics(model, data)
        for name, m in gm.moved(lid, pitch).items():
            assert data.body(name).xmat.reshape(3, 3) == pytest.approx(m[:3, :3], abs=1e-9)
            assert data.body(name).xpos * 1000 == pytest.approx(m[:3, 3], abs=1e-6)
    # the upper lids, the lower lids, their horns, their bars, their links, the cores with their caps, the push-rods
    # (each L and R alike); the pitch horn, the bail, the pitch bar
    assert model.njnt == 10


# The Bones (#703): the tie-bar's arms from each eye's pin to the yaw horn's, each push-rod from the lever's ball to
# the bail arm's; (part, its joints, the axial load on one arm: the servo's stall at its horn pin, the bail's ratio on)
TIE_PINS = [(-gm.EYE["L"][0], gm.CRANK), (gm.EYE["L"][0], gm.CRANK), (0.0, gm.YAW_Y + gm.CRANK)]
ROD_BALLS = [(0.0, 0.0, gm.LEVER), (0.0, gm.BAIL[0], gm.LEVER)]


def test_the_tie_bar_keeps_its_three_pin_bores():
    """Each bore takes the M3 shank (PIN_R) through the bar's 3 mm, with wall round it."""
    tie, z = gimbal.tie_bar().val(), sum(gm.TIE_Z) / 2
    for x, y in TIE_PINS:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            assert not tie.isInside(cq.Vector(x + dx * (gm.PIN_R - 0.05), y + dy * (gm.PIN_R - 0.05), z))
            assert tie.isInside(cq.Vector(x + dx * (gm.PIN_R + 0.5), y + dy * (gm.PIN_R + 0.5), z))


def test_each_push_rod_cup_closes_on_its_ball_under_the_equator():
    """The socket (0.1 over the ball) is clear, the cup's wall round it above and to the sides, and its mouth open
    2 mm under the ball's centre for the neck."""
    rod = gimbal.push_rod().val()
    for x, y, z in ROD_BALLS:
        r = gm.BALL_R + 0.05
        for d in ((0, 0, 1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
            assert not rod.isInside(cq.Vector(x + d[0] * r, y + d[1] * r, z + d[2] * r))
            assert rod.isInside(cq.Vector(x + d[0] * (r + 0.6), y + d[1] * (r + 0.6), z + d[2] * (r + 0.6)))
        assert not rod.isInside(cq.Vector(x, y, z - 2.05))


def test_the_bones_print_as_drawn_with_no_overhang_past_45_deg():
    """The tie-bar on its underside, its pins along Z; the push-rod on its cups' rims (the socket's crown inside them,
    an exact interface, excused)."""
    assert bone.overhang_deg(gimbal.tie_bar().val()) <= 45
    crown = lambda c: min(math.dist(c, b) for b in ROD_BALLS) > gm.BALL_R + 0.2  # noqa: E731
    assert bone.overhang_deg(gimbal.push_rod().val(), keep=crown) <= 45


def _section(solid, a, b, t, eps=0.01):
    """(mm2, the least mm4) of `solid`'s section square to the span a-b at t: its area and second moment."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    along = (b - a) / np.linalg.norm(b - a)
    side, up = np.cross(along, (0, 0, 1)), np.array([0.0, 0.0, 1.0])
    plane = cq.Plane(origin=tuple(a + (b - a) * t), xDir=tuple(side), normal=tuple(along))
    cut = solid.intersect(cq.Workplane(plane).rect(60, 60).extrude(eps / 2, both=True).val())
    inertia = np.array(cq.Shape.matrixOfInertia(cut)) / eps
    basis = np.array([side, up])
    return cut.Volume() / eps, float(np.linalg.eigvalsh(basis @ inertia @ basis.T).min())


@pytest.mark.parametrize(
    "part, a, b, load",
    [
        ("tie-bar", (*TIE_PINS[1], gm.TIE_Z[0]), (*TIE_PINS[2], gm.TIE_Z[0]), 1.0),
        ("push-rod", *ROD_BALLS, gm.BAIL_IN / gm.LEVER),
    ],
)
def test_each_bone_holds_its_servo_at_stall(part, a, b, load):
    """SF 2 (beams.MIN_SF) in PETG across its layers along its waist, pinned at both joints: on its strength and against
    Euler buckling over its span."""
    solid = (gimbal.tie_bar if part == "tie-bar" else gimbal.push_rod)().val()
    mat = g.MATERIALS[g.PRINTED[f"next {part}"][1]]
    force = beams.stall_force_n() * load
    area, least = min(_section(solid, a, b, t) for t in (0.3, 0.4, 0.5, 0.6, 0.7))
    assert mat["tensile_mpa"]["z"] * area / force >= beams.MIN_SF
    assert math.pi**2 * mat["E_mpa"]["z"] * least / math.dist(a, b) ** 2 / force >= beams.MIN_SF


# The full pass (#704): the yaw yoke prints as drawn, on its stem and crank (its yaw and crank pins along Z, the pitch
# axle's bores across the layers); the bail as drawn, on its rod's flat underside (all three bores along x: standing
# on an end would hang an arm and its ball in the air)
Y = gm.YOKE
BALLS = [(s * gm.EYE["L"][0], gm.BAIL[0], gm.LEVER) for s in (-1, 1)]
TIP = (0.0, gm.BAIL[0] + gm.BAIL_IN, gm.BAIL[1])


def test_the_yoke_keeps_its_bores():
    """The yaw shank's bore up the stem, the crank's pin bore, and the pitch axle's bore through each arm, each with
    wall round it."""
    yoke, r = gimbal.yoke().val(), gm.PIN_R
    z, zc = Y["stem_z"] + 4, sum(gm.YAW_CRANK_Z) / 2
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for x, y, zz in ((0, 0, z), (0, gm.CRANK, zc)):
            assert not yoke.isInside(cq.Vector(x + dx * (r - 0.05), y + dy * (r - 0.05), zz))
            assert yoke.isInside(cq.Vector(x + dx * (r + 0.5), y + dy * (r + 0.5), zz))
        for s in (-1, 1):
            x = s * (Y["inner"] + Y["wall"] / 2)
            assert not yoke.isInside(cq.Vector(x, dx * (r - 0.05), dy * (r - 0.05)))
            assert yoke.isInside(cq.Vector(x, dx * (r + 0.5), dy * (r + 0.5)))


def test_the_bail_keeps_its_bores_and_balls():
    """The shanks' bores in the rod's ends and the pitch bar's pin bore in the input arm's tip, each with wall round
    it; a ball on its neck behind each eye."""
    bail, r, (by, bz), end = gimbal.bail().val(), gm.PIN_R, gm.BAIL, gm.EYE["L"][0] + 8.0
    for dy, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for x, y, z in [(s * (end - 4), by, bz) for s in (-1, 1)] + [TIP]:
            assert not bail.isInside(cq.Vector(x, y + dy * (r - 0.05), z + dz * (r - 0.05)))
            assert bail.isInside(cq.Vector(x, y + dy * (r + 0.5), z + dz * (r + 0.5)))
    for x, y, z in BALLS:
        assert bail.isInside(cq.Vector(x, y, z + gm.BALL_R - 0.05)) and not bail.isInside(cq.Vector(x, y, z + 3.1))


def _off_bore(c, axis_points, r=gm.PIN_R + 0.2):
    """False on a bore's wall along x through any of the (y, z) points: its crown, an exact interface, is excused."""
    return all(math.hypot(c[1] - y, c[2] - z) > r for y, z in axis_points)


def test_the_yoke_and_the_bail_print_as_drawn_with_no_overhang_past_45_deg():
    """The pitch axle's and the bail's bores across the layers, the bail's balls on their necks: exact interfaces,
    excused."""
    shank = lambda c: math.hypot(c[0], c[1]) > gm.PIN_R + 0.2  # noqa: E731  the yaw shank's blind bore's crown
    assert bone.overhang_deg(gimbal.yoke().val(), keep=lambda c: _off_bore(c, [(0, 0)]) and shank(c)) <= 45
    ball = lambda c: all(  # noqa: E731
        math.dist(c, b) > gm.BALL_R + 0.2 and math.hypot(c[0] - b[0], c[1] - b[1]) > gimbal.NECK_R + 0.2 for b in BALLS
    )
    keep = lambda c: _off_bore(c, [gm.BAIL, TIP[1:]]) and ball(c)  # noqa: E731
    assert bone.overhang_deg(gimbal.bail().val(), keep=keep) <= 45


def _bending_sf(solid, a, b, force, d, lever, ts=(0.0, 0.25, 0.5, 0.75)):
    """The least SF in PETG across its layers on the member a-b's sections at ts, a `force` N along the axis `d` (x, y
    or z) `lever` mm from a: the section's second moment about its axis square to d, its extreme fibre along d."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    along, i = (b - a) / np.linalg.norm(b - a), "xyz".index(d)
    n = np.cross(along, np.eye(3)[i])
    mat, out = g.MATERIALS["PETG HF"], []
    for t in ts:
        plane = cq.Plane(origin=tuple(a + (b - a) * t), xDir=tuple(n), normal=tuple(along))
        cut = solid.intersect(cq.Workplane(plane).rect(80, 80).extrude(0.005, both=True).val())
        inertia = n @ np.array(cq.Shape.matrixOfInertia(cut)) @ n / 0.01
        box, mid = cut.BoundingBox(), cq.Shape.centerOfMass(cut).toTuple()[i]
        c = max(getattr(box, f"{d}max") - mid, mid - getattr(box, f"{d}min"))
        moment = force * (lever - t * np.linalg.norm(b - a))
        out.append(mat["tensile_mpa"]["z"] * inertia / (moment * c))
    return min(out)


def test_the_yokes_crank_and_the_bails_arms_hold_the_servos_at_stall():
    """SF 2 (beams.MIN_SF) in bending: the crank under the yaw servo's stall at its pin; each bail arm under the pitch
    servo's at its ball (one arm taking it all, the bail's ratio on); the input arm under it at the pitch bar's pin."""
    f, (by, bz) = beams.stall_force_n(), gm.BAIL
    assert _bending_sf(gimbal.yoke().val(), (0, 0, -25.5), (0, gm.CRANK, -25.5), f, "x", gm.CRANK) >= beams.MIN_SF
    for x, _, z in BALLS:
        arm = _bending_sf(gimbal.bail().val(), (x, by, bz + 4), (x, by, bz + 11), f * gm.BAIL_IN / z, "y", z - 4)
        assert arm >= beams.MIN_SF
    assert _bending_sf(gimbal.bail().val(), (0, by + 5, bz), TIP, f, "z", gm.BAIL_IN - 5) >= beams.MIN_SF


def test_each_push_rod_stays_within_its_cups_reach_of_the_balls_line():
    """gimbal.report reads the lids' clearance to a push-rod as a capsule CUP_R round the line between its balls."""
    v, _ = gimbal.push_rod().val().tessellate(0.01, 0.1)
    assert max(math.hypot(p.x, p.z - gm.LEVER) for p in v) <= gimbal.CUP_R + 1e-6


# The lid drives' Bones (#698, #704): each lies on its slab's face, its pins along x; (part, its joints in turn)
LID_HORN_PIN = tuple(np.add(gm.LID_HORN, gm.LID_PIN))
LID_BONES = {
    "lid bar": (gimbal.lid_bar, [gm.LID_PIN, gm.LINK_PIN, gm.LID_BEND, LID_HORN_PIN]),
    "lid link": (gimbal.lid_link, [gm.LINK_PIN, gm.LOWER_PIN]),
}


def _bed_down(solid):
    """`solid` turned so its slab's lower face (along x) lies on the bed (z), as it prints."""
    return solid.moved(gimbal._at([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]]))


@pytest.mark.parametrize("part", LID_BONES)
def test_the_lid_bones_print_as_drawn_with_no_overhang_past_45_deg(part):
    assert bone.overhang_deg(_bed_down(LID_BONES[part][0]().val())) <= 45


def _slice(solid, a, b, t, eps=0.01):
    """(mm2, the least mm4, the in-plane mm4, mm) of `solid`'s section square to the span a-b ((y, z), in its slab
    about x 0) at t: its area, its least second moment, the one that bends it in its plane, and its half-width there."""
    a, b = (np.array([0.0, *p]) for p in (a, b))
    along = (b - a) / np.linalg.norm(b - a)
    plane = cq.Plane(origin=tuple(a + (b - a) * t), xDir=(1, 0, 0), normal=tuple(along))
    cut = solid.intersect(cq.Workplane(plane).rect(60, 60).extrude(eps / 2, both=True).val())
    inertia = np.array(cq.Shape.matrixOfInertia(cut)) / eps
    basis = np.array([np.cross(along, (1, 0, 0)), (1.0, 0.0, 0.0)])
    mid = float(np.dot(cut.Center().toTuple(), basis[0]))
    half = max(abs(float(np.dot(v.toTuple(), basis[0])) - mid) for v in cut.Vertices())
    return cut.Volume() / eps, float(np.linalg.eigvalsh(basis @ inertia @ basis.T).min()), float(inertia[0, 0]), half


@pytest.mark.parametrize("style", ["bone", "plain"])  # both looks stay (#704)
@pytest.mark.parametrize("part", LID_BONES)
def test_each_lid_bone_holds_its_lid_servo_at_stall(part, style):
    """SF 2 (beams.MIN_SF) in PETG across its layers along every span, the servo's stall force pulling or pushing it
    between its end pins: on its strength, a span's offset from that line bending it in its plane (out to its
    half-width), and the straight link against Euler buckling."""
    make, joints = LID_BONES[part]
    solid, mat = make(plain=style == "plain").val(), g.MATERIALS[g.PRINTED[f"next {part}"][1]]
    force, (y0, z0), (y1, z1) = beams.stall_force_n(), joints[0], joints[-1]
    for a, b in zip(joints, joints[1:]):
        for t in (0.3, 0.5, 0.7):
            area, _, bend, half = _slice(solid, a, b, t)
            y, z = np.add(a, np.multiply(t, np.subtract(b, a)))
            off = abs((y - y0) * (z1 - z0) - (z - z0) * (y1 - y0)) / math.dist(joints[0], joints[-1])
            stress = force / area + force * off * half / bend
            assert mat["tensile_mpa"]["z"] / stress >= beams.MIN_SF, (a, b, t)
    if len(joints) == 2:
        least = min(_slice(solid, *joints, t)[1] for t in (0.3, 0.5, 0.7))
        assert math.pi**2 * mat["E_mpa"]["z"] * least / math.dist(*joints) ** 2 / force >= beams.MIN_SF
