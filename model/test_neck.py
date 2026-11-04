"""Seam: model/neck.py, the Mech's neck and jaw (#641): what the servos turn the head and jaw through, the servo
angles each range needs, and the report's numbers against #641's gates."""

import numpy as np
import pytest
import trimesh

from model import base, mjcf, neck, stages
from model import geometry as g

# a head of 300 g with its centre of mass 40 mm above the tilt axis, straight over it at rest
TILT_Y, TILT_Z = neck.HEAD_AXES["tilt"][0][1:]
HEAD = (300.0, (0.0, TILT_Y, TILT_Z + 40.0))


def test_the_head_interface_publishes_the_fixed_frame_and_tilt_then_pan_order():
    """#902's functional anchors, from the accepted Stage 3 coordinates; anatomy alignment remains #874's gate."""
    frame = stages.align(*neck.HEAD_FRAME)
    assert frame[:3, 3] == pytest.approx((0, -150, 177))
    for drive, point in (("tilt", (0, -73.4, 128.3)), ("pan", (0, -103.8, 141.8)), ("jaw", (0, -124, 153))):
        local, axis = neck.HEAD_AXES[drive]
        assert (frame @ np.r_[local, 1])[:3] == pytest.approx(point)
        assert tuple(axis) == (g.Z if drive == "pan" else g.X)
    assert neck.HEAD_PARENTS == {"tilt": None, "pan": "tilt", "jaw": "pan"}
    assert neck.HEAD_SERVOS == {"tilt": "tilt", "pan": "tilt", "mouth": "pan"}
    assert len(set(neck.HEAD_CARRIERS.values())) == 4


def test_the_real_neck_uses_a_fixed_cervical_carrier_then_nod_plate_then_pan_bearing():
    sub = stages.neck_sub()
    assert {"cervical carrier:1", "nod plate:1", "head mount:1", "pan bearing:1"} <= sub.parts.keys()
    assert not {"neck mount:1", "pan yoke:1", "pan bar:1", "tilt bar:1"} & sub.parts.keys()
    assert stages.stem(sub.parts["tilt servo:1"].file) == "standard servo"
    assert sub.parts["tilt servo:1"].material == (55, "documented")
    tilt, pan = sub.horns["tilt horn"], sub.horns["pan horn"]
    assert tilt.direct.joint == "tilt pivot" and tilt.direct.sign == -1
    assert pan.direct.joint == "pan pivot" and pan.direct.sign == 1
    assert {"nod plate:1", "tilt servo:1", "pan servo:1", "head mount:1"} <= set(tilt.direct.driven)
    assert not {"cervical carrier:1", "tilt horn:1"} & set(tilt.direct.driven)
    assert "head mount:1" in pan.direct.driven and "pan servo:1" not in pan.direct.driven


@pytest.mark.parametrize("sign", (-1, 1))
def test_a_direct_servo_turns_its_carrier_and_riders_but_not_its_fixed_reaction(sign):
    """A servo case on the moving plate reacts against a fixed horn; its output sign reverses (#902)."""
    parts = {
        name: stages.Part("unused.stl", stages.translate(point), (1.0, "documented"), None)
        for name, point in (("fixed:1", (0, 0, 0)), ("plate:1", (0, 10, 0)), ("head:1", (0, 20, 0)))
    }
    horn = stages.Horn(
        {"point": (0, 0, 0), "axis": g.X},
        (-20, 20),
        "plate:1",
        [],
        [],
        np.eye(4),
        direct=stages.Direct("tilt pivot", ["plate:1", "head:1"], sign),
    )
    pose = stages.pose(stages.Doc("direct", parts, {"tilt horn": horn}), "tilt horn", 20)
    assert pose.joints["tilt pivot"] == 20 * sign
    assert np.allclose(pose.parts["fixed:1"], parts["fixed:1"].matrix)
    for name, radius in (("plate:1", 10), ("head:1", 20)):
        assert pose.parts[name][:3, 3] == pytest.approx(
            (0, radius * np.cos(np.deg2rad(20)), sign * radius * np.sin(np.deg2rad(20)))
        )


