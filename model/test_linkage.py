"""Seam: the planar four-bar solver, on textbook linkages."""

import math

import pytest

from model import linkage


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
