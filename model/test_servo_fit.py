"""Seams: mjcf.drive (the 9 g servo as a dcmotor with its PWM delay, #625), through the fit's one-servo rig
(servo_fit.play), and servo_fit.fit, which must find the values a take was played with."""

import numpy as np
import pytest

from model import electrical, mjcf, servo_fit

RATED_DEG_S = electrical.servo.rate(electrical.SERVO_MIN_V)  # 428.6 deg/s, the 4.8 V sheet's no-load speed


def take(load_g, arm_mm, steps, seconds=0.8, fps=240):
    """A take as the filmed one will be: the camera's frames and the Core's writes, the horn played here."""
    t = np.arange(round(seconds * fps)) / fps
    return {"load_g": load_g, "arm_mm": arm_mm, "t_s": t.tolist(), "command": [(0, 0), *steps]}


def test_a_step_waits_the_pwm_frame_then_runs_no_faster_than_no_load_and_holds_the_command():
    """30 degrees on an unloaded horn: still for the 20 ms delay, never past the no-load speed, at the command
    150 ms after it, and its torque never past the stall torque (the drive voltage clamped at the rail's 4.8 V)."""
    step = take(0, 0, [(0.05, 30)], seconds=0.35, fps=2000)
    t, horn, torque = servo_fit.play(mjcf.SERVO, step, torque=True)
    assert np.abs(horn[t < 0.07]).max() < 0.01 and horn[t < 0.08].max() > 0.1
    assert np.diff(horn).max() / np.diff(t).max() <= RATED_DEG_S * 1.001
    assert np.abs(horn[t >= 0.2] - 30).max() < 0.5
    assert np.abs(torque).max() <= mjcf.SERVO["stall_nm"] * 1.001


def test_a_heavier_load_is_slower_to_its_command():
    """The load's inertia slows the motor's run-up: 50 g at 50 mm (about the gear train's own) reaches 90 % of 60 degrees
    5 ms or more after the bare horn."""
    reach = []
    for load in (0, 50):
        t, horn = servo_fit.play(mjcf.SERVO, take(load, 50, [(0.05, 60)], fps=2000))
        reach.append(t[np.argmax(horn >= 54)])
    assert reach[1] > reach[0] + 0.005, reach


@pytest.mark.model
def test_the_fit_finds_the_values_a_take_was_played_with():
    """Takes played with values off the 4.8 V sheet (a weaker, slower servo with a heavier gear train and a longer
    delay), on the bare horn and with 200 g at 50 mm, steps both ways: fit, started from the sheet's values (mjcf.SERVO), finds them
    within 10 percent, kp left as it was."""
    true = {**mjcf.SERVO, "stall_nm": 0.08, "no_load_rad_s": 6.0, "armature": 1.5e-4, "delay_s": 0.028}
    takes = [take(g, 50, [(0.05, 60), (0.4, -30), (0.7, -25)], seconds=1.0) for g in (0, 200)]
    for t in takes:
        t["horn_deg"] = servo_fit.play(true, t)[1].tolist()
    assert servo_fit.fit(takes) == pytest.approx(true, rel=0.1)
