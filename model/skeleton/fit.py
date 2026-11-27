"""The Warp (docs/adr/0025, #874): BodyParts3D's original Basis fitted to the Mech inside Morty's skin, in the head's
frame (mm, the eyes' middle at the origin). Each region (the skull, the mandible, the neck) is resized uniformly about
the eyes' middle and placed, then takes one smooth field, a cubic B-spline lattice (LATTICE mm), solved so the
functional landmarks land on the Mech (the orbits on the eyes, the condyles on the jaw's hinge, the occipital condyles
on the tilt axis, each vertebra's canal on the cervical canal's path, C1's round the pan axis) and every vertex lies
RAW under Morty's skin (envelope.py: the sculpt's surface, the bones' limit since 2026-11-27). The cranium's outer
side is drawn out to that limit, softly, so the vault closes over the mechanism and the skull base comes down toward
his nape. Its local length factors, the singular values of the field's Jacobian at every vertex, stay within the
confirmed budget (budget.py) or the fit raises.

rewarp.py hands Blender's Basis over and writes the Warp back: `warp(basis, faces, landmarks, skin)`."""

import numpy as np
import scipy.sparse as sp
import trimesh
from scipy import ndimage
from scipy.optimize import minimize
from scipy.spatial import cKDTree

from model import geometry as g
from model import gimbal, neck
from model.skeleton import budget, envelope

LATTICE = 20.0  # the field's control spacing, mm
LOW, MARGIN = 0.75, 0.01  # the compression floor; the solve's margin inside every bound, so the check passes
TOL_MM = 1.0  # a functional landmark's miss, at most
ROUNDS = 6  # the solve's rounds, at most, each adding the face points still short of the skin's limit
# the solve's weights: on a length factor past the budget, a landmark's miss and a vertex past its limit (a mm2 each)
BUDGET, PAIR, SKIN = 1e6, 1e3, 1e2
NECK = g.NECK  # C1 (the atlas) to C7
JAW = "mandible"
TILT, HINGE, PAN = (neck.HEAD_AXES[k][0] for k in ("tilt", "jaw", "pan"))
C0_BELOW = (
    3.0  # the occipital condyles' lowest points under the tilt axis, which runs through their curvature (inferred)
)
# a Warp's vertex under Morty's skin, at least: the limit and half the Finish's voxel, which its remesh can grow a
# bone by (model/skeleton PITCH); AIM: the solve's margin inside it, so the check passes
RAW, AIM = envelope.ROOM + 0.4, 0.5
# the eyes-and-nose gate (#991), from the fit measured in Morty's skin on 2026-11-27: within FACE_R of each orbit's
# centre and the nasal aperture's middle no triangle may fold; a sound one (its longest edge at most SOUND heights)
# shears at most SHEAR_MAX (measured 2.09 on a frontal triangle 12 mm long; the budget's own bound at a point is 1.25 /
# 0.75 = 1.67, 2.0 in the growth zone), a slenderer one shearing with the field's bend along it, whatever the Warp; the
# Jacobian stays over JACOBIAN_MIN (measured 0.61)
FACE_R, SOUND, SHEAR_MAX, JACOBIAN_MIN = 30.0, 20.0, 2.2, 0.5
# the cranium's outer side (the vault's bones' farthest vertices from MIDDLE on the Basis, outer()) drawn
# out to RAW under Morty's skin, FILL its pull's weight (on the rows' mean square gap): the vault closes over the mechanism,
# which lies 10 mm and more under his skin there, and (#991's skull-base guides) the growth zone's under side comes
# down toward his nape and under-jaw, each vertex of it under BASE_Z at least CLEAR_MM off what moves under it: the
# vertebrae over the tilt's and the pan's ranges
FILL, MIDDLE, BASE_Z, CLEAR_MM = 2.0, (0.0, 80.0, 45.0), TILT[2] + 20.0, 1.6  # model/skeleton's CLEAR_MM
VAULT, VAULT_EL = (*sorted(budget.CRANIAL), "frontal bone"), -20.0  # its bones; degrees up from MIDDLE
POSES = [(t, p) for t in np.linspace(*neck.RANGES["tilt"], 9) for p in np.linspace(*neck.RANGES["pan"], 7)]
GAP_MM = 15.6  # the alveolar ridges' gap at rest in BodyParts3D's own articulation (it has no teeth), kept
# the regions' uniform resize (the neck's: neck_scale()): the skull's back and crown then stand at Morty's own
SCALES = {"skull": 1.05, "mandible": 1.0}


