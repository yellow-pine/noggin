"""Seam: model/traces.py's gesture traces (model horn joint degrees per 100 ms frame, recorded from the eye program),
judged on the model's lid geometry (model/lids.py) against README "What it does"."""

import importlib.util
import os

import pytest

from model import geometry as g
from model import lids, sim

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location(
    "traces", os.path.join(HERE, "traces.py")
)  # by path: model/ must never shadow eyes/
traces = importlib.util.module_from_spec(spec)
spec.loader.exec_module(traces)

FRAME_S = traces.FRAME_MS / 1000


def looks(gesture):
    """Per frame and side: (gap between the lid edges deg, fraction of the pupil shown, eye horn deg)."""
    return [
        {
            s: (lids.gap(s, f[f"{s.lower()}_lid"]), lids.pupil_shown(s, f[f"{s.lower()}_lid"]), f[f"{s.lower()}_eye"])
            for s in "LR"
        }
        for f in traces.record(gesture)
    ]


def runs(flags):
    """Lengths in frames of the runs of consecutive True."""
    out, n = [], 0
    for x in [*flags, False]:
        if x:
            n += 1
        elif n:
            out, n = [*out, n], 0
    return out


@pytest.mark.parametrize("gesture", sorted(traces.GESTURES))
def test_every_gesture_stays_inside_the_calibrated_lid_ends_and_eye_limits(gesture):
    frames = traces.record(gesture)
    ends = sim.calibrated_extremes(traces.CAL)
    assert 10 <= len(frames) <= 200, len(frames)  # 1-20 s at 10 fps
    for f in frames:
        for s in "LR":
            closed, opened = ends[f"{s.lower()}_lid"]
            lo, hi = (d - 90 for d in g.HORN_LIMITS[f"{s.lower()}_eye"])
            assert closed - 0.01 <= f[f"{s.lower()}_lid"] <= opened + 0.01, (gesture, f)
            assert lo - 0.01 <= f[f"{s.lower()}_eye"] <= hi + 0.01, (gesture, f)


@pytest.mark.build
@pytest.mark.parametrize("side", "LR")
def test_the_calibrated_closed_end_shuts_the_lids_edges_just_touching(side):
    """The real Mech's lids close at their calibrated closed end (lo 39, #255): the edges just touch, quiet, no overlap
    (Cansin), and the pose is one just sim sweeps. The program's blinks close there (lid_closed 0)."""
    closed = traces.joint(f"{side.lower()}_lid", 0)
    assert -0.1 < lids.gap(side, closed) <= 0  # 0.1 deg of lip is 0.04 mm
    assert g.HORN_LIMITS[f"{side.lower()}_lid"][0] - 90 <= closed
    assert traces.joint(f"{side.lower()}_lid", traces.CAL["lid_closed"]) == closed


@pytest.mark.build
def test_rest_shows_the_pupils_between_closed_and_the_free_travel():
    rest = traces.record("wink")[0]  # every recording starts at rest
    # Conflict, recorded (geometry.HORN_AT_90): the rest-top photo (L -15.2, R -16.3) predates #213 and #255; at #255's
    # calibration the model rests at L -8.35, R -5.75, the right 2.6 deg more open (its rest 64 against 61.4)
    for s in "LR":
        lo, hi = (d - 90 for d in g.HORN_LIMITS[f"{s.lower()}_lid"])
        assert lo < rest[f"{s.lower()}_lid"] < hi and lids.pupil_shown(s, rest[f"{s.lower()}_lid"]) > 0.5
    assert rest["r_lid"] - rest["l_lid"] == pytest.approx(traces.CAL["r_lid_rest"] - traces.CAL["l_lid_rest"])
    assert rest["l_eye"] == pytest.approx(rest["r_eye"])


@pytest.mark.build
def test_eureka_peaks_wider_than_rest_and_blinks_shut_twice():
    frames = looks("eureka")
    rest = frames[0]["L"][0]
    for s in "LR":
        assert max(f[s][0] for f in frames) > rest + 30
        assert len(runs([f[s][0] <= 0 for f in frames])) == 2  # eureka 2: the double blink, shut at lid_closed


@pytest.mark.build
def test_attention_holds_half_lids_while_the_eyes_scan_both_ways():
    frames = looks("attention")
    scan = [f for f in frames if abs(f["L"][2]) > 2]
    assert len(scan) > 20
    for s in "LR":
        think, opened = (traces.joint(f"{s.lower()}_lid", traces.CAL[k]) for k in ("lid_think", "lid_open"))
        assert all(lids.gap(s, think) - 0.5 <= f[s][0] <= lids.gap(s, opened) + 0.5 for f in scan)
        assert all(f[s][1] > 0 for f in scan)  # the pupils show under the half lids
        assert min(f[s][2] for f in scan) < -5 and max(f[s][2] for f in scan) > 5


