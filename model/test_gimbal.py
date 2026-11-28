"""Seam: model/gimbal.py, the Mech's eye gimbal (#630): the eyes a pair of servo angles gives, the servo angles a
gaze needs, and the report's numbers against #630's gates."""

import itertools
import math

import numpy as np
import pytest

from model import envelopes, gimbal, mujoco_report


def test_the_eyes_are_mortys_at_life_size():
    """#901, #967: the eyes sit on his Sculpt's eyeballs, 73.3 mm apart (model/test_skin.py refits them); the core,
    its lever and the yoke are sized to his eyeball's own 37.1 mm, x1.4 of the gimbal's first 27 mm, so they turn
    inside the shell the hidden lids sweep. The cap is a 35.8 mm sphere, 1.3 mm under his eye's; the lids' band 0.55 mm
    over it and 0.75 mm thick, its outer face on his eye's own surface, so the shell ends at 37.6 mm (#850: the brows'
    room). At rest the lids are open: the upper's edge 83.3 deg up at the eye's middle, behind the top rim, the lower's
    on the cap's bottom edge, 59.4 deg down."""
    assert gimbal.SPACING == pytest.approx(73.3)
    assert gimbal.CAP_R == pytest.approx(34.9) == pytest.approx(gimbal.MORTY_BALL_R - 2.2)
    assert gimbal.CORE_R == pytest.approx(13.0 * 1.4) and gimbal.LEVER == pytest.approx(17.0 * 1.4)
    assert gimbal.LID_R == pytest.approx((35.45, 36.2)) and gimbal.LIDS_SHELL == pytest.approx((34.9, 36.7))
    assert gimbal.LID_REST == pytest.approx(81.7) and gimbal.LOWER_REST == pytest.approx(-57.0)


@pytest.mark.parametrize("drive", ["yaw", "pitch", "L lid", "R lid"])
def test_every_servo_sits_behind_and_between_the_eyes(drive):
    """#684: a compact head. Each servo's case and tabs lie within the eyes' overall width (the lids' outer faces) and
    behind the eyes' centres."""
    face, shaft, tab, _ = gimbal.drives()[drive]
    corners = [c for span in (envelopes.SERVO["case"], envelopes.SERVO["tabs"]) for c in itertools.product(*span)]
    world = (gimbal.servo_matrix(face, shaft, tab) @ np.c_[corners, np.ones(16)].T)[:3]  # the Envelope's STEP frame
    assert np.abs(world[0]).max() <= gimbal.SPACING / 2 + gimbal.FOOT_X[1]
    assert world[1].min() >= 0


@pytest.mark.parametrize("side", ["L", "R"])
def test_each_lid_servo_drives_from_the_inner_side_of_its_eye(side):
    """#698, #967: the lid servo turned 180 deg, its horn (and the bar and the link on it) between the eyes, facing the
    middle; the link's pin is one of the horn's own holes, on the arm the bar's is on; and the lids' hubs, the
    nearest the midline 1.8 mm from it, leave the frame's wall there its 1.3 mm a side and the lids' room."""
    face, shaft, _, _ = gimbal.drives()[f"{side} lid"]
    x = gimbal.EYE[side][0]
    assert 0 < abs(face[0]) < abs(x) and np.sign(shaft[0]) == -np.sign(x)
    assert gimbal.LINK_CRANK in envelopes.HORN["holes_x"] and gimbal.CRANK in envelopes.HORN["holes_x"]
    assert np.subtract(gimbal.LINK_PIN, gimbal.LID_HORN) * gimbal.CRANK == pytest.approx(
        np.multiply(gimbal.LID_PIN, gimbal.LINK_CRANK)
    )
    assert abs(x) - gimbal.LID_X["lower"][1] >= gimbal.WALL_X + gimbal.LID_CLEAR_MM - 1e-9
    assert abs(face[0]) == pytest.approx(abs(x) - gimbal.LID_X["bar"][0])  # the bar and the link on the horn's face


def _box(drive, part="case"):
    """(lo, hi) corners of a drive's servo `part` (its case or its tabs) in the gimbal's frame."""
    face, shaft, tab, _ = gimbal.drives()[drive]
    corners = np.c_[list(itertools.product(*envelopes.SERVO[part])), np.ones(8)]
    world = (gimbal.servo_matrix(face, shaft, tab) @ corners.T)[:3]
    return world.min(axis=1), world.max(axis=1)


