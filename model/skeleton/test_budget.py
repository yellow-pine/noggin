"""Confirmed exceptions stay on ORIGINAL anatomical zones, never on optimizer-selected vertices."""

import numpy as np
import pytest
import trimesh

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
    for protected in ("frontal bone", "mandible", "C5", "T1", "body of sternum", "L scapula", "L clavicle"):
        assert budget.caps(protected, points, REFERENCE) == pytest.approx(np.full(5, 1.25))


def test_ribs_and_cartilage_protect_spinal_sternal_attachments():
    support = trimesh.creation.box(extents=(2, 2, 2))
    points = np.array(((0, 0, 1), (0, 0, 100)), float)
    for name in ("L rib 1", "R costal cartilage 4"):
        assert budget.caps(name, points, REFERENCE, support) == pytest.approx((1.25, 1.5))
    with pytest.raises(ValueError, match="original support"):
        budget.caps("L rib 1", points, REFERENCE)


def test_growth_exception_never_relaxes_compression_or_other_vertices():
    fit.check_stretch(np.array([np.diag((1.4, 1, 1))]), 1.0, maximum=np.array((1.5,)))
    with pytest.raises(ValueError, match="local stretch"):
        fit.check_stretch(np.array([np.diag((0.74, 1, 1))]), 1.0, maximum=np.array((1.5,)))
    with pytest.raises(ValueError, match="local stretch"):
        fit.check_stretch(np.array([np.diag((1.4, 1, 1))] * 2), 1.0, maximum=np.array((1.5, 1.25)))


def test_a_triangle_touching_a_protected_vertex_keeps_the_default_limit():
    points = np.array(((0, 0, 0), (1, 0, 0), (0, 1, 0)), float)
    final = points * (1.4, 1, 1)
    with pytest.raises(ValueError, match="surface stretch"):
        fit.check_surface_stretch(points, final, np.array(((0, 1, 2),)), 1, maximum=np.array((1.5, 1.25, 1.5)))
