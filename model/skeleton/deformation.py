"""One smooth nonlinear field shared by an anatomical region's original connected geometry.

Anchor-conditioned Gaussian residuals keep functional anchors exact. Coefficients, anchors and widths are plain
JSON, so saved and interactive rewarps evaluate the SAME mapping. Optimizer success never replaces validation.
"""

from typing import Any, cast

import numpy as np
from scipy.optimize import NonlinearConstraint, minimize


def _basis(points, centres, anchors, width, affine=False):
    def kernel(a, b):
        delta = a[:, None] - b[None]
        value = np.exp(-np.sum(delta**2, axis=2) / (2 * width**2))
        return value, -value[:, :, None] * delta / width**2

    value, derivative = kernel(points, centres)
    if len(anchors):
        aa, _ = kernel(anchors, anchors)
        ac, _ = kernel(anchors, centres)
        if np.linalg.cond(aa) > 1e10:
            raise ValueError("Functional anchors are duplicate or numerically indistinguishable at this field width")
        correction = np.linalg.solve(aa, ac)
        pa, da = kernel(points, anchors)
        value -= pa @ correction
        derivative -= np.einsum("naj,ak->nkj", da, correction)
    if affine:
        # These global shape modes vanish on the anchors' affine span; Gaussians need not approximate a tilt/shear.
        origin = anchors.mean(0) if len(anchors) else np.zeros(3)
        centred = anchors - origin
        _, _, frame = np.linalg.svd(centred, full_matrices=True)
        rank = np.linalg.matrix_rank(centred) if len(anchors) else 0
        normals = frame[rank:]
        value = np.column_stack((value, (points - origin) @ normals.T / width))
        derivative = np.concatenate(
            (derivative, np.broadcast_to(normals / width, (len(points), len(normals), 3))), axis=1
        )
    return value, derivative


def evaluate(points, field):
    """Return final WORLD points and analytic derivatives with respect to ORIGINAL native coordinates."""
    matrix = np.asarray(field["matrix"])
    world = np.asarray(points) @ matrix[:3, :3].T + matrix[:3, 3]
    value, derivative = _basis(
        world,
        np.asarray(field["centres"]).reshape(-1, 3),
        np.asarray(field["anchors_world"]).reshape(-1, 3),
        field["width_mm"],
        field.get("affine_residual", False),
    )
    coefficients = np.asarray(field["coefficients"])
    moved = world + value @ coefficients
    gradient = (np.eye(3)[None] + np.einsum("nkj,ki->nij", derivative, coefficients)) @ matrix[:3, :3]
    return moved, gradient


