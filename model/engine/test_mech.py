"""Seam: model/engine/mech.py, the Mech-wide checks the engine folds into the report: peak horn acceleration from the
clocked gestures through the servo plant, reflected inertia about a horn axis, and dynamic torque per horn."""

import json
import os

import numpy as np
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
    by_deg = {0: {"gravity_kgf_cm": 0.1, "inertia_g_mm2": 1e5}, 10: {"gravity_kgf_cm": 0.05, "inertia_g_mm2": 1e5}}
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
        assert still[d]["kgf_cm"] == pytest.approx(gravity[d]) == torque[d]["gravity_kgf_cm"]  # no accel: static


def test_clutch_flags_the_poses_whose_holding_load_eats_the_1_5x_margin_on_0_9():
    by_deg = {-20: {"gravity_kgf_cm": 0.1}, 0: {"gravity_kgf_cm": 0.59}, 30: {"gravity_kgf_cm": 0.7}}
    assert mech.clutch(by_deg) == {"hold_kgf_cm": 0.7, "at_deg": 30, "limit_kgf_cm": 0.6, "flagged": [30]}


def test_footprint_margin_is_the_distance_to_the_nearest_edge_of_the_plan_hull():
    plate = [(x, y, z) for x in (0, 10) for y in (0, 10) for z in (0, 3)] + [(5, 5, 1)]
    outline = mech.footprint(plate)
    assert mech.margin(outline, (2.0, 5.0)) == pytest.approx(2.0)
    assert mech.margin(outline, (12.0, 5.0)) == pytest.approx(-2.0)


@pytest.mark.skipif(not HAVE_REFERENCES, reason="local references only")
def test_mech_poses_turn_the_tilted_head_about_the_pan_axis():
    stage = stages.STAGES["noggin-stage2"]
    poses = {(p, t): m for p, t, m in mech.mech_poses(stage, 10)}
    tilted = stages.pose(stage, "tilt horn (inferred)", 30).parts
    eye = lambda m: m["L eyeball:1"][:3, 3]
    assert np.allclose(poses[(0, 30)]["L eyeball:1"], tilted["L eyeball:1"])  # pan neutral: the tilt pose itself
    for p in (-30, 30, 60):  # the pan turns the tilted head about Z through the origin: radius and height kept
        a, b = eye(poses[(p, 30)]), eye(tilted)
        assert np.hypot(*a[:2]) == pytest.approx(np.hypot(*b[:2])) and a[2] == pytest.approx(b[2])
        assert not np.allclose(a, b)
