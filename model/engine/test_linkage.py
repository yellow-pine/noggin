"""Seam: the planar four-bar solver, on a textbook linkage and on the eyes' recorded transmission curves."""

import json
import math
import os

import pytest

from model import geometry as g
from model.engine import linkage

REPORTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")


def test_parallelogram_rocker_follows_the_crank():
    # crank 1 pointing +Z at neutral, coupler 4 along +Y, rocker 1: a parallelogram, so the rocker copies the crank
    solve = linkage.four_bar(o2=(0, 0, 0), a0=(0, 0, 1), o4=(0, 4, 0), b0=(0, 4, 1), axis=(1, 0, 0))
    for deg in (-60, -10, 0, 25, 80):
        rocker, a, b = solve(deg)
        assert rocker == pytest.approx(deg, abs=1e-6)
        assert a == pytest.approx((0, -math.sin(math.radians(deg)), math.cos(math.radians(deg))), abs=1e-9)


def test_crank_rocker_worked_example_picks_the_neutral_assembly_mode():
    # Crank 1 at (0,0), coupler 3.5, rocker 3 about (4,0); at crank 0 the upper mode puts B at (3.0417, 2.843): rocker 108.6 deg.
    b0 = (3.0417, 2.843, 0)
    solve = linkage.four_bar((0, 0, 0), (1, 0, 0), (4, 0, 0), b0, axis=(0, 0, 1))
    rocker, a, b = solve(0)
    assert rocker == pytest.approx(0, abs=1e-6) and b == pytest.approx(b0, abs=2e-4)
    assert linkage.rocker_angle(solve, 0, absolute=True) == pytest.approx(108.6, abs=0.05)
    rocker, a, b = solve(90)
    assert b[1] > 0  # still the upper mode
    assert math.dist(a, b) == pytest.approx(3.5, rel=1e-3) and math.dist(b, (4, 0, 0)) == pytest.approx(3.0, rel=1e-3)


def test_unreachable_crank_angle_raises():
    solve = linkage.four_bar(
        (0, 0, 0), (1, 0, 0), (10, 0, 0), (10, 1, 0), axis=(0, 0, 1)
    )  # coupler 9.06 + rocker 1 < the 11 mm reach at 180
    with pytest.raises(linkage.Unreachable):
        solve(180)


def lid_loop(key):
    """The L lid four-bar from geometry.py: horn pivot -> horn pin (12.75 along +Y), bar to the lid pin, lid about the eye."""
    spec = g.LID_LINKS[key]
    o2 = g.PIVOTS["l_lid_horn"]["point"]
    a0 = (spec["x"], o2[1] + g.HORN_STEP["pin"], o2[2])
    b0 = (spec["x"],) + g.LID_PINS[spec["lid"]][1:]
    return linkage.four_bar(o2, a0, g.EYE_L, b0, axis=g.X)


@pytest.mark.parametrize("key, joint", [("eyelid_bar", "L inside lid pivot"), ("eyelid_crank", "L outside lid pivot")])
def test_lid_linkage_matches_the_recorded_fusion_curve(key, joint):
    curves = json.load(open(os.path.join(REPORTS, "noggin-eyes-report.json")))["curves"]["L lid horn (inferred)"][joint]
    solve = lid_loop(key)
    for horn_deg, lid_deg in curves:
        assert solve(horn_deg)[0] == pytest.approx(lid_deg, abs=1.0), (horn_deg, lid_deg)


def test_eyeball_linkage_matches_the_recorded_fusion_curve():
    curves = json.load(open(os.path.join(REPORTS, "noggin-eyes-report.json")))["curves"]["L eye horn (inferred)"][
        "L eyeball pivot"
    ]
    arm_end, eye_end = g.EYEBALL_BAR_PINS
    solve = linkage.four_bar(g.PIVOTS["l_eye_horn"]["point"], arm_end, g.EYE_L, eye_end, axis=g.Y)
    for horn_deg, eye_deg in curves:
        assert solve(horn_deg)[0] == pytest.approx(eye_deg, abs=1.0), (horn_deg, eye_deg)
