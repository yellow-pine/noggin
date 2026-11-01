"""eyes/replay.py: the calibration from before #213 (servo-frame lid ends, a flip per lid) still loads, converted to the
shared lid frame, and the program writes the same servo angles under it."""

import pytest
import replay

OLD = {  # eyes/calibration.json as the Mech ran it before #213 (l_lid_hi tuned live 144 -> 136)
    "l_lid_lo": 51,
    "l_lid_hi": 136,
    "r_lid_lo": 44,
    "r_lid_hi": 129,
    "l_eye_lo": 58,
    "l_eye_hi": 118,
    "l_lid_flip": 1,
    "r_lid_flip": 0,
    "lid_rest": 0.28,
}


def test_the_old_shape_converts_to_the_shared_frame():
    new = replay.shared_frame(OLD)
    assert "l_lid_flip" not in new and "r_lid_flip" not in new
    for side in "lr":  # mirror-equal: identical numbers, the rest point on the old straight line at lid_rest
        assert (new[f"{side}_lid_lo"], new[f"{side}_lid_hi"]) == (44, 129)
        assert new[f"{side}_lid_rest"] == pytest.approx(44 + 85 * 0.28)
    assert (new["l_eye_lo"], new["l_eye_hi"], new["lid_rest"]) == (58, 118, 0.28)
    assert replay.shared_frame(new) == new  # the new shape passes through
    assert replay.shared_frame({"lid_rest": 0.3}) == {"lid_rest": 0.3}  # so does a partial file


def _old_lid_angle(self, pin, f):  # eyes/eyes.py before #213: a straight line between the servo-frame ends
    name = replay._eyes().NAME[pin]
    lo, hi = self.cal[name + "_lo"], self.cal[name + "_hi"]
    f = min(1.0, max(0.0, f))
    return lo + (hi - lo) * (1 - f if self.cal[name + "_flip"] else f)


def _old_range(self, pin):
    name = replay._eyes().NAME[pin]
    return self.cal[name + "_lo"], self.cal[name + "_hi"]


@pytest.mark.parametrize("line", [f"{g} {i}" for g in replay._eyes().Eyes.GESTURES for i in "123"])
def test_every_gesture_writes_the_same_servo_angles_after_the_conversion(monkeypatch, line):
    eyes = replay._eyes().Eyes
    with monkeypatch.context() as m:
        m.setattr(eyes, "_lid_angle", _old_lid_angle)
        m.setattr(eyes, "range", _old_range)
        before = replay.play(["rest", line, "thinking"], OLD)
    after = replay.play(["rest", line, "thinking"], replay.shared_frame(OLD))
    assert after[1] == before[1]
    assert [(t, p) for t, p, _ in after[0]] == [(t, p) for t, p, _ in before[0]]
    assert [a for *_, a in after[0]] == pytest.approx([a for *_, a in before[0]])
