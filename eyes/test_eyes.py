import pytest
import eyes as mod

def angle(duty):            # inverse of the stock bbl.servos formula; one duty step is 1.76 deg
    return (duty - 25) * 180 / 102

def assert_in_range_and_released(pwm_log):
    assert pwm_log, "nothing moved"
    for pin, duty in pwm_log:
        if duty:
            lo, hi = mod.RANGE[pin]
            assert lo - 1.8 <= angle(duty) <= hi + 1.8, f"pin {pin} at {angle(duty):.1f}, range {lo}-{hi}"
    last = {}
    for pin, duty in pwm_log:
        last[pin] = duty
    assert all(d == 0 for d in last.values()), "servos left powered"

@pytest.mark.parametrize("gesture", ["eureka", "attention", "bored", "wince"])
@pytest.mark.parametrize("intensity", [1, 2, 3])
def test_every_gesture_stays_in_range_and_ends_released(eyes, pwm_log, gesture, intensity):
    eyes.handle_line(f"{gesture} {intensity}")
    assert_in_range_and_released(pwm_log)

def test_bigger_eureka_moves_more(eyes, pwm_log):
    eyes.handle_line("eureka 1"); small = len(pwm_log); pwm_log.clear()
    eyes.handle_line("eureka 3"); big = len(pwm_log)
    assert big > small

def test_unknown_line_does_nothing(eyes, pwm_log):
    eyes.handle_line("dance 2"); eyes.handle_line(""); eyes.handle_line("eureka")
    assert pwm_log == []

def test_thinking_drifts_then_releases_and_rest_stops_it(eyes, pwm_log):
    eyes.handle_line("thinking")
    for t in range(0, 30_000, 100):
        eyes.tick(t)
    assert_in_range_and_released(pwm_log)
    drifts = len(pwm_log); pwm_log.clear()
    eyes.handle_line("rest")
    for t in range(30_000, 60_000, 100):
        eyes.tick(t)
    assert len(pwm_log) < drifts / 4   # rest pose once, then nothing