def lattice(points, lo, shape):
    """The cubic B-spline lattice's weights at `points`: [value, d/dx, d/dy, d/dz], each a sparse (n, nodes)."""
    t = (points - lo) / LATTICE
    i = np.floor(t).astype(int)
    t -= i
    b = [np.stack([(1 - s) ** 3, 3 * s**3 - 6 * s**2 + 4, -3 * s**3 + 3 * s**2 + 3 * s + 1, s**3], -1) / 6 for s in t.T]
    db = [
        np.stack([-3 * (1 - s) ** 2, 9 * s**2 - 12 * s, -9 * s**2 + 6 * s + 3, 3 * s**2], -1) / 6 / LATTICE for s in t.T
    ]
    rows, cols, vals = [], [], [[], [], [], []]
    for a in range(4):
        for c in range(4):
            for e in range(4):
                rows.append(np.arange(len(points)))
                cols.append(((i[:, 0] + a) * shape[1] + i[:, 1] + c) * shape[2] + i[:, 2] + e)
                for k, w in enumerate(((b, b, b), (db, b, b), (b, db, b), (b, b, db))):
                    vals[k].append(w[0][0][:, a] * w[1][1][:, c] * w[2][2][:, e])
    r, c, n = np.concatenate(rows), np.concatenate(cols), int(np.prod(shape))
    return [sp.csr_matrix((np.concatenate(v), (r, c)), shape=(len(points), n)) for v in vals]


def spread(x, faces):
    """Points about 1 mm apart on the mesh's faces (surface()'s), as their vertices' weights: a sparse (points,
    vertices)."""
    mesh = trimesh.Trimesh(x, faces, process=False)
    p, f = trimesh.sample.sample_surface(mesh, int(mesh.area) + 1, seed=0)
    w = trimesh.triangles.points_to_barycentric(mesh.triangles[f], p)
    return sp.csr_matrix((w.ravel(), (np.repeat(np.arange(len(p)), 3), faces[f].ravel())), shape=(len(p), len(x)))


def solve(x, caps, pairs, scale, skin=None, fill=None, lo=-np.inf, clear=None, faces=None):
    """The field over the region's Basis `x` (n, 3): x -> scale * (x + u(x)). `pairs`: (Basis point, target, per-axis
    weight); `skin` (envelope.Skin): every warped vertex RAW under it, and with the region's `faces` the points
    spread over them too (a crease of the skin cuts in between vertices: the points spread over the Basis, then, a
    round at a time, those spread over the Warp that still come short); `fill`: the rows drawn out to that limit,
    softly: the budget and the pairs win; `lo`: the warped region's lower bound; `clear` (rows, points): those rows
    kept CLEAR_MM off the points. Returns the warped x, the field's Jacobians (n, 3, 3) and the warped pair points."""
    origin = x.min(0) - LATTICE
    shape = np.ceil((x.max(0) + LATTICE - origin) / LATTICE).astype(int) + 3
    B = lattice(x, origin, shape)
    P, T, W = (np.array([p[i] for p in pairs], float) for i in range(3))
    Bp = lattice(P, origin, shape)[0]
    k = B[0].shape[1]
    over_faces = spread(x, faces) if skin and faces is not None else None

    def jacobians(d):
        return np.eye(3) + np.stack([B[j + 1] @ d for j in range(3)], -1)

    def energy(z):
        d = z.reshape(k, 3)
        y = scale * (x + B[0] @ d)
        u, s, vt = np.linalg.svd(jacobians(d))
        over, under = np.maximum(s[:, 0] - (caps - MARGIN), 0), np.maximum(LOW + MARGIN - s[:, 2], 0)
        gf = 2 * (over[:, None, None] * (u[:, :, :1] @ vt[:, :1]) - under[:, None, None] * (u[:, :, 2:] @ vt[:, 2:]))
        e = BUDGET * (over @ over + under @ under)
        gd = BUDGET * sum(B[j + 1].T @ gf[:, :, j] for j in range(3))
        r = (scale * (P + Bp @ d) - T) * W
        e += PAIR * (r * r).sum()
        gd += 2 * PAIR * scale * (Bp.T @ (r * W))
        v = np.maximum(lo - y, 0)
        e += 10 * (v * v).sum()
        gy = -20 * v
        if skin:
            depth, inward = skin.depth(y), skin.inward(y, 1e-3)
            v = np.maximum(RAW + AIM - depth, 0)
            e += SKIN * (v * v).sum()
            gy -= 2 * SKIN * v[:, None] * inward
            if fill is not None:
                v = np.maximum(depth[fill] - RAW - AIM, 0)
                e += FILL * (v * v).mean()
                gy[fill] += 2 * FILL / len(v) * v[:, None] * inward[fill]
            if over_faces is not None:
                q = over_faces @ y
                v = np.maximum(RAW + AIM - skin.depth(q), 0)
                e += SKIN * (v * v).sum()
                short = np.flatnonzero(v)
                push = np.zeros_like(q)
                push[short] = v[short, None] * skin.inward(q[short], 1e-3)
                gy -= 2 * SKIN * (over_faces.T @ push)
        if clear:
            off, j = clear[1].query(y[clear[0]])
            v = np.maximum(CLEAR_MM + AIM - off, 0)
            e += SKIN * (v * v).sum()
            gy[clear[0]] -= 2 * SKIN * (v / np.maximum(off, 1e-9))[:, None] * (y[clear[0]] - clear[1].data[j])
        gd += scale * (B[0].T @ gy)
        return e + 1e-3 * (z @ z), (gd + 2e-3 * d).ravel()

    z = np.zeros(k * 3)
    for _ in range(ROUNDS):
        z = minimize(energy, z, jac=True, method="L-BFGS-B", options={"maxiter": 4000, "maxfun": 8000}).x
        d = z.reshape(k, 3)
        y = scale * (x + B[0] @ d)
        if over_faces is None:
            break
        more = spread(y, faces)
        short = skin.depth(more @ y) < RAW + AIM / 2
        if not short.any():
            break
        over_faces = sp.vstack([over_faces, more[short]]).tocsr()
    return y, jacobians(d), scale * (P + Bp @ d)


