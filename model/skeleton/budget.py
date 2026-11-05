"""Fixed ORIGINAL-anatomy growth allowances (confirmed 2026-11-05); never an optimizer variable.

All lengths may squash only to75%. Default stretch is125%. Posterior/inferior cranial source zones and
ribs/cartilages may reach150%, with C2 transitions and protected facial/articular/attachment neighborhoods.
Coordinates and protection witnesses are original BodyParts3D Basis millimetres, before any region resize.
"""

import hashlib

import numpy as np

CRANIAL = {
    "occipital bone",
    "L parietal bone",
    "R parietal bone",
    "L temporal bone",
    "R temporal bone",
    "sphenoid bone",
}
SUPPORT = (
    {f"C{i}" for i in range(1, 8)}
    | {f"T{i}" for i in range(1, 13)}
    | {"manubrium", "body of sternum", "xiphoid process"}
)


def stamp(arrays, bones):
    h = hashlib.sha256()
    for b in sorted(bones, key=lambda b: b["name"]):
        h.update(b["name"].encode())
        h.update(np.asarray(arrays[b["key"] + "_basis"], dtype=np.float64).tobytes())
        h.update(np.asarray(arrays[b["key"] + "_faces"], dtype=np.int32).tobytes())
    return h.hexdigest()


def reference(arrays, bones, facts):
    return {
        "version": 1,
        "basis_sha256": stamp(arrays, bones),
        "c0": facts["canals"]["C1"]["centre"],
        "eyes": [facts["landmarks"][f"LM {side} orbit"] for side in ("L", "R")],
        "condyles": [facts["landmarks"][f"LM {side} condyle"] for side in ("L", "R")],
        "scope": "Fixed original-source posterior/inferior cranial and rib/cartilage allowances; compression floor .75 everywhere",
    }


def support_mesh(arrays, bones):
    import trimesh

    members = [
        trimesh.Trimesh(arrays[b["key"] + "_basis"], arrays[b["key"] + "_faces"], process=False)
        for b in bones
        if b["name"] in SUPPORT
    ]
    if not members:
        raise ValueError("Missing original support geometry for rib attachment protection")
    return trimesh.util.concatenate(members)


def smooth(t):
    t = np.clip(t, 0, 1)
    return t**3 * (t * (6 * t - 15) + 10)


def cranial_weight(y, z, reference):
    c0, eyes = np.asarray(reference["c0"]), np.asarray(reference["eyes"])
    posterior = smooth((y - c0[1]) / 20)
    inferior = smooth((eyes[:, 2].mean() - 20 - z) / 20) * smooth((y - (c0[1] - 20)) / 20)
    return 1 - (1 - posterior) * (1 - inferior)


def protected(reference):
    for key, radius in (("c0", 35), ("eyes", 45), ("condyles", 20)):
        centres = np.asarray(reference[key]).reshape(-1, 3)
        for centre in centres:
            yield centre, radius


def caps(bone, basis, reference, support=None):
    """Per-source-vertex upper length factor. No fitted position, transform or target changes this mask.

    Cranial planes are tied to the native C1 canal protection centre and orbital height. This broad C0 sphere is
    protective only: it does NOT claim the C1 canal centroid is the anatomical C0 articular rotation axis.
    Rib attachment protection uses actual original spinal/sternal surfaces, not the fitted rib's endpoints.
    """
    basis = np.asarray(basis)
    if bone.startswith(("L rib ", "R rib ", "L costal cartilage ", "R costal cartilage ")):
        import trimesh

        if support is None:
            raise ValueError("Missing original support geometry for rib attachment protection")
        _, distance, _ = trimesh.proximity.closest_point(support, basis)
        weight = smooth((distance - 15) / 20)
    elif bone in CRANIAL:
        weight = cranial_weight(basis[:, 1], basis[:, 2], reference)
        for centre, radius in protected(reference):
            weight *= smooth((np.linalg.norm(basis - centre, axis=1) - radius) / 10)
    else:
        weight = np.zeros(len(basis))
    return 1.25 + 0.25 * weight


def face_caps(bone, triangles, reference, support=None):
    """Conservative allowance valid EVERYWHERE on a source triangle, including protected-core crossings."""
    import trimesh

    if bone in CRANIAL:
        # Plane weights increase with Y and decrease with Z; these extrema bound their smooth union below.
        weight = cranial_weight(triangles[:, :, 1].min(axis=1), triangles[:, :, 2].max(axis=1), reference)
        for centre, radius in protected(reference):
            closest = trimesh.triangles.closest_point(triangles, np.broadcast_to(centre, (len(triangles), 3)))
            distance = np.linalg.norm(closest - centre, axis=1)
            weight *= smooth((distance - radius) / 10)
    elif bone.startswith(("L rib ", "R rib ", "L costal cartilage ", "R costal cartilage ")):
        if support is None:
            raise ValueError("Missing original support geometry for rib attachment protection")
        _, d, _ = trimesh.proximity.closest_point(support, triangles.reshape(-1, 3))
        diameter = np.linalg.norm(triangles - np.roll(triangles, 1, axis=1), axis=2).max(axis=1)
        # Distance to a fixed surface is1-Lipschitz; subtracting the whole triangle diameter is conservative.
        weight = smooth((d.reshape(-1, 3).min(axis=1) - diameter - 15) / 20)
    else:
        weight = np.zeros(len(triangles))
    return 1.25 + 0.25 * weight
