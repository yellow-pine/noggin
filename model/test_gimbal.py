"""Seam: model/gimbal.py, the next Mech's eye gimbal (#630): the eyes a pair of servo angles gives, the servo angles a
gaze needs, and the report's numbers against #630's gates."""

import itertools
import math

import numpy as np
import pytest

from model import envelopes, gimbal, mujoco_report


def test_the_eyes_are_mortys_at_life_size():
    """#901 (#872 step 3 round 2): the eyes sit on Morty's pupils, 72.7 mm apart; the cap is his eye's 40.4 mm sphere,
    the core x1.50 with it; the upper lid rides 1 mm off it, its edge at rest on his outline 68 deg over the gaze, and
    the lower lid's 52 deg under it."""
    assert gimbal.SPACING == pytest.approx(72.7)
    assert gimbal.CAP_R == pytest.approx(40.4)
    assert gimbal.CORE_R == pytest.approx(13.0 * 1.5, abs=0.1)
    assert gimbal.LID_R[0] == pytest.approx(41.4)
    assert gimbal.LID_REST == pytest.approx(68, abs=0.5)
    assert gimbal.LOWER_REST == pytest.approx(-52, abs=1.0)


@pytest.mark.parametrize("drive", ["yaw", "pitch", "L lid", "R lid"])
def test_every_servo_sits_behind_and_between_the_eyes(drive):
    """#684: a compact head. Each servo's case and tabs lie within the eyes' overall width (the lids' outer faces) and
    behind the eyes' centres."""
    face, shaft, tab, _ = gimbal.drives()[drive]
    corners = [c for span in (envelopes.SERVO["case"], envelopes.SERVO["tabs"]) for c in itertools.product(*span)]
    world = (gimbal.servo_matrix(face, shaft, tab) @ np.c_[corners, np.ones(16)].T)[:3]  # the Envelope's STEP frame
    assert np.abs(world[0]).max() <= gimbal.SPACING / 2 + gimbal.LID_X["upright"][1]
    assert world[1].min() >= 0


@pytest.mark.parametrize("side", ["L", "R"])
def test_each_lid_servo_drives_from_the_inner_side_of_its_eye(side):
    """#698: the lid servo turned 180 deg, its horn (and the crank and bars on it) between the eyes, facing the middle,
    so the frame's uprights come in to just outside the caps: a face about as wide as the eyes."""
    face, shaft, _, _ = gimbal.drives()[f"{side} lid"]
    x = gimbal.EYE[side][0]
    assert 0 < abs(face[0]) < abs(x) and np.sign(shaft[0]) == -np.sign(x)
    # the lids' frame across both eyes within Morty's life-size cranium (#901; today's Mech's 138)
    assert gimbal.SPACING + 2 * gimbal.LID_X["upright"][1] <= gimbal.HEAD_MM[0]


def test_each_lid_bar_meets_its_crank_at_the_transmission_floor_or_more():
    """#684: a lid's parallelogram bar keeps its direction (horn to lid pivot) while the crank turns with the lid, so
    the angle between them, folded to 0..90, stays at the MuJoCo report's floor over the lid servo's range."""
    bar = np.array(gimbal.LID_HORN) / np.linalg.norm(gimbal.LID_HORN)
    for lid in np.linspace(*np.subtract(gimbal.LID_EDGES, gimbal.LID_REST), 41):
        a = math.radians(lid)
        crank = np.array([[math.cos(a), math.sin(a)], [-math.sin(a), math.cos(a)]]) @ gimbal.LID_PIN / gimbal.CRANK
        assert (
            math.degrees(math.asin(min(1.0, abs(float(bar[0] * crank[1] - bar[1] * crank[0])))))
            >= mujoco_report.TRANSMISSION_DEG
        )


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
    assert report["lid"]["link_deg"] >= mujoco_report.TRANSMISSION_DEG  # rides the bar: the sim's loops() skips it


def test_the_hooke_error_is_the_literatures_and_the_command_map_takes_it_out(report):
    """1.6 deg at 15 deg pitch and 25 deg yaw (docs/research/2026-11-02-literature-mechanical.md 2): what the push-rod
    adds when the pitch servo ignores the yaw (the crosstalk), and what the command map leaves out of the gaze."""
    assert report["hooke_deg"] == pytest.approx(1.6, abs=0.05)
    assert report["crosstalk_deg"] == pytest.approx(report["hooke_deg"], abs=0.25)  # the form is first order
    assert report["gaze_deg"] == pytest.approx(report["play_deg"] + report["pupil_deg"], abs=0.015)  # each rounded


def test_the_gaze_gate_counts_the_pupils_seating_beside_the_play(report):
    """#650 (#51 perception [GH]): a pupil keyed with 0.3 mm of seat play strays 0.15 mm from its seat's centre, 0.21
    deg on Morty's 40.4 mm cap (#901); it can stray the way the play does, so the two add, and the total stays under 2
    deg."""
    assert report["pupil_deg"] == pytest.approx(0.21, abs=0.005)
    assert report["gaze_deg"] == pytest.approx(report["play_deg"] + 0.21, abs=0.015)
    assert report["gaze_deg"] <= gimbal.GAZE_DEG


def test_a_print_error_splits_the_eyes_a_little(report):
    assert 0 < report["vergence_deg"] < 0.5


