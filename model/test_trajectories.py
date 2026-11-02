import functools
import io
import json
import math

import numpy as np
import pytest

from model import electrical, gates, geometry, gimbal, mjcf, mujoco_report, traces
from model import trajectories as tj
from model.render import hero
from model.test_report import KNOWN_PAIRS

pytestmark = pytest.mark.model
SETTLED_DEG = 0.5  # a servo's deadband (mjcf.SERVO kp)


# Pairs a gesture drives deeper than at rest because the calibrated servo ends reach past the model's free travel, with
# why: excused only in the frames where their side's lid horn is past it (geometry.LIMITS), never at the closed end.
_OPEN = (
    "eureka widens the lids to lid_open (0.95: horn +29.4 L, +29.6 R) toward the calibrated open end 102 (+32.25,"
    " geometry.HORN_AT_90), which the Mech runs without binding (#255: no stop or clutch slip up to 133) but which lies"
    " past the model's free travel (geometry.LIMITS, #210): the ears' back corners cross from +16.5 and the upper lid"
    " reaches the eye bracket's arm from +28. Conflict, recorded, not settled"
)
# Pairs whose pieces read deeper than at rest along a motion where their exact solids cannot meet, with why.
NESTED = {
    frozenset((f"next {s} eyeball cap:1", f"next {s} lid:1")): "the lid's shell turns about the cap's own centre, its"
    " inside 1.5 mm out from the cap (gimbal.LID_R, CAP_R): its convex pieces fill that inside, so they read the cap"
    " 0.06 mm deeper than at rest as it yaws under a half-shut lid (attention); gimbal.report() holds the exact gap (#663)"
    for s in "LR"
}
KNOWN_CALIBRATED = {
    **{frozenset((f"{s} lower lid:1", f"{s} upper lid:1")): _OPEN for s in "LR"},
    **{frozenset((f"{s} upper lid:1", "eye bracket:1")): _OPEN for s in "LR"},
}


@functools.cache
def built(doc):
    return mjcf.model(doc)


def overlaps(doc, motion, calibrated=KNOWN_CALIBRATED):
    """{(part, part): (ms, mm)} a reading of each pair whose pieces go PENETRATION_MM deeper than at rest anywhere in
    the motion as played, certified between the sim's steps (gates.certify, #627), KNOWN_PAIRS and NESTED aside and the
    calibrated pairs while their lid horn is past its free travel."""
    model = built(doc)
    rest = mjcf.pose(model, {})
    floors = {
        p: min(gates.separation(model, rest, p), 0) - mujoco_report.PENETRATION_MM
        for p in gates.pairs(model)
        if frozenset(p) not in KNOWN_PAIRS.keys() | NESTED.keys()
    }

    def excused(pair, data):
        if frozenset(pair) not in calibrated:  # the next Mech has no such lids
            return False
        past = {
            s
            for s in "LR"
            if math.degrees(data.joint(f"{s} lid horn").qpos[0]) > geometry.HORN_LIMITS[f"{s.lower()}_lid"][1] - 90
        }
        return frozenset(pair) in calibrated and pair[0][0] in past  # pairs come sorted: a calibrated pair's lid first

    step_ms = model.opt.timestep * 1000
    writes, times = tj.commands(doc, motion)
    qpos = tj.play(model, writes, np.arange(0, times[-1] + step_ms / 2, step_ms), read=lambda d: d.qpos.copy())
    found = gates.certify(model, np.array(qpos), floors, excused)
    return {pair: (row * step_ms, mm) for pair, (row, mm) in found.items()}


@pytest.mark.parametrize(
    "doc,motion", [(d, m) for d in geometry.STAGES | geometry.NEXT for m in tj.motions(d)], ids=lambda x: x
)  # ids carry the document: CI's model shards split on it
def test_no_two_parts_overlap_in_any_frame_of_any_motion(doc, motion):
    """#255, #663: every gesture and the hero as played on each Stage, and the next Mech's gestures and Rest: no pair of
    parts more than PENETRATION_MM deeper than at rest at any step of the sim, not only in the 100 ms frames the GIFs and
    the web viewer draw (#627)."""
    assert overlaps(doc, motion) == {}


