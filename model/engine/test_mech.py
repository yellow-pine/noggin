"""Seam: model/engine/mech.py, the Mech-wide checks the engine folds into the report: peak horn acceleration from the
clocked gestures through the servo plant, reflected inertia about a horn axis, and dynamic torque per horn."""

import json
import os

import pytest
import trimesh

from model.engine import linkage, masses, mech, meshes, stages

HERE = os.path.dirname(os.path.dirname(__file__))
HAVE_REFERENCES = os.path.isdir(stages.MODELS["eyes"]) and os.path.isfile(stages.step("horn"))
CAL = json.load(open(os.path.join(os.path.dirname(HERE), "eyes", "calibration.json")))


def test_peak_acceleration_is_the_rated_slew_reached_within_one_pwm_frame():
    peak = mech.peak_accel(CAL)
    rest_to_rated = 500 / 0.02  # 0.12 s per 60 deg = 500 deg/s, reached in one 20 ms frame
    for servo in ("l_lid", "l_eye", "r_lid", "r_eye"):  # every gesture set snaps (blink, saccade) at the rated slew
        assert rest_to_rated <= peak[servo] <= 2 * rest_to_rated, servo
    assert set(peak) == {"l_lid", "l_eye", "r_lid", "r_eye"}  # no Core 2 choreography yet: nothing to trace


def test_acceleration_limit_is_the_torque_headroom_over_the_inertia():
    by_deg = {0: {"kgf_cm": 0.1, "inertia_g_mm2": 1e5}, 10: {"kgf_cm": 0.05, "inertia_g_mm2": 1e5}}
    # 0.1 kgf.cm headroom = 0.00980665 N.m over 1e-4 kg.m2 = 98.07 rad/s2
    assert mech.accel_limit(by_deg, 0.2) == pytest.approx(5618.8, abs=0.5)


def test_reflected_inertia_of_a_cube_swung_on_a_lever_is_m_r2_plus_its_own():
    cube = trimesh.creation.box((10.0, 10.0, 10.0))
    table = {"cube": masses.mass(cube, (1.24, "PLA Pure"))}
    at = lambda deg: {"cube": linkage.rotation((1, 0, 0), deg) @ stages.translate((0, 20.0, 0))}
    inertia = mech.inertia(at(-0.5), at(0.5), table, 1.0)
    assert inertia == pytest.approx(1.24 * 20**2 + 1.24 * 200 / 12, rel=1e-4)  # parallel axes: m r^2 + m (b^2+c^2)/12


@pytest.mark.skipif(not HAVE_REFERENCES, reason="local references only")
def test_dynamic_torque_adds_the_inertia_term_to_gravity_at_every_pose():
    stage = stages.STAGES["noggin-stage2"]
    table = masses.table(stage, meshes.load(stage))
    horn = "tilt horn (inferred)"
    degs = [-60, -30, 0, 30, 60]
    torque = mech.dynamic_torque(stage, table, horn, degs, 2 * 500 / 0.02)
    gravity = masses.gravity_torque(stage, horn, table, degs)
    still = mech.dynamic_torque(stage, table, horn, degs, 0.0)
    for d in degs:
        assert torque[d]["kgf_cm"] > gravity[d] and torque[d]["inertia_g_mm2"] > 1000  # the eyes ride the tilt arm
        assert still[d]["kgf_cm"] == pytest.approx(gravity[d])  # no acceleration: the static figure
