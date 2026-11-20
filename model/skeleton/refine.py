"""Geometry-exact, conforming refinement of original Bone surfaces and their authored shape-key history.

Every new vertex is an original-face barycentric point. Shared edges split once on BOTH incident faces; no vertex
moves, no face is deleted, no shape baseline or anatomical growth allowance is normalized after fitting.
"""

import hashlib

import numpy as np


def mesh(keys, faces, max_edge=1.0, aspect=20.0, rounds=8, select=None, lineage=None):
    """Refine long thin or predicate-selected SOURCE triangles; return extended keys, triangles and original lineage.

    The source-only stopping rule is not an acceptance gate. The caller still checks every final child triangle,
    actual shared-field Jacobian, Sculpt residual and original parent allowance after deformation.
    """
    if max_edge <= 0 or aspect <= 0 or not isinstance(rounds, int) or rounds < 0:
        raise ValueError("Invalid source refinement resolution")
    basis = np.asarray(keys["basis"], dtype=float)
    if basis.ndim != 2 or basis.shape[1] != 3 or not np.isfinite(basis).all():
        raise ValueError("Refinement needs finite original Basis coordinates")
    values = {kind: np.asarray(v, dtype=float).copy() for kind, v in keys.items()}
    if any(v.shape != basis.shape or not np.isfinite(v).all() for v in values.values()):
        raise ValueError("All authored shape keys must share the original Basis topology")
    if lineage is None:
        original = basis.copy()
        original_faces = np.asarray(faces, dtype=np.int64)
        if original_faces.ndim != 2 or original_faces.shape[1] != 3 or not len(original_faces):
            raise ValueError("Refinement needs original source triangles")
        if original_faces.min() < 0 or original_faces.max() >= len(original):
            raise ValueError("Invalid original source triangle index")
        triangles = original_faces.copy()
        parents = np.arange(len(triangles), dtype=np.int64)
        vertex_parent = [-1] * len(original)
        barycentric = [np.zeros(3) for _ in original]
    else:
        original_count = int(lineage["original_vertex_count"])
        original_faces = np.asarray(lineage["original_faces"], dtype=np.int64)
        if original_count <= 0 or original_count > len(basis):
            raise ValueError("Invalid original vertex count in refinement lineage")
        original = basis[:original_count].copy()
        expected = hashlib.sha256(
            original.astype(np.float64).tobytes() + original_faces.astype(np.int32).tobytes()
        ).hexdigest()
        if expected != lineage["original_sha256"]:
            raise ValueError("Refinement lineage does not match immutable original Basis/faces")
        triangles = np.asarray(faces, dtype=np.int64).copy()
        parents = np.asarray(lineage["parent_faces"], dtype=np.int64).copy()
        if triangles.ndim != 2 or triangles.shape[1] != 3 or len(triangles) != len(parents):
            raise ValueError("Refinement triangles and parent_faces must match")
        vertex_parent = list(map(int, lineage["vertex_parent_face"]))
        barycentric = list(np.asarray(lineage["vertex_barycentric"], dtype=float))
        if len(vertex_parent) != len(basis) or len(barycentric) != len(basis):
            raise ValueError("Refinement vertex lineage must match current vertex count")
    for _ in range(rounds):
        points = values["basis"][triangles]
        edges = np.stack((triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]), axis=1)
        length2 = np.sum((points - np.roll(points, -1, axis=1)) ** 2, axis=2)
        area2 = np.linalg.norm(np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0]), axis=1)
        if (area2 < 1e-12).any():
            raise ValueError("A source triangle is degenerate; refinement cannot erase it")
        longest = length2.argmax(axis=1)
        maximum = length2.max(axis=1)
        thin = (maximum > max_edge**2) & (maximum / area2 > aspect)
        if select is None:
            selected = thin
            requested = sorted({tuple(sorted(e)) for e in edges[np.flatnonzero(selected), longest[selected]]})
        else:
            flagged = np.asarray(select(values["basis"], triangles, parents), dtype=bool)
            if flagged.shape != (len(triangles),):
                raise ValueError("Refinement selector must return one boolean per current triangle")
            edge_set = set()
            for f in np.flatnonzero(flagged):
                threshold = 0.3 * maximum[f] if thin[f] else 0.0
                for i in range(3):
                    if length2[f, i] >= threshold and length2[f, i] > max_edge**2:
                        edge_set.add(tuple(sorted(edges[f, i])))
            while edge_set:
                added = False
                for f in np.flatnonzero(thin):
                    row = [tuple(sorted(e)) for e in edges[f]]
                    if any(e in edge_set for e in row):
                        for i, e in enumerate(row):
                            if length2[f, i] >= 0.3 * maximum[f] and length2[f, i] > max_edge**2 and e not in edge_set:
                                edge_set.add(e)
                                added = True
                if not added:
                    break
            requested = sorted(edge_set)
        if not requested:
            break
        ids = {edge: len(values["basis"]) + i for i, edge in enumerate(requested)}
        # A shared original-edge point has more than one valid parent; choose the lowest original face deterministically.
        parent = {}
        for f, row in enumerate(edges):
            for edge in row:
                key = tuple(sorted(edge))
                if key in ids:
                    parent[key] = min(parent.get(key, int(parents[f])), int(parents[f]))
        new_basis = (values["basis"][[e[0] for e in requested]] + values["basis"][[e[1] for e in requested]]) / 2
        for edge, p in zip(requested, new_basis):
            face = parent[edge]
            a, b, c = original[original_faces[face]]
            uv = np.linalg.lstsq(np.column_stack((b - a, c - a)), p - a, rcond=None)[0]
            weights = np.r_[1 - uv.sum(), uv]
            if weights.min() < -1e-9 or np.linalg.norm(weights @ original[original_faces[face]] - p) > 1e-9:
                raise ValueError("A refined point left its immutable original source surface")
            vertex_parent.append(face)
            barycentric.append(weights)
        for kind, v in values.items():
            values[kind] = np.vstack((v, (v[[e[0] for e in requested]] + v[[e[1] for e in requested]]) / 2))
        children, child_parents = [], []
        for f, row in enumerate(triangles):
            split = [tuple(sorted((row[i], row[(i + 1) % 3]))) in ids for i in range(3)]
            count = sum(split)
            if count == 0:
                pieces = [tuple(row)]
            elif count == 3:
                a, b, c = row
                ab, bc, ca = (ids[tuple(sorted((row[i], row[(i + 1) % 3])))] for i in range(3))
                pieces = [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
            else:
                i = split.index(True) if count == 1 else next(i for i in range(3) if split[i] and split[(i + 1) % 3])
                a, b, c = (row[(i + k) % 3] for k in range(3))
                ab = ids[tuple(sorted((a, b)))]
                if count == 1:
                    pieces = [(a, ab, c), (ab, b, c)]
                else:
                    bc = ids[tuple(sorted((b, c)))]
                    p = values["basis"]
                    quad = (
                        [(a, ab, bc), (a, bc, c)]
                        if np.linalg.norm(p[a] - p[bc]) <= np.linalg.norm(p[ab] - p[c])
                        else [(a, ab, c), (ab, bc, c)]
                    )
                    pieces = [(ab, b, bc), *quad]
            children.extend(pieces)
            child_parents.extend([parents[f]] * len(pieces))
        triangles, parents = np.array(children, dtype=np.int64), np.array(child_parents, dtype=np.int64)
    digest = hashlib.sha256(
        original.astype(np.float64).tobytes() + original_faces.astype(np.int32).tobytes()
    ).hexdigest()
    return (
        values,
        triangles,
        {
            "original_sha256": digest,
            "original_vertex_count": len(original),
            "original_faces": original_faces,
            "parent_faces": parents,
            "vertex_parent_face": np.array(vertex_parent, dtype=np.int64),
            "vertex_barycentric": np.array(barycentric),
            "settings": {"max_edge_mm": max_edge, "aspect": aspect, "rounds": rounds},
        },
    )


def adapt(
    keys,
    faces,
    world_fn,
    scale,
    face_maximum=1.25,
    margin_fn=None,
    lineage=None,
    max_edge=0.2,
    aspect=20.0,
    rounds=8,
):
    """Adaptively split only triangles whose deformed chord stretch or midpoint clearance violates the budget."""
    original_count = len(faces) if lineage is None else len(lineage["original_faces"])
    parent_caps = np.broadcast_to(face_maximum, (original_count,))

    def select(basis, triangles, parents):
        target = np.asarray(world_fn(basis), dtype=float)[triangles]
        source = basis[triangles]
        a = np.stack((source[:, 1] - source[:, 0], source[:, 2] - source[:, 0]), axis=2)
        b = np.stack((target[:, 1] - target[:, 0], target[:, 2] - target[:, 0]), axis=2)
        _, r = np.linalg.qr(a)
        sigma = np.linalg.svd(b @ np.linalg.inv(r), compute_uv=False) / scale
        caps = parent_caps[parents]
        bad = (sigma[:, 1] < 0.75 + 1e-4) | (sigma[:, 0] > caps - 1e-4)
        if margin_fn is not None:
            midpoints = 0.5 * (target + np.roll(target, -1, axis=1)).reshape(-1, 3)
            bad |= (np.asarray(margin_fn(midpoints)).reshape(len(triangles), 3) < 0).any(axis=1)
        return bad

    return mesh(keys, faces, max_edge=max_edge, aspect=aspect, rounds=rounds, select=select, lineage=lineage)