def test_known_calibrated_pairs_still_overlap():
    """When the model's lids can reach the calibrated open end, a KNOWN_CALIBRATED entry no longer overlaps: drop it."""
    assert set(KNOWN_CALIBRATED) <= {frozenset(p) for p in overlaps("noggin-stage1", "eureka", calibrated={})}


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
    """A 30 degree step on the L lid servo: after its PWM frame's delay the horn never runs ahead of the rated slew, is
    within the deadband by 250 ms and its rise to 90 % takes the delay and the slew's time give or take 30 ms."""
    model = built("noggin-stage1")
    writes = [(-1, s, 0.0) for s in ("l_lid", "l_eye", "r_lid", "r_eye")] + [(0, "l_lid", 30.0)]
    times = range(0, 401, 5)
    horn = model.body("L lid horn:1").id
    deg = turned(tj.play(model, writes, times), horn)
    rate = electrical.servo.rate(electrical.SERVO_MIN_V) / 1000  # deg per ms
    delay = mjcf.SERVO["delay_s"] * 1000
    assert all(d <= rate * max(t - delay, 0) + SETTLED_DEG for t, d in zip(times, deg))
    assert all(abs(d - 30) < SETTLED_DEG for t, d in zip(times, deg) if t >= 250)
    rise = next(t for t, d in zip(times, deg) if d >= 27)
    assert abs(rise - delay - 27 / rate) <= 30, rise


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


def test_an_edit_to_the_core_program_or_its_calibration_stales_the_trajectories(monkeypatch):
    """model/traces.py plays eyes/eyes.py under eyes/calibration.json, so an edit to either moves the stamp (#151 took
    them out of the report's inputs)."""
    before = tj.stamp("noggin-stage1")
    for edited in ("eyes/eyes.py", "eyes/calibration.json"):

        def opened(path, mode="r", edited=edited):
            with open(path, mode) as f:
                data = f.read()
            return io.BytesIO(data + b"#" if path.endswith(edited) else data)

        monkeypatch.setattr(tj, "open", opened, raising=False)
        assert tj.stamp("noggin-stage1") != before, edited


def test_the_hero_turns_the_head_as_keyed_and_never_through_the_pan_toggle():
    """Stage 3 plays the hero at full speed: the head follows its keys (hero.HEAD, the pan pivot's own degrees), read
    the servo's PWM delay late (mjcf.drive), within 2 degrees, so the pan four-bar never passes its dead point (geometry.LIMITS rotate: it toggles at horn -43.4, where
    the head would swing back the other way)."""
    model = built("noggin-stage3")
    frames = tj.play(model, *tj.hero_commands())
    assert len(frames) == len(hero.frames())
    head = turned(frames, model.body("pan turntable:1").id)
    for k, deg in enumerate(head):
        keyed = abs(hero._eased(hero.HEAD["rotate"], k / tj.FPS - mjcf.SERVO["delay_s"]))
        assert abs(deg - keyed) < 2, (k, deg, keyed)


def test_the_next_mech_plays_the_wink_on_its_eye_gimbal():
    """#663: the eye program's wink on the next Mech's MuJoCo model: one yaw servo turns both yokes alike to the glance
    (6.67 deg, model/test_traces.py) within the servos' deadband, the gaze stays level, the winking lid shuts past the
    cap's rim (-65, model/test_gimbal.py) and the other squints; all come back to rest."""
    model = built("next-mech")
    names = ("next L yaw pivot", "next R yaw pivot", "next L eyeball pitch", "next L lid pivot", "next R lid pivot")
    writes, times = tj.commands("next-mech", "wink")
    frames = np.degrees(tj.play(model, writes, times, read=lambda d: [d.joint(j).qpos[0] for j in names]))
    left, right, pitch, lid, other = frames.T
    assert np.abs(left - right).max() < 0.1 and np.abs(pitch).max() < SETTLED_DEG
    assert abs(left.max() - 8 / 30 * 25) < 1.5  # its saccade lands, overshooting a little on the way
    assert abs(lid.min() + 65) < SETTLED_DEG and -65 + 5 < other.min() < -5
    assert np.abs(frames[-1]).max() < SETTLED_DEG


def test_the_next_mechs_command_map_levels_a_yawed_gaze_in_mujoco():
    """#663: at full yaw the push-rod's Hooke error would lower a 15 deg upward gaze; the gimbal's command map
    (gimbal.servos) gives the pitch servo the turn that holds it at 15 deg in MuJoCo, as its kinematics solve it."""
    model = built("next-mech")
    yaw, pitch = gimbal.servos(gimbal.YAW, gimbal.PITCH)
    data = mjcf.pose(model, {"next yaw horn": yaw, "next pitch horn": pitch})
    for s in "LR":
        assert math.degrees(data.joint(f"next {s} yaw pivot").qpos[0]) == pytest.approx(gimbal.YAW, abs=SETTLED_DEG)
        assert math.degrees(data.joint(f"next {s} eyeball pitch").qpos[0]) == pytest.approx(15, abs=SETTLED_DEG)
