"""PROTOTYPE (#872): Re-warp. One thin-plate-spline field (scipy RBFInterpolator) from the landmark empties, written
into every bone's "Warp" shape key; Cansin's "Sculpt" key, relative to Warp, keeps its deltas through a re-warp.

A landmark is an empty "LM <name>" (on the source anatomy, parented to its bone group's pose empty) and its target
"LM <name> target" (free). An "LM frame ..." empty with no target is a fixed point (source = target), against folds and
extrapolation. Run from Blender's Text editor (Blender started with --python-use-system-env and PYTHONPATH on the
repo's .blender-site, for scipy), or import and call rewarp()."""

import bpy
import numpy as np
from scipy.interpolate import RBFInterpolator

LANDMARKS, SKELETON = "Landmarks", "Skeleton"


def _pairs(verbose=False):
    src, dst = [], []
    for ob in bpy.data.collections[LANDMARKS].all_objects:
        if ob.name.endswith(" target"):
            continue
        target = bpy.data.objects.get(ob.name + " target", ob)
        src.append(ob.matrix_world.translation[:])
        dst.append(target.matrix_world.translation[:])
        if verbose:
            a, b = np.array(src[-1]), np.array(dst[-1])
            print(f"  {ob.name:34s} {np.round(a, 1)} -> {np.round(b, 1)}  |d| {np.linalg.norm(b - a):6.1f}")
    return np.array(src), np.array(dst)


def _co(key, n):
    out = np.empty(n * 3)
    key.data.foreach_get("co", out)
    return out.reshape(n, 3)


def _bones():
    return [ob for ob in bpy.data.collections[SKELETON].all_objects if ob.type == "MESH"]


def field(verbose=False):
    src, dst = _pairs(verbose)
    return RBFInterpolator(src, dst - src, kernel="thin_plate_spline"), src, dst


def min_jacobian(rbf, lo, hi, n=14, h=0.5):
    """The warp's least Jacobian determinant over an n^3 grid in (lo, hi): <= 0 folds, near 0 collapses."""
    axes = [np.linspace(a, b, n) for a, b in zip(lo, hi)]
    p = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    jac = np.empty((len(p), 3, 3))
    for i in range(3):
        d = np.zeros(3)
        d[i] = h
        jac[:, :, i] = (rbf(p + d) - rbf(p - d)) / (2 * h)
    jac += np.eye(3)
    det = np.linalg.det(jac)
    print(f"  least Jacobian {det.min():.3f} at {np.round(p[det.argmin()], 1)}")
    return float(det.min())


def rewarp():
    rbf, src, dst = field(verbose=True)
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for ob in _bones():
        me, n = ob.data, len(ob.data.vertices)
        if me.shape_keys is None:
            ob.shape_key_add(name="Basis", from_mix=False)
        keys = me.shape_keys.key_blocks
        basis = _co(keys["Basis"], n)
        warp = keys.get("Warp") or ob.shape_key_add(name="Warp", from_mix=False)
        sculpt = keys.get("Sculpt")
        delta = _co(sculpt, n) - _co(warp, n) if sculpt else np.zeros((n, 3))
        m = np.array(ob.matrix_world)
        world = basis @ m[:3, :3].T + m[:3, 3]
        lo, hi = np.minimum(lo, world.min(0)), np.maximum(hi, world.max(0))
        moved = world + rbf(world)
        local = (moved - m[:3, 3]) @ np.linalg.inv(m[:3, :3]).T
        warp.data.foreach_set("co", local.ravel())
        if sculpt is None:
            sculpt = ob.shape_key_add(name="Sculpt", from_mix=False)
        sculpt.relative_key = warp
        sculpt.data.foreach_set("co", (local + delta).ravel())
        warp.value = sculpt.value = 1.0
        me.update()
    det = min_jacobian(rbf, lo, hi)
    err = float(np.abs(src + rbf(src) - dst).max())
    scene = bpy.context.scene
    scene["warp_min_jacobian"], scene["warp_landmark_err_mm"] = det, err
    print(f"Re-warp: {len(src)} landmarks, residual {err:.2e} mm, least Jacobian {det:.3f}")
    return det, err


if __name__ == "__main__":
    rewarp()