@pytest.mark.parametrize("side", ["L", "R"])
def test_each_lid_servo_stands_behind_the_belt_its_eyes_drives_leave_through(side):
    """#967: once the lids stow under Morty's skin, the only way out of an eye's sphere is the belt behind it, between
    the two stowed lids, and the lid servo's case stood across it (31 to 43 mm behind the eye). It stands behind it
    now: the skull (#874) keeps a belt 48 mm back free, and the prototype's routes (comment 7209502441) end before
    y 46.5. The pitch servo stays behind it."""
    for part in ("case", "tabs"):
        lo, hi = _box(f"{side} lid", part)
        assert lo[1] >= 48.0
        assert hi[1] <= _box("pitch")[0][1] - 2.0  # the sim's collision pieces stray up to 1.4 mm


def test_the_bail_turns_over_the_lid_servos_and_under_the_cranium_tray():
    """#967: the bail's rod crosses the head over both lid servos' cases and tabs, which stand where its axis was, and
    under the cranium tray's plate (model/base.py TRAY_Z): its round, 3 mm about its axis, with 2 mm either way
    (model/printed/test_gimbal.py reads the drawn bail, its Bones' flat-bottomed rod too, on the exact solids)."""
    from model import base

    y, z = gimbal.BAIL
    for side in "LR":
        for part in ("case", "tabs"):
            lo, hi = _box(f"{side} lid", part)
            assert lo[1] < y < hi[1]  # over it, so it has to clear its top
            assert z - 3.0 - hi[2] >= 2.0
    assert base.TRAY_Z[0] - (z + 3.0) >= 2.0


def _meets(u, v):
    """The angle two links meet at, folded to 0..90 deg."""
    cos = abs(float(np.dot(u, v))) / np.linalg.norm(u) / np.linalg.norm(v)
    return math.degrees(math.acos(min(1.0, cos)))


@pytest.mark.parametrize("yaw", [-25.0, 0.0, 25.0])
def test_each_push_rod_meets_its_lever_and_its_bail_arm_at_the_transmission_floor_or_more(yaw):
    """#967: the rod leans down to the back, so it is square to neither the lever nor the bail's arm; over the pitch,
    and the yaw, it meets each at the MuJoCo report's floor or more (a rod is no loop: the sim's report skips it)."""
    for pitch in np.linspace(-gimbal.PITCH, gimbal.PITCH, 13):
        m = gimbal.moved(0.0, pitch, yaw)
        for s, (x, _, _) in gimbal.EYE.items():
            centre, axis = np.array([x, 0, 0]), np.array([x, *gimbal.BAIL])
            ball = (m[f"{s} eyeball core:1"] @ (x, 0, gimbal.LEVER, 1))[:3]
            pin = (m["bail:1"] @ (x, *gimbal.BAIL_BALL, 1))[:3]
            assert _meets(pin - ball, ball - centre) >= mujoco_report.TRANSMISSION_DEG
            assert _meets(pin - ball, pin - axis) >= mujoco_report.TRANSMISSION_DEG


def test_the_pitch_bar_meets_the_horn_and_the_input_arm_at_the_transmission_floor_or_more():
    """#967: the pitch servo and its horn stay where they were and the bail's axis rose, so the bar leans; over the
    pitch servo's range it meets the horn's arm and the bail's input arm at the MuJoCo report's floor or more."""
    horn, axis = np.array([0, *gimbal.PITCH_HORN]), np.array([0, *gimbal.BAIL])
    lo, hi = (gimbal.servos(0, p)[1] for p in (-gimbal.PITCH, gimbal.PITCH))
    assert -gimbal.SERVO_DEG < lo < 0 < hi < gimbal.SERVO_DEG
    for pitch in np.linspace(-gimbal.PITCH, gimbal.PITCH, 13):
        m = gimbal.moved(0.0, pitch)
        a = (m["pitch horn:1"] @ (0, gimbal.PITCH_HORN[0] + gimbal.CRANK, gimbal.PITCH_HORN[1], 1))[:3]
        b = (m["bail:1"] @ (0, *gimbal.BAIL_TIP, 1))[:3]
        assert _meets(b - a, a - horn) >= mujoco_report.TRANSMISSION_DEG
        assert _meets(b - a, b - axis) >= mujoco_report.TRANSMISSION_DEG


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


@pytest.mark.parametrize("side", ["L", "R"])
def test_the_tie_bar_meets_each_yoke_crank_at_the_transmission_floor_or_more(side):
    """#1003: the tie-bar is a parallelogram, so each eye's bar (from the yaw horn's pin to the yoke's) keeps its
    direction, the horn's axis to the eye's centre, while the crank turns with the yaw; the angle between them, folded
    to 0..90, stays at the MuJoCo report's floor over the yaw's range (22 mm behind the eyes it fell to 33.8)."""
    bar = np.array([gimbal.EYE[side][0], -gimbal.YAW_Y]) / math.hypot(gimbal.EYE[side][0], gimbal.YAW_Y)
    for yaw in np.linspace(-gimbal.YAW, gimbal.YAW, 41):
        a = math.radians(yaw)
        crank = (-math.sin(a), math.cos(a))  # the cranks point +y at rest, turned about z
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
    assert report["lid"]["link_deg"] >= mujoco_report.TRANSMISSION_DEG
    assert report["lid"]["apart_mm"] >= 2 * (gimbal.WALL_X + gimbal.LID_CLEAR_MM) - 1e-9  # the frame's wall between


