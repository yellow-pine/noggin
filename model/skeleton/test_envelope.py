"""Exact signed Skin distances retain real concave air grooves, regardless of face winding."""

import numpy as np
import pytest

from model.skeleton.envelope import Envelope


def test_exact_closed_surface_distance_keeps_a_concave_groove():
    # Extruded L: the missing upper-right square is true exterior air, not part of its convex hull.
    ring = np.array(((0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)))
    vertices = np.vstack([np.column_stack((ring, np.full(6, z))) for z in (0, 1)])
    cap = np.array(((0, 1, 3), (1, 2, 3), (0, 3, 5), (3, 4, 5)))
    sides = [(i, (i + 1) % 6, (i + 1) % 6 + 6) for i in range(6)]
    sides += [(i, (i + 1) % 6 + 6, i + 6) for i in range(6)]
    faces = np.vstack((cap[:, ::-1], cap + 6, sides))
    query = np.array(((0.5, 0.5, 0.5), (1.5, 1.5, 0.5), (0.25, 1.5, 0.5)))
    for triangles in (faces, faces[:, ::-1]):
        envelope = Envelope(vertices, triangles)
        assert envelope.distance(query) == pytest.approx((0.5, -0.5, 0.25), abs=1e-7)


def test_an_open_skin_cannot_silently_classify_points_as_inside():
    with pytest.raises(ValueError, match="closed"):
        Envelope(np.array(((0, 0, 0), (1, 0, 0), (0, 1, 0))), np.array(((0, 1, 2),)))