@pytest.mark.build
def test_thinking_keeps_the_pupils_showing_under_low_lids():
    frames = looks("thinking")
    rest = frames[0]
    settled = frames[int(0.6 / FRAME_S) :]
    for s in "LR":
        shown = [f[s][1] > 0 for f in settled]
        assert sum(shown) >= 0.9 * len(settled)  # a blink may fall in the window
        assert all(f[s][0] < rest[s][0] for f in settled)


@pytest.mark.build
def test_wink_closes_one_eye_and_the_other_squints():
    frames = looks("wink")  # wink 1: the mech's left lid; the right squints 20% (#258)
    squint = lids.gap("R", traces.joint("r_lid", 0.8 * traces.CAL["lid_rest"]))
    assert min(f["L"][0] for f in frames) <= 0
    assert 0 < min(f["R"][0] for f in frames) == pytest.approx(squint, abs=0.5)


@pytest.mark.build
def test_bored_has_one_long_closure_under_two_seconds():
    frames = looks("bored")
    closures = runs([f["L"][0] <= 0 and f["R"][0] <= 0 for f in frames])
    long = [n for n in closures if n * FRAME_S > 1.0]
    assert len(closures) == 3 and len(long) == 1 and long[0] * FRAME_S < 2.0


@pytest.mark.build
def test_wince_squeezes_then_reopens():
    frames = looks("wince")
    for s in "LR":
        squeeze = next(i for i, f in enumerate(frames) if f[s][0] <= 0)
        assert squeeze <= 2  # snaps shut at once
        assert frames[-1][s][0] == pytest.approx(frames[0][s][0], abs=1)


def horn(writes, name):
    """[(ms, deg)] the writes to one of the next Mech's horns."""
    return [(t, d) for t, s, d in writes if s == name]


def test_the_next_mech_points_its_linked_eyes_through_the_gimbals_command_map():
    """#663: the wink's glance, the eye program's 8 deg of its 30 to the Mech's left, is a sixth of a turn over the
    gimbal's 25 deg range on the one yaw servo (6.67 deg), the pitch servo level; the winking lid shuts past the cap's
    rim (lid servo -65, model/test_gimbal.py) as the other squints, and both come back to rest (lid servo 0)."""
    writes, times = traces.next_commands("wink")
    yaw, pitch = (horn(writes, f"next {s} horn") for s in ("yaw", "pitch"))
    assert any(d == pytest.approx(8 / 30 * 25, abs=0.01) for _, d in yaw)  # where the saccade lands
    assert -1 < min(d for _, d in yaw) and max(d for _, d in yaw) < 8  # a real saccade overshoots a little
    assert all(abs(d) < 0.01 for _, d in pitch)
    left, right = (horn(writes, f"next {s} lid horn") for s in "LR")
    assert min(d for _, d in left) == pytest.approx(-65)
    assert -65 < min(d for _, d in right) < 0
    assert left[0][1] == right[0][1] == left[-1][1] == right[-1][1] == 0
    assert times[-1] > max(t for t, _, _ in writes)


def test_the_next_mech_rests_with_a_blink_its_lids_following_its_level_gaze():
    """#663, #51 Gestures: Rest on the next Mech blinks within its span (the eye program's 3-6 s gap), both lids shut
    and back to rest; the gaze stays level (today's program has no pitch), so the lids follow it at rest."""
    writes, _ = traces.next_commands("rest")
    for s in "LR":
        lid = horn(writes, f"next {s} lid horn")
        shut = [t for t, d in lid if d == pytest.approx(-65)]
        assert shut and 3000 <= shut[0] <= 6000 + 200 and lid[-1][1] == 0
    assert set(traces.NEXT_MOTIONS) == {*traces.GESTURES, "rest"}


@pytest.mark.parametrize("doc", sorted(g.NEXT))
def test_every_motion_of_the_next_mech_has_its_commands(doc):
    """Each motion a next Mech document plays (trajectories.motions) gives writes before ms 0 and its frame times: its
    gestures and Rest through the eye gimbal, the next hero (#642) as the hero's own writes."""
    from model import trajectories

    for motion in trajectories.motions(doc):
        writes, times = trajectories.commands(doc, motion)
        assert any(t < 0 for t, _, _ in writes) and len(times) > 1, motion
