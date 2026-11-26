"""In Blender, on the Skeleton scene (docs/adr/0025): the Warp re-run. One thin-plate-spline field (scipy's
RBFInterpolator) from the Landmarks, written into every bone's Warp shape key; the Sculpt key over it, Cansin's hand
edits, keeps its deltas through a re-warp. `just rewarp` runs it and saves the scene; scipy comes from the repo's
gitignored .blender-site (`just blender-site`), never from Blender.app.

A Landmark is an empty "LM <name>" on the anatomy and its target "LM <name> target"; an "LM frame ..." empty with no
target is a fixed point (source = target), against folds and extrapolation."""

import bpy
import numpy as np
from scipy.interpolate import RBFInterpolator

LANDMARKS, SKULL = "Landmarks", "Skull"


def _pairs():
    src, dst = [], []
    for ob in bpy.data.collections[LANDMARKS].all_objects:
        if not ob.name.endswith(" target"):
            src.append(ob.matrix_world.translation[:])
            dst.append(bpy.data.objects.get(ob.name + " target", ob).matrix_world.translation[:])
    return np.array(src), np.array(dst)


def _co(key, n):
    out = np.empty(n * 3)
    key.data.foreach_get("co", out)
    return out.reshape(n, 3)


def min_jacobian(rbf, lo, hi, n=14, h=0.5):
    """The warp's least Jacobian determinant over an n^3 grid in (lo, hi): <= 0 folds, near 0 collapses."""
    p = np.stack(np.meshgrid(*[np.linspace(a, b, n) for a, b in zip(lo, hi)], indexing="ij"), -1).reshape(-1, 3)
    jac = np.empty((len(p), 3, 3))
    for i in range(3):
        d = np.zeros(3)
        d[i] = h
        jac[:, :, i] = (rbf(p + d) - rbf(p - d)) / (2 * h)
    return float(np.linalg.det(jac + np.eye(3)).min())


def rewarp():
    src, dst = _pairs()
    rbf = RBFInterpolator(src, dst - src, kernel="thin_plate_spline")
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for ob in bpy.data.collections[SKULL].all_objects:
        me, n = ob.data, len(ob.data.vertices)
        keys = me.shape_keys.key_blocks
        warp, sculpt = keys["Warp"], keys["Sculpt"]
        delta = _co(sculpt, n) - _co(warp, n)
        m = np.array(ob.matrix_world)
        world = _co(keys["Basis"], n) @ m[:3, :3].T + m[:3, 3]
        lo, hi = np.minimum(lo, world.min(0)), np.maximum(hi, world.max(0))
        local = (world + rbf(world) - m[:3, 3]) @ np.linalg.inv(m[:3, :3]).T
        warp.data.foreach_set("co", local.ravel())
        sculpt.data.foreach_set("co", (local + delta).ravel())
        me.update()
    det, err = min_jacobian(rbf, lo, hi), float(np.abs(src + rbf(src) - dst).max())
    print(f"rewarp: {len(src)} landmarks, residual {err:.2e} mm, least Jacobian {det:.3f}", flush=True)
    return det, err


if __name__ == "__main__":
    rewarp()
    bpy.ops.wm.save_mainfile(compress=True)
