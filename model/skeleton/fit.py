"""Numerical fitting of public anatomical meshes; private reference meshes stay outside this module."""

import numpy as np
from scipy.interpolate import RBFInterpolator
from shapely.geometry import Polygon


def warp(arrays, scene):
    """Fit all public raw bones in one world field, keeping each local Sculpt−Warp delta.

    Input/output are the public scene exchange, never a private reference mesh. Blender only applies the result;
    the numerical solve and its non-collapse gate run on GX10.
    """
    pairs = list(scene["landmarks"].values())
    source, target = (np.array([p[k] for p in pairs]) for k in ("source", "target"))
    field = RBFInterpolator(source, target - source, kernel="thin_plate_spline")
    result, world = {}, []
    for bone in scene["bones"]:
        key, matrix = bone["key"], np.asarray(bone["matrix"])
        points = arrays[key + "_basis"] @ matrix[:3, :3].T + matrix[:3, 3]
        world.append(points)
        local = (points + field(points) - matrix[:3, 3]) @ np.linalg.inv(matrix[:3, :3]).T
        result[key + "_warp"] = local
        result[key + "_sculpt"] = local + arrays[key + "_sculpt"] - arrays[key + "_warp"]
    points = np.vstack(world)
    probes = np.stack(
        np.meshgrid(*[np.linspace(a, b, 14) for a, b in zip(points.min(0), points.max(0))], indexing="ij"), -1
    ).reshape(-1, 3)
    jac = np.empty((len(probes), 3, 3))
    for i in range(3):
        step = np.eye(3)[i] * 0.5
        jac[:, :, i] = field(probes + step) - field(probes - step)
    determinant = float(np.linalg.det(jac + np.eye(3)).min())
    if determinant <= 0.1:
        raise ValueError(f"Bust warp folds or collapses: least Jacobian {determinant:.4f}")
    return result, {
        "min_jacobian": determinant,
        "landmark_error_mm": float(np.linalg.norm(source + field(source) - target, axis=1).max()),
    }


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
