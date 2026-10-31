"""Stall-time rule: the clutch servos slip (and decalibrate) when held against a mechanical stop, so no gesture
may keep a servo within STOP_MARGIN_DEG of a range end for more than MAX_HOLD_MS, and the poses the program holds
indefinitely (rest, thinking) must sit clear of the margin. Uses the real eyes/calibration.json."""
import json, os, pytest
import replay

CAL = json.load(open(os.path.join(os.path.dirname(__file__), "calibration.json")))
STOP_MARGIN_DEG, MAX_HOLD_MS = 10, 2000


@pytest.mark.parametrize("gesture", ["eureka", "attention", "bored", "wince", "wink"])
@pytest.mark.parametrize("intensity", [1, 2, 3])
def test_no_gesture_holds_a_servo_near_a_stop_for_more_than_2s(gesture, intensity):
    holds = replay.near_stop_holds([f"{gesture} {intensity}"], CAL, STOP_MARGIN_DEG)
    assert max(holds.values()) <= MAX_HOLD_MS, holds


@pytest.mark.parametrize("mode", ["rest", "thinking"])
def test_held_poses_sit_clear_of_the_stops(mode):
    log, total = replay.play([mode], CAL)
    last = {pin: angle for _, pin, angle in log}
    for pin, angle in last.items():
        lo, hi = replay.ranges(CAL)[pin]
        assert lo + STOP_MARGIN_DEG < angle < hi - STOP_MARGIN_DEG, (mode, pin, angle)


def test_near_stop_holds_sums_consecutive_segments():
    # one pin, range 0-100: near the low stop 0-300 ms and 300-900 ms (two writes), then clear
    log = [(0, 1, 5.0), (300, 1, 8.0), (900, 1, 50.0)]
    assert replay.hold_ms(log, 1000, {1: (0, 100)}, 10) == {1: 900}
