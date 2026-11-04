import pytest

import eyes as mod

RANGES = {mod.L_LID: (85, 168.2), mod.YAW: (65, 115), mod.R_LID: (11.8, 95), mod.PITCH: (59.6, 120.4)}  # servo degrees


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


@pytest.mark.parametrize("gesture", mod.Eyes.GESTURES)
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
    assert eyes.range(mod.L_LID) == (85, 168.2) and eyes.range(mod.R_LID) == (11.8, 95)


def test_the_lid_map_runs_closed_rest_open_in_two_straight_pieces(eyes):
    """#213: the lid bars make equal servo steps unequal lid steps, so each lid has a third point at lid_rest."""
    eyes.handle_line("set r_lid_rest 60")  # well off the straight line 11.8..95 (35.1 at 0.28)
    rest = eyes.cal["lid_rest"]
    pos = [eyes._lid_angle(mod.R_LID, i / 100) for i in range(101)]
    assert eyes._lid_angle(mod.R_LID, 0) == 11.8 and eyes._lid_angle(mod.R_LID, 1) == 95
    assert eyes._lid_angle(mod.R_LID, rest) == 60
    assert all(a < b for a, b in zip(pos, pos[1:], strict=False))  # monotonic: never reverses
    assert eyes._lid_angle(mod.R_LID, rest / 2) == pytest.approx((11.8 + 60) / 2)  # straight closed..rest
    assert eyes._lid_angle(mod.R_LID, (rest + 1) / 2) == pytest.approx((60 + 95) / 2)  # straight rest..open
    assert eyes._lid_angle(mod.R_LID, -1) == 11.8 and eyes._lid_angle(mod.R_LID, 2) == 95  # clamped to the ends


def test_set_changes_calibration_live(eyes, pwm_log):
    eyes.handle_line("set yaw_lo 70")
    eyes.handle_line("set yaw_hi 130")  # centre becomes 100
    eyes.handle_line("rest")
    moves = [d for p, d in pwm_log if p == mod.YAW and d]
    assert abs(angle(moves[-1]) - 100) < 0.01


def test_the_gaze_turns_both_eyes_on_the_yaw_and_holds_them_level_on_the_pitch(eyes, pwm_log):
    """Stage 1's gimbal (#896): one yaw servo turns both eyes, one pitch servo tilts both; the gestures look left and
    right only, and at a level gaze the model's command map holds the pitch servo at its centre at any yaw
    (model/gimbal.py servos)."""
    for line in ("rest", "eureka 3", "wink 1", "attention 2"):
        eyes.handle_line(line)
    yaw = [angle(d) for p, d in pwm_log if p == mod.YAW and d]
    pitch = {round(angle(d), 6) for p, d in pwm_log if p == mod.PITCH and d}
    assert max(yaw) - min(yaw) > 40
    assert pitch == {90}  # the middle of 59.6..120.4


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
    assert last_ns(pwm_log, mod.YAW) == 0 and last_ns(pwm_log, mod.L_LID) == 0
    eyes.handle_line("rest")
    assert last_ns(pwm_log, mod.YAW) != 0


def test_pose_holds(eyes, pwm_log):
    eyes.handle_line("pose lids 0.4 eyes 100")
    assert last_ns(pwm_log, mod.YAW) != 0 and last_ns(pwm_log, mod.L_LID) != 0
    moves = [d for p, d in pwm_log if p == mod.YAW and d]
    assert abs(angle(moves[-1]) - 100) < 0.01  # centre 90 + 10


def test_exercise_stays_mid_range_and_ends_in_rest(eyes, pwm_log):
    eyes.handle_line("exercise 1")
    for t in range(0, 70_000, 50):
        eyes.tick(t)
    lo, hi = RANGES[mod.YAW]
    eye = [angle(d) for p, d in pwm_log if p == mod.YAW and d]
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
    eye = [d for p, d in pwm_log if p == mod.YAW and d]
    assert len(eye) >= 2000 * gaze_trace.HZ // 1000 - 2  # at least one eye write per trace sample


