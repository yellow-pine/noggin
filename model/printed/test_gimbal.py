"""Seam: the next Mech's eye gimbal parts (model/printed/gimbal.py) as model/stages.py places them at rest, each lid's
shank beside them: no two overlap, and each cap's pupil seat turns toward the other eye (the toe-in, #630)."""

import itertools

import cadquery as cq
import mujoco
import pytest

from model import gimbal as gm
from model.printed import gimbal

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