def stretch(f, caps):
    """Each vertex's least and greatest local length factor; raises past the budget (LOW to its cap)."""
    s = np.linalg.svd(f, compute_uv=False)
    bad = (s[:, 0] > caps) | (s[:, 2] < LOW)
    if bad.any():
        raise ValueError(
            f"local stretch outside the budget at {bad.sum()} vertices: {s[:, 2].min():.3f}..{s[:, 0].max():.3f}"
        )
    return s[:, 2], s[:, 0]


def shear(basis, warped, faces):
    """Each triangle's shear: its greatest over its least in-plane length factor from `basis` to `warped`, 1 where it
    kept its shape (its aspect can change by no more); inf for one flattened to a line."""
    gram = []
    for v in (basis, warped):
        e = np.stack([v[faces[:, 1]] - v[faces[:, 0]], v[faces[:, 2]] - v[faces[:, 0]]], 1)
        gram.append(e @ e.transpose(0, 2, 1))
    with np.errstate(divide="ignore", invalid="ignore"):
        lam = np.sort(np.linalg.eigvals(np.linalg.solve(*gram)).real, axis=1)
        return np.sqrt(lam[:, 1] / lam[:, 0])


def gate(x, y, faces, det, centres):
    """The eyes-and-nose gate (#991) on the Warp `y` of the Basis `x`, over the triangles and vertices within FACE_R of
    `centres` (the orbits' and the nasal aperture's, on the Basis). Raises on a folded triangle (its normal turned past a
    right angle), a sound one (no slenderer than SOUND) sheared past SHEAR_MAX, or a Jacobian (`det`, a vertex each)
    under JACOBIAN_MIN; returns its report."""

    def near(p):
        return np.min([np.linalg.norm(p - c, axis=1) for c in centres], axis=0) < FACE_R

    f = faces[near(x[faces].mean(1))]
    e0, e1 = (v[f[:, [1, 2, 0]]] - v[f] for v in (x, y))
    n0, n1 = (np.cross(e[:, 0], e[:, 1]) for e in (e0, e1))
    folded = int(((n0 * n1).sum(1) <= 0).sum())
    sound = np.linalg.norm(e0, axis=2).max(1) ** 2 <= SOUND * np.linalg.norm(n0, axis=1)  # its longest edge by height
    report = {
        "triangles": len(f),
        "folded": folded,
        "shear": round(float(shear(x, y, f[sound]).max(initial=1.0)), 3),
        "least_jacobian": round(float(det[near(x)].min()), 3),
    }
    if folded or report["shear"] > SHEAR_MAX or report["least_jacobian"] < JACOBIAN_MIN:
        raise ValueError(
            f"the Warp at the eyes and nose: {folded} folded triangles, a sound one sheared {report['shear']} (at most "
            f"{SHEAR_MAX}), the least Jacobian {report['least_jacobian']} (at least {JACOBIAN_MIN})"
        )
    return report


