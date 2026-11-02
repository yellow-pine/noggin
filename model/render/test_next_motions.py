"""Seam: model/render/pictures.py next_motions() and next_played(), the next Mech in motion (#656, #663): the eye
gimbal's poses per frame of the keyed sweep, from its rest pose and model/gimbal.py's kinematics, and of each motion it
plays, from its baked trajectory."""

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


def test_each_motion_loops_from_rest_and_moves_the_eyes_alone(motions):
    for frames in motions.values():
        first = frames[0]
        assert set(first) == set(stages.next_eyes().parts)
        assert len(frames) > pictures.HERO_FPS  # longer than a second
        for n, m in first.items():
            assert m == pytest.approx(motions["sweep"][0][n])  # every motion starts and loops at the same rest


def test_the_next_mech_plays_each_gesture_and_rest_in_the_pictures_as_mujoco_baked_it(monkeypatch):
    """#663: beside the keyed sweep, a picture of each motion the next Mech plays (its gestures and Rest), its eye gimbal
    alone, from its baked trajectory (here 3 s at the trajectory's 10 fps) at the hero's 8 fps."""
    parts = stages.STAGES["next-mech"].parts
    baked = [{n: np.eye(4) * (1 + k) for n in parts} for k in range(30)]
    monkeypatch.setattr(pictures.trajectories, "poses", lambda doc, m: baked if doc == "next-mech" else None)
    assert [m for m, keys in pictures.NEXT_MOTIONS.items() if keys is None] == [
        "eureka", "attention", "bored", "wince", "wink", "thinking", "rest"
    ]  # fmt: skip
    played = pictures.next_played()
    assert set(played) == {"eureka", "attention", "bored", "wince", "wink", "thinking", "rest"}
    for frames in played.values():
        assert len(frames) == 24 and set(frames[0]) == set(stages.next_eyes().parts)
        assert frames[-1]["next L lid:1"][0, 0] == pytest.approx(30)  # it ends on the last baked frame
