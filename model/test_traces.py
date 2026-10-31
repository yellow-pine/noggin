"""Seam: model/traces.py's gesture traces (joint degrees per 100 ms frame, recorded from the eye program)."""
import importlib.util, os, pytest

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("traces", os.path.join(HERE, "traces.py"))   # by path: model/ must never shadow eyes/
traces = importlib.util.module_from_spec(spec); spec.loader.exec_module(traces)


@pytest.mark.parametrize("gesture", sorted(traces.GESTURES))
def test_every_gesture_records_frames_inside_the_calibrated_extremes(gesture):
    frames = traces.record(gesture)
    ext = traces.sim.calibrated_extremes(traces.CAL)
    assert 10 <= len(frames) <= 200, len(frames)                       # 1-20 s at 10 fps
    for f in frames:
        for s in ("l_lid", "r_lid", "l_eye", "r_eye"):
            assert ext[s][0] - 0.5 <= f[s] <= ext[s][1] + 0.5, (gesture, f)


def test_a_wink_closes_one_lid_only():
    frames = traces.record("wink")                                      # wink 1 = the mech's left lid
    assert min(f["l_lid"] for f in frames) < -45 and min(f["r_lid"] for f in frames) > -30   # closed is about -45, rest -22..-28
