"""Seam: model/gimbal.py, the next Mech's eye gimbal (#630): the eyes a pair of servo angles gives, the servo angles a
gaze needs, and the report's numbers against #630's gates."""

import math

import pytest

from model import gimbal


def test_both_eyes_turn_together_and_the_pitch_rod_couples_to_yaw_in_the_hooke_form():
    """The tie-bar is a parallelogram: both eyes take the yaw servo's angle. At yaw 0 the pitch push-rods are
    parallelograms too, so both eyes pitch as the bail; with the eyes yawed the push-rod sets the lever's fore-aft
    reach, sin(pitch) cos(yaw), the Hooke form (docs/research/2026-11-02-literature-mechanical.md 2)."""
    s = gimbal.servos(0, 12)[1]
    level = gimbal.eyes(0, s)
    assert level["L"] == pytest.approx((0, 12), abs=1e-6) and level["R"] == pytest.approx((0, 12), abs=1e-6)
    turned = gimbal.eyes(25, s)
    hooke = math.degrees(math.asin(math.sin(math.radians(12)) / math.cos(math.radians(25))))
    for side in "LR":
        assert turned[side][0] == pytest.approx(25, abs=1e-6)
        assert turned[side][1] == pytest.approx(hooke, abs=0.2)  # the form is first order: the rod's tilt adds 0.13


def test_the_command_map_gives_every_gaze_in_range():
    for yaw, pitch in ((-25, -15), (25, 15), (10, -7)):
        assert gimbal.eyes(*gimbal.servos(yaw, pitch))["L"] == pytest.approx((yaw, pitch), abs=1e-3)


@pytest.fixture(scope="module")
def report():
    return gimbal.report()


def test_the_report_holds_the_gates(report):
    """#630's gates: gaze within 2 deg including play, the caps at least 1 mm apart, the lids clear of everything that
    moves inside them, every lid range within its servo's travel."""
    assert report["gaze_deg"] <= gimbal.GAZE_DEG
    assert report["cap_gap_mm"] >= gimbal.CAP_GAP_MM
    assert report["lid"]["clearance_mm"] >= gimbal.LID_CLEAR_MM
    assert all(abs(d) <= gimbal.SERVO_DEG for d in report["lid"]["servo_deg"])


def test_the_hooke_error_is_the_literatures_and_the_command_map_takes_it_out(report):
    """1.6 deg at 15 deg pitch and 25 deg yaw (docs/research/2026-11-02-literature-mechanical.md 2): what the push-rod
    adds when the pitch servo ignores the yaw (the crosstalk), and what the command map leaves out of the gaze."""
    assert report["hooke_deg"] == pytest.approx(1.6, abs=0.05)
    assert report["crosstalk_deg"] == pytest.approx(report["hooke_deg"], abs=0.25)  # the form is first order
    assert report["gaze_deg"] == pytest.approx(report["play_deg"] + report["pupil_deg"], abs=0.015)  # each rounded


def test_the_gaze_gate_counts_the_pupils_seating_beside_the_play(report):
    """#650 (#51 perception [GH]): a pupil keyed with 0.3 mm of seat play strays 0.15 mm from its seat's centre, 0.32
    deg on the 27 mm cap; it can stray the way the play does, so the two add, and the total stays under 2 deg."""
    assert report["pupil_deg"] == pytest.approx(0.32, abs=0.005)
    assert report["gaze_deg"] == pytest.approx(report["play_deg"] + 0.32, abs=0.015)
    assert report["gaze_deg"] <= gimbal.GAZE_DEG


def test_a_print_error_splits_the_eyes_a_little(report):
    assert 0 < report["vergence_deg"] < 0.5


def test_the_lid_covers_the_cap_closed_and_tracks_the_pitch_open(report):
    """Closed, the lid's edge is past the cap's rim; open, it sits over the pupil at full pitch up (#51 lid = rest +
    pitch): the range runs from one to the other."""
    closed, opened = report["lid"]["edge_deg"]
    assert closed < -gimbal.CAP_HALF and opened == pytest.approx(gimbal.PUPIL_DEG + 2 + gimbal.PITCH)


