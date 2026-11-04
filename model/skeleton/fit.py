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


def canal(mesh, normal=(0, 0, 1), details=False):
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
            hole = max(central, key=lambda p: p.area)
            c = hole.centroid
            xy = np.array((c.x, c.y))
            z = origin[2] - np.dot(np.asarray(normal)[:2], xy - origin[:2]) / normal[2]
            centre = np.array((c.x, c.y, z))
            return {"centre": centre.tolist(), "clear_radius_xy_mm": hole.exterior.distance(c)} if details else centre
    raise ValueError("No enclosed central neural passage for the 6 mm wire path")


def original_facts(arrays, scene):
    """Dimensions and actual main canal sections in ORIGINAL BodyParts coordinates, before ANY prototype affine."""
    points = {}
    out = {"regions": {}, "canals": {}, "landmarks": {}}
    for bone in scene["bones"]:
        p, key = arrays[bone["key"] + "_basis"], bone["key"]
        points.setdefault(REGIONS[bone["group"]], []).append(p)
        if bone["name"] in {f"C{i}" for i in range(1, 8)} | {"T1"}:
            normal = (0, np.sin(np.deg2rad(15)), np.cos(np.deg2rad(15))) if bone["name"] == "C2" else (0, 0, 1)
            out["canals"][bone["name"]] = canal(trimesh.Trimesh(p, arrays[key + "_faces"]), normal, details=True)
    for name, members in points.items():
        p = np.vstack(members)
        out["regions"][name] = {"bounds": [p.min(0).tolist(), p.max(0).tolist()], "spans": np.ptp(p, axis=0).tolist()}
    matrices = {b["group"]: np.asarray(b["matrix"]) for b in scene["bones"]}
    for name in ("LM L orbit", "LM R orbit", "LM L condyle", "LM R condyle", "LM menton"):
        matrix = matrices["Mandible" if "condyle" in name or "menton" in name else "Skull"]
        out["landmarks"][name] = (
            (np.asarray(scene["landmarks"][name]["source"]) - matrix[:3, 3]) @ np.linalg.inv(matrix[:3, :3]).T
        ).tolist()
    return out


