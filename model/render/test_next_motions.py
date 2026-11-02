"""Seam: model/render/pictures.py next_motions(), the next Mech in motion (#656): the eye gimbal's poses per frame of
each motion, from its rest pose and model/gimbal.py's kinematics."""

import math

import numpy as np
import pytest

from model import gimbal, stages
from model.render import pictures


@pytest.fixture(scope="module")
def motions():
    """Each motion's frames from the next Mech's rest as model/stages.py places it, in metres, as MuJoCo's would be."""
    rest = {}
    for n, p in stages.STAGES["next-mech"].parts.items():
        rest[n] = p.matrix.copy()
        rest[n][:3, 3] /= 1000
    return pictures.next_motions(rest)


def angles(frames, part, point):
    """Per frame the part's (yaw, elevation) of the unit `point` (its mesh frame, a direction from its eye centre)."""
    out = []
    for f in frames:
        d = f[part][:3, :3] @ point
        out.append((math.degrees(math.atan2(d[0], -d[1])), math.degrees(math.asin(d[2]))))
    return np.array(out)


def test_the_sweep_turns_the_eyes_through_their_whole_range_and_the_lids_follow(motions):
    gaze = angles(motions["sweep"], "next L eyeball core:1", (0, -1, 0))
    assert gaze.min(axis=0) == pytest.approx((-gimbal.YAW, -gimbal.PITCH), abs=0.01)
    assert gaze.max(axis=0) == pytest.approx((gimbal.YAW, gimbal.PITCH), abs=0.01)
    lid = angles(motions["sweep"], "next R lid:1", (0, -1, 0))[:, 1]
    assert lid == pytest.approx(angles(motions["sweep"], "next R eyeball core:1", (0, -1, 0))[:, 1], abs=0.5)


def test_a_blink_shuts_both_lids_and_a_wink_one(motions):
    shut = gimbal.LID_EDGES[0] - gimbal.LID_REST
    lid = lambda m, s: angles(motions[m], f"next {s} lid:1", (0, -1, 0))[:, 1].min()  # noqa: E731
    lowest = {m: [lid(m, s) for s in "LR"] for m in ("blink", "wink")}
    assert lowest["blink"] == pytest.approx([shut, shut])
    assert lowest["wink"] == pytest.approx([shut, 0])


def test_each_motion_loops_from_rest_and_moves_the_eyes_alone(motions):
    for frames in motions.values():
        first = frames[0]
        assert set(first) == set(stages.next_eyes().parts)
        assert len(frames) > pictures.HERO_FPS  # longer than a second
        for n, m in first.items():
            assert m == pytest.approx(motions["blink"][0][n])  # every motion starts and loops at the same rest
