"""Seam: model/engine/masses.py, mass / centre of mass / inertia per part from the meshes and the spool densities, and the
gravity torque per horn from engine poses."""

import json
import os

import pytest
import trimesh

from model.engine import masses, meshes, stages

HERE = os.path.dirname(os.path.dirname(__file__))
HAVE_REFERENCES = stages.HAVE_REFERENCES


def test_cube_mass_centre_and_inertia_follow_density_and_placement():
    cube = trimesh.creation.box((10.0, 10.0, 10.0))  # 1 cm3
    m = masses.mass(cube, (1.24, "PLA Pure"))
    assert m["g"] == pytest.approx(1.24) and m["source"] == "PLA Pure"
    assert m["com"] == pytest.approx((0, 0, 0), abs=1e-9)
    assert m["inertia_g_mm2"][0][0] == pytest.approx(
        1.24 * (100 + 100) / 12, abs=1e-3
    )  # solid cube: m (b^2 + c^2) / 12
    assert masses.com_at(m, stages.translate((5, 0, 0))) == pytest.approx((5, 0, 0))


@pytest.mark.skipif(not HAVE_REFERENCES, reason="local references only")
def test_printed_part_masses_match_the_recorded_fusion_masses():
    recorded = json.load(open(os.path.join(HERE, "reports", "noggin-eyes-report.json")))["mass"]
    stage = stages.STAGES["noggin-eyes"]
    names = ["L eyeball:1", "L servo bracket:1", "L lid bar:1", "L lid servo:1"]
    table = masses.table(stage, meshes.load(stage, names))
    for name in names:
        assert table[name]["g"] == pytest.approx(recorded[name], rel=0.02), name
    assert table["L lid servo:1"]["source"] == "documented"


@pytest.mark.skipif(not HAVE_REFERENCES, reason="local references only")
def test_gravity_torque_of_the_tilt_horn_is_tiny_at_neutral_and_grows_with_the_arm_lean():
    stage = stages.STAGES["noggin-pan-tilt"]
    table = masses.table(stage, meshes.load(stage))
    torque = masses.gravity_torque(
        stage, "tilt horn", table, [-70, -60, -50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50, 60]
    )
    assert set(torque) == set(range(-70, 70, 10)) and all(t >= 0 for t in torque.values())
    assert max(torque.values()) < 0.2  # the arm alone, no eyes on it: well under the servo's derated 0.2 kgf.cm
