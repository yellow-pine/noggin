"""Numerical fitting of public anatomical meshes; private reference meshes stay outside this module."""

import numpy as np
from shapely.geometry import Polygon


def canal(mesh):
    """The main neural passage at mid-height in the source's anatomical XYZ frame (mm).

    Actual triangle sections preserve an oblique canal which a whole-bone plan projection can close.
    The neural passage is the largest enclosed opening near the midsagittal plane, not a lateral foramen.
    An absent enclosed passage is an error: a vertex mean is not an anatomical landmark.
    """
    lo, hi = mesh.bounds
    z = (lo[2] + hi[2]) / 2
    section = mesh.section(plane_origin=(0, 0, z), plane_normal=(0, 0, 1))
    if section is None:
        raise ValueError("No axial section through the vertebra")
    loops = [Polygon(p[:, :2]) for p in section.discrete if len(p) >= 4 and np.allclose(p[0], p[-1])]
    loops = [p for p in loops if p.is_valid and p.area > 0]
    holes = [p for p in loops if sum(q.contains(p) for q in loops if q is not p) % 2]
    mid = (lo[0] + hi[0]) / 2
    central = [p for p in holes if abs(p.centroid.x - mid) < (hi[0] - lo[0]) / 6]
    if not central:
        raise ValueError("No enclosed central neural passage at vertebral mid-height")
    centre = max(central, key=lambda p: p.area).centroid
    return np.array((centre.x, centre.y, z))
