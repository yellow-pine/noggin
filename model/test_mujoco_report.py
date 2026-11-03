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


def test_the_parts_share_the_items_in_turn_each_once():
    """#809: CI's sim runs a document's poses and motions in parts, the earlier part the earlier ones, the first none
    (it measures the rest, the gimbal's sweep the slowest)."""
    items = list(range(205))
    first, *parts = [mujoco_report.share(items, (i, 3)) for i in range(3)]
    assert first == [] and sum(parts, []) == items and max(map(len, parts)) - min(map(len, parts)) <= 1
    assert mujoco_report.share(items, (0, 1)) == items


def _part(poses, pair_mm, at, residual, margin, hold, peak, tip, moving, **first):
    a = {"pose": at}
    return {
        "poses": poses,
        "pairs": [{"pair": ["a:1", "b:1"], "rest_mm": 0.2, "min_mm": pair_mm, "at": a}],
        "residuals": {"tilt pivot": {"max_mm": residual, "at": a}},
        "loops": {
            "tilt pivot": {"margin_mm_rad": margin, "margin_at": a, "transmission_deg": 50.0, "transmission_at": a}
        },
        "actuators": {"tilt horn": {"hold_kgf_cm": hold, "at": a, "rated_kgf_cm": 0.4}},
        "motions": {
            "names": [f"motion {at}"],
            "servos": {
                "tilt horn": {"rest_kgf_cm": at, "hold_kgf_cm": hold, "hold_at": a, "peak_kgf_cm": peak, "peak_at": a}
            },
            "shells": {"face:1": {"g": 80.0, "peak_m_s2": 10.0 * peak, "at": a}},
        },
        "tip_over": {"margin_mm": tip, "at": a, "moving": {"margin_mm": moving, "at": a}, "footprint_mm": [90, 90]},
        **first,
    }


def test_the_parts_merge_into_each_figures_worst_the_earlier_on_a_tie():
    """#809: the merged report reads as one measured whole: the closest pair, the most open loop, the least margin, the
    heaviest hold and peak, the motions in turn and the first part's own figures (full speed, vibration), that part
    measuring no pose."""
    speed = {"tilt horn": {"off_deg": 0.1}}
    rest = {
        "poses": 0,
        "pairs": [],
        "residuals": {},
        "loops": {},
        "actuators": {},
        "full_speed": speed,
        "vibration": {},
    }
    rest |= {
        "motions": {"names": [], "servos": {}, "shells": {}},
        "tip_over": {"moving": None, "footprint_mm": [90, 90]},
    }
    one = _part(100, -0.1, 1, 0.02, 3.0, 0.3, 0.5, 5.0, 4.0, full_speed={})
    two = _part(105, -0.1, 2, 0.04, 2.5, 0.3, 0.6, 6.0, 3.0, full_speed={}, vibration={"x": 1})
    m = mujoco_report.merge([rest, one, two])
    assert m["poses"] == 205 and m["pairs"][0]["at"] == {"pose": 1}  # a tie: the earlier
    assert m["residuals"]["tilt pivot"]["max_mm"] == 0.04 and m["loops"]["tilt pivot"]["margin_at"] == {"pose": 2}
    assert m["loops"]["tilt pivot"]["transmission_at"] == {"pose": 1} and m["actuators"] == one["actuators"]
    assert m["motions"]["names"] == ["motion 1", "motion 2"]
    s = m["motions"]["servos"]["tilt horn"]
    assert (s["rest_kgf_cm"], s["hold_at"], s["peak_kgf_cm"], s["peak_at"]) == (1, {"pose": 1}, 0.6, {"pose": 2})
    assert m["motions"]["shells"]["face:1"] == {"g": 80.0, "peak_m_s2": 6.0, "at": {"pose": 2}}  # a Shell's peak (#665)
    assert (m["tip_over"]["margin_mm"], m["tip_over"]["moving"]["margin_mm"]) == (5.0, 3.0)
    assert (m["full_speed"], m["vibration"], m["tip_over"]["footprint_mm"]) == (speed, {}, [90, 90])