def refit(arrays, scene, envelope):
    """Original anatomy, four declared uniform regions, then one bounded residual field.

    The similarity sizes are chosen BEFORE shape deformation from fixed eye/C0 anchors and measured Skin room.
    Original cervical curvature is retained; no independent Bone poses or interpolated C2-C7 targets are used.
    """
    import copy

    historical = copy.deepcopy(scene["landmarks"])
    facts = original_facts(arrays, scene)
    eye_l, eye_r = (np.array(facts["landmarks"][f"LM {side} orbit"]) for side in ("L", "R"))
    c1, t1 = (np.array(facts["canals"][name]["centre"]) for name in ("C1", "T1"))
    fixed_c0 = np.array(envelope["canal_ends"]["C1"])
    fixed_t1 = np.array(envelope["canal_ends"]["T1"])
    source = np.array((eye_l, eye_r, c1))
    target = np.array(((36.35, -150, 177), (-36.35, -150, 177), fixed_c0))
    a, b = source - source.mean(0), target - target.mean(0)
    u, _, vh = np.linalg.svd(a.T @ b)
    rotation = vh.T @ np.diag((1, 1, np.linalg.det(vh.T @ u.T))) @ u.T
    ratios = [
        np.linalg.norm(target[i] - target[j]) / np.linalg.norm(source[i] - source[j])
        for i, j in ((0, 1), (0, 2), (1, 2))
    ]
    head_scale = float(np.sqrt(min(ratios) * max(ratios)))

    def matrix(scale, rotate, point, dest):
        m = np.eye(4)
        m[:3, :3] = scale * rotate
        m[:3, 3] = dest - scale * rotate @ point
        return m

    head = matrix(head_scale, rotation, source.mean(0), target.mean(0))
    shared_c1 = head[:3, :3] @ c1 + head[:3, 3]
    # Match two shared endpoints without straightening the original curve between them.
    z = (c1 - t1) / np.linalg.norm(c1 - t1)
    wanted = (shared_c1 - fixed_t1) / np.linalg.norm(shared_c1 - fixed_t1)

    def frame(axis):
        x = np.array((1.0, 0, 0))
        x -= axis * np.dot(x, axis)
        x /= np.linalg.norm(x)
        return np.column_stack((x, np.cross(axis, x), axis))

    neck_rotation = frame(wanted) @ frame(z).T
    neck_scale = float(np.linalg.norm(shared_c1 - fixed_t1) / np.linalg.norm(c1 - t1))
    neck = matrix(neck_scale, neck_rotation, c1, shared_c1)
    chest_points = np.vstack([arrays[b["key"] + "_basis"] for b in scene["bones"] if b["group"] == "Ribcage"])
    raw_width = envelope["regional_room"]["upper_chest_outer_width_mm"] - 2 * envelope["inset_mm"]
    chest_scale = float(raw_width / np.ptp(chest_points @ neck_rotation.T, axis=0)[0])
    chest = matrix(chest_scale, neck_rotation, t1, fixed_t1)
    regions = {
        name: {"scale": scale, "matrix": m.tolist()}
        for name, scale, m in (
            ("skull", head_scale, head),
            ("jaw", head_scale, head),
            ("cervicals", neck_scale, neck),
            ("upper_chest", chest_scale, chest),
        )
    }
    regional_seed(arrays, scene, regions)
    scene["original_anatomical_landmarks"] = historical
    constraints = {}

    def anchor(name, native, region, dest):
        m = np.array(regions[region]["matrix"])
        p = m[:3, :3] @ native + m[:3, 3]
        scene["landmarks"][name] = {"source": p.tolist(), "target": np.asarray(dest).tolist()}
        constraints[name] = {
            "source_native": np.asarray(native).tolist(),
            "region": region,
            "target": np.asarray(dest).tolist(),
        }

    anchor("LM fixed L orbit", eye_l, "skull", target[0])
    anchor("LM fixed R orbit", eye_r, "skull", target[1])
    anchor("LM shared C1 canal", c1, "cervicals", fixed_c0)
    anchor("LM shared T1 canal", t1, "upper_chest", fixed_t1)
    # Original chest shape takes priority over filling the cavity. Hold its uniformly fitted corners, not old warps.
    chest_world = chest_points @ chest[:3, :3].T + chest[:3, 3]
    lo, hi = chest_world.min(0), chest_world.max(0)
    for i, p in enumerate(np.array((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])):
        scene["landmarks"][f"LM chest room {i}"] = {"source": p.tolist(), "target": p.tolist()}
    skull_bones = [b for b in scene["bones"] if b["group"] == "Skull"]
    crown = max((p for b in skull_bones for p in arrays[b["key"] + "_basis"]), key=lambda p: p[2])
    crown_world = head[:3, :3] @ crown + head[:3, 3]
    crown_target = crown_world.copy()
    crown_target[2] = min(crown_target[2], envelope["regional_room"]["head_outer_top_mm"] - envelope["inset_mm"])
    anchor("LM crown containment", crown, "skull", crown_target)
    scene["anatomical_constraints"] = constraints
    result, report = warp(arrays, scene)
    report["declared_regional_sizes"] = {name: r["scale"] for name, r in regions.items()}
    report["landmark_scope"] = (
        "Sparse eye/C1-canal/T1/crown constraints; full anatomical joint/facet registration UNVERIFIED"
    )
    report["pending_acceptance"] = [
        "actual skull-base/C1 and C7/T1 joint faces",
        "finished walls/containment",
        "8mm hardware wire corridor",
        "actual978 mechanism",
        "full motion/print/worn gates",
    ]
    report["actual_canals_after_sculpt"] = {}
    for bone in scene["bones"]:
        if bone["name"] not in facts["canals"]:
            continue
        m = np.array(bone["matrix"])
        key = bone["key"]
        p = result[key + "_sculpt"] @ m[:3, :3].T + m[:3, 3]
        source_normal = (
            np.array((0, np.sin(np.deg2rad(15)), np.cos(np.deg2rad(15))))
            if bone["name"] == "C2"
            else np.array((0, 0, 1))
        )
        normal = m[:3, :3] @ source_normal
        normal /= np.linalg.norm(normal)
        try:
            report["actual_canals_after_sculpt"][bone["name"]] = canal(
                trimesh.Trimesh(p, arrays[key + "_faces"]), normal, details=True
            )
        except ValueError as e:
            report["actual_canals_after_sculpt"][bone["name"]] = {"error": str(e)}
    return result, report


if __name__ == "__main__":
    if sys.argv[1] == "--facts":
        print(json.dumps(original_facts(np.load(sys.argv[2]), json.load(open(sys.argv[3]))), indent=2))
        sys.exit()
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
