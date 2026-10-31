import pytest
import eyes as mod

RANGES = {mod.L_LID: (51, 144), mod.L_EYE: (58, 118), mod.R_LID: (51, 129), mod.R_EYE: (58, 118)}

def angle(duty):            # inverse of the stock bbl.servos formula; one duty step is 1.76 deg
    return (duty - 25) * 180 / 102

def assert_in_range_and_held(pwm_log):
    assert pwm_log, "nothing moved"
    for pin, duty in pwm_log:
        if duty:
            lo, hi = RANGES[pin]
            assert lo - 1.8 <= angle(duty) <= hi + 1.8, f"pin {pin} at {angle(duty):.1f}, range {lo}-{hi}"
    last = {}
    for pin, duty in pwm_log:
        last[pin] = duty
    assert all(d != 0 for d in last.values()), "servos released: gravity would move the Mech"

@pytest.mark.parametrize("gesture", ["eureka", "attention", "bored", "wince"])
@pytest.mark.parametrize("intensity", [1, 2, 3])
def test_every_gesture_stays_in_range_and_ends_held(eyes, pwm_log, gesture, intensity):
    eyes.handle_line(f"{gesture} {intensity}")
    assert_in_range_and_held(pwm_log)

def test_bigger_eureka_moves_more(eyes, pwm_log):
    eyes.handle_line("eureka 1"); small = len(pwm_log); pwm_log.clear()
    eyes.handle_line("eureka 3"); big = len(pwm_log)
    assert big > small

def test_unknown_line_does_nothing(eyes, pwm_log):
    eyes.handle_line("dance 2"); eyes.handle_line(""); eyes.handle_line("eureka")
    assert pwm_log == []

def test_thinking_drifts_and_rest_stops_it(eyes, pwm_log):
    eyes.handle_line("thinking")
    for t in range(0, 30_000, 100):
        eyes.tick(t)
    assert_in_range_and_held(pwm_log)
    drifts = len(pwm_log); pwm_log.clear()
    eyes.handle_line("rest")
    for t in range(30_000, 60_000, 100):
        eyes.tick(t)
    assert len(pwm_log) < drifts / 4   # rest pose once, then nothing

def test_thinking_blinks_occasionally(eyes, pwm_log):
    eyes.handle_line("thinking")
    for t in range(0, 120_000, 100):
        eyes.tick(t)
    lid_writes = [d for pin, d in pwm_log if pin in (mod.L_LID, mod.R_LID) and d]
    closed = mod._duty(eyes._lid_angle(mod.L_LID, eyes.cal["lid_closed"]))
    assert any(abs(d - closed) <= 2 for d in lid_writes), "no blink during 2 min of thinking"


def last_duty(pwm_log, pin):
    return [d for p, d in pwm_log if p == pin][-1]

def test_set_changes_calibration_live(eyes, pwm_log):
    eyes.handle_line("set l_eye_lo 70"); eyes.handle_line("set l_eye_hi 130")   # centre becomes 100
    eyes.handle_line("rest")
    moves = [d for p, d in pwm_log if p == mod.L_EYE and d]
    assert abs(angle(moves[-1]) - 100) < 1.8

def test_set_rejects_unknown_key(eyes, pwm_log):
    before = dict(eyes.cal)
    eyes.handle_line("set nonsense 3")
    assert eyes.cal == before

def test_blink_glides_to_lid_closed_not_the_stop(eyes, pwm_log):
    eyes.handle_line("set lid_closed 0.2")
    eyes.handle_line("rest"); pwm_log.clear()
    eyes.blink()
    lid = [angle(d) for p, d in pwm_log if p == mod.R_LID and d]      # R lid: open = high end
    lo, hi = RANGES[mod.R_LID]
    assert min(lid) >= lo + (hi - lo) * 0.2 - 1.8                  # never past lid_closed
    assert len(lid) >= 4                                            # glided, not snapped

def test_release_unpowers_and_next_command_repowers(eyes, pwm_log):
    eyes.handle_line("rest"); eyes.handle_line("release")
    assert last_duty(pwm_log, mod.L_EYE) == 0 and last_duty(pwm_log, mod.L_LID) == 0
    eyes.handle_line("rest")
    assert last_duty(pwm_log, mod.L_EYE) != 0

def test_pose_holds(eyes, pwm_log):
    eyes.handle_line("pose lids 0.4 eyes 100")
    assert last_duty(pwm_log, mod.L_EYE) != 0 and last_duty(pwm_log, mod.L_LID) != 0
    moves = [d for p, d in pwm_log if p == mod.R_EYE and d]
    assert abs(angle(moves[-1]) - 98) < 1.8                           # centre 88 + 10

def test_exercise_stays_mid_range_and_ends_in_rest(eyes, pwm_log):
    eyes.handle_line("exercise 1")
    for t in range(0, 70_000, 50):
        eyes.tick(t)
    lo, hi = RANGES[mod.L_EYE]
    eye = [angle(d) for p, d in pwm_log if p == mod.L_EYE and d]
    assert min(eye) >= lo + (hi - lo) * 0.15 - 1.8 and max(eye) <= lo + (hi - lo) * 0.85 + 1.8
    assert eyes.mode == "rest"
    assert_in_range_and_held(pwm_log)


def test_think_trace_replays_the_recording_when_enabled(eyes, pwm_log):
    import gaze_trace
    eyes.handle_line("set think_trace 1"); eyes.handle_line("thinking"); pwm_log.clear()
    for t in range(0, 2000, 10):
        eyes.tick(t)
    eye = [d for p, d in pwm_log if p == mod.L_EYE and d]
    assert len(eye) >= 2000 * gaze_trace.HZ // 1000 - 2    # one eye write per trace sample
