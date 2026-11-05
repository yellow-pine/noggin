"""Numerical fitting of public anatomical meshes; private reference meshes stay outside this module.

GX10: python -m model.skeleton.fit <public-bones.npz> <public-bones.json> <out-prefix>
Blender exports/applies this public exchange; the private reference never travels with it.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, cast

import numpy as np
import trimesh
from numpy.typing import ArrayLike
from scipy.interpolate import RBFInterpolator
from scipy.optimize import Bounds, NonlinearConstraint, minimize
from shapely.geometry import Point, Polygon

from model.skeleton import budget, deformation, refine
from model.skeleton.envelope import Envelope

REGIONS = {"Skull": "skull", "Mandible": "jaw", "Ribcage": "upper_chest"} | {f"C{i}": "cervicals" for i in range(1, 8)}


def _stretch_report(lengths, label, maximum: ArrayLike = 1.25):
    if not np.isfinite(lengths).all() or not lengths.size:
        raise ValueError(f"Invalid {label} measurement")
    limits = np.broadcast_to(maximum, lengths.shape[:-1])
    if not np.isfinite(limits).all() or (limits < 1.25).any() or (limits > 1.5).any():
        raise ValueError("Invalid source-anatomical growth allowance")
    low, high = float(lengths.min()), float(lengths.max())
    if low < 0.75 - 1e-6 or (lengths > limits[:, None] + 1e-6).any():
        raise ValueError(f"{label} {low:.6f}..{high:.6f} exceeds its fixed anatomical stretch allowance")
    return {
        "minimum": low,
        "maximum": high,
        "exception_allowed": int((limits > 1.25 + 1e-6).sum()),
        "exception_used": int((lengths.max(axis=1) > 1.25 + 1e-6).sum()),
        "maximum_allowance": float(limits.max()),
    }


def check_stretch(gradients, regional_scale, maximum: ArrayLike = 1.25):
    """Principal local lengths from ORIGINAL Basis, after only a declared regional UNIFORM resize."""
    if not np.isfinite(regional_scale) or regional_scale <= 0:
        raise ValueError("Declare a positive uniform anatomical-region size")
    if not np.isfinite(gradients).all() or (np.linalg.det(gradients) <= 0).any():
        raise ValueError("A local stretch mapping folds or has invalid gradients")
    return _stretch_report(np.linalg.svd(gradients, compute_uv=False) / regional_scale, "local stretch", maximum)


def check_surface_stretch(basis, final_sculpt, faces, regional_scale, maximum: ArrayLike = 1.25, face_maximum=None):
    """Exact triangle tangent lengths include every final Sculpt edit; no per-Bone fitted normalization."""
    source, target = np.asarray(basis)[faces], np.asarray(final_sculpt)[faces]
    a = np.stack((source[:, 1] - source[:, 0], source[:, 2] - source[:, 0]), axis=2)
    b = np.stack((target[:, 1] - target[:, 0], target[:, 2] - target[:, 0]), axis=2)
    _, r = np.linalg.qr(a)
    if (np.abs(np.linalg.det(r)) < 1e-12).any():
        raise ValueError("Original anatomical Basis has a degenerate triangle")
    tangent = b @ np.linalg.inv(r)
    limits = np.broadcast_to(maximum, (len(basis),))[faces].min(axis=1) if face_maximum is None else face_maximum
    return _stretch_report(np.linalg.svd(tangent, compute_uv=False) / regional_scale, "surface stretch", limits)


def regional_pose(source, target, uniform_size, pitch_deg=0.0):
    """A declared uniform size and rigid pitch, with explicit measured deformation along a bilateral axis.

    Both functional anchors stay exact. Their spacing correction is part of the deformation budget, NOT an
    anisotropic baseline. No old canal-centroid position or crown-fill target constrains this initializer.
    """
    source, target = np.asarray(source, dtype=float), np.asarray(target, dtype=float)
    if source.shape != (2, 3) or target.shape != (2, 3) or not np.isfinite([source, target]).all():
        raise ValueError("A regional pose needs two finite bilateral source/target anchors")
    if not np.isfinite([uniform_size, pitch_deg]).all() or uniform_size <= 0:
        raise ValueError("Declare a finite positive uniform anatomical size and pitch")

    def frame(points):
        axis = points[0] - points[1]
        length = np.linalg.norm(axis)
        if length < 1e-8:
            raise ValueError("Bilateral pose anchors must be distinct")
        x = axis / length
        y = np.array((0.0, 1, 0)) - x * x[1]
        if np.linalg.norm(y) < 1e-8:
            raise ValueError("Bilateral anchors must define a lateral anatomical axis")
        y /= np.linalg.norm(y)
        return np.column_stack((x, y, np.cross(x, y))), length

    native, a = frame(source)
    world, b = frame(target)
    angle = np.deg2rad(pitch_deg)
    pitch = np.array(((1, 0, 0), (0, np.cos(angle), -np.sin(angle)), (0, np.sin(angle), np.cos(angle))))
    rotation = world @ pitch @ native.T
    matrix, declared = np.eye(4), np.eye(4)
    matrix[:3, :3] = world @ pitch @ np.diag((b / a, uniform_size, uniform_size)) @ native.T
    declared[:3, :3] = uniform_size * rotation
    for m in (matrix, declared):
        m[:3, 3] = target.mean(0) - m[:3, :3] @ source.mean(0)
    lengths = np.linalg.svd(matrix[:3, :3], compute_uv=False) / uniform_size
    if lengths.min() < 0.75 or lengths.max() > 1.25:
        raise ValueError(
            "No admissible bilateral affine initializer at this size; nonlinear infeasibility is NOT established"
        )
    return matrix, {
        "declared_uniform_size": float(uniform_size),
        "rigid_pitch_deg": float(pitch_deg),
        "declared_uniform_frame": declared.tolist(),
        "measured_initial_local_lengths": lengths.tolist(),
        "scope": "Initializer only; actual Skin/articulation/finished geometry still require independent validation",
    }


def constrained_affine(source, target, inequalities=None):
    """Fit one anatomical region with three EXACT anchors and an explicitly optimized uniform size.

    Three noncollinear anchors fix two columns; only the third column and the declared size are optimized.
    Optional inequality values are positive inside the caller's fixed constraint set. Final independent SVD and
    anchor/inequality checks determine feasibility, not the optimizer's success flag alone.
    """
    source, target = np.asarray(source), np.asarray(target)
    if source.shape != (3, 3) or target.shape != (3, 3):
        raise ValueError("An affine regional fit needs three noncollinear anatomical anchors")
    ratios = [
        np.linalg.norm(target[i] - target[j]) / np.linalg.norm(source[i] - source[j])
        for i, j in ((0, 1), (0, 2), (1, 2))
    ]
    low, high = max(ratios) / 1.25, min(ratios) / 0.75
    if low >= high:
        raise ValueError("affine anchor scale interval is empty; nonlinear-field infeasibility is NOT established")
    centre, dest = source[:2].mean(0), target[:2].mean(0)
    length = np.linalg.norm(source[1] - source[0])
    x = (source[1] - source[0]) / length
    q = source[2] - centre
    along = q @ x
    y = q - along * x
    height = np.linalg.norm(y)
    if height < 1e-8:
        raise ValueError("An affine regional fit needs three noncollinear anatomical anchors")
    y /= height
    frame = np.column_stack((x, y, np.cross(x, y)))
    b0 = (target[1] - target[0]) / length
    b1 = (target[2] - dest - along * b0) / height
    normal = np.cross(b0, b1)
    normal /= np.linalg.norm(normal)
    initial_scale = np.sqrt(min(ratios) * max(ratios))

    def unpack(parameters):
        matrix = np.eye(4)
        matrix[:3, :3] = np.column_stack((b0, b1, parameters[:3])) @ frame.T
        matrix[:3, 3] = dest - matrix[:3, :3] @ centre
        return matrix, np.exp(parameters[3])

    def gram(parameters):
        matrix, scale = unpack(parameters)
        a = matrix[:3, :3] / scale
        return a.T @ a

    def principal_minors(m):
        return [*np.diag(m), *(np.linalg.det(m[np.ix_(p, p)]) for p in ((0, 1), (0, 2), (1, 2))), np.linalg.det(m)]

    def stretch_constraints(parameters):
        g = gram(parameters)
        matrix, scale = unpack(parameters)
        return np.array(
            principal_minors(g - 0.75**2 * np.eye(3))
            + principal_minors(1.25**2 * np.eye(3) - g)
            + [np.linalg.det(matrix[:3, :3] / scale) - 0.1]
        )

    constraints = [NonlinearConstraint(stretch_constraints, 0, np.inf, keep_feasible=True)]
    if inequalities is not None:
        constraints.append(NonlinearConstraint(lambda p: inequalities(unpack(p)[0]), 0, np.inf))
    solution = minimize(
        lambda p: np.square(gram(p) - np.eye(3)).sum(),
        np.r_[normal * initial_scale, np.log(initial_scale)],
        method="trust-constr",
        # SciPy accepts array bounds; its installed default-value annotation incorrectly narrows these to float.
        bounds=cast(Any, Bounds)([-np.inf] * 3 + [np.log(low)], [np.inf] * 3 + [np.log(high)]),
        constraints=constraints,
        options={"maxiter": 150, "gtol": 1e-9, "xtol": 1e-10, "barrier_tol": 1e-10},
    )
    matrix, scale = unpack(solution.x)
    stretch = check_stretch(matrix[None, :3, :3], scale)
    error = float(np.linalg.norm(source @ matrix[:3, :3].T + matrix[:3, 3] - target, axis=1).max())
    if error > 1e-6 or (inequalities is not None and np.min(inequalities(matrix)) < -1e-6):
        raise ValueError(f"No feasible affine candidate found: {solution.message}; anchor error {error:.6g} mm")
    return matrix, {
        "uniform_scale": float(scale),
        "scale_interval_from_anchors": [float(low), float(high)],
        "stretch": stretch,
        "anchor_error_mm": error,
        "optimizer_success": bool(solution.success),
        "optimizer_message": str(solution.message),
        "iterations": int(solution.nit),
    }


def coarse_head_margin(points, cage, inset):
    """Signed distance to each interpolated eight-sided cross-section, minus its radial-plane reserve.

    The star polygon retains measured diagonal grooves. It is an OWN coarse proxy, never an exact private Skin
    certificate; between-section slopes and unmeasured detail still require the independent local oracle.
    """
    rings = sorted((float(z), r) for z, r in cage["radial_first_exits"].items())
    heights = [z for z, _ in rings]
    cx = np.interp(points[:, 2], heights, [r["origin_world_x_mm"] for _, r in rings])
    cy = np.interp(points[:, 2], heights, [r["origin_world_y_mm"] for _, r in rings])
    radii = np.column_stack(
        [
            np.interp(points[:, 2], heights, [r["radius_mm_by_angle_deg"][str(angle)] for _, r in rings])
            for angle in range(0, 360, 45)
        ]
    )
    angles = np.arange(8) * np.pi / 4
    vertices = radii[:, :, None] * np.column_stack((np.cos(angles), np.sin(angles)))[None]
    edges = np.roll(vertices, -1, axis=1) - vertices
    p = points[:, :2] - np.column_stack((cx, cy))
    t = np.clip(np.sum((p[:, None] - vertices) * edges, axis=2) / np.sum(edges**2, axis=2), 0, 1)
    distance = np.linalg.norm(p[:, None] - vertices - t[:, :, None] * edges, axis=2).min(axis=1)
    lengths = np.linalg.norm(p, axis=1)
    direction = p / np.maximum(lengths[:, None], 1e-12)
    sector = np.floor(np.mod(np.arctan2(p[:, 1], p[:, 0]), 2 * np.pi) / (np.pi / 4)).astype(int)
    v, e = vertices[np.arange(len(p)), sector], edges[np.arange(len(p)), sector]
    cross = lambda a, b: a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    radius = cross(v, e) / np.where(lengths > 1e-12, cross(direction, e), 1.0)
    inside = (lengths <= radius + 1e-9) | (lengths <= 1e-12)
    return np.where(inside, distance, -distance) - inset


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
    allowance = scene.get("anatomical_budget")
    support = None
    if allowance:
        if allowance["version"] != 1 or allowance["basis_sha256"] != budget.stamp(arrays, scene["bones"]):
            raise ValueError("The anatomical growth mask must match the immutable original Basis/topology")
        if any(
            b["name"].startswith(("L rib ", "R rib ", "L costal cartilage ", "R costal cartilage "))
            for b in scene["bones"]
        ):
            support = budget.support_mesh(arrays, scene["bones"])
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

        def field(x):
            t = np.clip((x @ normal - low) / (high - low), 0, 1)
            weight = (t**3 * (t * (6 * t - 15) + 10))[:, None]  # C2-smooth, including both ends
            return weight * fields["head"](x) + (1 - weight) * fields["body"](x)

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
        maximum = budget.caps(bone["name"], arrays[key + "_basis"], allowance, support) if allowance else 1.25
        face_maximum = (
            budget.face_caps(bone["name"], arrays[key + "_basis"][arrays[key + "_faces"]], allowance, support)
            if allowance
            else None
        )
        n = len(arrays[key + "_basis"])
        gradient = (jac[offset : offset + n] + np.eye(3)) @ matrix[:3, :3]
        final = result[key + "_sculpt"] @ matrix[:3, :3].T + matrix[:3, 3]
        stretch[bone["name"]] = {
            "region": REGIONS[bone["group"]],
            "declared_uniform_scale": scale,
            "field": check_stretch(gradient, scale, maximum),
            "surface_including_sculpt": check_surface_stretch(
                arrays[key + "_basis"], final, arrays[key + "_faces"], scale, maximum, face_maximum
            ),
        }
        offset += n
    return result, {
        "min_jacobian": determinant,
        "landmark_error_mm": error,
        "regional_stretch": stretch,
        "anatomical_budget_version": 1 if allowance else None,
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


def c1_window(arrays, scene, original):
    """Actual candidate C1 triangles versus the fixed public shaft line; a diagnostic, never pose acceptance."""
    bone = next(b for b in scene["bones"] if b["name"] == "C1")
    key, matrix = bone["key"], np.asarray(bone["matrix"])
    points = arrays[key + "_sculpt"] @ matrix[:3, :3].T + matrix[:3, 3]
    mesh = trimesh.Trimesh(points, original[key + "_faces"], process=False)
    axis = Point(0, -73.4)
    out = {
        "scope": "UNACCEPTED candidate C1 only; not Skull/Skin/whole-hardware clearance",
        "bounds_world": mesh.bounds.tolist(),
        "sections": {},
    }
    for z in (128.3, 132, 137, 140, 145, 148, 152):
        if not mesh.bounds[0, 2] <= z <= mesh.bounds[1, 2]:
            out["sections"][str(z)] = {"C1_absent_at_height": True}
            continue
        section = mesh.section(plane_origin=(0, 0, z), plane_normal=(0, 0, 1))
        if section is None:
            out["sections"][str(z)] = {"error": "No closed C1 cross-section"}
            continue
        paths = section.discrete
        open_paths = sum(not np.allclose(p[0], p[-1]) for p in paths if len(p) >= 2)
        loops = [Polygon(p[:, :2]) for p in paths if len(p) >= 4 and np.allclose(p[0], p[-1])]
        loops = [p for p in loops if p.is_valid and p.area > 0]
        holes = [p for p in loops if sum(q.contains(p) for q in loops if q is not p) % 2]
        if not loops:
            out["sections"][str(z)] = {"error": "No valid closed C1 material contours", "open_paths": open_paths}
            continue
        in_bone = sum(p.contains(axis) for p in loops) % 2 == 1
        radius = float(min(p.exterior.distance(axis) for p in loops))
        certified_air = not in_bone and open_paths == 0
        out["sections"][str(z)] = {
            "axis_in_bone_material": in_bone,
            "axis_in_enclosed_neural_hole": any(p.contains(axis) for p in holes),
            "open_paths": open_paths,
            "clear_radius_about_actual_axis_mm": radius,
            "OD12_plus1_6_clear_at_this_plane": certified_air and radius >= 7.6,
            "OD20_plus1_6_clear_at_this_plane": certified_air and radius >= 11.6,
            "OD23_shoulder_plus1_6_clear_at_this_plane": certified_air and radius >= 13.1,
        }
    return out


def affine_head_facts(arrays, scene, envelope):
    """Analytic/constrained head submodel only: no body/proxy/source adoption or anatomical certificate."""
    facts = original_facts(arrays, scene)
    source = np.array(
        [facts["landmarks"][f"LM {side} orbit"] for side in ("L", "R")] + [facts["canals"]["C1"]["centre"]]
    )
    target = np.array(((36.35, -150, 177), (-36.35, -150, 177), envelope["canal_ends"]["C1"]))
    matrix, report = constrained_affine(source, target)
    report["matrix_native_to_world"] = matrix.tolist()
    report["scope"] = "Affine hard-anchor feasibility only; C1 canal reference is NOT a verified C0 articular axis"
    report["anatomical_witnesses_world"] = {
        name: (np.asarray(p) @ matrix[:3, :3].T + matrix[:3, 3]).tolist() for name, p in facts["landmarks"].items()
    }
    points = np.vstack([arrays[b["key"] + "_basis"] for b in scene["bones"] if b["group"] in ("Skull", "Mandible")])
    world = points @ matrix[:3, :3].T + matrix[:3, 3]
    report["raw_head_bounds_world"] = [world.min(0).tolist(), world.max(0).tolist()]
    return report


def affine_head_room(arrays, scene, envelope, cage):
    """Generate worst-vertex constraints for the affine UPPER VAULT submodel; no body/proxy adoption.

    The supplied own coarse cage is only a diagnostic. Success still requires the independent exact private
    oracle, every lower-face point, actual anatomical joint registration and all finished geometry gates.
    """
    facts = original_facts(arrays, scene)
    source = np.array(
        [facts["landmarks"][f"LM {side} orbit"] for side in ("L", "R")] + [facts["canals"]["C1"]["centre"]]
    )
    target = np.array(((36.35, -150, 177), (-36.35, -150, 177), envelope["canal_ends"]["C1"]))
    matrix, report = constrained_affine(source, target)
    vault = {
        "frontal bone",
        "L parietal bone",
        "R parietal bone",
        "occipital bone",
        "L temporal bone",
        "R temporal bone",
    }
    points, ids = [], []
    floor = min(map(float, cage["radial_first_exits"]))
    for bone in scene["bones"]:
        if bone["name"] not in vault:
            continue
        p = arrays[bone["key"] + "_basis"]
        included = np.flatnonzero((p @ matrix[:3, :3].T + matrix[:3, 3])[:, 2] >= floor)
        points.extend(p[included])
        ids.extend((bone["name"], int(i)) for i in included)
    points = np.array(points)
    inset = envelope["inset_mm"] + 0.05  # source radii rounded0.1mm; never spend that rounding on claimed clearance
    top = envelope["regional_room"]["head_outer_top_mm"] - inset

    def margins(m, selected):
        q = selected @ m[:3, :3].T + m[:3, 3]
        return np.minimum(coarse_head_margin(q, cage, inset), top - q[:, 2])

    active = set()
    for iteration in range(8):
        full = margins(matrix, points)
        if full.min() >= -1e-6:
            break
        active.update(map(int, np.argsort(full)[:12]))
        selected = points[sorted(active)]
        print(f"fit: affine constraint round {iteration + 1}, {len(active)} public vault vertices", flush=True)
        try:
            matrix, report = constrained_affine(source, target, lambda m: margins(m, selected))
        except ValueError as error:
            return {
                "status": "No feasible candidate found in this affine/coarse-proxy submodel; NOT global infeasibility",
                "error": str(error),
                "active_public_vertex_ids": [ids[i] for i in sorted(active)],
                "initial_anchor_only_report": report,
                "scope": "Current head-method analysis only; body/proxy adoption held",
            }
    full = margins(matrix, points)
    report |= {
        "matrix_native_to_world": matrix.tolist(),
        "scope": "UNACCEPTED coarse UPPER VAULT affine result; no whole Skin/joint/finished certificate",
        "proxy_min_margin_mm": float(full.min()),
        "proxy_violating_vertices": int((full < -1e-6).sum()),
        "scanned_vertices": len(points),
        "active_public_vertex_ids": [ids[i] for i in sorted(active)],
        "source_proxy_sha256": cage["source_sha256"],
    }
    return report


def refit(arrays, scene, envelope, seed_only=False, skin=None):
    """Original anatomy, four declared uniform regions, then one bounded residual field.

    The similarity sizes are chosen BEFORE shape deformation from fixed eye/C0 anchors and measured Skin room.
    Original cervical curvature is retained; no independent Bone poses or interpolated C2-C7 targets are used.
    """
    if skin is not None and not seed_only:
        return fit_bust(arrays, scene, envelope, skin)
    import copy
    import hashlib

    historical = copy.deepcopy(scene["landmarks"])
    arrays = dict(arrays)
    digest = hashlib.sha256()
    for bone in scene["bones"]:
        key = bone["key"]
        digest.update(bone["name"].encode())
        digest.update((arrays[key + "_sculpt"] - arrays[key + "_warp"]).tobytes())
        arrays[key + "_sculpt"] = arrays[key + "_warp"].copy()
    scene["historical_sculpt_policy"] = {
        "policy": "Original-anatomy refit starts with zero working Sculpt residual; historical source/Git/exchange remain unchanged",
        "original_delta_sha256": digest.hexdigest(),
    }
    facts = original_facts(arrays, scene)
    scene["anatomical_budget"] = budget.reference(arrays, scene["bones"], facts)
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
    seed, seed_report = regional_seed(arrays, scene, regions)
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
    if seed_only:
        errors = {n: float(np.linalg.norm(np.array(p["source"]) - p["target"])) for n, p in scene["landmarks"].items()}
        seed_report["scaffold_landmark_error_mm"] = seed_report["landmark_error_mm"]
        seed_report["landmark_error_mm"] = max(errors.values())
        seed_report["anatomical_anchor_errors_mm"] = errors
        seed_report["landmark_scope"] = (
            "UNACCEPTED uniform regional seed: eye/C0/T1/crown residuals reported, full joints UNVERIFIED"
        )
        seed_report["declared_regional_sizes"] = {name: r["scale"] for name, r in regions.items()}
        return seed, seed_report
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


def floor_extended_skin(vertices, faces, extension_mm=250.0):
    """Extend the horizontal Z=0 bust base cut downward without altering any Z>0 sidewall or shoulder triangle."""
    v = np.asarray(vertices, dtype=float)
    f = np.asarray(faces, dtype=np.int64)
    tri = v[f]
    centroids = tri.mean(axis=1)
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normals = cross / np.maximum(np.linalg.norm(cross, axis=1, keepdims=True), 1e-12)
    is_floor = (centroids[:, 2] <= 1.0) & (normals[:, 2] < -0.95)
    if not is_floor.any():
        return v.copy(), f.copy()
    side_faces = f[~is_floor]
    floor_faces = f[is_floor].copy()
    side_v = set(np.unique(side_faces).tolist())
    floor_v = set(np.unique(floor_faces).tolist())
    shared = sorted(side_v & floor_v)
    floor_only = sorted(floor_v - side_v)
    out_v = v.copy()
    if floor_only:
        out_v[floor_only, 2] -= extension_mm
    dup = {idx: len(out_v) + i for i, idx in enumerate(shared)}
    dup_v = v[shared].copy()
    dup_v[:, 2] -= extension_mm
    out_v = np.vstack((out_v, dup_v))
    remap = np.arange(len(v), dtype=np.int64)
    for idx, new_idx in dup.items():
        remap[idx] = new_idx
    floor_faces = remap[floor_faces]
    floor_half = {(int(row[i]), int(row[(i + 1) % 3])) for row in f[is_floor] for i in range(3)}
    walls = []
    for row in side_faces:
        for i in range(3):
            a, b = int(row[i]), int(row[(i + 1) % 3])
            if (b, a) in floor_half:
                walls.append((a, dup[b], b))
                walls.append((a, dup[a], dup[b]))
    out_f = np.vstack((side_faces, np.asarray(walls, dtype=np.int64), floor_faces))
    return out_v, out_f


def hair_vault_guides(skin_vertices, skin_faces, skull_mesh, head_matrix, inset_mm=4.2):
    """Subordinate cranial-vault guide pairs from the inner/crease trough of the reference hair cap."""
    skin_mesh = trimesh.Trimesh(skin_vertices, skin_faces, process=False)
    inv_a = np.linalg.inv(head_matrix[:3, :3])
    origin_world = np.array((0.0, -78.0, 185.0))
    origin_native = (origin_world - head_matrix[:3, 3]) @ inv_a.T
    directions = []
    for phi_deg in (18, 32, 48, 64, 78):
        phi = np.deg2rad(phi_deg)
        for theta_deg in range(-150, 180, 30):
            theta = np.deg2rad(theta_deg)
            d = np.array((np.sin(phi) * np.sin(theta), -np.sin(phi) * np.cos(theta), np.cos(phi)))
            # Keep superior vault dome and posterior occipital/parietal dome above the hair-cap crease.
            if phi_deg <= 50 or d[1] > -0.25:
                directions.append(d / np.linalg.norm(d))
    directions = np.asarray(directions)
    locs, rays, _ = skin_mesh.ray.intersects_location(np.tile(origin_world, (len(directions), 1)), directions)
    world_targets, valid_dirs = [], []
    for i, d in enumerate(directions):
        pts = locs[rays == i]
        dists = (pts - origin_world) @ d
        pos = dists[dists > 10.0]
        if len(pos):
            r = float(pos.min()) - (inset_mm + 1.0)
            if r > 20.0:
                world_targets.append(origin_world + r * d)
                valid_dirs.append(d)
    if not world_targets:
        return np.empty((0, 3)), np.empty((0, 3))
    world_targets = np.asarray(world_targets)
    native_targets = (world_targets - head_matrix[:3, 3]) @ inv_a.T
    native_sources = outer_cortex(skull_mesh, native_targets, origin_native)
    return native_sources, world_targets


JOINT_SPECS = (
    ("C0 L", "occipital bone", "C1", "L", 3.5, "cross_region"),
    ("C0 R", "occipital bone", "C1", "R", 3.5, "cross_region"),
    ("TMJ L L", "mandible", "L temporal bone", "L", 3.5, "cross_region"),
    ("TMJ R R", "mandible", "R temporal bone", "R", 3.5, "cross_region"),
    ("C7 T1 L", "C7", "T1", "L", 3.5, "cross_region"),
    ("C7 T1 R", "C7", "T1", "R", 3.5, "cross_region"),
    ("SC L", "manubrium", "L clavicle", "L", 3.5, "intra_region"),
    ("SC R", "manubrium", "R clavicle", "R", 3.5, "intra_region"),
    ("AC L", "L clavicle", "L scapula", "L", 5.0, "intra_region"),
    ("AC R", "R clavicle", "R scapula", "R", 5.0, "intra_region"),
    ("Manubriosternal", "manubrium", "body of sternum", None, 3.5, "intra_region"),
    ("Costovertebral T1 L", "T1", "L rib 1", "L", 3.5, "intra_region"),
    ("Costovertebral T1 R", "T1", "R rib 1", "R", 3.5, "intra_region"),
    ("Sternocostal 1 L", "manubrium", "L costal cartilage 1", "L", 3.5, "intra_region"),
    ("Sternocostal 1 R", "manubrium", "R costal cartilage 1", "R", 3.5, "intra_region"),
    *((f"C{i} C{i + 1}", f"C{i}", f"C{i + 1}", None, 3.5, "intra_region") for i in range(1, 7)),
)


def joint_witnesses(arrays, scene):
    """Extract deterministic opposing surface patches on native Basis for cross-region and intra-region joints."""
    by_name = {b["name"]: b for b in scene["bones"]}
    meshes = {}
    for name, b in by_name.items():
        key = b["key"]
        refinement = b.get("refinement")
        basis = np.asarray(arrays[key + "_basis"], dtype=float)
        if refinement and key + "_refinement_original_faces" in arrays:
            basis = basis[: int(refinement["original_vertex_count"])]
            faces = np.asarray(arrays[key + "_refinement_original_faces"], dtype=np.int64)
        else:
            faces = np.asarray(arrays[key + "_faces"], dtype=np.int64)
        meshes[name] = trimesh.Trimesh(basis, faces, process=False)
    joints = {}
    for label, name_a, name_b, side, radius, kind in JOINT_SPECS:
        if name_a not in meshes or name_b not in meshes:
            continue
        ma, mb = meshes[name_a], meshes[name_b]
        va, vb = np.asarray(ma.vertices), np.asarray(mb.vertices)
        mask_a = np.ones(len(va), dtype=bool)
        mask_b = np.ones(len(vb), dtype=bool)
        if side == "L":
            mask_a &= va[:, 0] > 2.0
            mask_b &= vb[:, 0] > 2.0
        elif side == "R":
            mask_a &= va[:, 0] < -2.0
            mask_b &= vb[:, 0] < -2.0
        idx_a = np.flatnonzero(mask_a)
        idx_b = np.flatnonzero(mask_b)
        if not len(idx_a) or not len(idx_b):
            continue
        closest_b, dist_a, _ = trimesh.proximity.closest_point(mb, va[idx_a])
        closest_a, dist_b, _ = trimesh.proximity.closest_point(ma, vb[idx_b])
        sel_a = dist_a <= radius
        sel_b = dist_b <= radius
        if not sel_a.any() or not sel_b.any():
            continue
        ids_a = idx_a[sel_a]
        ids_b = idx_b[sel_b]
        gaps = np.r_[dist_a[sel_a], dist_b[sel_b]]
        joints[label] = {
            "bone_a": name_a,
            "bone_b": name_b,
            "kind": kind,
            "side": side,
            "max_distance_mm": float(radius),
            "a_vertex_count": int(len(ids_a)),
            "b_vertex_count": int(len(ids_b)),
            "a_vertex_ids": ids_a.tolist(),
            "b_vertex_ids": ids_b.tolist(),
            "a_patch_centroid_native": va[ids_a].mean(0).tolist(),
            "b_patch_centroid_native": vb[ids_b].mean(0).tolist(),
            "a_paired_on_b_centroid_native": closest_b[sel_a].mean(0).tolist(),
            "b_paired_on_a_centroid_native": closest_a[sel_b].mean(0).tolist(),
            "native_gap_mm": {
                "min": float(gaps.min()),
                "median": float(np.median(gaps)),
                "max": float(gaps.max()),
            },
        }
    return {
        "scope": "Native BodyParts3D opposing articular surface patches (before any affine/nonlinear fit)",
        "joints": joints,
    }


def evaluate_joint_witnesses(witnesses, world_by_name, faces_by_name):
    """Measure deformed patch centroids and surface-to-surface articular gaps across all witnessed joints."""
    meshes = {name: trimesh.Trimesh(world_by_name[name], faces_by_name[name], process=False) for name in world_by_name}
    out = {}
    for label, info in witnesses["joints"].items():
        na, nb = info["bone_a"], info["bone_b"]
        va = world_by_name[na][info["a_vertex_ids"]]
        vb = world_by_name[nb][info["b_vertex_ids"]]
        _, da, _ = trimesh.proximity.closest_point(meshes[nb], va)
        _, db, _ = trimesh.proximity.closest_point(meshes[na], vb)
        gaps = np.r_[da, db]
        ca, cb = va.mean(0), vb.mean(0)
        out[label] = {
            "bone_a": na,
            "bone_b": nb,
            "kind": info.get("kind", "cross_region"),
            "a_centroid_world": ca.tolist(),
            "b_centroid_world": cb.tolist(),
            "centroid_distance_mm": float(np.linalg.norm(ca - cb)),
            "deformed_gap_mm": {
                "min": float(gaps.min()),
                "median": float(np.median(gaps)),
                "max": float(gaps.max()),
            },
            "native_gap_mm": info["native_gap_mm"],
        }
    return out


def _fps(points, count):
    points = np.asarray(points, dtype=float)
    if len(points) <= count:
        return np.arange(len(points), dtype=np.int64)
    chosen = [int(np.argmax(np.sum((points - points.mean(0)) ** 2, axis=1)))]
    dist2 = np.sum((points - points[chosen[0]]) ** 2, axis=1)
    for _ in range(1, count):
        nxt = int(np.argmax(dist2))
        chosen.append(nxt)
        dist2 = np.minimum(dist2, np.sum((points - points[nxt]) ** 2, axis=1))
    return np.array(chosen, dtype=np.int64)


def _diverse_violators(world_points, margins, limit=64, min_dist_mm=3.5):
    bad = np.flatnonzero(margins < 1e-4)
    if not len(bad):
        return []
    order = bad[np.argsort(margins[bad])]
    picked = [int(order[0])]
    min_d2 = min_dist_mm**2
    for idx in order[1:]:
        if len(picked) >= limit:
            break
        p = world_points[idx]
        if all(np.sum((p - world_points[j]) ** 2) >= min_d2 for j in picked):
            picked.append(int(idx))
    for idx in order[: min(16, len(order))]:
        if int(idx) not in picked:
            picked.append(int(idx))
    return picked


def _load_skin(skin):
    if isinstance(skin, tuple) and len(skin) == 2:
        return np.asarray(skin[0], dtype=float), np.asarray(skin[1], dtype=np.int64)
    data = np.load(skin) if isinstance(skin, (str, Path)) else skin
    for vk, fk in (("vertices_world", "faces"), ("skin_vertices", "skin_faces"), ("vertices", "faces"), ("v", "f")):
        if vk in data and fk in data:
            return np.asarray(data[vk], dtype=float), np.asarray(data[fk], dtype=np.int64)
    raise ValueError(f"Unrecognized skin archive keys: {list(data.keys())}")


def fit_bust(arrays, scene, envelope, skin):
    """Solve the 4 connected anatomical regions inside the exact Skin Envelope with conforming adaptive refinement."""
    import copy
    import hashlib

    skin_v, skin_f = _load_skin(skin)
    inset = float(envelope.get("inset_mm", 4.2))
    head_env = Envelope(skin_v, skin_f)
    ext_v, ext_f = floor_extended_skin(skin_v, skin_f, extension_mm=250.0)
    chest_env = Envelope(ext_v, ext_f)
    head_margin = lambda p: head_env.distance(p) - inset
    chest_margin = lambda p: chest_env.distance(p) - inset

    historical = copy.deepcopy(scene.get("landmarks", {}))
    arrays = {k: np.asarray(v).copy() for k, v in arrays.items()}
    digest = hashlib.sha256()
    for bone in scene["bones"]:
        key = bone["key"]
        digest.update(bone["name"].encode())
        digest.update((arrays[key + "_sculpt"] - arrays[key + "_warp"]).tobytes())
        arrays[key + "_sculpt"] = arrays[key + "_warp"].copy()
    scene["historical_sculpt_policy"] = {
        "policy": "Original-anatomy refit starts with zero working Sculpt residual; historical source/Git/exchange remain unchanged",
        "original_delta_sha256": digest.hexdigest(),
    }
    facts = original_facts(arrays, scene)
    allowance = budget.reference(arrays, scene["bones"], facts)
    scene["anatomical_budget"] = allowance
    support = budget.support_mesh(arrays, scene["bones"])
    witnesses = joint_witnesses(arrays, scene)

    bone_meta = {}
    for bone in scene["bones"]:
        key = bone["key"]
        basis = np.asarray(arrays[key + "_basis"], dtype=float)
        faces = np.asarray(arrays[key + "_faces"], dtype=np.int64)
        v_caps = budget.caps(bone["name"], basis, allowance, support)
        f_caps = budget.face_caps(bone["name"], basis[faces], allowance, support)
        eff_v = v_caps.copy()
        np.minimum.at(eff_v, faces[:, 0], f_caps)
        np.minimum.at(eff_v, faces[:, 1], f_caps)
        np.minimum.at(eff_v, faces[:, 2], f_caps)
        tri = basis[faces]
        fc = tri.mean(axis=1)
        em = 0.5 * (tri + np.roll(tri, -1, axis=1)).reshape(-1, 3)
        bone_meta[bone["name"]] = {
            "bone": bone,
            "key": key,
            "basis": basis,
            "faces": faces,
            "v_caps": v_caps,
            "f_caps": f_caps,
            "eff_v_caps": eff_v,
            "fc": fc,
            "em": em,
        }

    def solve_region(
        region_name,
        bones,
        pose_candidates_fn,
        margin_fn,
        width_mm,
        n_centres,
        guides_fn=None,
        rounds=8,
        maxiter=120,
    ):
        metas = [bone_meta[b["name"]] for b in bones]
        all_v = np.vstack([m["basis"] for m in metas])
        all_v_caps = np.concatenate([m["eff_v_caps"] for m in metas])
        all_fc = np.vstack([m["fc"] for m in metas])
        all_fc_caps = np.concatenate([m["f_caps"] for m in metas])
        all_em = np.vstack([m["em"] for m in metas])
        all_check = np.vstack((all_v, all_fc, all_em))
        bone_v_slices = []
        offset = 0
        for m in metas:
            n = len(m["basis"])
            bone_v_slices.append((offset, offset + n))
            offset += n

        candidates = pose_candidates_fn(all_v, margin_fn)
        best_result = None
        for cand_idx, (src_anc, dst_anc, scale, pitch, matrix, pose_rep) in enumerate(candidates):
            world_v = all_v @ matrix[:3, :3].T + matrix[:3, 3]
            fixed = src_anc @ matrix[:3, :3].T + matrix[:3, 3]
            d_anc = np.linalg.norm(world_v[:, None] - fixed[None], axis=2).min(axis=1)
            far_v = world_v[d_anc >= 0.35 * width_mm]
            if len(far_v) < 4:
                far_v = world_v
            centres = far_v[_fps(far_v, n_centres)]
            guides = guides_fn(matrix, scale) if guides_fn is not None else None

            pool_pts = np.vstack((all_v, all_fc))
            pool_caps = np.concatenate((all_v_caps, all_fc_caps))
            s_idx = set(_fps(pool_pts, min(len(pool_pts), 1100)).tolist())
            # Always include transition points where allowance > 1.25 meets 1.25.
            trans = np.flatnonzero((pool_caps > 1.2501) & (pool_caps < 1.499))
            if len(trans):
                s_idx.update(trans[_fps(pool_pts[trans], min(len(trans), 250))].tolist())

            w_check = all_check @ matrix[:3, :3].T + matrix[:3, 3]
            m_init = margin_fn(w_check)
            c_idx = set(_fps(w_check, min(len(w_check), 48)).tolist())
            c_idx.update(_diverse_violators(w_check, m_init, limit=72, min_dist_mm=4.0))
            for a, b in bone_v_slices:
                c_idx.add(a + int(np.argmin(m_init[a:b])))

            field = None
            solver_rep = {}
            for r in range(rounds):
                s_list = sorted(s_idx)
                c_list = sorted(c_idx)
                s_caps = np.where(pool_caps[s_list] > 1.254, pool_caps[s_list] - 0.003, 1.25)
                field, solver_rep = deformation.solve(
                    pool_pts[s_list],
                    matrix,
                    scale,
                    src_anc,
                    centres,
                    width_mm,
                    margin_fn,
                    all_check[c_list],
                    maximum=s_caps,
                    maxiter=maxiter,
                    initial=field,
                    guides=guides,
                    minimum=0.753,
                )
                moved_check, _ = deformation.evaluate(all_check, field)
                margins = margin_fn(moved_check)
                _, grad_pool = deformation.evaluate(pool_pts, field)
                sv = np.linalg.svd(grad_pool, compute_uv=False) / scale
                s_violation = np.maximum(
                    0.7525 - sv[:, 2], sv[:, 0] - np.where(pool_caps > 1.254, pool_caps - 0.002, 1.25)
                )
                bad_s = np.flatnonzero(s_violation > 0)
                new_s = 0
                if len(bad_s):
                    top_s = bad_s[np.argsort(-s_violation[bad_s])[:120]]
                    before_s = len(s_idx)
                    s_idx.update(map(int, top_s))
                    new_s = len(s_idx) - before_s
                min_m = float(margins.min())
                print(
                    f"fit[{region_name}]: cand {cand_idx + 1} round {r + 1}/{rounds} "
                    f"min_margin={min_m:.4f} mm constraints={len(c_idx)} strains={len(s_idx)}",
                    flush=True,
                )
                if min_m >= -1e-5 and new_s == 0:
                    break
                before_c = len(c_idx)
                c_idx.update(_diverse_violators(moved_check, margins, limit=64, min_dist_mm=2.5 if r < 2 else 1.0))
                for a, b in bone_v_slices:
                    if margins[a:b].min() < 0:
                        c_idx.add(a + int(np.argmin(margins[a:b])))
                if len(c_idx) == before_c and new_s == 0:
                    break

            assert field is not None
            moved_v, _ = deformation.evaluate(all_v, field)
            min_v_margin = float(margin_fn(moved_v).min())
            if best_result is None or min_v_margin > best_result[0]:
                best_result = (min_v_margin, src_anc, dst_anc, scale, pitch, matrix, pose_rep, field, solver_rep)
            if min_v_margin >= -1e-5:
                break

        assert best_result is not None
        _, src_anc, dst_anc, scale, pitch, matrix, pose_rep, field, solver_rep = best_result
        return {
            "source_anchors": src_anc,
            "target_anchors": dst_anc,
            "scale": scale,
            "pitch_deg": pitch,
            "affine_matrix": matrix,
            "pose_report": pose_rep,
            "field": field,
            "solver_report": solver_rep,
        }

    # 1. Solve SKULL
    eye_l, eye_r = (np.asarray(facts["landmarks"][f"LM {side} orbit"], dtype=float) for side in ("L", "R"))
    src_eyes = np.array((eye_l, eye_r))
    dst_eyes = np.array(((36.35, -150.0, 177.0), (-36.35, -150.0, 177.0)))
    skull_bones = [b for b in scene["bones"] if REGIONS[b["group"]] == "skull"]
    vault_names = {
        "frontal bone",
        "L parietal bone",
        "R parietal bone",
        "occipital bone",
        "L temporal bone",
        "R temporal bone",
    }
    skull_vault_mesh = trimesh.util.concatenate(
        [
            trimesh.Trimesh(bone_meta[b["name"]]["basis"], bone_meta[b["name"]]["faces"], process=False)
            for b in skull_bones
            if b["name"] in vault_names
        ]
    )

    def skull_candidates(all_v, margin_fn):
        scored = []
        for s in (0.865, 0.875, 0.855, 0.885):
            for p in (2.0, 0.0, 4.0, -2.0):
                try:
                    mat, rep = regional_pose(src_eyes, dst_eyes, uniform_size=s, pitch_deg=p)
                except ValueError:
                    continue
                m = margin_fn(all_v @ mat[:3, :3].T + mat[:3, 3])
                score = float(m.min()) + 0.5 * float(np.percentile(m, 5))
                scored.append((score, (src_eyes, dst_eyes, s, p, mat, rep)))
        scored.sort(key=lambda x: -x[0])
        return [x[1] for x in scored[:2]]

    skull_sol = solve_region(
        "skull",
        skull_bones,
        skull_candidates,
        head_margin,
        width_mm=38.0,
        n_centres=48,
        guides_fn=lambda mat, _s: (*hair_vault_guides(skin_v, skin_f, skull_vault_mesh, mat, inset_mm=inset), 2e-3),
        rounds=8,
        maxiter=130,
    )
    skull_field = skull_sol["field"]

    def paired_candidates(joint_l, joint_r, a_is_parent, scale_bounds, pitches, extra_score_fn=None):
        jl, jr = witnesses["joints"][joint_l], witnesses["joints"][joint_r]
        if a_is_parent:
            parent_l_v = bone_meta[jl["bone_a"]]["basis"][jl["a_vertex_ids"]]
            parent_r_v = bone_meta[jr["bone_a"]]["basis"][jr["a_vertex_ids"]]
            parent_l_nat = np.asarray(jl["a_patch_centroid_native"], dtype=float)
            parent_r_nat = np.asarray(jr["a_patch_centroid_native"], dtype=float)
            child_l_nat = np.asarray(jl["a_paired_on_b_centroid_native"], dtype=float)
            child_r_nat = np.asarray(jr["a_paired_on_b_centroid_native"], dtype=float)
            parent_field = skull_field if REGIONS[bone_meta[jl["bone_a"]]["bone"]["group"]] == "skull" else cerv_field
        else:
            parent_l_v = bone_meta[jl["bone_b"]]["basis"][jl["b_vertex_ids"]]
            parent_r_v = bone_meta[jr["bone_b"]]["basis"][jr["b_vertex_ids"]]
            parent_l_nat = np.asarray(jl["b_patch_centroid_native"], dtype=float)
            parent_r_nat = np.asarray(jr["b_patch_centroid_native"], dtype=float)
            child_l_nat = np.asarray(jl["b_paired_on_a_centroid_native"], dtype=float)
            child_r_nat = np.asarray(jr["b_paired_on_a_centroid_native"], dtype=float)
            parent_field = skull_field
        pl_world = deformation.evaluate(parent_l_v, parent_field)[0].mean(0)
        pr_world = deformation.evaluate(parent_r_v, parent_field)[0].mean(0)
        delta_l = child_l_nat - parent_l_nat
        delta_r = child_r_nat - parent_r_nat
        src = np.array((child_l_nat, child_r_nat))
        ratio = float(np.linalg.norm(pl_world - pr_world) / np.linalg.norm(src[0] - src[1]))
        lo = max(scale_bounds[0], ratio / 1.20)
        hi = min(scale_bounds[1], ratio / 0.82)
        if lo > hi:
            lo, hi = ratio / 1.23, ratio / 0.78

        def build(all_v, margin_fn):
            scored = []
            for s in np.linspace(lo, hi, 5):
                for p in pitches:
                    try:
                        _, rep0 = regional_pose(
                            src, np.array((pl_world, pr_world)), uniform_size=float(s), pitch_deg=float(p)
                        )
                        rot = np.asarray(rep0["declared_uniform_frame"])[:3, :3] / float(s)
                        dst = np.array((pl_world + rot @ (float(s) * delta_l), pr_world + rot @ (float(s) * delta_r)))
                        mat, rep = regional_pose(src, dst, uniform_size=float(s), pitch_deg=float(p))
                    except ValueError:
                        continue
                    w = all_v @ mat[:3, :3].T + mat[:3, 3]
                    m = margin_fn(w)
                    score = float(m.min()) + 0.5 * float(np.percentile(m, 5))
                    if extra_score_fn is not None:
                        score += float(extra_score_fn(mat, float(s)))
                    scored.append((score, (src, dst, float(s), float(p), mat, rep)))
            scored.sort(key=lambda x: -x[0])
            return [x[1] for x in scored[:2]]

        return build

    # 2. Solve JAW (mandible) coupled at bilateral TMJ
    jaw_bones = [b for b in scene["bones"] if REGIONS[b["group"]] == "jaw"]
    jaw_sol = solve_region(
        "jaw",
        jaw_bones,
        paired_candidates(
            "TMJ L L", "TMJ R R", a_is_parent=False, scale_bounds=(0.76, 0.92), pitches=(-8, -4, 0, 4, 8)
        ),
        head_margin,
        width_mm=28.0,
        n_centres=24,
        rounds=6,
        maxiter=110,
    )

    # 3. Solve CERVICALS (C1..C7) coupled at bilateral C0 condyles
    cerv_bones = [b for b in scene["bones"] if REGIONS[b["group"]] == "cervicals"]
    c7_l_nat = np.asarray(witnesses["joints"]["C7 T1 L"]["a_patch_centroid_native"], dtype=float)
    c7_r_nat = np.asarray(witnesses["joints"]["C7 T1 R"]["a_patch_centroid_native"], dtype=float)
    c7_mid_nat = 0.5 * (c7_l_nat + c7_r_nat)
    c7_half_x = 0.5 * float(c7_l_nat[0] - c7_r_nat[0]) * 0.80
    t1_corridor_center = np.array(envelope["canal_ends"]["T1"], dtype=float)

    def cerv_guide_fn(mat, _s):
        w_mid = c7_mid_nat @ mat[:3, :3].T + mat[:3, 3]
        target_mid = np.array((0.0, 0.5 * (w_mid[1] + t1_corridor_center[1]), w_mid[2]))
        dst = np.array(
            (
                target_mid + np.array((c7_half_x, 0.0, 0.0)),
                target_mid + np.array((-c7_half_x, 0.0, 0.0)),
            )
        )
        return np.array((c7_l_nat, c7_r_nat)), dst, 2e-3

    cerv_sol = solve_region(
        "cervicals",
        cerv_bones,
        paired_candidates(
            "C0 L",
            "C0 R",
            a_is_parent=True,
            scale_bounds=(0.78, 0.90),
            pitches=(-12, -8, -4, 0, 4, 8, 12),
            extra_score_fn=lambda mat, _s: (
                -0.25 * float(np.linalg.norm((c7_mid_nat @ mat[:3, :3].T + mat[:3, 3])[:2] - t1_corridor_center[:2]))
            ),
        ),
        head_margin,
        width_mm=28.0,
        n_centres=24,
        guides_fn=cerv_guide_fn,
        rounds=6,
        maxiter=110,
    )
    cerv_field = cerv_sol["field"]

    # 4. Solve UPPER CHEST (Ribcage) coupled at bilateral C7/T1 facets
    chest_bones = [b for b in scene["bones"] if REGIONS[b["group"]] == "upper_chest"]
    chest_sol = solve_region(
        "upper_chest",
        chest_bones,
        paired_candidates(
            "C7 T1 L",
            "C7 T1 R",
            a_is_parent=True,
            scale_bounds=(0.74, 0.84),
            pitches=(-10, -6, -2, 0, 2, 6, 10),
        ),
        chest_margin,
        width_mm=42.0,
        n_centres=56,
        rounds=8,
        maxiter=130,
    )

    region_solutions = {
        "skull": (skull_sol, head_margin),
        "jaw": (jaw_sol, head_margin),
        "cervicals": (cerv_sol, head_margin),
        "upper_chest": (chest_sol, chest_margin),
    }

    regions_out = {}
    fields_out = {}
    for r_name, (sol, _) in region_solutions.items():
        declared = np.asarray(sol["pose_report"]["declared_uniform_frame"], dtype=float)
        regions_out[r_name] = {
            "scale": float(sol["scale"]),
            "pitch_deg": float(sol["pitch_deg"]),
            "matrix": declared.tolist(),
            "pose_report": sol["pose_report"],
        }
        fields_out[r_name] = sol["field"]
    scene["anatomical_regions"] = regions_out
    scene.pop("warp_blend", None)
    scene["original_anatomical_landmarks"] = historical

    # Adaptive conforming refinement and final verification per bone.
    result = {}
    stretch_report = {}
    world_by_name = {}
    faces_by_name = {}
    containment_by_region = {}
    total_orig_faces = 0
    total_ref_faces = 0

    for bone in scene["bones"]:
        name = bone["name"]
        key = bone["key"]
        r_name = REGIONS[bone["group"]]
        sol, m_fn = region_solutions[r_name]
        field = sol["field"]
        scale = float(sol["scale"])
        declared = np.asarray(regions_out[r_name]["matrix"], dtype=float)
        inv_decl = np.linalg.inv(declared[:3, :3])
        bone["matrix"] = declared.tolist()

        meta = bone_meta[name]
        orig_keys = {
            "basis": meta["basis"],
            "warp": arrays[key + "_warp"],
            "sculpt": arrays[key + "_sculpt"],
        }
        orig_faces = meta["faces"]
        parent_f_caps = meta["f_caps"]
        total_orig_faces += len(orig_faces)

        refined_keys, refined_faces, lineage = refine.adapt(
            orig_keys,
            orig_faces,
            lambda p, fld=field: deformation.evaluate(p, fld)[0],
            scale,
            face_maximum=parent_f_caps,
            margin_fn=m_fn,
            max_edge=0.15,
            aspect=20.0,
            rounds=8,
        )
        total_ref_faces += len(refined_faces)
        ref_basis = refined_keys["basis"]
        moved_warp, grad = deformation.evaluate(ref_basis, field)
        sculpt_delta = refined_keys["sculpt"] - refined_keys["warp"]
        moved_sculpt = moved_warp + sculpt_delta @ declared[:3, :3].T
        local_warp = (moved_warp - declared[:3, 3]) @ inv_decl.T
        local_sculpt = (moved_sculpt - declared[:3, 3]) @ inv_decl.T

        ref_v_caps = budget.caps(name, ref_basis, allowance, support)
        child_f_caps = budget.face_caps(name, ref_basis[refined_faces], allowance, support)
        effective_f_caps = np.minimum(parent_f_caps[lineage["parent_faces"]], child_f_caps)

        stretch_report[name] = {
            "region": r_name,
            "declared_uniform_scale": scale,
            "field": check_stretch(grad, scale, ref_v_caps),
            "surface_including_sculpt": check_surface_stretch(
                ref_basis, moved_sculpt, refined_faces, scale, ref_v_caps, effective_f_caps
            ),
            "refined_faces": int(len(refined_faces)),
            "original_faces": int(len(orig_faces)),
        }

        result[key + "_basis"] = ref_basis
        result[key + "_faces"] = refined_faces.astype(np.int32)
        result[key + "_warp"] = local_warp
        result[key + "_sculpt"] = local_sculpt
        result[key + "_refinement_original_faces"] = lineage["original_faces"].astype(np.int32)
        result[key + "_refinement_parent_faces"] = lineage["parent_faces"].astype(np.int32)
        result[key + "_refinement_vertex_parent_face"] = lineage["vertex_parent_face"].astype(np.int32)
        result[key + "_refinement_vertex_barycentric"] = lineage["vertex_barycentric"].astype(np.float64)
        bone["refinement"] = {
            "original_sha256": lineage["original_sha256"],
            "original_vertex_count": int(lineage["original_vertex_count"]),
            "original_face_count": int(len(lineage["original_faces"])),
            "refined_vertex_count": int(len(ref_basis)),
            "refined_face_count": int(len(refined_faces)),
            "settings": lineage["settings"],
        }
        world_by_name[name] = moved_sculpt
        faces_by_name[name] = refined_faces
        containment_by_region.setdefault(r_name, []).append(moved_sculpt)

    # Global 14^3 Jacobian probe check per region + all bone vertices.
    min_jac = np.inf
    for r_name, (sol, _) in region_solutions.items():
        r_bones = [b for b in scene["bones"] if REGIONS[b["group"]] == r_name]
        pts = np.vstack([result[b["key"] + "_basis"] for b in r_bones])
        grid = np.stack(
            np.meshgrid(*[np.linspace(a, b, 14) for a, b in zip(pts.min(0), pts.max(0))], indexing="ij"), -1
        ).reshape(-1, 3)
        probes = np.vstack((grid, pts, sol["source_anchors"]))
        _, g = deformation.evaluate(probes, sol["field"])
        dets = np.linalg.det(g / float(sol["scale"]))
        min_jac = min(min_jac, float(dets.min()))
    if min_jac <= 0.1:
        raise ValueError(f"Connected bust field folds or collapses: min_jacobian={min_jac:.6f}")

    # Record bilateral regional functional anchors in scene["landmarks"] and scene["anatomical_constraints"].
    scene["landmarks"] = {}
    constraints = {}
    anchor_labels = {
        "skull": ("LM fixed L orbit", "LM fixed R orbit"),
        "jaw": ("LM TMJ L", "LM TMJ R"),
        "cervicals": ("LM C0 L", "LM C0 R"),
        "upper_chest": ("LM C7 T1 L", "LM C7 T1 R"),
    }
    anchor_errors = {}
    for r_name, (sol, _) in region_solutions.items():
        declared = np.asarray(regions_out[r_name]["matrix"], dtype=float)
        src_a = sol["source_anchors"]
        dst_a = sol["target_anchors"]
        moved_a, _ = deformation.evaluate(src_a, sol["field"])
        for i, label in enumerate(anchor_labels[r_name]):
            src_w = src_a[i] @ declared[:3, :3].T + declared[:3, 3]
            scene["landmarks"][label] = {"source": src_w.tolist(), "target": moved_a[i].tolist(), "region": r_name}
            constraints[label] = {
                "source_native": src_a[i].tolist(),
                "region": r_name,
                "target": dst_a[i].tolist(),
            }
            anchor_errors[label] = float(np.linalg.norm(moved_a[i] - dst_a[i]))
    scene["anatomical_constraints"] = constraints
    scene["regional_fields"] = fields_out
    max_anchor_err = float(max(anchor_errors.values()))

    # Skin containment report (including explicit Z>=0 vs Z<0 floor-cut classification for upper_chest).
    skin_report = {}
    for r_name in ("skull", "jaw", "cervicals"):
        pts = np.vstack(containment_by_region[r_name])
        m = head_margin(pts)
        skin_report[r_name] = {
            "envelope": "exact_vtk_skin_4.2mm",
            "vertex_count": int(len(pts)),
            "min_margin_mm": float(m.min()),
            "violating_vertices": int((m < -1e-5).sum()),
        }
    chest_pts = np.vstack(containment_by_region["upper_chest"])
    chest_m = chest_margin(chest_pts)
    above_z0 = chest_pts[:, 2] >= 0.0
    raw_above_m = head_margin(chest_pts[above_z0]) if above_z0.any() else np.array([0.0])
    skin_report["upper_chest"] = {
        "envelope": "floor_extended_vtk_skin_4.2mm",
        "vertex_count": int(len(chest_pts)),
        "min_margin_mm": float(chest_m.min()),
        "violating_vertices": int((chest_m < -1e-5).sum()),
        "above_floor_z0_vertex_count": int(above_z0.sum()),
        "above_floor_z0_min_wall_margin_mm": float(chest_m[above_z0].min()) if above_z0.any() else None,
        "below_floor_z0_base_cut_vertex_count": int((~above_z0).sum()),
        "below_floor_z0_min_z_mm": float(chest_pts[:, 2].min()),
        "raw_z0_floor_cap_proximity_min_mm": float(raw_above_m.min()),
        "floor_cut_classification": "Vertices with Z < 0 cross the intentional horizontal Z = 0 bust base cut plane while remaining >= 4.2 mm inside the extruded thoracic perimeter wall",
    }

    # Canal verification after deformation.
    canals_after = {}
    for bone in scene["bones"]:
        if bone["name"] not in facts["canals"]:
            continue
        name = bone["name"]
        r_name = REGIONS[bone["group"]]
        sol, _ = region_solutions[r_name]
        c_nat = np.asarray(facts["canals"][name]["centre"], dtype=float)[None]
        _, g_c = deformation.evaluate(c_nat, sol["field"])
        src_normal = (
            np.array((0.0, np.sin(np.deg2rad(15)), np.cos(np.deg2rad(15))))
            if name == "C2"
            else np.array((0.0, 0.0, 1.0))
        )
        normal = g_c[0] @ src_normal
        normal /= np.linalg.norm(normal)
        canals_after[name] = canal(trimesh.Trimesh(world_by_name[name], faces_by_name[name]), normal, details=True)

    joint_report = evaluate_joint_witnesses(witnesses, world_by_name, faces_by_name)
    report = {
        "min_jacobian": float(min_jac),
        "landmark_error_mm": max_anchor_err,
        "anatomical_anchor_errors_mm": anchor_errors,
        "declared_regional_sizes": {k: v["scale"] for k, v in regions_out.items()},
        "declared_regional_pitches_deg": {k: v["pitch_deg"] for k, v in regions_out.items()},
        "anatomical_budget_version": 1,
        "refinement_summary": {
            "original_total_faces": int(total_orig_faces),
            "refined_total_faces": int(total_ref_faces),
            "added_faces": int(total_ref_faces - total_orig_faces),
        },
        "skin_containment": skin_report,
        "joint_witnesses": joint_report,
        "actual_canals_after_sculpt": canals_after,
        "regional_stretch": stretch_report,
    }
    return result, report


if __name__ == "__main__":
    if sys.argv[1] == "--c1-window":
        report = c1_window(np.load(sys.argv[2]), json.load(open(sys.argv[3])), np.load(sys.argv[4]))
        Path(sys.argv[5]).parent.mkdir(parents=True, exist_ok=True)
        Path(sys.argv[5]).write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        sys.exit()
    if sys.argv[1] == "--facts":
        print(json.dumps(original_facts(np.load(sys.argv[2]), json.load(open(sys.argv[3]))), indent=2))
        sys.exit()
    if sys.argv[1] == "--affine-facts":
        report = affine_head_facts(
            np.load(sys.argv[2]), json.load(open(sys.argv[3])), json.load(open("model/skeleton/envelope.json"))
        )
        Path(sys.argv[4]).parent.mkdir(parents=True, exist_ok=True)
        Path(sys.argv[4]).write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        sys.exit()
    if sys.argv[1] == "--affine-room":
        report = affine_head_room(
            np.load(sys.argv[2]),
            json.load(open(sys.argv[3])),
            json.load(open("model/skeleton/envelope.json")),
            json.load(open(sys.argv[4])),
        )
        Path(sys.argv[5]).parent.mkdir(parents=True, exist_ok=True)
        Path(sys.argv[5]).write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        sys.exit()
    if sys.argv[1] == "--joint-witnesses":
        report = joint_witnesses(np.load(sys.argv[2]), json.load(open(sys.argv[3])))
        Path(sys.argv[4]).parent.mkdir(parents=True, exist_ok=True)
        Path(sys.argv[4]).write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        sys.exit()
    if sys.argv[1] == "--skin":
        skin_path, path, metadata, out = sys.argv[2:6]
        scene = json.load(open(metadata))
        with open("model/skeleton/envelope.json") as f:
            envelope = json.load(f)
        result, report = fit_bust(np.load(path), scene, envelope, skin_path)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out + ".npz", **result)
        with open(out + ".json", "w") as f:
            json.dump(scene | {"fit_report": report}, f, indent=2)
        print(json.dumps(report, indent=2), flush=True)
        sys.exit()
    landmarks = sys.argv[1] == "--landmarks"
    seed_only = sys.argv[1] == "--regional-seed"
    path, metadata, out = sys.argv[2:] if landmarks or seed_only else sys.argv[1:]
    scene = json.load(open(metadata))
    if landmarks:
        result, report = warp(np.load(path), scene)
    else:
        with open("model/skeleton/envelope.json") as f:
            envelope = json.load(f)
        skin_env = os.environ.get("NOGGIN_PRIVATE_SKIN_NPZ")
        result, report = refit(np.load(path), scene, envelope, seed_only=seed_only, skin=skin_env)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out + ".npz", **result)
    with open(out + ".json", "w") as f:
        json.dump(scene | {"fit_report": report}, f, indent=2)
    print(json.dumps(report, indent=2), flush=True)
