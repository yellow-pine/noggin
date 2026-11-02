"""Seam: model/mujoco_report.py's tip-over margin, on a plan outline drawn by hand, and its servo torques, on a
parallelogram four-bar written by hand (the report itself: test_report.py)."""

import mujoco
import pytest

from model import mujoco_report

# A parallelogram: the horn and the rocker 100 mm long, level, their pivots 50 mm apart one above the other, a 100 g
# mass on the rocker's tip; the coupler stays upright, so the horn carries the rocker's torque one to one.
FOUR_BAR = """
<mujoco>
  <worldbody>
    <body name="horn">
      <joint name="horn" type="hinge" axis="0 1 0" armature="0.5"/>
      <geom type="sphere" pos="0.1 0 0" size="0.001" mass="1e-6"/>
      <body name="coupler" pos="0.1 0 0">
        <joint name="coupler" type="hinge" axis="0 1 0"/>
        <geom type="sphere" size="0.001" mass="1e-6"/>
        <site name="coupler pin" pos="0 0 0.05"/>
      </body>
    </body>
    <body name="rocker" pos="0 0 0.05">
      <joint name="rocker" type="hinge" axis="0 1 0"/>
      <geom type="sphere" pos="0.1 0 0" size="0.001" mass="0.1"/>
      <site name="rocker pin" pos="0.1 0 0"/>
    </body>
  </worldbody>
  <equality><connect site1="coupler pin" site2="rocker pin"/></equality>
  <actuator><motor joint="horn"/></actuator>
</mujoco>
"""


def test_footprint_margin_is_the_distance_to_the_nearest_edge_of_the_plan_hull():
    plate = [(x, y, z) for x in (0, 10) for y in (0, 10) for z in (0, 3)] + [(5, 5, 1)]
    outline = mujoco_report.footprint(plate)
    assert mujoco_report.margin(outline, (2.0, 5.0)) == pytest.approx(2.0)
    assert mujoco_report.margin(outline, (12.0, 5.0)) == pytest.approx(-2.0)


def test_an_accelerating_centre_of_mass_bears_on_the_footprint_h_a_over_g_behind_it():
    outline = mujoco_report.footprint([(x, y, 0) for x in (0, 10) for y in (0, 10)])
    # 20 mm above the floor, accelerating at g/10 toward +x: it bears 2 mm toward -x
    at = mujoco_report.shifted((3.0, 5.0, 20.0), (9.81 / 10, 0, 0), floor=0.0)
    assert mujoco_report.margin(outline, at) == pytest.approx(1.0)


def test_a_held_servo_carries_the_gravity_torque_its_four_bar_brings_it():
    model = mujoco.MjModel.from_xml_string(FOUR_BAR)
    data = mujoco.MjData(model)
    data.qvel[:] = 3  # held: the torque at the pose, whatever the speed
    assert abs(mujoco_report.torques(model, data, moving=False)[0]) == pytest.approx(
        0.1 * 9.81 * 0.1, rel=1e-4
    )  # the light links weigh 1e-6 kg


def test_a_moving_servo_turns_its_load_without_its_own_rotor():
    model = mujoco.MjModel.from_xml_string(FOUR_BAR)
    model.opt.gravity[:] = 0
    data = mujoco.MjData(model)
    data.qacc[:] = [2, -2, 2]  # the horn and rocker at 2 rad/s2, the coupler upright on the horn
    # the 100 g at 100 mm: 0.001 kg.m2 on the rocker, carried one to one; the horn's armature (0.5 kg.m2) is the servo's
    assert abs(mujoco_report.torques(model, data)[0]) == pytest.approx(0.1 * 0.1**2 * 2, rel=1e-3)