def test_the_hooke_error_is_the_literatures_and_the_command_map_takes_it_out(report):
    """1.6 deg at 15 deg pitch and 25 deg yaw (docs/research/2026-11-02-literature-mechanical.md 2): what the push-rod
    adds when the pitch servo ignores the yaw (the crosstalk), and what the command map leaves out of the gaze."""
    assert report["hooke_deg"] == pytest.approx(1.6, abs=0.05)
    assert report["crosstalk_deg"] == pytest.approx(report["hooke_deg"], abs=0.25)  # the form is first order
    assert report["gaze_deg"] == pytest.approx(report["play_deg"] + report["pupil_deg"], abs=0.015)  # each rounded


def test_the_gaze_gate_counts_each_pitch_pin_through_the_angle_its_link_meets_its_arm_at(report):
    """#967: a pin's play strays its link along its own line, so it turns the arm the link is on by more the further
    the two are from square. The leaned push-rod meets its lever at 50 to 75 deg, so the pitch's play is more than a
    square drive's (each pin's play over its arm), and the gaze gate holds with it."""
    from model import fits

    c = fits.CLEARANCE[0]
    square = math.hypot(math.degrees(2 * c / gimbal.CRANK), math.degrees(c * (2 / gimbal.BAIL_IN + 2 / gimbal.LEVER)))
    assert square * 1.1 < report["play_deg"] < gimbal.GAZE_DEG - report["pupil_deg"]


def test_the_gaze_gate_counts_the_pupils_seating_beside_the_play(report):
    """#650 (#51 perception [GH]): a pupil keyed with 0.3 mm of seat play strays 0.15 mm from its seat's centre, 0.24
    deg on Morty's 35.8 mm cap (#967); it can stray the way the play does, so the two add, and the total stays under 2
    deg."""
    assert report["pupil_deg"] == pytest.approx(0.25, abs=0.005)
    assert report["gaze_deg"] == pytest.approx(report["play_deg"] + 0.25, abs=0.015)
    assert report["gaze_deg"] <= gimbal.GAZE_DEG


def test_a_print_error_splits_the_eyes_a_little(report):
    assert 0 < report["vergence_deg"] < 0.5


def test_the_lids_shut_on_one_line_and_rest_open(report):
    """#967 (Cansin, 2026-11-28): the servo's range runs from the lids shut, both edges on one line 6.5 deg over the
    eye's middle, through its centre, the lids open, to 4.5 deg wider, the room the eye program's lid map keeps over
    its rest; no lid follows the pitch any more."""
    lid = report["lid"]
    assert lid["shut_deg"] == pytest.approx([gimbal.LID_SHUT, gimbal.LID_SHUT], abs=0.05) and gimbal.LID_SHUT == 6.5
    assert lid["edge_deg"] == pytest.approx([gimbal.LID_SHUT, gimbal.LID_REST + gimbal.LID_WIDE])
    assert lid["servo_deg"] == pytest.approx([-gimbal.UPPER_TRAVEL, gimbal.LID_WIDE])


def test_the_lower_lid_turns_against_the_upper_through_its_own_travel():
    """#698, #967: one servo drives both lids of an eye; as the upper lid turns its 76.8 deg down the lower turns its
    65.9 up (0.86 of it), all the way, and about half of it by half of the upper's."""
    shut = gimbal.LID_SHUT - gimbal.LID_REST
    assert gimbal.lower(0) == pytest.approx(0, abs=1e-9)
    assert gimbal.lower(shut) == pytest.approx(gimbal.LOWER_TRAVEL, abs=0.05)
    assert gimbal.lower(shut / 2) / gimbal.LOWER_TRAVEL == pytest.approx(0.5, abs=0.06)
    turns = [gimbal.lower(s) for s in np.linspace(shut, gimbal.LID_WIDE, 41)]
    assert all(np.diff(turns) < 0)  # the servo opening the upper lid opens the lower, all the way


@pytest.mark.parametrize("pitch", [-12, 14])
def test_at_yaw_0_every_part_turns_about_x(pitch):
    """#670: at yaw 0 every drive is planar across x, so each part turns about x alone, as the lid sweep's hinges do."""
    for name, m in gimbal.moved(-30, pitch).items():
        assert m[0, :3] == pytest.approx((1, 0, 0), abs=1e-9) and m[:3, 0] == pytest.approx((1, 0, 0), abs=1e-9), name


