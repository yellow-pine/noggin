import functools
import io
import json
import math

import numpy as np
import pytest

from model import electrical, gates, geometry, gimbal, mjcf, mujoco_report, stages
from model import trajectories as tj
from model.test_report import known

pytestmark = pytest.mark.model
SETTLED_DEG = 0.5  # a servo's deadband (mjcf.SERVO kp)
DOC = geometry.SIMULATED[-1]  # the whole Mech, mechanical (#809)


# Pairs whose pieces read deeper than at rest along a motion where their exact solids cannot meet, with why.
NESTED = {
    frozenset(
        (f"next {s} eyeball cap:1", f"next {s} upper lid:1")
    ): "the upper lid's shell turns about the cap's own centre, its"
    " inside 1.5 mm out from the cap (gimbal.LID_R, CAP_R): its convex pieces fill that inside, so they read the cap"
    " 0.06 mm deeper than at rest as it yaws under a half-shut lid (attention); gimbal.report() holds the exact gap (#663)"
    for s in "LR"
}


@functools.cache
def built(doc):
    return mjcf.model(doc)


@functools.cache
def played(doc, motion):
    """(model, qpos a sim step, floors): the motion as played, and the floor (mm) of each pair, PENETRATION_MM deeper
    than at rest, the known pairs aside (test_report.known, NESTED)."""
    model = built(doc)
    rest = mjcf.pose(model, {})
    floors = {
        p: min(gates.separation(model, rest, p), 0) - mujoco_report.PENETRATION_MM
        for p in gates.pairs(model)
        if not known(p) and frozenset(p) not in NESTED
    }
    step_ms = model.opt.timestep * 1000
    writes, times = tj.commands(doc, motion)
    qpos = tj.play(model, writes, np.arange(0, times[-1] + step_ms / 2, step_ms), read=lambda d: d.qpos.copy())
    return model, np.array(qpos), floors


@pytest.fixture
def motion(doc, name):
    """The motion played in setup, once a worker: CI's 15 s times the certifying alone."""
    return played(doc, name)


CHUNKS = 4  # a motion's pairs certified in four tests, so each holds CI's 15 s (#808)


def overlaps(played, chunk, chunks):
    """{(part, part): (ms, mm)} a reading of each pair (the chunk-th of `chunks` of them) whose pieces go below its
    floor anywhere in the motion as played, certified between the sim's steps (gates.certify, #627)."""
    model, qpos, floors = played
    mine = {p: floors[p] for p in sorted(floors)[chunk::chunks]}
    step_ms = model.opt.timestep * 1000
    return {pair: (row * step_ms, mm) for pair, (row, mm) in gates.certify(model, qpos, mine).items()}


@pytest.mark.parametrize(
    "doc, name, chunk",
    [(d, m, c) for d in geometry.NEXT for m in tj.motions(d) for c in range(CHUNKS) if d in geometry.SIMULATED],
    ids=str,
)  # ids carry the document: CI's model shards split on it
def test_no_two_parts_overlap_in_any_frame_of_any_motion(motion, chunk):
    """#255, #663: every motion as played on the next Mech (its gestures and Rest on its eye gimbal, #663; the next hero
    on its neck and jaw, #642): no pair of parts more than PENETRATION_MM deeper than at rest at any step of the sim, not
    only in the 100 ms frames the GIFs and the web viewer draw (#627)."""
    assert overlaps(motion, chunk, CHUNKS) == {}


def turned(frames, body):
    """Degrees the body has turned from frame 0, per frame."""
    q0 = frames[0][1][body]
    return [math.degrees(2 * math.acos(min(1.0, abs(float(np.dot(q0, q[body])))))) for _, q in frames]


def test_the_mech_at_rest_stays_at_rest():
    model = built(DOC)
    rest = [(-1, h, 0.0) for h in stages.STAGES[DOC].horns]
    frames = tj.play(model, rest, range(0, 1001, 100))
    for pos, quat in frames[1:]:
        assert np.abs(pos - frames[0][0]).max() * 1000 < 0.01
        assert np.abs(quat - frames[0][1]).max() < 1e-4


def test_a_step_reaches_its_target_no_faster_than_the_servo_slews():
    """A 30 degree step on the L lid servo: after its PWM frame's delay the horn never runs ahead of the rated slew, is
    within the deadband by 250 ms and its rise to 90 % takes the delay and the slew's time give or take 30 ms."""
    model = built(DOC)
    writes = [(-1, h, 0.0) for h in stages.STAGES[DOC].horns] + [(0, "next L lid horn", -30.0)]
    times = range(0, 401, 5)
    deg = turned(tj.play(model, writes, times), model.body("next L lid horn:1").id)
    rate = electrical.servo.rate(electrical.SERVO_MIN_V) / 1000  # deg per ms
    delay = mjcf.SERVO["delay_s"] * 1000
    assert all(d <= rate * max(t - delay, 0) + SETTLED_DEG for t, d in zip(times, deg))
    assert all(abs(d - 30) < SETTLED_DEG for t, d in zip(times, deg) if t >= 250)
    rise = next(t for t, d in zip(times, deg) if d >= 27)
    assert abs(rise - delay - 27 / rate) <= 30, rise


