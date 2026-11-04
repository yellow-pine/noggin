"""Numerical fitting of public anatomical meshes; private reference meshes stay outside this module.

GX10: python -m model.skeleton.fit <public-bones.npz> <public-bones.json> <out-prefix>
Blender exports/applies this public exchange; the private reference never travels with it.
"""

import json
import sys

import numpy as np
import trimesh
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
    probes = np.vstack((probes, points, source))
    jac = np.empty((len(probes), 3, 3))
    for i in range(3):
        step = np.eye(3)[i] * 0.5
        jac[:, :, i] = field(probes + step) - field(probes - step)
    determinants = np.linalg.det(jac + np.eye(3))
    determinant = float(determinants.min())
    if determinant <= 0.1:
        raise ValueError(
            f"Bust warp folds or collapses: least Jacobian {determinant:.4f} at {probes[determinants.argmin()]}"
        )
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


def refit(arrays, scene, envelope):
    """Register the true cervical canals in one skull-to-T1 frame and fit the vault to our coarse cage.

    The anatomical corridor is independent of the pan bearing. Its provisional C1 y=-73.4 and original T1 end
    preserve the accepted head interface while correcting the lateral-hole translations, not the bone order.
    """
    original = {b["group"]: np.array(b["matrix"]) for b in scene["bones"]}
    common = original["Skull"]
    canals, target = {}, {}
    for bone in scene["bones"]:
        name, key = bone["name"], bone["key"]
        if name not in {"C" + str(i) for i in range(1, 8)} | {"T1"}:
            continue
        normal = (0, np.sin(np.deg2rad(15)), np.cos(np.deg2rad(15))) if name == "C2" else (0, 0, 1)
        c = canal(trimesh.Trimesh(arrays[key + "_basis"], arrays[key + "_faces"]), normal)
        canals[name] = c @ common[:3, :3].T + common[:3, 3]
    top, bottom = (np.array(envelope["canal_ends"][n]) for n in ("C1", "T1"))
    for name, centre in canals.items():
        fraction = (centre[2] - canals["T1"][2]) / (canals["C1"][2] - canals["T1"][2])
        target[name] = bottom + fraction * (top - bottom)
    # Every original bone uses the SAME pre-field transform. No independent cervical translations survive.
    for bone in scene["bones"]:
        bone["matrix"] = common.tolist()
        if bone["group"] == "Ribcage":
            # Actual chest points constrain its affine fit; the old full-ribcage box alone left the upper chest loose.
            p = np.asarray(arrays[bone["key"] + "_basis"]).mean(axis=0)
            old = original["Ribcage"]
            scene["landmarks"]["LM chest " + bone["name"]] = {
                "source": (p @ old[:3, :3].T + old[:3, 3]).tolist(),
                "target": (p @ old[:3, :3].T + old[:3, 3]).tolist(),
            }
    for name, pair in scene["landmarks"].items():
        group = name.split()[1]
        if group == "frame":
            continue
        group = "Ribcage" if group in ("ribcage", "chest") else group if group in original else "Skull"
        old = original[group]
        local = (np.array(pair["source"]) - old[:3, 3]) @ np.linalg.inv(old[:3, :3]).T
        pair["source"] = (local @ common[:3, :3].T + common[:3, 3]).tolist()
    scene["landmarks"] = {
        n: p
        for n, p in scene["landmarks"].items()
        if not n.startswith(tuple("LM C" + str(i) + " anchor" for i in range(1, 8)))
    }
    for name, source in canals.items():
        scene["landmarks"]["LM canal " + name] = {"source": source.tolist(), "target": target[name].tolist()}
    target_canals = target
    # Replace the superseded adult-cap vault targets with one declared regional envelope target set.
    obsolete = {"vertex", "opisthocranion", "euryon", "forehead"}
    scene["landmarks"] = {n: p for n, p in scene["landmarks"].items() if not obsolete.intersection(n.split())}
    vault = []
    for bone in scene["bones"]:
        if bone["name"] not in {
            "frontal bone",
            "L parietal bone",
            "R parietal bone",
            "occipital bone",
            "L temporal bone",
            "R temporal bone",
        }:
            continue
        matrix, key = np.array(bone["matrix"]), bone["key"]
        vault.append(trimesh.Trimesh(arrays[key + "_basis"] @ matrix[:3, :3].T + matrix[:3, 3], arrays[key + "_faces"]))
    target = []
    for mark in envelope["landmarks"]:
        if any(
            mark["elevation"] == x["elevation"] and mark["azimuth"] in x["azimuths"]
            for x in envelope["excluded_openings"]
        ):
            continue
        a, e = np.deg2rad((mark["azimuth"], mark["elevation"]))
        direction = np.array((np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)))
        target.append(np.array(envelope["origin"]) + direction * (mark["outer_radius_mm"] - envelope["inset_mm"]))
    nearest = trimesh.proximity.closest_point_naive(trimesh.util.concatenate(vault), np.array(target))[0]
    for i, (source, dest) in enumerate(zip(nearest, target)):
        scene["landmarks"][f"LM vault {i}"] = {"source": source.tolist(), "target": dest.tolist()}
    result, report = warp(arrays, scene)
    report["canal_targets_before_field"] = {n: c.tolist() for n, c in target_canals.items()}
    return result, report


if __name__ == "__main__":
    path, metadata, out = sys.argv[1:]
    scene = json.load(open(metadata))
    with open("model/skeleton/envelope.json") as f:
        envelope = json.load(f)
    result, report = refit(np.load(path), scene, envelope)
    np.savez_compressed(out + ".npz", **result)
    with open(out + ".json", "w") as f:
        json.dump(scene | {"fit_report": report}, f, indent=2)
    print(json.dumps(report, indent=2), flush=True)
