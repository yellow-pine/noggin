"""Seam: model/traces.py's gesture traces (model horn joint degrees per 100 ms frame, recorded from the eye program),
judged on the engine's lid geometry (model/engine/lids.py) against README "What it does"."""

import importlib.util
import os

import pytest

from model import geometry as g
from model import sim
from model.engine import lids

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


@pytest.mark.parametrize("side", "LR")
def test_the_calibrated_close_shuts_the_lids_inside_the_swept_range(side):
    """The real Mech winks shut at lid_closed (#134): the edges just touch, no overlap (Cansin, #189: the lids close
    quietly), and the pose is one make sim sweeps."""
    closed = traces.joint(f"{side.lower()}_lid", traces.CAL["lid_closed"])
    assert -0.1 < lids.gap(side, closed) <= 0  # 0.1 deg of lip is 0.04 mm
    assert g.HORN_LIMITS[f"{side.lower()}_lid"][0] - 90 <= closed


def test_rest_matches_the_rest_photo():
    rest = traces.record("wink")[0]  # every recording starts at rest
    # docs/build-photos/eyes-rest-top.jpg read at face value: lid horns L -15.2, R -16.3 (docs/research/2026-10-31-shafts.md);
    # the camera tilt the photo's eye readings show only raises the lid readings, so the model may sit up to 1.5 above
    assert -15.2 <= rest["l_lid"] <= -15.2 + 1.5 and -16.3 <= rest["r_lid"] <= -16.3 + 1.5
    assert rest["l_eye"] == pytest.approx(rest["r_eye"])


def test_eureka_peaks_wider_than_rest_and_blinks_shut_twice():
    frames = looks("eureka")
    rest = frames[0]["L"][0]
    for s in "LR":
        assert max(f[s][0] for f in frames) > rest + 30
        assert len(runs([f[s][0] <= 0 for f in frames])) == 2  # eureka 2: the double blink, shut at lid_closed


def test_attention_holds_half_lids_while_the_eyes_scan_both_ways():
    frames = looks("attention")
    scan = [f for f in frames if abs(f["L"][2]) > 2]
    assert len(scan) > 20
    for s in "LR":
        think, opened = (traces.joint(f"{s.lower()}_lid", traces.CAL[k]) for k in ("lid_think", "lid_open"))
        assert all(lids.gap(s, think) - 0.5 <= f[s][0] <= lids.gap(s, opened) + 0.5 for f in scan)
        assert all(f[s][1] > 0 for f in scan)  # the pupils show under the half lids
        assert min(f[s][2] for f in scan) < -5 and max(f[s][2] for f in scan) > 5


def test_thinking_keeps_the_pupils_showing_under_low_lids():
    frames = looks("thinking")
    rest = frames[0]
    settled = frames[int(0.6 / FRAME_S) :]
    for s in "LR":
        shown = [f[s][1] > 0 for f in settled]
        assert sum(shown) >= 0.9 * len(settled)  # a blink may fall in the window
        assert all(f[s][0] < rest[s][0] for f in settled)


def test_wink_closes_one_eye_only():
    frames = looks("wink")  # wink 1: the mech's left lid
    assert min(f["L"][0] for f in frames) <= 0
    assert min(f["R"][0] for f in frames) == pytest.approx(frames[0]["R"][0], abs=0.5)


def test_bored_has_one_long_closure_under_two_seconds():
    frames = looks("bored")
    closures = runs([f["L"][0] <= 0 and f["R"][0] <= 0 for f in frames])
    long = [n for n in closures if n * FRAME_S > 1.0]
    assert len(closures) == 3 and len(long) == 1 and long[0] * FRAME_S < 2.0


def test_wince_squeezes_then_reopens():
    frames = looks("wince")
    for s in "LR":
        squeeze = next(i for i, f in enumerate(frames) if f[s][0] <= 0)
        assert squeeze <= 2  # snaps shut at once
        assert frames[-1][s][0] == pytest.approx(frames[0][s][0], abs=1)