def surface(v, faces):
    """The mesh's vertices and points sampled about 1 mm apart on its faces: its surface, for a distance."""
    mesh = trimesh.Trimesh(v, faces, process=False)
    return np.vstack([v[np.unique(faces)], trimesh.sample.sample_surface(mesh, int(mesh.area) + 1, seed=0)[0]])


def aperture(basis):
    """The nasal aperture's middle on the Basis: between the nasal bones' lowest point and the maxillae's front point
    on the midline (inferred)."""
    nasal, upper = (np.vstack([basis[f"{s} {b}"] for s in "LR"]) for b in ("nasal bone", "maxilla"))
    mid = upper[np.abs(upper[:, 0]) < 4]
    return (nasal[nasal[:, 2].argmin()] + mid[mid[:, 1].argmin()]) / 2


def seen(points, tilt, pan):
    """Points fixed to the neck as the head sees them, tilted and panned (degrees; the pan's axis tilts with it)."""
    turn = trimesh.transformations.rotation_matrix
    head = turn(np.radians(tilt), (1, 0, 0), TILT) @ turn(np.radians(pan), (0, 0, 1), PAN)
    return trimesh.transform_points(points, np.linalg.inv(head))


def canal(mesh, b=0.5):
    """(x, y) of a vertebra's canal: the largest hole in its plan view (its surface sampled, b mm bins)."""
    p = trimesh.sample.sample_surface(mesh, int(mesh.area / b**2 * 4), seed=0)[0][:, :2]
    lo = p.min(axis=0)
    ij = np.floor((p - lo) / b).astype(int)
    occ = np.zeros(ij.max(axis=0) + 1, bool)
    occ[ij[:, 0], ij[:, 1]] = True
    occ = ndimage.binary_closing(occ, iterations=2)
    holes = ndimage.binary_fill_holes(occ) & ~occ
    label, n = ndimage.label(holes)
    biggest = np.argmax(ndimage.sum(holes, label, range(1, n + 1))) + 1
    return np.argwhere(label == biggest).mean(axis=0) * b + lo


def canal_y(z):
    """The cervical canal's path (model/neck.py CERVICAL_PATH, from its foot up): its y at height z."""
    y, zs = np.array(neck.CERVICAL_PATH[2:]).T
    return float(np.interp(z, zs, y))


def occipital_condyles(occipital):
    """Each occipital condyle's lowest points' middle (L, R): the occipital's lowest 5 to 30 mm off the midline."""
    out = []
    for side in (1, -1):
        p = occipital[(occipital[:, 0] * side > 5) & (occipital[:, 0] * side < 30)]
        out.append(p[p[:, 2] < p[:, 2].min() + 3].mean(0))
    return out


def neck_scale(basis):
    """The neck's uniform resize: C1's top to C7's foot, from under the occipital condyles to the canal path's foot."""
    span = basis[NECK[0]][:, 2].max() - basis[NECK[-1]][:, 2].min()
    return round((TILT[2] - C0_BELOW - 0.5 - neck.CERVICAL_PATH[2][1]) / span, 3)