def test_a_gesture_trajectory_has_a_frame_per_trace_frame_and_every_part(tmp_path, monkeypatch):
    monkeypatch.setattr(tj, "OUT", str(tmp_path))
    (path,) = tj.bake(DOC, ["wink"])
    out = json.load(open(path))
    model = built(DOC)
    assert (out["doc"], out["motion"], out["fps"], out["stamp"]) == (DOC, "wink", 10, tj.stamp(DOC))
    assert set(out["parts"]) == {model.body(b).name for b in range(1, model.nbody)}
    n = len(tj.commands(DOC, "wink")[1])
    assert all(len(p["pos"]) == len(p["quat"]) == n for p in out["parts"].values())
    lid = out["parts"]["next L lid horn:1"]["quat"]
    assert lid[0] != lid[n // 2]  # the wink moves it
    assert tj.stale(DOC)  # its other motions are not baked here


def test_an_edit_to_the_core_program_or_its_calibration_stales_the_trajectories(monkeypatch):
    """model/traces.py plays eyes/eyes.py under eyes/calibration.json, so an edit to either moves the stamp (#151 took
    them out of the report's inputs)."""
    before = tj.stamp(DOC)
    for edited in ("eyes/eyes.py", "eyes/calibration.json"):

        def opened(path, mode="r", edited=edited):
            with open(path, mode) as f:
                data = f.read()
            return io.BytesIO(data + b"#" if path.endswith(edited) else data)

        monkeypatch.setattr(tj, "open", opened, raising=False)
        assert tj.stamp(DOC) != before, edited


def test_the_next_mech_plays_the_wink_on_its_eye_gimbal():
    """#663: the eye program's wink on the next Mech's MuJoCo model: one yaw servo turns both yokes alike to the glance
    (6.67 deg, model/test_traces.py) within the servos' deadband, the gaze stays level, the winking eye's upper lid
    shuts (-21, model/test_gimbal.py) and its lower lid rises on its link to meet it, and the other squints; all come
    back to rest."""
    model = built(DOC)
    names = ("next L yaw pivot", "next R yaw pivot", "next L eyeball pitch", "next L lid pivot", "next R lid pivot")
    names += ("next L lower lid pivot",)
    writes, times = tj.commands(DOC, "wink")
    frames = np.degrees(tj.play(model, writes, times, read=lambda d: [d.joint(j).qpos[0] for j in names]))
    left, right, pitch, lid, other, under = frames.T
    assert np.abs(left - right).max() < 0.1 and np.abs(pitch).max() < SETTLED_DEG
    assert abs(left.max() - 8 / 30 * 25) < 1.5  # its saccade lands, overshooting a little on the way
    assert abs(lid.min() + 21) < SETTLED_DEG and -21 + 5 < other.min() < -2
    assert abs(under.max() - gimbal.lower(-21)) < SETTLED_DEG
    assert np.abs(frames[-1]).max() < SETTLED_DEG


def test_the_next_mechs_head_turns_the_eyes_way_on_a_wide_gaze_shift_in_mujoco():
    """#688: eureka's 22 deg dart on the next Mech's MuJoCo model: the pan pivot turns the head the way the eyes look, to
    the 11 deg it carries (model/test_traces.py) within the servo's deadband, while the eyes counter-rotate back from
    the dart; the head comes back to rest."""
    model = built(DOC)
    writes, times = tj.commands(DOC, "eureka")
    names = ("next L yaw pivot", "pan pivot")
    yaw, pan = np.degrees(tj.play(model, writes, times, read=lambda d: [d.joint(j).qpos[0] for j in names])).T
    side = np.sign(yaw[np.abs(yaw).argmax()])
    assert (side * pan).max() == pytest.approx(0.6 * 22 * 25 / 30, abs=1)
    turned = int(np.abs(pan).argmax())
    assert abs(yaw[turned] + pan[turned] - side * 22 * 25 / 30) < 2  # the gaze held on the dart
    assert abs(pan[-1]) < SETTLED_DEG


def test_the_next_mechs_command_map_levels_a_yawed_gaze_in_mujoco():
    """#663: at full yaw the push-rod's Hooke error would lower a 15 deg upward gaze; the gimbal's command map
    (gimbal.servos) gives the pitch servo the turn that holds it at 15 deg in MuJoCo, as its kinematics solve it."""
    model = built(DOC)
    yaw, pitch = gimbal.servos(gimbal.YAW, gimbal.PITCH)
    data = mjcf.pose(model, {"next yaw horn": yaw, "next pitch horn": pitch})
    for s in "LR":
        assert math.degrees(data.joint(f"next {s} yaw pivot").qpos[0]) == pytest.approx(gimbal.YAW, abs=SETTLED_DEG)
        assert math.degrees(data.joint(f"next {s} eyeball pitch").qpos[0]) == pytest.approx(15, abs=SETTLED_DEG)