def test_the_lids_cover_the_cap_shut_and_track_the_pitch(report):
    """Shut, the upper lid reaches past the cap's top rim and the lower past its bottom one; the servo's range runs from
    shut tracking a pitch down as far as the servo turns (#51 lid = rest + pitch, #698) to Morty's rest edge, 68 deg up
    (#901): the servo's whole travel one side of its centre."""
    lid = report["lid"]
    assert lid["shut_deg"][0] + gimbal.LID_SPAN > gimbal.CAP_HALF
    assert lid["shut_deg"][1] - gimbal.LOWER_SPAN < -gimbal.CAP_HALF
    assert lid["edge_deg"] == pytest.approx([68.2 - 90, 68.2], abs=0.1)
    assert lid["edge_deg"][0] < gimbal.LID_SHUT


def test_the_lower_lid_turns_against_the_upper_and_they_meet_below_the_middle():
    """#698, #901: one servo drives both lids of an eye; from Morty's rest edges (68 deg up, 52 down) the lower travels
    against the upper, 37 deg to its 82, and shut the two edges meet below the eye's middle, 1.5 deg apart."""
    shut = gimbal.LID_SHUT - gimbal.LID_REST
    assert gimbal.lower(0) == pytest.approx(0, abs=1e-9)
    assert gimbal.lower(shut) / shut == pytest.approx(-37 / 82, abs=0.03)
    lo, hi = np.subtract(gimbal.LID_EDGES, gimbal.LID_REST)
    turns = [gimbal.lower(s) for s in np.linspace(lo, hi, 41)]
    assert all(np.diff(turns) < 0)  # the servo opening the upper lid opens the lower, all the way
    upper, under = gimbal.LID_SHUT, gimbal.LOWER_REST + gimbal.lower(shut)
    assert -20 < under < upper < 0 and upper - under == pytest.approx(1.5, abs=0.01)


@pytest.mark.parametrize("pitch", [-12, 14])
def test_at_yaw_0_every_part_turns_about_x(pitch):
    """#670: at yaw 0 every drive is planar across x, so each part turns about x alone, as the lid sweep's hinges do."""
    for name, m in gimbal.moved(-30, pitch).items():
        assert m[0, :3] == pytest.approx((1, 0, 0), abs=1e-9) and m[:3, 0] == pytest.approx((1, 0, 0), abs=1e-9), name


@pytest.mark.parametrize("lid", [-36, -20, 15])
@pytest.mark.parametrize("pitch", [-15, 0, 15])
def test_the_moved_parts_keep_their_pins_together(lid, pitch):
    """moved() carries each part the lid servos and the eyes' pitch move (#650): every pin two of them share lands on
    one point in both, so the sweep poses an assembly, not loose parts."""
    m = gimbal.moved(lid, pitch)
    c, (hy, hz), (by, bz) = gimbal.CRANK, gimbal.PITCH_HORN, gimbal.BAIL
    pins = [(("next pitch horn:1", "next pitch bar:1"), (0, hy + c, hz))]
    pins.append((("next bail:1", "next pitch bar:1"), (0, by + gimbal.BAIL_IN, bz)))
    for s, (x, _, _) in gimbal.EYE.items():
        pins.append(((f"next {s} upper lid:1", f"next {s} lid bar:1"), (x, *gimbal.LID_PIN)))
        pins.append(((f"next {s} lid bar:1", f"next {s} lid link:1"), (x, *gimbal.LINK_PIN)))
        pins.append(((f"next {s} lid link:1", f"next {s} lower lid:1"), (x, *gimbal.LOWER_PIN)))
        pins.append(((f"next {s} lid bar:1", f"next {s} lid horn:1"), (x, *np.add(gimbal.LID_HORN, gimbal.LID_PIN))))
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
    pins = [(("next yaw horn:1", "next tie-bar:1"), (0, gimbal.YAW_Y + c, 0))]
    for s, (x, _, _) in gimbal.EYE.items():
        pins.append(((f"next {s} yaw yoke:1", "next tie-bar:1"), (x, c, 0)))
        pins.append(((f"next {s} eyeball core:1", f"next {s} push-rod:1"), (x, 0, gimbal.LEVER)))
        pins.append((("next bail:1", f"next {s} push-rod:1"), (x, by, bz + gimbal.LEVER)))
    for (a, b), p in pins:
        assert (m[a] @ [*p, 1]) == pytest.approx(m[b] @ [*p, 1], abs=1e-6), (a, b)
    front = m["next L eyeball core:1"] @ (gimbal.EYE["L"][0], -1, 0, 1)
    assert math.degrees(math.atan2(front[0] - gimbal.EYE["L"][0], -front[1])) == pytest.approx(yaw, abs=1e-3)


def test_each_lid_takes_its_own_servo():
    """A wink (#656): one eye's lids shut while the other's stay open."""
    m = gimbal.moved({"L": -21, "R": 0}, 0)
    edge = {s: m[f"next {s} upper lid:1"] @ (x, -1, 0, 1) for s, (x, _, _) in gimbal.EYE.items()}
    assert [round(math.degrees(math.atan2(e[2], -e[1]))) for e in edge.values()] == [-21, 0]


def test_the_lid_and_the_eyes_turn_as_commanded():
    """The lid servo's degrees turn the upper lid's edge up by as many and the lower lid's down by lower(); the core
    takes the eyes' pitch up."""
    m = gimbal.moved(-30, 10)
    x = gimbal.EYE["L"][0]
    for part, turn in (("upper lid", -30), ("lower lid", gimbal.lower(-30))):
        edge = m[f"next L {part}:1"] @ (x, -1, 0, 1)
        assert math.degrees(math.atan2(edge[2], -edge[1])) == pytest.approx(turn)
    assert gimbal.lower(-30) > 6  # closing, the lower lid rises
    front = m["next L eyeball core:1"] @ (x, -1, 0, 1)
    assert math.degrees(math.atan2(front[2], -front[1])) == pytest.approx(10, abs=1e-3)
