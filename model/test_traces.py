"""Seam: model/traces.py's gesture traces, the eye program's writes as the next Mech's eyes Core takes them (#663)."""

import importlib.util
import os

import pytest

from model import geometry as g
from model import trajectories

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location(
    "traces", os.path.join(HERE, "traces.py")
)  # by path: model/ must never shadow eyes/
traces = importlib.util.module_from_spec(spec)
spec.loader.exec_module(traces)


def horn(writes, name):
    """[(ms, deg)] the writes to one of the next Mech's horns."""
    return [(t, d) for t, s, d in writes if s == name]


def test_the_next_mech_points_its_linked_eyes_through_the_gimbals_command_map():
    """#663, #896: the wink's glance, the eye program's 8 deg to the Mech's left, is 8 deg on the one yaw servo (the
    program's range is the gimbal's, its calibration the model's nominals), the pitch servo level; the winking eye's lids shut, meeting
    below its middle (lid servo -21, model/test_gimbal.py) as the other squints, and both come back to rest (0)."""
    writes, times = traces.next_commands("wink")
    yaw, pitch = (horn(writes, f"next {s} horn") for s in ("yaw", "pitch"))
    assert any(d == pytest.approx(8, abs=0.01) for _, d in yaw)  # where the saccade lands
    assert -1 < min(d for _, d in yaw) and max(d for _, d in yaw) < 9.5  # a real saccade overshoots a little
    assert all(abs(d) < 0.01 for _, d in pitch)
    left, right = (horn(writes, f"next {s} lid horn") for s in "LR")
    assert min(d for _, d in left) == pytest.approx(-21)
    assert -21 < min(d for _, d in right) < 0
    assert left[0][1] == right[0][1] == left[-1][1] == right[-1][1] == 0
    assert times[-1] > max(t for t, _, _ in writes)


def test_the_next_mech_rests_with_a_blink_its_lids_following_its_level_gaze():
    """#663, #51 Gestures: Rest on the next Mech blinks within its span (the eye program's 3-6 s gap), both lids shut
    and back to rest; the gaze stays level (today's program has no pitch), so the lids follow it at rest."""
    writes, _ = traces.next_commands("rest")
    for s in "LR":
        lid = horn(writes, f"next {s} lid horn")
        shut = [t for t, d in lid if d == pytest.approx(-21)]
        assert shut and 3000 <= shut[0] <= 6000 + 200 and lid[-1][1] == 0
    assert set(traces.NEXT_MOTIONS) == {*traces.GESTURES, "rest"}


def held(writes, ms):
    """The last of [(ms, deg)] at or before each ms of `ms`."""
    out, i, last = [], 0, writes[0][1]
    for t in ms:
        while i < len(writes) and writes[i][0] <= t:
            last, i = writes[i][1], i + 1
        out.append(last)
    return out


def test_the_next_mechs_head_joins_a_wide_gaze_shift_within_its_gaze_error_the_neck_core_late():
    """#688, #51 Gestures: eureka's 22 deg dart (the eye program's degrees are the gimbal's yaw, #896) on the next Mech:
    its pan horn turns the head the eyes' way to 0.6 of it (13.2 deg), the neck Core's writes 40 ms after the eyes
    Core's (traces.DELAY_MS); once the gaze, yaw plus the head's pan, reaches the dart, it stays within #51's 2 deg gaze
    error while the head arrives and the eyes counter-rotate, and the head comes back."""
    from model import neck

    writes, times = traces.next_commands("eureka")
    assert traces.DELAY_MS == {"core1": 0, "core2": 40}
    pan = [(t, neck.LINKAGES["pan"](d)[0]) for t, d in horn(writes, "pan horn")]
    yaw = horn(writes, "next yaw horn")
    ms = range(0, times[-1])
    gaze = [y + p for y, p in zip(held(yaw, ms), held(pan, ms), strict=True)]
    head = held(pan, ms)
    side = 1 if max(gaze) > -min(gaze) else -1
    assert max(side * h for h in head) == pytest.approx(0.6 * 22, abs=0.05)
    there = next(t for t in ms if side * gaze[t] >= 22 - 2)
    arrived = next(t for t in ms if side * head[t] >= 0.6 * 22 - 0.05)
    assert there < arrived and all(abs(side * gaze[t] - 22) <= 2 for t in range(there, arrived))
    assert head[-1] == pytest.approx(0, abs=0.01)


@pytest.mark.parametrize(
    "doc, motion", [(d, m) for d in sorted(g.NEXT) for m in trajectories.motions(d)], ids=lambda x: x
)  # a test a motion: each holds CI's 15 s (#808)
def test_every_motion_of_the_next_mech_has_its_commands(doc, motion):
    """Each motion a next Mech document plays (trajectories.motions) gives writes before ms 0 and its frame times: its
    gestures and Rest through the eye gimbal, the next hero (#642) as the hero's own writes."""
    writes, times = trajectories.commands(doc, motion)
    assert any(t < 0 for t, _, _ in writes) and len(times) > 1
