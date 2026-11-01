import pytest

import eyes as mod

RANGES = {mod.L_LID: (51, 136), mod.L_EYE: (58, 118), mod.R_LID: (44, 129), mod.R_EYE: (58, 118)}  # servo degrees


def angle(ns):  # inverse of the stock bbl.servos mapping as a pulse width (10-bit duty / 1023 of 20 ms)
    return (ns * 1023 / 20_000_000 - 25) * 180 / 102


def test_pulse_width_keeps_the_stock_mapping_at_sub_degree_steps(eyes, pwm_log):
    eyes.set({mod.L_LID: 90})
    eyes.set({mod.L_LID: 90.5})
    assert [ns for _, ns in pwm_log] == [1_485_826, 1_491_365]  # 0.489 ms at 0, 2.483 at 180; duty() stepped 1.76 deg


def assert_in_range_and_held(pwm_log):
    assert pwm_log, "nothing moved"
    for pin, ns in pwm_log:
        if ns:
            lo, hi = RANGES[pin]
            assert lo - 0.01 <= angle(ns) <= hi + 0.01, f"pin {pin} at {angle(ns):.1f}, range {lo}-{hi}"
    last = {}
    for pin, ns in pwm_log:
        last[pin] = ns
    assert all(d != 0 for d in last.values()), "servos released: gravity would move the Mech"


@pytest.mark.parametrize("gesture", ["eureka", "attention", "bored", "wince", "wink"])
@pytest.mark.parametrize("intensity", [1, 2, 3])
def test_every_gesture_stays_in_range_and_ends_held(eyes, pwm_log, gesture, intensity):
    eyes.handle_line(f"{gesture} {intensity}")
    assert_in_range_and_held(pwm_log)


def test_bigger_eureka_moves_more(eyes, pwm_log):
    eyes.handle_line("eureka 1")
    small = len(pwm_log)
    pwm_log.clear()
    eyes.handle_line("eureka 3")
    big = len(pwm_log)
    assert big > small


def test_unknown_line_does_nothing(eyes, pwm_log):
    eyes.handle_line("dance 2")
    eyes.handle_line("")
    eyes.handle_line("eureka")
    assert pwm_log == []


def test_thinking_drifts_and_rest_stops_it(eyes, pwm_log):
    eyes.handle_line("thinking")
    for t in range(0, 30_000, 100):
        eyes.tick(t)
    assert_in_range_and_held(pwm_log)
    drifts = len(pwm_log)
    pwm_log.clear()
    eyes.handle_line("rest")
    for t in range(30_000, 60_000, 100):
        eyes.tick(t)
    assert len(pwm_log) < drifts / 4  # rest pose once, then nothing


def test_thinking_blinks_occasionally(eyes, pwm_log):
    eyes.handle_line("thinking")
    for t in range(0, 120_000, 100):
        eyes.tick(t)
    lid_writes = [d for pin, d in pwm_log if pin in (mod.L_LID, mod.R_LID) and d]
    closed = eyes._lid_angle(mod.L_LID, eyes.cal["lid_closed"])
    assert any(abs(angle(d) - closed) < 0.01 for d in lid_writes), "no blink during 2 min of thinking"


def last_ns(pwm_log, pin):
    return [d for p, d in pwm_log if p == pin][-1]


def test_both_lids_take_the_same_numbers_and_the_left_servo_mirrors_them(eyes):
    """#213: lid positions are in one shared frame (the right lid servo's degrees, lo closed .. hi open); the left lid
    servo is mounted mirror-image, so the Core writes 180 - a to it."""
    assert all(mod.DEFAULT_CAL["l_lid" + k] == mod.DEFAULT_CAL["r_lid" + k] for k in ("_lo", "_rest", "_hi"))
    for f in (0, 0.03, 0.1, 0.28, 0.5, 0.95, 1):
        assert eyes._lid_angle(mod.L_LID, f) == pytest.approx(180 - eyes._lid_angle(mod.R_LID, f))
    assert eyes.range(mod.L_LID) == (51, 136) and eyes.range(mod.R_LID) == (44, 129)


def test_the_lid_map_runs_closed_rest_open_in_two_straight_pieces(eyes):
    """#213: the lid bars make equal servo steps unequal lid steps, so each lid has a third point at lid_rest."""
    eyes.handle_line("set r_lid_rest 80")  # well off the straight line 44..129 (67.8 at 0.28)
    rest = eyes.cal["lid_rest"]
    pos = [eyes._lid_angle(mod.R_LID, i / 100) for i in range(101)]
    assert eyes._lid_angle(mod.R_LID, 0) == 44 and eyes._lid_angle(mod.R_LID, 1) == 129
    assert eyes._lid_angle(mod.R_LID, rest) == 80
    assert all(a < b for a, b in zip(pos, pos[1:], strict=False))  # monotonic: never reverses
    assert eyes._lid_angle(mod.R_LID, rest / 2) == pytest.approx((44 + 80) / 2)  # straight closed..rest
    assert eyes._lid_angle(mod.R_LID, (rest + 1) / 2) == pytest.approx((80 + 129) / 2)  # straight rest..open
    assert eyes._lid_angle(mod.R_LID, -1) == 44 and eyes._lid_angle(mod.R_LID, 2) == 129  # clamped to the ends