@pytest.mark.parametrize("sign", (-1, 1))
def test_a_direct_servo_in_mujoco_drives_its_joint_and_riders_with_the_physical_sign(tmp_path, monkeypatch, sign):
    """#902: the real actuator, not just the kinematic command map, turns the rigid carrier against ground."""
    mesh = tmp_path / "gimbal frame.stl"
    trimesh.creation.box((2, 2, 2)).export(mesh)
    parts = {
        name: stages.Part(str(mesh), stages.translate(point), (16.0, "documented"), None)
        for name, point in (("fixed:1", (0, 0, 0)), ("plate:1", (0, 10, 0)), ("head:1", (0, 20, 0)))
    }
    horn = stages.Horn(
        {"point": (0, 0, 0), "axis": g.Z},
        (-45, 45),
        "plate:1",
        [],
        [],
        np.eye(4),
        direct=stages.Direct("pan pivot", ["plate:1", "head:1"], sign),
    )
    doc = "mech-back-mechanical"
    monkeypatch.setitem(stages.STAGES, doc, stages.Doc(doc, parts, {"pan horn": horn}))
    spec = mjcf.spec(doc, collide=False)
    spec.modelfiledir = mjcf.BUILD
    model = spec.compile()
    assert model.actuator("pan horn").trnid[0] == model.joint("pan pivot").id
    assert model.actuator("pan horn").gear[0] == sign
    data = mjcf.pose(model, {"pan horn": 20})
    assert np.degrees(data.joint("pan pivot").qpos[0]) == pytest.approx(20 * sign, abs=0.5)
    assert data.body("fixed:1").xpos == pytest.approx((0, 0, 0))
    assert data.body("head:1").xpos == pytest.approx(
        (-sign * 0.02 * np.sin(np.deg2rad(20)), 0.02 * np.cos(np.deg2rad(20)), 0), abs=0.0002
    )


@pytest.fixture(scope="module")
def report():
    return neck.report(HEAD)


@pytest.mark.parametrize("drive", ["jaw"])
def test_every_drive_reaches_its_range_within_the_servos_travel_at_40_deg_or_better(report, drive):
    """#641: each bar meets its lever at a transmission angle of at least 40 deg over the whole range, and the servo
    turns no further than its travel to get there."""
    r = report[drive]
    assert r["transmission_deg"] >= neck.TRANSMISSION_DEG
    assert all(abs(s) <= neck.SERVO_DEG for s in r["servo_deg"])


def test_the_servo_angles_give_the_ranges_ends():
    for drive, (lo, hi) in neck.RANGES.items():
        for out in (lo, hi):
            assert neck.output(drive, neck.servo_for(drive, out)) == pytest.approx(out, abs=1e-3)


def test_a_bar_parallel_to_its_lever_meets_it_square_at_rest():
    """At rest each horn and its lever lie parallel, the bar square to both: a transmission angle of 90 deg."""
    for drive in neck.LINKAGES:
        assert neck.transmission(drive, 0.0) == pytest.approx(90.0, abs=1e-6)


def test_the_balance_spring_holds_the_heads_weight_and_the_servo_what_is_left(report):
    """#838: the tilt axis behind the head's centre of mass, a torsion spring on its shank holds the head. A head of
    300 g 40 mm in front of the axis and 30 over it turns itself face down with 300 g x 40 mm = 1.2 kgf.cm at rest, so
    the spring turns it back as much, and its rate is the weight's lever's change, 300 g x 30 mm = 0.9 kgf.cm a radian;
    tilted 20 deg the spring's line misses the weight's turn by 0.08 kgf.cm, the servo holding that through the linkage.
    Straight over the axis the spring takes the 40 mm's change alone: nothing at rest."""
    ahead = neck.report((300.0, (0.0, TILT_Y - 40.0, TILT_Z + 30.0)))["tilt"]
    assert ahead["spring"] == {"rest_kgf_cm": -1.2, "rate_kgf_cm_rad": 0.9}
    assert ahead["rest_kgf_cm"] == pytest.approx(0.0, abs=1e-3)
    assert ahead["hold_kgf_cm"] == pytest.approx(0.079)  # 1:1 now, not the retired four-bar's torque reduction
    tilt = report["tilt"]
    assert tilt["spring"] == {"rest_kgf_cm": 0.0, "rate_kgf_cm_rad": 1.2} and tilt["rest_kgf_cm"] == pytest.approx(0.0)
    assert report["head"] == {"grams": 300.0, "above_tilt_mm": 40.0, "behind_tilt_mm": 0.0}


