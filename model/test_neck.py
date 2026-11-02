"""Seam: model/neck.py, the next Mech's neck and jaw (#641): what the servos turn the head and jaw through, the servo
angles each range needs, and the report's numbers against #641's gates."""

import math

import numpy as np
import pytest

from model import base, neck, stages
from model import geometry as g

# a head of 300 g with its centre of mass 40 mm above the tilt axis, straight over it at rest
HEAD = (300.0, (0.0, neck.AXIS[0], neck.AXIS[1] + 40.0))


@pytest.fixture(scope="module")
def report():
    return neck.report(HEAD)


@pytest.mark.parametrize("drive", ["pan", "tilt", "jaw"])
def test_every_drive_reaches_its_range_within_the_servos_travel_at_40_deg_or_better(report, drive):
    """#641: each bar meets its lever at a transmission angle of at least 40 deg over the whole range, and the servo
    turns no further than its travel to get there."""
    r = report[drive]
    assert r["transmission_deg"] >= neck.TRANSMISSION_DEG
    assert all(abs(s) <= neck.SERVO_DEG for s in r["servo_deg"])


def test_the_servo_angles_give_the_ranges_ends():
    for drive, (lo, hi) in neck.RANGES.items():
        solve = neck.LINKAGES[drive]
        for out in (lo, hi):
            assert solve(neck.servo_for(drive, out))[0] == pytest.approx(out, abs=1e-3)


def test_a_bar_parallel_to_its_lever_meets_it_square_at_rest():
    """At rest each horn and its lever lie parallel, the bar square to both: a transmission angle of 90 deg."""
    for drive in neck.RANGES:
        assert neck.transmission(drive, 0.0) == pytest.approx(90.0, abs=1e-6)


def test_the_tilt_servo_holds_the_heads_weight_through_the_linkage(report):
    """Straight over the axis the head weighs nothing at rest; tilted 20 deg its 40 mm lever arm is 40 sin 20 = 13.7
    mm, 300 g x 13.7 mm = 0.41 kgf.cm at the head, and the servo holds that times the linkage's speed ratio there."""
    tilt = report["tilt"]
    assert tilt["rest_kgf_cm"] == pytest.approx(0.0, abs=1e-3)
    at_head = 0.3 * 40 * math.sin(math.radians(20)) / 10
    assert 0.25 * at_head < tilt["hold_kgf_cm"] < at_head
    assert report["head"] == {"grams": 300.0, "above_tilt_mm": 40.0, "behind_tilt_mm": 0.0}


def test_each_flexing_span_bends_no_tighter_than_ten_lead_diameters(report):
    spans = report["spans"]
    assert spans["floor_mm"] == pytest.approx(10 * neck.LEAD_OD)
    assert min(spans["pan"]["bend_mm"], spans["tilt"]["bend_mm"]) >= spans["floor_mm"]


def test_the_pan_span_bends_in_an_s_and_the_tilt_spans_arc_breathes(report):
    """Pan: clamps 30 mm apart along z at 18 mm from the axis, the yoke's swung 45 deg: 36 sin 22.5 = 13.78 mm across,
    two arcs of (15^2 + 6.89^2) / 13.78 = 19.78 mm. Tilt: a 45 deg arc of 22 mm radius opened by 20 deg to 65 deg
    spreads the same length over more turn: 22 x 45 / 65 = 15.23 mm."""
    assert report["spans"]["pan"]["bend_mm"] == pytest.approx(19.78, abs=0.01)
    assert report["spans"]["tilt"]["bend_mm"] == pytest.approx(15.23, abs=0.01)


@pytest.mark.parametrize("doc", g.NEXT)
def test_the_neck_and_the_gimbal_share_the_heads_frame_the_torsos_foot_on_z_0(doc):
    """geometry.NEXT copies the Torso's depth (ADR 0011): the neck, the gimbal and the base are drawn in one frame, the
    head's, and the document stands the Torso's foot on z 0."""
    frames = g.NEXT[doc]
    assert len({f for f in frames.values()}) == 1
    assert frames["next-neck"][0][2] == -base.TORSO[2][0]


@pytest.mark.parametrize("doc", g.NEXT)
@pytest.mark.parametrize("drive,horn,pivot", [("pan", "pan horn", "pan pivot"), ("tilt", "tilt horn", "tilt pivot")])
def test_each_neck_servo_turns_the_head_with_the_gimbal_on_it(doc, drive, horn, pivot):
    """#642: the neck moves in the model. Its servo at the angle servo_for gives turns the head its range's end about its
    pivot, and every part of the eye gimbal turns with the head mount, rigidly."""
    stage = stages.STAGES[doc]
    end = neck.RANGES[drive][1]
    pose = stages.pose(stage, horn, neck.servo_for(drive, end))
    assert pose.joints[pivot] == pytest.approx(end, abs=0.01)
    mats = pose.parts
    carry = mats["next head mount:1"] @ np.linalg.inv(stage.parts["next head mount:1"].matrix)
    for name in stages.next_eyes().parts:
        assert np.allclose(mats[name], carry @ stage.parts[name].matrix)
    assert not np.allclose(carry, np.eye(4))


def test_the_head_is_the_parts_the_tilt_turns():
    parts = stages.next_neck().parts | stages.next_jaw().parts
    assert set(neck.HEAD) <= set(parts)
    assert {f"next {label} servo:1" for label in neck.drives()} <= set(parts)
