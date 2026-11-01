import functools
import json
import math

import numpy as np
import pytest

from model import electrical, mjcf, traces
from model import trajectories as tj
from model.render import hero

pytestmark = pytest.mark.model
SETTLED_DEG = 0.5  # a servo's deadband (mjcf.KP)


@functools.cache
def built(doc):
    return mjcf.model(doc)


def turned(frames, body):
    """Degrees the body has turned from frame 0, per frame."""
    q0 = frames[0][1][body]
    return [math.degrees(2 * math.acos(min(1.0, abs(float(np.dot(q0, q[body])))))) for _, q in frames]


def test_the_mech_at_rest_stays_at_rest():
    model = built("noggin-stage3")
    rest = [(-1, s, 0.0) for s in ("l_lid", "l_eye", "r_lid", "r_eye", "mouth", "tilt", "rotate")]
    frames = tj.play(model, rest, range(0, 1001, 100))
    for pos, quat in frames[1:]:
        assert np.abs(pos - frames[0][0]).max() * 1000 < 0.01
        assert np.abs(quat - frames[0][1]).max() < 1e-4


def test_a_step_reaches_its_target_no_faster_than_the_servo_slews():
    """A 30 degree step on the L lid servo: the horn never runs ahead of the rated slew, is within the deadband by
    250 ms and its rise to 90 % takes the slew's time give or take 30 ms."""
    model = built("noggin-stage1")
    writes = [(-1, s, 0.0) for s in ("l_lid", "l_eye", "r_lid", "r_eye")] + [(0, "l_lid", 30.0)]
    times = range(0, 401, 5)
    horn = model.body("L lid horn:1").id
    deg = turned(tj.play(model, writes, times), horn)
    rate = electrical.servo.rate(electrical.SERVO_MIN_V) / 1000  # deg per ms
    assert all(d <= rate * t + SETTLED_DEG for t, d in zip(times, deg))
    assert all(abs(d - 30) < SETTLED_DEG for t, d in zip(times, deg) if t >= 250)
    rise = next(t for t, d in zip(times, deg) if d >= 27)
    assert abs(rise - 27 / rate) <= 30, rise


def test_a_gesture_trajectory_has_a_frame_per_trace_frame_and_every_part(tmp_path, monkeypatch):
    monkeypatch.setattr(tj, "OUT", str(tmp_path))
    (path,) = tj.bake("noggin-stage1", ["wink"])
    out = json.load(open(path))
    model = built("noggin-stage1")
    assert (out["doc"], out["motion"], out["fps"], out["stamp"]) == (
        "noggin-stage1",
        "wink",
        10,
        tj.stamp("noggin-stage1"),
    )
    assert set(out["parts"]) == {model.body(b).name for b in range(1, model.nbody)}
    n = len(traces.record("wink"))
    assert all(len(p["pos"]) == len(p["quat"]) == n for p in out["parts"].values())
    assert out["parts"]["L lid horn:1"]["quat"][0] != out["parts"]["L lid horn:1"]["quat"][n // 2]  # the wink moves it
    assert tj.stale("noggin-stage1")  # its other gestures are not baked here


def test_the_hero_turns_the_head_as_keyed_and_never_through_the_pan_toggle():
    """Stage 3 plays the hero at full speed: the head follows its keys (hero.HEAD, the pan pivot's own degrees) within
    2 degrees, so the pan four-bar never passes its dead point (geometry.LIMITS rotate: it toggles at horn -43.4, where
    the head would swing back the other way)."""
    model = built("noggin-stage3")
    frames = tj.play(model, *tj.hero_commands())
    assert len(frames) == len(hero.frames())
    head = turned(frames, model.body("pan turntable:1").id)
    for k, deg in enumerate(head):
        keyed = abs(hero._eased(hero.HEAD["rotate"], k / tj.FPS))
        assert abs(deg - keyed) < 2, (k, deg, keyed)