def test_one_balance_spring_splits_its_miss_between_the_head_in_its_skin_and_bare():
    """#830: one spring holds the head with its Skin on and off. A bare head of 300 g 40 mm in front of the axis and 30
    over it wants -1.2 kgf.cm at rest and 0.9 a radian; its Skin doubles it, -2.4 and 1.8. The spring wound between them,
    -1.8 and 1.35, misses each by 0.6 kgf.cm at rest, which the servo holds through the linkage's gain, alike."""
    bare = (300.0, (0.0, TILT_Y - 40.0, TILT_Z + 30.0))
    tilt = neck.report((600.0, bare[1]), bare)["tilt"]
    assert tilt["spring"] == {"rest_kgf_cm": -1.8, "rate_kgf_cm_rad": 1.35}
    assert tilt["rest_kgf_cm"] == pytest.approx(0.6 * tilt["gain"], abs=2e-3)
    assert tilt["bare"]["rest_kgf_cm"] == tilt["rest_kgf_cm"]
    assert tilt["bare"]["hold_kgf_cm"] >= tilt["bare"]["rest_kgf_cm"]


def test_each_flexing_span_bends_no_tighter_than_ten_lead_diameters(report):
    spans = report["spans"]
    assert spans["floor_mm"] == pytest.approx(10 * neck.LEAD_OD)
    assert min(spans["pan"]["bend_mm"], spans["tilt"]["bend_mm"]) >= spans["floor_mm"]


def test_the_pan_span_bends_in_an_s_and_the_tilt_spans_arc_breathes(report):
    """Pan: clamps 30 mm apart along z at 18 mm from the axis, the yoke's swung 45 deg: 36 sin 22.5 = 13.78 mm across,
    two arcs of (15^2 + 6.89^2) / 13.78 = 19.78 mm. Tilt: a 45 deg arc of 22 mm radius opened by 20 deg to 65 deg
    spreads the same length over more turn: 22 x 45 / 65 = 15.23 mm."""
    assert report["spans"]["pan"]["bend_mm"] == pytest.approx(19.78, abs=0.01)
    assert report["spans"]["tilt"]["bend_mm"] == pytest.approx(16.62, abs=0.01)


@pytest.mark.parametrize("doc", g.MECH)
def test_the_neck_and_the_gimbal_share_the_heads_frame_the_torsos_foot_on_z_0(doc):
    """geometry.MECH copies the Torso's depth (ADR 0011): the neck, the gimbal and the base are drawn in one frame, the
    head's, and the document stands the Torso's foot on z 0."""
    frames = g.MECH[doc]
    assert len({f for f in frames.values()}) == 1
    assert frames["neck"][0][2] == -base.TORSO[2][0]


@pytest.mark.parametrize("doc", g.MECH)
@pytest.mark.parametrize("drive,horn,pivot", [("pan", "pan horn", "pan pivot"), ("tilt", "tilt horn", "tilt pivot")])
def test_each_neck_servo_turns_the_head_with_the_gimbal_on_it(doc, drive, horn, pivot):
    """#642: the neck moves in the model. Its servo at the angle servo_for gives turns the head its range's end about its
    pivot, and every part of the eye gimbal turns with the head mount, rigidly."""
    stage = stages.STAGES[doc]
    end = neck.RANGES[drive][1]
    pose = stages.pose(stage, horn, neck.servo_for(drive, end))
    assert pose.joints[pivot] == pytest.approx(end, abs=0.01)
    mats = pose.parts
    carry = mats["head mount:1"] @ np.linalg.inv(stage.parts["head mount:1"].matrix)
    for name in stages.eyes_sub().parts:
        assert np.allclose(mats[name], carry @ stage.parts[name].matrix)
    assert not np.allclose(carry, np.eye(4))


def test_the_head_is_the_parts_the_tilt_turns():
    parts = stages.neck_sub().parts | stages.jaw_sub().parts
    assert set(neck.HEAD) <= set(parts)
    assert {f"{label} servo:1" for label in neck.drives()} <= set(parts)