@pytest.mark.parametrize("lid", [-75, -36, 4])
@pytest.mark.parametrize("pitch", [-15, 0, 15])
def test_the_moved_parts_keep_their_pins_together(lid, pitch):
    """moved() carries each part the lid servos and the eyes' pitch move (#650): every pin two of them share lands on
    one point in both, so the sweep poses an assembly, not loose parts."""
    m = gimbal.moved(lid, pitch)
    c, (hy, hz) = gimbal.CRANK, gimbal.PITCH_HORN
    pins = [(("pitch horn:1", "pitch bar:1"), (0, hy + c, hz))]
    pins.append((("bail:1", "pitch bar:1"), (0, *gimbal.BAIL_TIP)))
    for s, (x, _, _) in gimbal.EYE.items():
        pins.append(((f"{s} upper lid:1", f"{s} lid bar:1"), (x, *gimbal.LID_PIN)))
        pins.append(((f"{s} lid horn:1", f"{s} lid link:1"), (x, *gimbal.LINK_PIN)))
        pins.append(((f"{s} lid link:1", f"{s} lower lid:1"), (x, *gimbal.LOWER_PIN)))
        pins.append(((f"{s} lid bar:1", f"{s} lid horn:1"), (x, *np.add(gimbal.LID_HORN, gimbal.LID_PIN))))
        pins.append(((f"{s} eyeball core:1", f"{s} push-rod:1"), (x, 0, gimbal.LEVER)))
        pins.append((("bail:1", f"{s} push-rod:1"), (x, *gimbal.BAIL_BALL)))
    for (a, b), p in pins:
        assert (m[a] @ [*p, 1]) == pytest.approx(m[b] @ [*p, 1], abs=1e-6), (a, b)


@pytest.mark.parametrize("yaw", [-25, 25])
@pytest.mark.parametrize("pitch", [-15, 15])
def test_a_yaw_keeps_the_tie_bar_and_the_push_rods_on_their_pins(yaw, pitch):
    """#656: with the eyes yawed the yaw horn, the tie-bar and the yokes turn together and each push-rod still meets its
    lever's ball and its bail arm's: the motion pictures pose an assembly."""
    m = gimbal.moved(0, pitch, yaw)
    c = gimbal.CRANK
    pins = [(("yaw horn:1", "tie-bar:1"), (0, gimbal.YAW_Y + c, 0))]
    for s, (x, _, _) in gimbal.EYE.items():
        pins.append(((f"{s} yaw yoke:1", "tie-bar:1"), (x, c, 0)))
        pins.append(((f"{s} eyeball core:1", f"{s} push-rod:1"), (x, 0, gimbal.LEVER)))
        pins.append((("bail:1", f"{s} push-rod:1"), (x, *gimbal.BAIL_BALL)))
    for (a, b), p in pins:
        assert (m[a] @ [*p, 1]) == pytest.approx(m[b] @ [*p, 1], abs=1e-6), (a, b)
    front = m["L eyeball core:1"] @ (gimbal.EYE["L"][0], -1, 0, 1)
    assert math.degrees(math.atan2(front[0] - gimbal.EYE["L"][0], -front[1])) == pytest.approx(yaw, abs=1e-3)


def test_each_lid_takes_its_own_servo():
    """A wink (#656): one eye's lids shut while the other's stay open."""
    m = gimbal.moved({"L": -21, "R": 0}, 0)
    edge = {s: m[f"{s} upper lid:1"] @ (x, -1, 0, 1) for s, (x, _, _) in gimbal.EYE.items()}
    assert [round(math.degrees(math.atan2(e[2], -e[1]))) for e in edge.values()] == [-21, 0]


def test_the_lid_and_the_eyes_turn_as_commanded():
    """The lid servo's degrees turn the upper lid's edge up by as many and the lower lid's down by lower(); the core
    takes the eyes' pitch up."""
    m = gimbal.moved(-12, 10)
    x = gimbal.EYE["L"][0]
    for part, turn in (("upper lid", -12), ("lower lid", gimbal.lower(-12))):
        edge = m[f"L {part}:1"] @ (x, -1, 0, 1)
        assert math.degrees(math.atan2(edge[2], -edge[1])) == pytest.approx(turn)
    assert gimbal.lower(-12) > 6  # shutting, the lower lid rises
    front = m["L eyeball core:1"] @ (x, -1, 0, 1)
    assert math.degrees(math.atan2(front[2], -front[1])) == pytest.approx(10, abs=1e-3)