@pytest.mark.parametrize("lid", [-65, -20, 15])
@pytest.mark.parametrize("pitch", [-15, 0, 15])
def test_the_moved_parts_keep_their_pins_together(lid, pitch):
    """moved() carries each part the lid servos and the eyes' pitch move (#650): every pin two of them share lands on
    one point in both, so the sweep poses an assembly, not loose parts."""
    m = gimbal.moved(lid, pitch)
    c, (hy, hz), (by, bz) = gimbal.CRANK, gimbal.PITCH_HORN, gimbal.BAIL
    pins = [(("next pitch horn:1", "next pitch bar:1"), (0, hy + c, hz))]
    pins.append((("next bail:1", "next pitch bar:1"), (0, by + gimbal.BAIL_IN, bz)))
    for s, (x, _, _) in gimbal.EYE.items():
        pins.append(((f"next {s} lid:1", f"next {s} lid bar:1"), (x, c, 0)))
        pins.append(((f"next {s} lid bar:1", f"next {s} lid horn:1"), (x, gimbal.LID_HORN[0] + c, gimbal.LID_HORN[1])))
        pins.append(((f"next {s} eyeball core:1", f"next {s} push-rod:1"), (x, 0, gimbal.LEVER)))
        pins.append((("next bail:1", f"next {s} push-rod:1"), (x, by, bz + gimbal.LEVER)))
    for (a, b), p in pins:
        assert (m[a] @ [*p, 1]) == pytest.approx(m[b] @ [*p, 1], abs=1e-6), (a, b)


@pytest.mark.parametrize("yaw", [-25, 25])
@pytest.mark.parametrize("pitch", [-15, 15])
def test_a_yaw_keeps_the_tie_bar_and_the_push_rods_on_their_pins(yaw, pitch):
    """#656: with the eyes yawed the yaw horn, the tie-bar and the yokes turn together and each push-rod still meets its
    lever's ball and its bail arm's: the motion pictures pose an assembly."""
    m = gimbal.moved(0, pitch, yaw)
    c, (by, bz) = gimbal.CRANK, gimbal.BAIL
    pins = [(("next yaw horn:1", "next tie-bar:1"), (0, c, 0))]
    for s, (x, _, _) in gimbal.EYE.items():
        pins.append(((f"next {s} yaw yoke:1", "next tie-bar:1"), (x, c, 0)))
        pins.append(((f"next {s} eyeball core:1", f"next {s} push-rod:1"), (x, 0, gimbal.LEVER)))
        pins.append((("next bail:1", f"next {s} push-rod:1"), (x, by, bz + gimbal.LEVER)))
    for (a, b), p in pins:
        assert (m[a] @ [*p, 1]) == pytest.approx(m[b] @ [*p, 1], abs=1e-6), (a, b)
    front = m["next L eyeball core:1"] @ (gimbal.EYE["L"][0], -1, 0, 1)
    assert math.degrees(math.atan2(front[0] - gimbal.EYE["L"][0], -front[1])) == pytest.approx(yaw, abs=1e-3)


def test_each_lid_takes_its_own_servo():
    """A wink (#656): one lid closes while the other stays open."""
    m = gimbal.moved({"L": -65, "R": 0}, 0)
    edge = {s: m[f"next {s} lid:1"] @ (x, -1, 0, 1) for s, (x, _, _) in gimbal.EYE.items()}
    assert [round(math.degrees(math.atan2(e[2], -e[1]))) for e in edge.values()] == [-65, 0]


def test_the_lid_and_the_eyes_turn_as_commanded():
    """The lid servo's degrees turn the lid's edge up by as many; the core takes the eyes' pitch up."""
    m = gimbal.moved(20, 10)
    x = gimbal.EYE["L"][0]
    edge = m["next L lid:1"] @ (x, -1, 0, 1)
    assert math.degrees(math.atan2(edge[2], -edge[1])) == pytest.approx(20)
    front = m["next L eyeball core:1"] @ (x, -1, 0, 1)
    assert math.degrees(math.atan2(front[2], -front[1])) == pytest.approx(10, abs=1e-3)
