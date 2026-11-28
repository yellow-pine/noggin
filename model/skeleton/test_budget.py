"""Confirmed exceptions stay on ORIGINAL anatomical zones, never on optimizer-selected vertices."""

import numpy as np
import pytest

from model.skeleton import budget, fit

REFERENCE = {
    "c0": [0, 0, 0],
    "eyes": [[-30, -100, 100], [30, -100, 100]],
    "condyles": [[-40, 10, 20], [40, 10, 20]],
}


def test_only_posterior_inferior_cranium_gets_smooth_exception():
    points = np.array(((0, 100, 100), (0, -110, 100), (0, 0, 0), (40, 10, 20), (0, 10, 100)), float)
    caps = budget.caps("L parietal bone", points, REFERENCE)
    assert caps == pytest.approx((1.5, 1.25, 1.25, 1.25, 1.375))
    for protected in ("frontal bone", "mandible", "C5", "L rib 1"):
        assert budget.caps(protected, points, REFERENCE) == pytest.approx(np.full(5, 1.25))


def test_growth_exception_never_relaxes_compression_or_other_vertices():
    fit.stretch(np.array([np.diag((1.4, 1, 1))]), np.array((1.5,)))
    with pytest.raises(ValueError, match="local stretch"):
        fit.stretch(np.array([np.diag((0.74, 1, 1))]), np.array((1.5,)))
    with pytest.raises(ValueError, match="local stretch"):
        fit.stretch(np.array([np.diag((1.4, 1, 1))] * 2), np.array((1.5, 1.25)))


def test_only_c5_behind_its_canal_and_c6_round_it_may_be_slimmed_past_the_floor():
    """Cansin, 2026-11-27 (#893's third round): the neck's skin rides the head and its rim swings through C5 and C6,
    so those two alone may be squashed to budget.SLIM, each beyond 8 mm from its canal's middle on the original
    anatomy: C6 all round, C5 from its canal's middle back and beside it (none of it straight ahead)."""
    canal = np.array((0.0, 10.0))
    points = np.array(((0, 10, 0), (0, 30, 0), (0, -10, 0), (20, 10, 3), (0, 17, 0)), float)  # y: canal, behind, front
    assert budget.floors("c5", points, canal) == pytest.approx((0.75, budget.SLIM, 0.75, budget.SLIM, 0.75))
    assert budget.floors("c6", points, canal) == pytest.approx((0.75, budget.SLIM, budget.SLIM, budget.SLIM, 0.75))
    for whole in ("atlas", "axis", "c3", "c4", "c7", "mandible", "occipital bone"):
        assert budget.floors(whole, points, canal) == pytest.approx(np.full(5, 0.75))
    assert 0 < budget.SLIM < 0.75


def test_a_slimmed_zone_is_drawn_in_toward_its_canal_and_nothing_else_moves():
    """At a factor of 0.4 a point 28 mm behind C6's canal ends 17.2 mm behind it (8 kept, 20 taken to 8, and 1.2 of
    easing), at its own height; one within 8 mm stays; C5's bone in front of its canal stays, and so does every
    vertex of a vertebra with no zone."""
    canal = np.array((0.0, 10.0))
    points = np.array(((0, 38, 5), (0, 16, 5), (0, -18, 5), (28, 10, -3)), float)
    assert budget.slim("c6", points, canal, 0.4) == pytest.approx(
        np.array(((0, 27.2, 5), (0, 16, 5), (0, -7.2, 5), (17.2, 10, -3))), abs=0.01
    )
    assert budget.slim("c5", points, canal, 0.4) == pytest.approx(
        np.array(((0, 27.2, 5), (0, 16, 5), (0, -18, 5), (17.2, 10, -3))), abs=0.01
    )
    assert budget.slim("c4", points, canal, 0.4) == pytest.approx(points)
    assert budget.slim("c6", points, canal, 1.0) == pytest.approx(points)
