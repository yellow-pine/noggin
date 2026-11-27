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