def test_saccade_follows_the_real_profile(eyes, pwm_log):
    eyes.handle_line("rest")
    pwm_log.clear()
    eyes.saccade(110)
    eye = [angle(d) for p, d in pwm_log if p == mod.YAW and d]
    assert len(eye) >= 16 and abs(eye[-1] - (90 + 20)) < 0.01  # 16 profile points, lands on target
    assert eye[3] < eye[-1] - 3  # still travelling a third of the way in


def test_wink_closes_one_lid_and_the_other_only_squints(eyes, pwm_log):
    eyes.handle_line("rest")
    pwm_log.clear()
    eyes.handle_line("wink 2")  # mech's right lid
    r = [angle(d) for p, d in pwm_log if p == mod.R_LID and d]
    left = [angle(d) for p, d in pwm_log if p == mod.L_LID and d]
    assert min(r) == pytest.approx(eyes._lid_angle(mod.R_LID, eyes.cal["lid_closed"]), abs=1e-3)  # the pulse's step
    assert max(left) == pytest.approx(eyes._lid_angle(mod.L_LID, 0.8 * eyes.cal["lid_rest"]), abs=1e-3)  # mirrored


def test_core_json_ports_pick_the_gpio_per_servo_name(tmp_path, monkeypatch, pwm_log):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "sleep_ms", lambda ms: None)
    (tmp_path / "core.json").write_text(
        '{"name": "eyes", "ports": {"1": "pitch", "2": "r_lid", "3": "yaw", "4": "l_lid"}}'
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


def test_take_writes_each_move_on_time_by_the_core_clock_however_slow_the_link_polls(eyes, pwm_log, monkeypatch):
    """The servo test's moves (docs/build/tests.md) start with a ramp of 1 degree a frame to +25, then step -25, +25,
    +5, -5, -1, 0 a second apart from 1.5 s; each lands within one slow poll of its time, never later, with 3 ms of
    Link polling after every 20 ms sleep (a drift of 15 % if the waits were only summed), and the Core holds still."""
    wall = [0]
    monkeypatch.setattr(mod, "sleep_ms", lambda ms: wall.__setitem__(0, wall[0] + ms + 3))
    monkeypatch.setattr(mod, "ticks_ms", lambda: wall[0])
    eyes.handle_line("pose eyes 90")
    pwm_log.clear()
    original, at = eyes.set, []
    monkeypatch.setattr(eyes, "set", lambda t: (at.extend([wall[0]] * (mod.YAW in t)), original(t)))
    start = wall[0]
    eyes.handle_line("take")
    moves = [round(angle(d) - 90) for p, d in pwm_log if p == mod.YAW]
    assert moves == [*range(26), -25, 25, 5, -5, -1, 0]
    late = [
        t - start - want for t, want in zip(at, [*range(0, 520, 20), 1500, 2500, 3500, 4500, 5500, 6500], strict=True)
    ]
    assert 0 <= min(late) and max(late) <= 3, late
    assert eyes.mode == "pose"


def gaze_log(e, move):
    """[(ms, head, eye)] at each write while move() plays: the program's head and the L eye in it, deg from centre."""
    log, put = [], e.set

    def logged(targets):
        put(targets)
        log.append((mod.clock, e.head, e.pos[mod.YAW] - e._eye_angle(mod.YAW, mod.EYE_CENTER)))

    e.set = logged
    move()
    e.set = put
    return log


def test_the_nominal_calibration_leaves_the_neck_alone(eyes):
    """#688: head_share 0 until a Mech is calibrated: the eyes carry every gaze shift and the pan is never written, so
    the neck Core stays as it was."""
    assert mod.DEFAULT_CAL["head_share"] == 0
    for line in ("rest", "eureka 3", "thinking", "attention 2", "rest"):
        eyes.handle_line(line)
    assert mod.PAN not in eyes.pos


def test_the_neck_joins_a_gaze_shift_past_15_deg_and_the_eyes_counter_rotate_as_it_arrives(eyes):
    """#688, #51 Gestures: with the head carrying 0.6 of the gaze, a 22 deg dart: the eyes lead the head by 20-50 ms
    ([RU14]), the head turns to 0.6 x 22 = 13.2, and once the gaze is there it holds while the head arrives, the eyes
    counter-rotating back to 8.8 in the head; the gaze at most 0.6 of the eyes' full speed ([PE13]), the head at
    most 50 deg/s ([AND])."""
    eyes.handle_line("set head_share 0.6")
    eyes.handle_line("rest")
    log = gaze_log(eyes, lambda: eyes.saccade(112))
    eye_at = next(t for t, _, e in log if e)
    head_at = next(t for t, h, _ in log if h)
    assert 20 <= head_at - eye_at <= 50
    assert log[-1][1:] == pytest.approx((13.2, 8.8))
    there = next(i for i, (_, h, e) in enumerate(log) if h + e == pytest.approx(22))
    assert log[there][1] < 13.2 - 1  # the head still on its way
    assert all(h + e == pytest.approx(22) for _, h, e in log[there:])
    assert max(e for _, _, e in log) > 8.8 + 1  # the eyes counter-rotated back
    speed = [(abs(h1 + e1 - h0 - e0), abs(h1 - h0)) for (_, h0, e0), (_, h1, e1) in zip(log, log[1:], strict=False)]
    assert max(g for g, _ in speed) * 1000 / mod.FRAME <= 257  # 428 deg/s x (1 - 2/3 x 0.6)
    assert max(h for _, h in speed) * 1000 / mod.FRAME <= 50  # the head's peak ([AND])


def test_a_small_shift_leaves_the_head_where_it_is(eyes):
    eyes.handle_line("set head_share 0.6")
    eyes.handle_line("rest")
    log = gaze_log(eyes, lambda: eyes.saccade(98))
    assert {h for _, h, _ in log} == {0} and log[-1][2] == pytest.approx(8)


def test_rest_brings_the_head_back(eyes):
    eyes.handle_line("set head_share 0.6")
    eyes.handle_line("thinking")  # its 18 deg averted look turns the head
    assert eyes.head
    eyes.handle_line("rest")
    assert eyes.head == 0 and eyes.pos[mod.YAW] == eyes._eye_angle(mod.YAW, mod.EYE_CENTER)


def test_the_neck_core_turns_the_head_on_the_eyes_cores_timeline(tmp_path, monkeypatch, pwm_log):
    """#688: both Cores play the same line and each writes only its own servos, so the neck Core's pan follows the
    head the eyes Core counter-rotates against, write for write (the Wi-Fi delay between them aside)."""
    monkeypatch.setattr(mod, "sleep_ms", lambda ms: None)
    runs = []
    for core in ("eyes", "neck"):
        (tmp_path / core).mkdir()
        monkeypatch.chdir(tmp_path / core)  # the eyes Core: the default map; the neck Core: its core.json
        if core == "neck":
            ports = '{"1": "tilt", "2": "mouth", "3": "pan"}'
            (tmp_path / core / "core.json").write_text('{"name": "neck", "ports": ' + ports + "}")
        e = mod.Eyes()
        e.handle_line("set head_share 0.6")
        e.handle_line("rest")
        pwm_log.clear()
        start = mod.clock
        runs.append([(t - start, h) for t, h, _ in gaze_log(e, lambda e=e: e.handle_line("eureka 2"))])
    assert runs[0] == runs[1] and max(abs(h) for _, h in runs[1]) == pytest.approx(13.2)
    assert {pin for pin, _ in pwm_log} == {mod.PORT_GPIO["3"]}  # the neck Core's last run: the pan alone


def test_both_cores_pick_a_gestures_side_from_the_lines_alone(monkeypatch):
    """#688: the Cores tick on their own clocks, so one may blink or drift once more than the other; the side a gesture
    looks to still matches, or the neck would turn the head away from the eyes."""
    monkeypatch.setattr(mod, "sleep_ms", lambda ms: None)
    a, b = mod.Eyes(), mod.Eyes()
    for e, ticks in ((a, 60_000), (b, 64_000)):
        e.handle_line("rest")
        for t in range(0, ticks, 100):
            e.tick(t)
    assert [a._side() for _ in range(20)] == [b._side() for _ in range(20)]
