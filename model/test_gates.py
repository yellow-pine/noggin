"""Seam: the gates (model/gates.py) on small hand-written MuJoCo models, light enough for just check-light; the Mech's
own runs are CI's (model/test_report.py, model/test_trajectories.py)."""

import mujoco
import numpy as np
import pytest

from model import gates


def four_bar(a, b):
    """A planar four-bar about Z (mm): rocker pivot at the origin, its pin at b, the coupler from the horn pin a to b,
    the horn on a pivot 2 mm left of a, driven; assembled as written."""
    o2 = (a[0] - 2, a[1], 0)
    m = lambda p: " ".join(str(c / 1000) for c in p)  # noqa: E731
    rel = lambda p, q: m(np.subtract(p, q))  # noqa: E731
    xml = f"""<mujoco><worldbody>
      <body name="horn" pos="{m(o2)}"><joint name="horn" axis="0 0 1"/><geom size="0.001" mass="0.001"/>
        <body name="coupler" pos="{rel(a, o2)}"><joint name="coupler" axis="0 0 1"/><geom size="0.001" mass="0.001"/>
          <site name="pin c" pos="{rel(b, a)}"/></body></body>
      <body name="rocker"><joint name="rocker pivot" axis="0 0 1"/><geom size="0.001" mass="0.001"/>
        <site name="pin r" pos="{m(b)}"/></body>
    </worldbody>
    <equality><connect name="rocker pivot" site1="pin c" site2="pin r"/></equality>
    <actuator><position joint="horn"/></actuator></mujoco>"""
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data


def test_a_four_bar_at_right_angles_has_its_shorter_link_as_margin_and_a_90_degree_transmission():
    # coupler 3 mm along +Y onto the rocker's 4 mm along +X: the free pivots move the pin along orthogonal directions,
    # 3 and 4 mm per radian, so the smallest singular value is 3 and the coupler meets the rocker square
    margin, transmission = gates.loops(*four_bar(a=(4, 3, 0), b=(4, 0, 0)))["rocker pivot"]
    assert margin == pytest.approx(3.0) and transmission == pytest.approx(90.0)


def test_a_four_bar_at_its_toggle_has_no_margin():
    # the coupler in line with the rocker (bar and lever in line): the two free pivots move the pin the same way
    margin, transmission = gates.loops(*four_bar(a=(7, 0, 0), b=(4, 0, 0)))["rocker pivot"]
    assert margin == pytest.approx(0.0, abs=1e-9) and transmission == pytest.approx(0.0, abs=1e-6)


def arm_past_a_post(post_mm):
    """A 30 mm arm turning about Z at the origin from +X, and a 2 mm post 25 mm out at 67.5 deg, post_mm from Z."""
    x, y = (post_mm / 1000 * f(np.radians(67.5)) for f in (np.cos, np.sin))
    xml = f"""<mujoco><worldbody>
      <body name="arm"><joint axis="0 0 1"/><geom type="box" size="0.015 0.001 0.001" pos="0.015 0 0"/></body>
      <body name="post" pos="{x} {y} 0"><geom size="0.002"/></body>
    </worldbody></mujoco>"""
    return mujoco.MjModel.from_xml_string(xml)


SWEEP = np.radians(np.linspace(0, 180, 1001))[:, None]  # one row per sim step


def test_a_sweep_past_a_post_overlaps_between_the_frames_a_fixed_sampling_reads():
    """The arm crosses the post between two of the 45 degree frames; each frame reads it clear, the certified sweep
    does not."""
    model = arm_past_a_post(25)
    data = mujoco.MjData(model)
    for q in SWEEP[::250]:
        data.qpos[:] = q
        mujoco.mj_kinematics(model, data)
        assert gates.separation(model, data, ("arm", "post")) > 1
    ((i, mm),) = gates.certify(model, SWEEP, {("arm", "post"): -0.05}).values()
    assert abs(np.degrees(SWEEP[i, 0]) - 67.5) < 10 and mm < -0.05  # the arm is 2 mm thick, the post 4 across


def test_a_sweep_that_clears_the_post_is_certified():
    assert gates.certify(arm_past_a_post(40), SWEEP, {("arm", "post"): -0.05}) == {}


def test_a_sweep_reads_through_the_separation_it_is_given():
    """The post 40 mm out clears the arm, but a reading that has every pose 1 mm in fails it at the sweep's start."""
    found = gates.certify(arm_past_a_post(40), SWEEP, {("arm", "post"): -0.05}, separation=lambda m, d, p: -1.0)
    assert found == {("arm", "post"): (0, -1.0)}


def test_a_turn_too_short_to_close_the_gap_is_read_only_at_its_ends():
    """The arm turns 10 degrees, its tip 5 mm along, short of the post 8 mm off; a piece of it 300 mm up the hinge's
    axis turns no further than the tip, so the two readings certify the turn without splitting it."""
    model = mujoco.MjModel.from_xml_string("""<mujoco><worldbody>
      <body name="arm"><joint axis="0 0 1"/><geom type="box" size="0.015 0.001 0.001" pos="0.015 0 0"/>
        <geom size="0.001" pos="0 0 0.3"/></body>
      <body name="post" pos="0.04 0 0"><geom size="0.002"/></body>
    </worldbody></mujoco>""")
    reads = []

    def separation(model, data, pair):
        reads.append(pair)
        return gates.separation(model, data, pair)

    turn = np.radians(np.linspace(0, 10, 101))[:, None]
    assert gates.certify(model, turn, {("arm", "post"): 0.5}, separation=separation) == {}
    assert len(reads) == 2


def test_the_pairs_a_motion_can_change_are_the_ones_a_hinge_turns_apart():
    model = mujoco.MjModel.from_xml_string("""<mujoco><worldbody>
      <body name="base"><geom size="0.001"/>
        <body name="lid"><joint axis="1 0 0"/><geom size="0.001"/><body name="cover"><geom size="0.001"/></body></body>
        <body name="label"><geom size="0.001" contype="0" conaffinity="0"/></body></body>
      <body name="post"><geom size="0.001"/></body>
    </worldbody></mujoco>""")
    assert sorted(gates.pairs(model)) == [("base", "cover"), ("base", "lid"), ("cover", "post"), ("lid", "post")]