def vertebrae(basis, faces, skin):
    """({vertebra: fitted vertices}, the report): C1 to C7 resized uniformly about C1's top, under the occipital
    condyles, each canal onto the path, C1's round the pan axis; then one field over them all that brings every spine
    RAW under `skin` (Morty's neck and shoulders), each canal and each body's front staying where they stand."""
    s, top = neck_scale(basis), basis[NECK[0]][:, 2].max()
    placed, pairs = [], []
    for n in NECK:
        v = basis[n]
        c, zc = canal(trimesh.Trimesh(v, faces[n], process=False)), (v[:, 2].min() + v[:, 2].max()) / 2
        z = TILT[2] - C0_BELOW - 0.5 + s * (zc - top)
        at = (0.0, PAN[1] if n == NECK[0] else canal_y(z), z)
        placed.append(s * (v - (*c, zc)) + at)
        front = placed[-1][placed[-1][:, 1].argmin()]
        pairs += [(at, at, (1, 1, 1)), (front, front, (1, 1, 1))]
    x = np.vstack(placed)
    caps = np.full(len(x), 1.25)
    tris = np.vstack([faces[n] + at for n, at in zip(NECK, np.cumsum([0, *map(len, placed[:-1])]))])
    foot = (-np.inf, -np.inf, neck.CERVICAL_PATH[2][1])  # the path's
    y, f, hit = solve(x, caps, pairs, 1.0, skin, lo=foot, faces=tris)
    report = _region(f, caps, hit, pairs) | {"scale": s, "skin_mm": _under(skin, y, tris)}
    return dict(zip(NECK, np.split(y, np.cumsum([len(v) for v in placed])[:-1]))), report


def _under(skin, y, faces):
    """The warped surface's least depth under the skin (its vertices and points 1 mm apart on it); raises under RAW."""
    points = surface(y, faces)
    depth = skin.depth(points)
    if depth.min() < RAW:
        at = points[depth.argmin()].round(1).tolist()
        raise ValueError(f"the bone comes within {depth.min():.2f} mm of Morty's skin at {at}, less than {RAW}")
    return round(float(depth.min()), 2)


def _region(f, caps, hit, pairs):
    lo, hi = stretch(f, caps)
    miss = np.abs(hit - np.array([p[1] for p in pairs])) * np.array([p[2] for p in pairs])
    if miss.max() > TOL_MM:
        raise ValueError(f"a landmark misses by {miss.max():.2f} mm")
    return {
        "stretch": [round(float(lo.min()), 3), round(float(hi.max()), 3)],
        "over_1.25": int((hi > 1.25).sum()),
        "least_jacobian": round(float(np.linalg.det(f).min()), 3),
        "landmark_mm": round(float(miss.max()), 2),
    }


def outer(x, caps, step=3.0, skin=3.0):
    """Which of the skull's vertices `x` lie on its outer side, where Morty's skin is to be reached: within `skin` mm
    of the farthest one from the cranium's MIDDLE in their direction (`step` degrees a bin), over the skull base
    (VAULT_EL up from MIDDLE) or on the growth zone's under side (`caps` over halfway to its 1.5)."""
    v = x - MIDDLE
    r = np.linalg.norm(v, axis=1)
    az, el = np.degrees(np.arctan2(v[:, 0], v[:, 1])), np.degrees(np.arcsin(v[:, 2] / r))
    bins = (np.floor(az / step).astype(int) + 1000) * 1000 + np.floor(el / step).astype(int)
    _, at = np.unique(bins, return_inverse=True)
    far = np.zeros(at.max() + 1)
    np.maximum.at(far, at, r)
    return (r > far[at] - skin) & ((el > VAULT_EL) | (caps > 1.375))


