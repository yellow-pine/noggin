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
    assert report["gaze_deg"] == pytest.approx(report["play_deg"], abs=0.01)


def test_a_print_error_splits_the_eyes_a_little(report):
    assert 0 < report["vergence_deg"] < 0.5


def test_the_lid_covers_the_cap_closed_and_tracks_the_pitch_open(report):
    """Closed, the lid's edge is past the cap's rim; open, it sits over the pupil at full pitch up (#51 lid = rest +
    pitch): the range runs from one to the other."""
    closed, opened = report["lid"]["edge_deg"]
    assert closed < -gimbal.CAP_HALF and opened == pytest.approx(gimbal.PUPIL_DEG + 2 + gimbal.PITCH)
