"""Seam: model/mujoco_report.py's tip-over margin, on a plan outline drawn by hand, and its servo torques, on a
parallelogram four-bar written by hand (the report itself: test_report.py)."""

import json

import mujoco
import numpy as np
import pytest

from model import mjcf, mujoco_report, neck, stages


def test_finished_anatomy_adds_carried_mass_inertia_and_gravity_without_collision_meshes(tmp_path, monkeypatch):
    """The same finished export's head/jaw loads must affect torque even in mechanical-only documents (ADR0020)."""
    loads = {
        stem: {"carrier": carrier, "mass_g": grams, "com_mm": [100, 0, 0], "inertia_g_mm2": np.eye(3).tolist()}
        for stem, carrier, grams in [("skull", "pan", 100), ("calvaria", "pan", 50), ("mandible", "jaw", 10)]
        + [(f"c{i}", "fixed", 1) for i in range(1, 8)]
    }
    path = tmp_path / "loads.json"
    path.write_text(json.dumps({"source": "synthetic finished mesh fixture", "parts": loads}))
    monkeypatch.setattr(mjcf, "ANATOMY_LOADS", str(path), raising=False)
    spec = mujoco.MjSpec.from_string("""<mujoco><worldbody>
        <body name="head mount:1"><joint name="tilt" axis="0 1 0"/><geom size="0.001" mass="1e-6"/>
          <body name="jaw:1"><geom size="0.001" mass="1e-6"/></body></body>
        <body name="cervical carrier:1"><geom size="0.001" mass="1e-6"/></body>
        </worldbody><actuator><motor joint="tilt"/></actuator></mujoco>""")
    parts = {
        n: stages.Part("unused.stl", np.eye(4), None, None) for n in neck.HEAD_CARRIERS.values() if n != "nod plate:1"
    }
    horn = stages.Horn({}, (), "", [], [], np.eye(4))
    stage = stages.Doc("synthetic", parts, {"tilt horn": horn})
    mjcf.anatomy(spec, stage, {n: spec.body(n) for n in parts})
    model = spec.compile()
    assert model.body_subtreemass[model.body("head mount:1").id] == pytest.approx(0.160002)
    assert model.ngeom == 3  # inertial loads never add collision or visual geometry
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    assert data.body("anatomy skull").xipos == pytest.approx((0.1, 0, 0))
    assert abs(mujoco_report.torques(model, data, moving=False)[0]) == pytest.approx(0.16 * 9.81 * 0.1)
    matrix = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, matrix)
    assert matrix[0, 0] > 0.16 * 0.1**2  # each finished mesh's own COM inertia also survives


def test_the_standard_tilt_motor_holds_a_load_the_micro_servo_cannot():
    """200 g on a 100 mm arm requires 2 kgf.cm: below the standard's inferred continuous limit, above micro stall."""
    spec = mujoco.MjSpec.from_string("""<mujoco><worldbody><body>
        <joint name="tilt pivot" axis="0 1 0"/><geom type="sphere" pos="0.1 0 0" size="0.001" mass="0.2"/>
        </body></worldbody></mujoco>""")
    mujoco_report.mjcf.drive(spec, "tilt pivot", name="tilt horn")
    model = spec.compile()
    data = mujoco_report.mjcf.pose(model, {"tilt horn": 0})
    assert abs(np.degrees(data.joint("tilt pivot").qpos[0])) < 0.5
    assert abs(data.actuator("tilt horn").force[0]) == pytest.approx(0.2 * 9.81 * 0.1, rel=0.01)


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


def test_a_reversed_direct_reaction_reports_motor_torque_with_its_physical_sign():
    model = mujoco.MjModel.from_xml_string(FOUR_BAR.replace('<motor joint="horn"/>', '<motor joint="horn" gear="-1"/>'))
    reference = mujoco.MjModel.from_xml_string(FOUR_BAR)
    torque = mujoco_report.torques(model, mujoco.MjData(model), moving=False)[0]
    expected = mujoco_report.torques(reference, mujoco.MjData(reference), moving=False)[0]
    assert torque == pytest.approx(-expected, rel=1e-6)


def test_a_balance_spring_on_the_rocker_takes_its_share_off_the_held_servo():
    """#838: a torsion spring on the rocker's pivot wound to the mass's torque at rest (mjcf.balance's stiffness and
    springref) leaves the servo nothing to hold there; wound to half of it, half."""
    for wound, left in ((1.0, 0.0), (0.5, 0.5)):
        model = mujoco.MjModel.from_xml_string(FOUR_BAR)
        rocker = model.joint("rocker")
        model.jnt_stiffness[rocker.id] = 1.0
        model.qpos_spring[rocker.qposadr] = -wound * 0.1 * 9.81 * 0.1  # the 100 g turns it -y: the spring +y
        torque = mujoco_report.torques(model, mujoco.MjData(model), moving=False)[0]
        assert abs(torque) == pytest.approx(left * 0.1 * 9.81 * 0.1, abs=1e-5)  # the light links weigh 1e-6 kg


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


# The Torso's mesh, mm in metres: a 92 x 93.5 foot 2 mm thick and, 4 mm off the table, a pad standing 4 mm out of its
# front wall, as a Seat's (model/skin.py, #665)
FOOT, PAD = (
    [(x, y, z) for x in (0, 92) for y in (0, 93.5) for z in (0, 2)],
    [(x, y, z) for x in (40, 54) for y in (-4, 0) for z in (4, 18)],
)
TORSO = f"""
<mujoco>
  <asset><mesh name="torso" scale="0.001 0.001 0.001" vertex="{" ".join(f"{c}" for p in FOOT + PAD for c in p)}"/></asset>
  <worldbody><body name="torso:1"><geom type="mesh" mesh="torso" group="{mujoco_report.mjcf.VISUAL}"/></body></worldbody>
</mujoco>"""


def test_the_footprint_is_the_torsos_foot_not_what_stands_off_the_table():
    """#665: a Seat's pad on the Torso's wall is no part of what stands on the table."""
    model = mujoco.MjModel.from_xml_string(TORSO)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    plate = mujoco_report._plate(model, data)
    assert plate[:, :2].min(axis=0) == pytest.approx((0, 0), abs=1e-3)
    assert plate[:, :2].max(axis=0) == pytest.approx((92, 93.5), abs=1e-3)