def warp(basis, faces, landmarks, skin):
    """({bone: warped vertices}, the report) from {bone: Basis vertices}, {bone: triangles}, the Basis's landmarks
    {name: point} (the scene's LM empties) and Morty's `skin` (envelope.Skin), all in the head's frame."""
    lm = {k.removeprefix("LM "): np.asarray(v, float) for k, v in landmarks.items()}
    occ = occipital_condyles(basis["occipital bone"])
    ref = {
        "c0": np.mean(occ, 0),
        "eyes": [lm["L orbit"], lm["R orbit"]],
        "condyles": [lm["L condyle"], lm["R condyle"]],
    }
    out, report = {}, {"scales": dict(SCALES)}
    fitted, report["neck"] = vertebrae(basis, faces, skin)
    report["scales"]["neck"] = report["neck"].pop("scale")

    skull = [n for n in basis if n not in (*NECK, JAW)]
    x = np.vstack([basis[n] for n in skull])
    caps = np.concatenate([budget.caps(n, basis[n], ref) for n in skull])
    sizes = [len(basis[n]) for n in skull]
    tris = np.vstack([faces[n] + at for n, at in zip(skull, np.cumsum([0, *sizes[:-1]]))])
    fill = np.flatnonzero(outer(x, caps) & np.concatenate([np.full(len(basis[n]), n in VAULT) for n in skull]))
    # the skull base: its growth zone's under side stays clear of the neck as the head moves
    zone = np.flatnonzero((caps > 1.375) & (SCALES["skull"] * x[:, 2] < BASE_Z))
    moving = cKDTree(np.vstack([seen(surface(fitted[n], faces[n]), *pose) for n in NECK for pose in POSES]))
    pairs = [
        *((lm[f"{s} orbit"], (sign * gimbal.SPACING / 2, 0, 0), (1, 1, 1)) for s, sign in (("L", 1), ("R", -1))),
        *((lm[f"{s} condyle"], HINGE, (0, 1, 1)) for s in "LR"),
        *((p, (0, TILT[1], TILT[2] - C0_BELOW), (0, 1, 1)) for p in occ),
    ]
    y, f, hit = solve(x, caps, pairs, SCALES["skull"], skin, fill, clear=(zone, moving), faces=tris)
    report["skull"] = _region(f, caps, hit, pairs) | {"skin_mm": _under(skin, y, tris)}
    report["eyes_and_nose"] = gate(x, y, tris, np.linalg.det(f), [*ref["eyes"], aperture(basis)])
    base = np.isin(tris, zone).all(axis=1)
    room = float(moving.query(surface(y, tris[base]))[0].min())
    if room < CLEAR_MM:
        raise ValueError(
            f"the skull base comes within {room:.2f} mm of the neck as the head moves, less than {CLEAR_MM}"
        )
    under = skin.depth(y[fill])
    report["vault"] = {
        "vertices": len(fill),
        "under_skin_mm": [round(float(np.percentile(under, q)), 1) for q in (50, 90, 100)],  # median, p90, most
        "base_lowest": round(float(y[zone, 2].min()), 1),
        "base_to_neck_mm": round(room, 2),
    }
    out |= dict(zip(skull, np.split(y, np.cumsum(sizes)[:-1])))

    # the mandible: its condyles on the hinge, its ridge GAP_MM under the maxillae's, its chin inside Morty's
    upper = np.vstack([out["L maxilla"], out["R maxilla"]])
    ridge = upper[upper[:, 2].argmin()]
    m = basis[JAW]
    top = m[np.abs(m[:, 0]) < 8]
    top = top[top[:, 2].argmax()]
    pairs = [
        *((lm[f"{s} condyle"], HINGE, (0, 1, 1)) for s in "LR"),
        (top, (0, ridge[1], ridge[2] - GAP_MM * SCALES["mandible"]), (1, 1, 1)),
    ]
    caps = budget.caps(JAW, m, ref)
    out[JAW], f, hit = solve(m, caps, pairs, SCALES["mandible"], skin, faces=faces[JAW])
    report["mandible"] = _region(f, caps, hit, pairs) | {"skin_mm": _under(skin, out[JAW], faces[JAW])}

    return out | fitted, report


def rewarp(scene):
    """`just rewarp`: the scene's Basis out of Blender (rewarp.py), fitted here, the Warp written back and saved."""
    import json
    import os
    import subprocess
    import tempfile

    from model import skeleton, stages

    frame = np.array(stages.DOCS[skeleton.DOC]["eyes"][0])
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rewarp.py")

    def blender(*args):
        r = subprocess.run(
            [skeleton.BLENDER, "--factory-startup", scene, "-P", script, "--", *args],
            text=True,
            capture_output=True,
        )
        if r.returncode or "rewarp: " + args[0] + " done" not in r.stdout:
            raise RuntimeError(f"Blender's rewarp {args[0]} failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")

    with tempfile.TemporaryDirectory() as tmp:
        src, dst, rep = (os.path.join(tmp, f) for f in ("basis.npz", "warped.npz", "report.json"))
        blender("export", src)
        data = np.load(src)
        names = [k.split("|", 1)[1] for k in data if k.startswith("basis|")]
        out, report = warp(
            {n: data["basis|" + n] - frame for n in names},
            {n: data["faces|" + n] for n in names},
            {k.split("|", 1)[1]: data[k] - frame for k in data if k.startswith("landmark|")},
            envelope.morty(),
        )
        np.savez(dst, **{n: v + frame for n, v in out.items()})
        json.dump(report, open(rep, "w"))
        print(json.dumps(report), flush=True)
        blender("apply", dst, rep)


if __name__ == "__main__":
    import sys

    rewarp(sys.argv[1])
