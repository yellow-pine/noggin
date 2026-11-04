"""Numerical fitting of public anatomical meshes; private reference meshes stay outside this module.

GX10: python -m model.skeleton.fit <public-bones.npz> <public-bones.json> <out-prefix>
Blender exports/applies this public exchange; the private reference never travels with it.
"""

import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy.interpolate import RBFInterpolator
from shapely.geometry import Polygon

REGIONS = {"Skull": "skull", "Mandible": "jaw", "Ribcage": "upper_chest"} | {f"C{i}": "cervicals" for i in range(1, 8)}


def _stretch_report(lengths, label):
    if not np.isfinite(lengths).all() or not lengths.size:
        raise ValueError(f"Invalid {label} measurement")
    low, high = float(lengths.min()), float(lengths.max())
    if low < 0.75 - 1e-6 or high > 1.25 + 1e-6:
        raise ValueError(f"{label} {low:.6f}..{high:.6f} exceeds confirmed 0.75..1.25")
    return {"minimum": low, "maximum": high}


def check_stretch(gradients, regional_scale):
    """Principal local lengths from ORIGINAL Basis, after only a declared regional UNIFORM resize."""
    if not np.isfinite(regional_scale) or regional_scale <= 0:
        raise ValueError("Declare a positive uniform anatomical-region size")
    if not np.isfinite(gradients).all() or (np.linalg.det(gradients) <= 0).any():
        raise ValueError("A local stretch mapping folds or has invalid gradients")
    return _stretch_report(np.linalg.svd(gradients, compute_uv=False) / regional_scale, "local stretch")


def check_surface_stretch(basis, final_sculpt, faces, regional_scale):
    """Exact triangle tangent lengths include every final Sculpt edit; no per-Bone fitted normalization."""
    source, target = np.asarray(basis)[faces], np.asarray(final_sculpt)[faces]
    a = np.stack((source[:, 1] - source[:, 0], source[:, 2] - source[:, 0]), axis=2)
    b = np.stack((target[:, 1] - target[:, 0], target[:, 2] - target[:, 0]), axis=2)
    _, r = np.linalg.qr(a)
    if (np.abs(np.linalg.det(r)) < 1e-12).any():
        raise ValueError("Original anatomical Basis has a degenerate triangle")
    tangent = b @ np.linalg.inv(r)
    return _stretch_report(np.linalg.svd(tangent, compute_uv=False) / regional_scale, "surface stretch")


def outer_cortex(mesh, targets, origin):
    """Source correspondence on the exterior cortex, even when the new envelope is inside the donor skull.

    The nearest surface can be the inner wall. Follow that anatomical radial direction through every source
    triangle and take its outermost positive crossing; never stretch the inner cortex onto the Skin target.
    """
    directions = np.asarray(targets) - origin
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    locations, rays, _ = mesh.ray.intersects_location(np.tile(origin, (len(targets), 1)), directions)
    result = []
    for i, direction in enumerate(directions):
        points = locations[rays == i]
        distances = (points - origin) @ direction
        if not len(distances) or distances.max() <= 0:
            raise ValueError(f"No exterior cranial cortex along source ray {i}")
        result.append(points[distances.argmax()])
    return np.array(result)


