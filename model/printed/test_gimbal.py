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

# a horn's hub on its servo's spline: the Envelopes overlap there by design, as in today's Stages
ON_SPLINE = {frozenset((f"next {d} servo:1", f"next {d} horn:1")) for d in gm.drives()}


def _overlaps(a, b):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    apart = any(
        getattr(ba, f"{k}max") < getattr(bb, f"{k}min") or getattr(bb, f"{k}max") < getattr(ba, f"{k}min")
        for k in "xyz"
    )
    return 0.0 if apart else a.intersect(b).Volume()


@pytest.mark.build
def test_no_two_parts_overlap_at_rest():
    shapes = gimbal.at_rest()
    hits = [
        f"{a} / {b}: {v:.2f} mm3"
        for a, b in itertools.combinations(shapes, 2)
        if frozenset((a, b)) not in ON_SPLINE and (v := _overlaps(shapes[a], shapes[b])) > 0.01
    ]
    assert hits == []


@pytest.mark.build
def test_the_block_fits_the_compact_head():
    """#684: the gimbal, servos and horns included, fits a head of at most 140 W x 120 D x 150 H."""
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
    poses = [(-60, -12), (-20, 0), (10, 14)]
    model, rows = gimbal.skeleton(gimbal.at_rest())
    data = mujoco.MjData(model)
    for (lid, pitch), q in zip(poses, rows(poses)):
        data.qpos[:] = q
        mujoco.mj_kinematics(model, data)
        for name, m in gm.moved(lid, pitch).items():
            assert data.body(name).xmat.reshape(3, 3) == pytest.approx(m[:3, :3], abs=1e-9)
            assert data.body(name).xpos * 1000 == pytest.approx(m[:3, 3], abs=1e-6)
    # the lids, their horns, their bars, the cores with their caps, the push-rods (each L and R alike); the pitch horn,
    # the bail, the pitch bar
    assert model.njnt == 8


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


def test_each_push_rod_stays_within_its_cups_reach_of_the_balls_line():
    """gimbal.report reads the lids' clearance to a push-rod as a capsule CUP_R round the line between its balls."""
    v, _ = gimbal.push_rod().val().tessellate(0.01, 0.1)
    assert max(math.hypot(p.x, p.z - gm.LEVER) for p in v) <= gimbal.CUP_R + 1e-6