def test_set_changes_calibration_live(eyes, pwm_log):
    eyes.handle_line("set l_eye_lo 70")
    eyes.handle_line("set l_eye_hi 130")  # centre becomes 100
    eyes.handle_line("rest")
    moves = [d for p, d in pwm_log if p == mod.L_EYE and d]
    assert abs(angle(moves[-1]) - 100) < 0.01


def test_set_rejects_unknown_key(eyes, pwm_log):
    before = dict(eyes.cal)
    eyes.handle_line("set nonsense 3")
    assert eyes.cal == before


def test_blink_glides_to_lid_closed_not_the_stop(eyes, pwm_log):
    eyes.handle_line("set lid_closed 0.2")
    eyes.handle_line("rest")
    pwm_log.clear()
    eyes.blink()
    lid = [angle(d) for p, d in pwm_log if p == mod.R_LID and d]  # R lid: open = high end
    lo, hi = RANGES[mod.R_LID]
    assert min(lid) >= lo + (hi - lo) * 0.2 - 0.01  # never past lid_closed
    assert len(lid) >= 4  # glided, not snapped


def test_release_unpowers_and_next_command_repowers(eyes, pwm_log):
    eyes.handle_line("rest")
    eyes.handle_line("release")
    assert last_ns(pwm_log, mod.L_EYE) == 0 and last_ns(pwm_log, mod.L_LID) == 0
    eyes.handle_line("rest")
    assert last_ns(pwm_log, mod.L_EYE) != 0


def test_pose_holds(eyes, pwm_log):
    eyes.handle_line("pose lids 0.4 eyes 100")
    assert last_ns(pwm_log, mod.L_EYE) != 0 and last_ns(pwm_log, mod.L_LID) != 0
    moves = [d for p, d in pwm_log if p == mod.R_EYE and d]
    assert abs(angle(moves[-1]) - 98) < 0.01  # centre 88 + 10


def test_exercise_stays_mid_range_and_ends_in_rest(eyes, pwm_log):
    eyes.handle_line("exercise 1")
    for t in range(0, 70_000, 50):
        eyes.tick(t)
    lo, hi = RANGES[mod.L_EYE]
    eye = [angle(d) for p, d in pwm_log if p == mod.L_EYE and d]
    assert min(eye) >= lo + (hi - lo) * 0.15 - 0.01 and max(eye) <= lo + (hi - lo) * 0.85 + 0.01
    assert eyes.mode == "rest"
    assert_in_range_and_held(pwm_log)


def test_think_trace_replays_the_recording_when_enabled(eyes, pwm_log):
    import gaze_trace

    eyes.handle_line("set think_trace 1")
    eyes.handle_line("thinking")
    pwm_log.clear()
    for t in range(0, 2000, 10):
        eyes.tick(t)
    eye = [d for p, d in pwm_log if p == mod.L_EYE and d]
    assert len(eye) >= 2000 * gaze_trace.HZ // 1000 - 2  # at least one eye write per trace sample


def test_saccade_follows_the_real_profile(eyes, pwm_log):
    eyes.handle_line("rest")
    pwm_log.clear()
    eyes.saccade(110)
    eye = [angle(d) for p, d in pwm_log if p == mod.L_EYE and d]
    assert len(eye) >= 16 and abs(eye[-1] - (88 + 20)) < 0.01  # 16 profile points, lands on target
    assert eye[3] < eye[-1] - 3  # still travelling a third of the way in


def test_wink_closes_one_lid_and_the_other_only_squints(eyes, pwm_log):
    eyes.handle_line("rest")
    pwm_log.clear()
    eyes.handle_line("wink 2")  # mech's right lid
    r = [angle(d) for p, d in pwm_log if p == mod.R_LID and d]
    left = [angle(d) for p, d in pwm_log if p == mod.L_LID and d]
    assert min(r) == pytest.approx(eyes._lid_angle(mod.R_LID, eyes.cal["lid_closed"]))
    assert max(left) == pytest.approx(eyes._lid_angle(mod.L_LID, 0.8 * eyes.cal["lid_rest"]))  # mirrored: shut is up


def test_core_json_ports_pick_the_gpio_per_servo_name(tmp_path, monkeypatch, pwm_log):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "sleep_ms", lambda ms: None)
    (tmp_path / "core.json").write_text(
        '{"name": "eyes", "ports": {"1": "r_eye", "2": "r_lid", "3": "l_eye", "4": "l_lid"}}'
    )
    e = mod.Eyes()
    pwm_log.clear()
    e.handle_line("pose lids 0.5")  # lids on ports 2 and 4 -> GPIO 2 and 0
    assert {pin for pin, _ in pwm_log} == {2, 0}


def test_neck_core_never_drives_the_eye_pins(tmp_path, monkeypatch, pwm_log):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "sleep_ms", lambda ms: None)
    (tmp_path / "core.json").write_text('{"name": "neck", "ports": {"1": "tilt", "2": "mouth", "3": "pan"}}')
    e = mod.Eyes()
    pwm_log.clear()
    e.handle_line("eureka 2")
    e.handle_line("wink 1")  # eye servo names unknown here: skipped, not crashed
    assert pwm_log == []