def warp(arrays, scene):
    """Fit all public raw bones in one world field, keeping each local Sculpt−Warp delta.

    Input/output are the public scene exchange, never a private reference mesh. Blender only applies the result;
    the numerical solve and its non-collapse gate run on GX10.
    """
    anatomical_regions = scene.get("anatomical_regions")
    if not anatomical_regions:
        raise ValueError("Declare uniform anatomical_regions from original Basis before warping")
    for bone in scene["bones"]:
        declared = anatomical_regions[REGIONS[bone["group"]]]
        matrix = np.asarray(declared["matrix"])
        if not np.allclose(np.linalg.svd(matrix[:3, :3], compute_uv=False), declared["scale"], rtol=1e-6):
            raise ValueError("An anatomical region resize must be uniform, not an inherited anisotropic affine")
        if not np.allclose(bone["matrix"], matrix, atol=1e-6):
            raise ValueError("Bones must share their declared anatomical region placement")
    pairs = list(scene["landmarks"].values())
    source, target = (np.array([p[k] for p in pairs]) for k in ("source", "target"))
    blend = scene.get("warp_blend")
    if blend:
        normal = np.asarray(blend["normal"])
        low, high = blend["low"], blend["high"]
        assert high > low and np.isfinite(normal).all()
        level = source @ normal
        regions = np.array([p.get("region", "shared") for p in pairs])
        assert set(regions) <= {"head", "body", "shared"}
        shared = (
            (regions == "shared") | ((regions == "body") & (level >= low)) | ((regions == "head") & (level <= high))
        )
        fields = {}
        for region in ("head", "body"):
            selected = shared | (regions == region)
            fields[region] = RBFInterpolator(source[selected], (target - source)[selected], kernel="thin_plate_spline")

        def field(points):
            t = np.clip((points @ normal - low) / (high - low), 0, 1)
            weight = (t**3 * (t * (6 * t - 15) + 10))[:, None]  # C2-smooth, including both ends
            return weight * fields["head"](points) + (1 - weight) * fields["body"](points)

    else:
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
    error = float(np.linalg.norm(source + field(source) - target, axis=1).max())
    if error > 1.0:
        raise ValueError(f"Bust warp misses an anatomical landmark by {error:.4f} mm")
    stretch, offset = {}, len(probes) - len(points) - len(source)
    for bone in scene["bones"]:
        key, matrix = bone["key"], np.asarray(bone["matrix"])
        scale = anatomical_regions[REGIONS[bone["group"]]]["scale"]
        n = len(arrays[key + "_basis"])
        gradient = (jac[offset : offset + n] + np.eye(3)) @ matrix[:3, :3]
        final = result[key + "_sculpt"] @ matrix[:3, :3].T + matrix[:3, 3]
        stretch[bone["name"]] = {
            "region": REGIONS[bone["group"]],
            "declared_uniform_scale": scale,
            "field": check_stretch(gradient, scale),
            "surface_including_sculpt": check_surface_stretch(
                arrays[key + "_basis"], final, arrays[key + "_faces"], scale
            ),
        }
        offset += n
    return result, {
        "min_jacobian": determinant,
        "landmark_error_mm": error,
        "regional_stretch": stretch,
    }


