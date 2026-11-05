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
from scipy.optimize import Bounds, NonlinearConstraint, minimize
from shapely.geometry import Point, Polygon

from model.skeleton import budget

REGIONS = {"Skull": "skull", "Mandible": "jaw", "Ribcage": "upper_chest"} | {f"C{i}": "cervicals" for i in range(1, 8)}


def _stretch_report(lengths, label, maximum=1.25):
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


def check_stretch(gradients, regional_scale, maximum=1.25):
    """Principal local lengths from ORIGINAL Basis, after only a declared regional UNIFORM resize."""
    if not np.isfinite(regional_scale) or regional_scale <= 0:
        raise ValueError("Declare a positive uniform anatomical-region size")
    if not np.isfinite(gradients).all() or (np.linalg.det(gradients) <= 0).any():
        raise ValueError("A local stretch mapping folds or has invalid gradients")
    return _stretch_report(np.linalg.svd(gradients, compute_uv=False) / regional_scale, "local stretch", maximum)


def check_surface_stretch(basis, final_sculpt, faces, regional_scale, maximum=1.25, face_maximum=None):
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
        bounds=Bounds([-np.inf] * 3 + [np.log(low)], [np.inf] * 3 + [np.log(high)]),
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


def refit(arrays, scene, envelope, seed_only=False):
    """Original anatomy, four declared uniform regions, then one bounded residual field.

    The similarity sizes are chosen BEFORE shape deformation from fixed eye/C0 anchors and measured Skin room.
    Original cervical curvature is retained; no independent Bone poses or interpolated C2-C7 targets are used.
    """
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
    landmarks = sys.argv[1] == "--landmarks"
    seed_only = sys.argv[1] == "--regional-seed"
    path, metadata, out = sys.argv[2:] if landmarks or seed_only else sys.argv[1:]
    scene = json.load(open(metadata))
    if landmarks:
        result, report = warp(np.load(path), scene)
    else:
        with open("model/skeleton/envelope.json") as f:
            envelope = json.load(f)
        result, report = refit(np.load(path), scene, envelope, seed_only=seed_only)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out + ".npz", **result)
    with open(out + ".json", "w") as f:
        json.dump(scene | {"fit_report": report}, f, indent=2)
    print(json.dumps(report, indent=2), flush=True)
