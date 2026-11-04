"""The neck Core's commands and PWM writes (#929), through the same program as the eyes Core."""

import pytest

from noggin.core import GESTURES


def angle(ns):
    return (ns * 1023 / 20_000_000 - 25) * 180 / 102


@pytest.fixture
def neck(eyes, tmp_path, monkeypatch, pwm_log):
    import eyes as mod

    monkeypatch.chdir(tmp_path)
    (tmp_path / "core.json").write_text('{"name":"neck","ports":{"1":"tilt","2":"mouth","3":"pan"}}')
    pwm_log.clear()
    return mod.Eyes()


def test_pose_reaches_the_neck_cores_tilt_and_jaw(neck, pwm_log):
    neck.handle_line("pose tilt 100 jaw 0.5")
    last = {pin: angle(ns) for pin, ns in pwm_log}
    assert last == pytest.approx({3: 100, 2: 71.85}, abs=1e-3)


def test_set_changes_the_neck_ranges_and_pose_stays_inside_them(neck, pwm_log):
    for line in ("set tilt_lo 80", "set tilt_hi 100", "set mouth_lo 100", "set mouth_hi 60"):
        neck.handle_line(line)
    neck.handle_line("pose tilt 180 jaw 2")
    assert {pin: angle(ns) for pin, ns in pwm_log} == pytest.approx({3: 100, 2: 60}, abs=1e-3)


def test_eureka_moves_the_tilt_and_jaw_then_returns_them_to_rest(neck, pwm_log):
    neck.handle_line("rest")
    pwm_log.clear()
    neck.handle_line("eureka 2")
    for pin, rest in ((3, 90), (2, 90)):
        positions = [angle(ns) for p, ns in pwm_log if p == pin]
        assert positions and max(positions) - min(positions) > 5
        assert positions[-1] == pytest.approx(rest, abs=1e-3)


@pytest.mark.parametrize("gesture", [f"{g} {i}" for g in GESTURES for i in (1, 2, 3)])
def test_neck_gestures_keep_calibrated_ranges_slew_frames_and_the_start_budget(neck, monkeypatch, gesture):
    import eyes as mod

    events, put = [], mod.PWM.duty_ns

    def write(pwm, ns):
        events.append((mod.clock, pwm.pin, angle(ns)))
        put(pwm, ns)

    monkeypatch.setattr(mod.PWM, "duty_ns", write)
    neck.handle_line("set head_share 0.6")
    neck.handle_line("rest")
    last = {pin: (t, a) for t, pin, a in events}
    events.clear()
    neck.handle_line(gesture)
    ranges = {3: (42.1, 139.7), 2: (53.7, 90), 1: (60, 120)}
    ends = {}
    for t, pin, a in events:
        assert ranges[pin][0] - 0.001 <= a <= ranges[pin][1] + 0.001
        before, old = last[pin]
        assert t - before >= 20
        assert abs(a - old) <= 428 * (t - before) / 1000 + 0.001
        ends[pin] = t + abs(a - old) * 1000 / 428
        assert sum(end > t + 0.01 for end in ends.values()) <= 2
        last[pin] = t, a