def solve(
    points,
    matrix,
    scale,
    anchors,
    centres,
    width,
    margin,
    constrained_points,
    maximum=1.25,
    maxiter=150,
    triangles=None,
    triangle_maximum=1.25,
    initial=None,
):
    """Find the smallest nonlinear residual satisfying this FIXED sampled constraint set.

    `margin` returns one signed inside distance per WORLD point. The caller scans held-out geometry and adds
    violating source points between solves; a sampled fit is never a whole-Skin or volume-strain certificate.
    Crown fill is absent from this feasibility objective. The declared uniform size is fixed before this solve.
    """
    matrix, points, anchors, centres = map(np.asarray, (matrix, points, anchors, centres))
    if scale <= 0 or width <= 0 or not np.isfinite(matrix).all():
        raise ValueError("A shared field needs finite placement, positive uniform size and kernel width")
    limits = np.broadcast_to(maximum, (len(points),))
    if (limits < 1.25).any() or (limits > 1.5).any():
        raise ValueError("Source-frozen anatomical length allowances must be1.25..1.50")
    fixed = anchors @ matrix[:3, :3].T + matrix[:3, 3]
    world = points @ matrix[:3, :3].T + matrix[:3, 3]
    _, derivative = _basis(world, centres, fixed, width, affine=True)
    # dF/dnative = A + sum coefficient[k,i] * dphi[k]/dnative.
    d = derivative @ matrix[:3, :3]
    target = np.asarray(constrained_points) @ matrix[:3, :3].T + matrix[:3, 3]
    values, _ = _basis(target, centres, fixed, width, affine=True)
    count = values.shape[1]
    triangles = np.empty((0, 3, 3)) if triangles is None else np.asarray(triangles)
    source_edges = np.stack((triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=2)
    _, r = np.linalg.qr(source_edges)
    if (np.abs(np.linalg.det(r)) < 1e-12).any():
        raise ValueError("Original anatomical Basis has a degenerate triangle")
    inverse = np.linalg.inv(r)
    baseline_tangent = matrix[:3, :3] @ source_edges @ inverse
    triangle_world = triangles.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]
    phi, _ = _basis(triangle_world, centres, fixed, width, affine=True)
    phi = phi.reshape(len(triangles), 3, count)
    tangent_modes = np.stack((phi[:, 1] - phi[:, 0], phi[:, 2] - phi[:, 0]), axis=2) @ inverse
    surface_limits = np.broadcast_to(triangle_maximum, (len(triangles),))
    if (surface_limits < 1.25).any() or (surface_limits > 1.5).any():
        raise ValueError("Original triangle allowances must be1.25..1.50")

    def principal_lengths(baseline, modes, c):
        gradient = (baseline + np.einsum("nkj,ki->nij", modes, c.reshape(count, 3))) / scale
        u, sigma, vh = np.linalg.svd(gradient, full_matrices=False)
        right = np.einsum("nkj,nlj->nkl", modes, vh)
        jac = np.einsum("nil,nkl->nlki", u, right).reshape(len(gradient), gradient.shape[2], count * 3) / scale
        return gradient, sigma, jac

    def lengths(c):
        gradient, sigma, jac = principal_lengths(matrix[None, :3, :3], d, c)
        det = np.linalg.det(gradient)
        cofactors = np.stack(
            (
                np.cross(gradient[:, :, 1], gradient[:, :, 2]),
                np.cross(gradient[:, :, 2], gradient[:, :, 0]),
                np.cross(gradient[:, :, 0], gradient[:, :, 1]),
            ),
            axis=2,
        )
        det_jac = np.einsum("nij,nkj->nki", cofactors, d).reshape(len(points), -1) / scale
        return sigma, jac, det, det_jac

    def strains(c):
        sigma, _, det, _ = lengths(c)
        _, surface, _ = principal_lengths(baseline_tangent, tangent_modes, c)
        return np.r_[
            (sigma - 0.75).ravel(),
            (limits[:, None] - sigma).ravel(),
            det - 0.1,
            (surface - 0.75).ravel(),
            (surface_limits[:, None] - surface).ravel(),
        ]

    def strain_jac(c):
        _, jac, _, det_jac = lengths(c)
        j = jac.reshape(-1, count * 3)
        _, _, sj = principal_lengths(baseline_tangent, tangent_modes, c)
        sj = sj.reshape(-1, count * 3)
        return np.vstack((j, -j, det_jac, sj, -sj))

    def room(c):
        return np.asarray(margin(target + values @ c.reshape(count, 3)))

    def room_jac(c):
        q = target + values @ c.reshape(count, 3)
        gradient = np.column_stack(
            [(margin(q + np.eye(3)[i] * 0.001) - margin(q - np.eye(3)[i] * 0.001)) / 0.002 for i in range(3)]
        )
        return np.einsum("nk,ni->nki", values, gradient).reshape(len(q), -1)

    start = np.zeros(count * 3)
    if initial is not None:
        if not (
            initial.get("affine_residual")
            and np.allclose(initial["matrix"], matrix)
            and np.array_equal(np.asarray(initial["centres"]).reshape(-1, 3), centres)
            and np.allclose(initial["anchors_world"], fixed)
            and initial["width_mm"] == width
        ):
            raise ValueError("A continued field must use the same placement, controls and exact anchors")
        start = np.asarray(initial["coefficients"]).ravel()
        if start.shape != (count * 3,) or not np.isfinite(start).all():
            raise ValueError("Invalid continued field coefficients")
        # New held-out constraints can exclude the old iterate. Retreat the INITIAL GUESS toward the original
        # feasible affine placement; never clamp individual vertices or accept a budget violation.
        for _ in range(80):
            if strains(start).min() > 1e-7:
                break
            start *= 0.99
        else:
            start = np.zeros(count * 3)
    # SciPy's installed constructor annotation narrows jac to str despite its documented callable support.
    constraint = cast(Any, NonlinearConstraint)
    result = minimize(
        lambda c: (float(c @ c), 2 * c),
        start,
        jac=True,
        hess=lambda c: 2 * np.eye(len(c)),
        method="trust-constr",
        constraints=[
            constraint(strains, 0, np.inf, jac=strain_jac, keep_feasible=True),
            constraint(room, 0, np.inf, jac=room_jac),
        ],
        options={
            "maxiter": maxiter,
            "gtol": 1e-9,
            "xtol": 1e-10,
            "barrier_tol": 1e-10,
            "sparse_jacobian": True,
            "factorization_method": "AugmentedSystem",
            "initial_barrier_parameter": 1e-4,
            "initial_constr_penalty": 1000.0,
        },
    )
    # Interior steps preserve the strain budget; an active-set finish resolves thin-triangle boundary constraints.
    if room(result.x).min() < -1e-6 or strains(result.x).min() < -1e-6:
        polished = minimize(
            lambda c: (float(c @ c), 2 * c),
            result.x,
            jac=True,
            method="SLSQP",
            constraints=[
                {"type": "ineq", "fun": strains, "jac": strain_jac},
                {"type": "ineq", "fun": room, "jac": room_jac},
            ],
            options={"maxiter": maxiter, "ftol": 1e-10},
        )
        if room(polished.x).min() >= -1e-6 and strains(polished.x).min() >= -1e-6:
            result = polished
    sigma, _, det, _ = lengths(result.x)
    _, surface, _ = principal_lengths(baseline_tangent, tangent_modes, result.x)
    minimum_room = float(room(result.x).min())
    field = {
        "version": 1,
        "kind": "anchor_conditioned_gaussian",
        "affine_residual": True,
        "matrix": matrix.tolist(),
        "uniform_scale": float(scale),
        "anchors_world": fixed.tolist(),
        "centres": centres.tolist(),
        "width_mm": float(width),
        "coefficients": result.x.reshape(count, 3).tolist(),
    }
    report = {
        "optimizer_success": bool(result.success),
        "message": str(result.message),
        "iterations": int(result.nit),
        "minimum_length": float(sigma.min()),
        "maximum_length": float(sigma.max()),
        "minimum_determinant": float(det.min()),
        "minimum_triangle_length": float(surface.min()) if len(surface) else None,
        "maximum_triangle_length": float(surface.max()) if len(surface) else None,
        "minimum_sampled_room_mm": minimum_room,
        "sampled_feasible": bool(strains(result.x).min() >= -1e-6 and minimum_room >= -1e-6),
        "scope": "SAMPLED field constraints only; full original/Sculpt surfaces, joints and exact Skin remain mandatory",
    }
    return field, report
