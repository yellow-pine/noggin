"""Numerical fitting of public anatomical meshes; private reference meshes stay outside this module."""

import numpy as np
from shapely.geometry import Polygon


def canal(mesh, normal=(0, 0, 1)):
    """The main neural passage near mid-height in the source's anatomical XYZ frame (mm).

    Actual triangle sections preserve an oblique canal which a whole-bone plan projection can close.
    The neural passage is the largest enclosed opening near the midsagittal plane, not a lateral foramen.
    `normal` follows the annotated anatomical passage (the axis's arch slopes beneath its dens).
    An absent enclosed passage with room for the 6 mm wire path is an error, never a vertex-mean fallback.
    """
    lo, hi = mesh.bounds
    mid = (lo[0] + hi[0]) / 2
    for fraction in sorted(np.linspace(0.1, 0.9, 17), key=lambda f: abs(f - 0.5)):
        origin = (lo + hi) / 2
        origin[2] = lo[2] + fraction * (hi[2] - lo[2])
        section = mesh.section(plane_origin=origin, plane_normal=normal)
        if section is None:
            continue
        loops = [Polygon(p[:, :2]) for p in section.discrete if len(p) >= 4 and np.allclose(p[0], p[-1])]
        loops = [p for p in loops if p.is_valid and p.area > 0]
        holes = [p for p in loops if sum(q.contains(p) for q in loops if q is not p) % 2]
        central = [
            p for p in holes if abs(p.centroid.x - mid) < (hi[0] - lo[0]) / 6 and p.contains(p.centroid.buffer(3))
        ]
        if central:
            c = max(central, key=lambda p: p.area).centroid
            xy = np.array((c.x, c.y))
            z = origin[2] - np.dot(np.asarray(normal)[:2], xy - origin[:2]) / normal[2]
            return np.array((c.x, c.y, z))
    raise ValueError("No enclosed central neural passage for the 6 mm wire path")