def regional_seed(arrays, scene, regions):
    """Place ORIGINAL connected Basis with four declared similarities, then the SAME bounded interactive solver.

    This seed has no residual shape field. Subsequent authored landmarks use warp(), with identical limits.
    Shared regions keep original internal joints; anatomical cross-region joint/containment acceptance is separate.
    """
    scene["anatomical_regions"] = regions
    scene.pop("warp_blend", None)
    scene["landmarks"] = {}
    world = []
    for bone in scene["bones"]:
        matrix = np.asarray(regions[REGIONS[bone["group"]]]["matrix"])
        bone["matrix"] = matrix.tolist()
        world.append(arrays[bone["key"] + "_basis"] @ matrix[:3, :3].T + matrix[:3, 3])
    points = np.vstack(world)
    for i, p in enumerate(
        np.array((x, y, z))
        for x in (points[:, 0].min(), points[:, 0].max())
        for y in (points[:, 1].min(), points[:, 1].max())
        for z in (points[:, 2].min(), points[:, 2].max())
    ):
        scene["landmarks"][f"LM regional frame {i}"] = {"source": p.tolist(), "target": p.tolist()}
    return warp(arrays, scene)


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
    # Keep only authored landmarks; generated poses/anchors are rebuilt from the ORIGINAL connected anatomy.
    generated = ("LM chest ", "LM canal ", "LM vault ", "LM correction ")
    scene["landmarks"] = {n: p for n, p in scene["landmarks"].items() if not n.startswith(generated)}
    for name, pair in scene["landmarks"].items():
        group = name.split()[1]
        if group == "frame":
            continue
        group = "Ribcage" if group == "ribcage" else group if group in original else "Skull"
        old = original[group]
        local = (np.array(pair["source"]) - old[:3, 3]) @ np.linalg.inv(old[:3, :3]).T
        pair["source"] = (local @ common[:3, :3].T + common[:3, 3]).tolist()
    legacy = ("LM ribcage anchor",) + tuple("LM C" + str(i) + " anchor" for i in range(1, 8))
    scene["landmarks"] = {n: p for n, p in scene["landmarks"].items() if not n.startswith(legacy)}
    # Every original bone uses the SAME pre-field transform. No independent cervical translations survive.
    chest = np.array(envelope["chest_frame"])

    def chest_target(point):
        at = point @ chest[:3, :3].T + chest[:3, 3]
        bottom_z, top_z = envelope["chest_forward"]["fade_z_mm"]
        t = np.clip((at[2] - bottom_z) / (top_z - bottom_z), 0, 1)
        at[1] -= envelope["chest_forward"]["offset_mm"] * t * t * (3 - 2 * t)
        return at

    chest_points = []
    for bone in scene["bones"]:
        bone["matrix"] = common.tolist()
        if bone["group"] == "Ribcage":
            p = np.asarray(arrays[bone["key"] + "_basis"])
            chest_points.append(p)
            scene["landmarks"]["LM chest " + bone["name"]] = {
                "source": (p.mean(0) @ common[:3, :3].T + common[:3, 3]).tolist(),
                "target": chest_target(p.mean(0)).tolist(),
                "region": "body",
            }
    points = np.vstack(chest_points)
    lo, hi = points.min(0), points.max(0)
    for i, p in enumerate(np.array((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])):
        scene["landmarks"][f"LM chest frame {i}"] = {
            "source": (p @ common[:3, :3].T + common[:3, 3]).tolist(),
            "target": chest_target(p).tolist(),
            "region": "body",
        }
    for name, source in canals.items():
        for offset in (-3.0, 0.0, 3.0):
            normal = (
                np.array((0, np.sin(np.deg2rad(15)), np.cos(np.deg2rad(15)))) if name == "C2" else np.array((0, 0, 1))
            )
            p = source + offset * normal
            fraction = (p[2] - canals["T1"][2]) / (canals["C1"][2] - canals["T1"][2])
            scene["landmarks"][f"LM canal {name} {offset:g}"] = {
                "source": p.tolist(),
                "target": (bottom + fraction * (top - bottom)).tolist(),
            }
    for side, x in (("L", 36.35), ("R", -36.35)):
        scene["landmarks"][f"LM {side} orbit"]["target"] = [x, -150.0, 177.0]
    target_canals = target
    # Replace the superseded adult-cap vault targets with one declared regional envelope target set.
    obsolete = {"vertex", "opisthocranion", "euryon", "forehead"}
    scene["landmarks"] = {n: p for n, p in scene["landmarks"].items() if not obsolete.intersection(n.split())}
    vault, reference_vault = [], []
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
        vault.append(
            trimesh.Trimesh(
                arrays[key + "_basis"] @ matrix[:3, :3].T + matrix[:3, 3], arrays[key + "_faces"], process=False
            )
        )
        reference_vault.append(
            trimesh.Trimesh(
                arrays[key + "_warp"] @ matrix[:3, :3].T + matrix[:3, 3], arrays[key + "_faces"], process=False
            )
        )
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
    vault = trimesh.util.concatenate(vault)
    reference = trimesh.util.concatenate(reference_vault)
    assert np.array_equal(vault.faces, reference.faces)
    # Correspond through the prior anatomical Warp: its raised brow must not collapse onto a raw radial latitude.
    exterior = outer_cortex(reference, np.array(target), np.array(envelope["origin"]))
    nearest, _, faces = trimesh.proximity.closest_point(reference, exterior)
    barycentric = trimesh.triangles.points_to_barycentric(reference.triangles[faces], nearest)
    source = np.einsum("ij,ijk->ik", barycentric, vault.triangles[faces])
    for i, (point, dest) in enumerate(zip(source, target)):
        scene["landmarks"][f"LM vault {i}"] = {"source": point.tolist(), "target": dest.tolist(), "region": "head"}
    scene["landmarks"].update(envelope["bone_landmarks"])
    menton = np.asarray(scene["landmarks"]["LM menton"]["source"])
    # The C1/menton plane keeps the jaw with the head; the whole cervical chain blends continuously down to T1.
    slope = (canals["C1"][2] - menton[2]) / (canals["C1"][1] - menton[1])
    normal = np.array((0, -slope, 1))
    scene["warp_blend"] = {
        "normal": normal.tolist(),
        "low": float(canals["T1"] @ normal),
        "high": float(canals["C1"] @ normal),
    }
    result, report = warp(arrays, scene)
    report["canal_targets_before_field"] = {n: c.tolist() for n, c in target_canals.items()}
    return result, report


if __name__ == "__main__":
    landmarks = sys.argv[1] == "--landmarks"
    path, metadata, out = sys.argv[2:] if landmarks else sys.argv[1:]
    scene = json.load(open(metadata))
    if landmarks:
        result, report = warp(np.load(path), scene)
    else:
        with open("model/skeleton/envelope.json") as f:
            envelope = json.load(f)
        result, report = refit(np.load(path), scene, envelope)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out + ".npz", **result)
    with open(out + ".json", "w") as f:
        json.dump(scene | {"fit_report": report}, f, indent=2)
    print(json.dumps(report, indent=2), flush=True)
