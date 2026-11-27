"""The Warp (docs/adr/0025, #874): BodyParts3D's original Basis fitted to the Mech, in the head's frame (mm, the eyes'
middle at the origin). Each region (the skull, the mandible, the neck) is resized uniformly about the eyes' middle and
placed, then the skull and the mandible each take one smooth field, a cubic B-spline lattice (LATTICE mm), solved so
the functional landmarks land on the Mech: the orbits on the eyes, the condyles on the jaw's hinge, the occipital
condyles on the tilt axis, the skull's box on the compact head's (LO, HI). Its local length factors, the singular
values of the field's Jacobian at every vertex, stay within the confirmed budget (budget.py) or the fit raises. The
neck's seven vertebrae are only resized and moved, each canal onto the cervical canal's path, C1's round the pan axis.

rewarp.py hands Blender's Basis over and writes the Warp back: `warp(basis, faces, landmarks)`."""

import numpy as np
import scipy.sparse as sp
import trimesh
from scipy import ndimage
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import minimize
from scipy.spatial import cKDTree

from model import geometry as g
from model import gimbal, neck, skin
from model.skeleton import budget

LATTICE = 20.0  # the field's control spacing, mm
LOW, MARGIN = 0.75, 0.01  # the compression floor; the solve's margin inside every bound, so the check passes
TOL_MM = 1.0  # a functional landmark's miss, at most
NECK = g.NECK  # C1 (the atlas) to C7
JAW = "mandible"
TILT, HINGE, PAN = (neck.HEAD_AXES[k][0] for k in ("tilt", "jaw", "pan"))
C0_BELOW = (
    3.0  # the occipital condyles' lowest points under the tilt axis, which runs through their curvature (inferred)
)
# the box the skull fills (the head's frame): the compact head's (gimbal.HEAD_MM) round #975's mechanism, its eyes 0.54
# up it; the finished bones' own box is base.DOME
LO, HI = np.array(((-80.0, -41.0, -93.5), (80.0, 134.9, 80.0)))
# the eyes-and-nose gate (#991), from the fit measured on 2026-11-27: within FACE_R of each orbit's centre and the
# nasal aperture's middle no triangle may fold; a sound one (its longest edge at most SOUND heights, 98% of them)
# shears at most SHEAR_MAX (measured 1.72; the budget's own 1.25 / 0.75 at a point is 1.67), a slenderer one shearing
# with the field's bend along it, whatever the Warp (measured up to 5.1); the Jacobian stays over JACOBIAN_MIN
FACE_R, SOUND, SHEAR_MAX, JACOBIAN_MIN = 30.0, 20.0, 1.8, 0.5
# the skull-base guides (#991): the cranial growth zone's under side (budget.caps over halfway to its 1.5, under BASE_Z)
# drawn down toward the head's bottom (LO), which the Skin's nape and under-jaw lie past (z -100 at y 129 and -110
# at y 3 on the private reference, our measure, inferred), each vertex no lower than CLEAR_MM over what moves under it:
# the vertebrae over the tilt's and the pan's ranges. GUIDE: the pull's weight against the budget's
GUIDE, BASE_Z, CLEAR_MM = 0.02, TILT[2] + 20.0, 1.6  # model/skeleton's CLEAR_MM
POSES = [(t, p) for t in np.linspace(*neck.RANGES["tilt"], 9) for p in np.linspace(*neck.RANGES["pan"], 7)]
GAP_MM = 15.6  # the alveolar ridges' gap at rest in BodyParts3D's own articulation (it has no teeth), kept
SCALES = {"skull": 1.05, "mandible": 0.95}  # the regions' uniform resize (the neck's: neck_scale())
# the Skin's neck back, the head's frame: its y (BACK_Y) at |x| (BACK_X) and z (BACK_Z), our own coarse measure of the
# private Morty reference (docs/adr/0025: a coarse hull of our own, inferred), from his nape down to his shoulders; a
# vertebra stays ROOM in front of it: the Skin's wall and the clearance behind it
BACK_X, BACK_Z = (0.0, 20.0, 40.0), (-150.0, -140.0, -130.0, -120.0, -110.0, -100.0, -90.0)
BACK_Y = (
    (126.7, 125.4, 122.9, 118.0, 114.7, 128.9, 140.6),
    (124.9, 123.6, 121.6, 117.6, 111.8, 126.8, 138.6),
    (119.1, 118.9, 117.5, 114.6, 108.9, 117.1, 132.8),
)
ROOM, AIM = skin.WALL + CLEAR_MM, 1.0  # the solve's margin inside it, so the check passes


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


def solve(x, caps, pairs, scale, box, reach=(), guide=None):
    """The field over the region's Basis `x` (n, 3): x -> scale * (x + u(x)). `pairs`: (Basis point, target, per-axis
    weight); `box` (lo, hi): the warped region inside it; `reach`: (axis, bound, +1 its max or -1 its min) to touch;
    `guide` (rows, floors): those vertices drawn down toward their floors (z), softly: the budget and the pairs win.
    Returns the warped x, the field's Jacobians (n, 3, 3) and the warped pair points."""
    lo = x.min(0) - LATTICE
    shape = np.ceil((x.max(0) + LATTICE - lo) / LATTICE).astype(int) + 3
    B = lattice(x, lo, shape)
    P, T, W = (np.array([p[i] for p in pairs], float) for i in range(3))
    Bp = lattice(P, lo, shape)[0]
    k = B[0].shape[1]

    def jacobians(d):
        return np.eye(3) + np.stack([B[j + 1] @ d for j in range(3)], -1)

    def energy(z):
        d = z.reshape(k, 3)
        y = scale * (x + B[0] @ d)
        u, s, vt = np.linalg.svd(jacobians(d))
        over, under = np.maximum(s[:, 0] - (caps - MARGIN), 0), np.maximum(LOW + MARGIN - s[:, 2], 0)
        gf = 2 * (over[:, None, None] * (u[:, :, :1] @ vt[:, :1]) - under[:, None, None] * (u[:, :, 2:] @ vt[:, 2:]))
        e = 1e4 * (over @ over + under @ under)
        gd = 1e4 * sum(B[j + 1].T @ gf[:, :, j] for j in range(3))
        r = (scale * (P + Bp @ d) - T) * W
        e += 10 * (r * r).sum()
        gd += 20 * scale * (Bp.T @ (r * W))
        gy = np.zeros_like(y)
        for sign, bound in ((1, box[1]), (-1, box[0])):
            v = np.maximum(sign * (y - bound), 0)
            e += 10 * (v * v).sum()
            gy += 20 * sign * v
        for axis, bound, sign in reach:
            j = np.argmax(sign * y[:, axis])
            e += 10 * (y[j, axis] - bound) ** 2
            gy[j, axis] += 20 * (y[j, axis] - bound)
        if guide:
            v = np.maximum(y[guide[0], 2] - guide[1], 0)
            e += GUIDE * (v * v).sum()
            gy[guide[0], 2] += 2 * GUIDE * v
        gd += scale * (B[0].T @ gy)
        return e + 1e-3 * (z @ z), (gd + 2e-3 * d).ravel()

    d = minimize(energy, np.zeros(k * 3), jac=True, method="L-BFGS-B", options={"maxiter": 4000, "maxfun": 8000})
    d = d.x.reshape(k, 3)
    return scale * (x + B[0] @ d), jacobians(d), scale * (P + Bp @ d)


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


def floors(points, obstacles, reach=CLEAR_MM + 2.0):
    """Each point's floor: CLEAR_MM and the solve's AIM over the top of the `obstacles` under it (within `reach` in
    plan), the head's bottom (LO) where nothing is."""
    near = cKDTree(obstacles[:, :2]).query_ball_point(points[:, :2], reach)
    tops = [obstacles[i, 2][obstacles[i, 2] < p[2]].max(initial=-np.inf) for i, p in zip(near, points)]
    return np.maximum(np.array(tops) + CLEAR_MM + AIM, LO[2])


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


def back(p):
    """The Skin's neck back behind each point of `p` (n, 3): its y (BACK_Y), level past the measure's ends."""
    at = np.stack([np.clip(np.abs(p[:, 0]), BACK_X[0], BACK_X[-1]), np.clip(p[:, 2], BACK_Z[0], BACK_Z[-1])], 1)
    return RegularGridInterpolator((BACK_X, BACK_Z), BACK_Y)(at)


def vertebrae(basis, faces):
    """({vertebra: fitted vertices}, the report): C1 to C7 resized uniformly about C1's top, under the occipital
    condyles, each canal onto the path, C1's round the pan axis; then one field over them all that brings every spine
    ROOM in front of the Skin's neck back, each canal and each body's front staying where they stand."""
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
    hi = np.full_like(x, np.inf)
    hi[:, 1] = back(x) - ROOM - AIM
    caps = np.full(len(x), 1.25)
    y, f, hit = solve(x, caps, pairs, 1.0, ((-np.inf, -np.inf, neck.CERVICAL_PATH[2][1]), hi))  # over the path's foot
    room = float((back(y) - y[:, 1]).min())
    if room < ROOM:
        raise ValueError(f"the neck comes within {room:.2f} mm of the Skin's back, less than {ROOM}")
    report = _region(f, caps, hit, pairs) | {"scale": s, "skin_back_mm": round(room, 2)}
    return dict(zip(NECK, np.split(y, np.cumsum([len(v) for v in placed])[:-1]))), report


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


def warp(basis, faces, landmarks):
    """({bone: warped vertices}, the report) from {bone: Basis vertices}, {bone: triangles} and the Basis's landmarks
    {name: point} (the scene's LM empties), all in the head's frame."""
    lm = {k.removeprefix("LM "): np.asarray(v, float) for k, v in landmarks.items()}
    occ = occipital_condyles(basis["occipital bone"])
    ref = {
        "c0": np.mean(occ, 0),
        "eyes": [lm["L orbit"], lm["R orbit"]],
        "condyles": [lm["L condyle"], lm["R condyle"]],
    }
    out, report = {}, {"scales": dict(SCALES)}
    fitted, report["neck"] = vertebrae(basis, faces)
    report["scales"]["neck"] = report["neck"].pop("scale")

    skull = [n for n in basis if n not in (*NECK, JAW)]
    x = np.vstack([basis[n] for n in skull])
    caps = np.concatenate([budget.caps(n, basis[n], ref) for n in skull])
    sizes = [len(basis[n]) for n in skull]
    tris = np.vstack([faces[n] + at for n, at in zip(skull, np.cumsum([0, *sizes[:-1]]))])
    # the skull base's guides: its growth zone's under side, down to the head's bottom or over the neck as it moves
    zone = np.flatnonzero((caps > 1.375) & (SCALES["skull"] * x[:, 2] < BASE_Z))
    moving = np.vstack([seen(surface(fitted[n], faces[n]), *pose) for n in NECK for pose in POSES])
    lo = np.tile(LO, (len(x), 1))
    lo[zone, 2] = floors(SCALES["skull"] * x[zone], moving)
    pairs = [
        *((lm[f"{s} orbit"], (sign * gimbal.SPACING / 2, 0, 0), (1, 1, 1)) for s, sign in (("L", 1), ("R", -1))),
        *((lm[f"{s} condyle"], HINGE, (0, 1, 1)) for s in "LR"),
        *((p, (0, TILT[1], TILT[2] - C0_BELOW), (0, 1, 1)) for p in occ),
    ]
    touch = ((2, HI[2], 1), (1, LO[1], -1), (1, HI[1], 1))
    y, f, hit = solve(x, caps, pairs, SCALES["skull"], (lo, HI), touch, (zone, lo[zone, 2]))
    report["skull"] = _region(f, caps, hit, pairs)
    report["eyes_and_nose"] = gate(x, y, tris, np.linalg.det(f), [*ref["eyes"], aperture(basis)])
    base = np.isin(tris, zone).all(axis=1)
    room = float(cKDTree(moving).query(surface(y, tris[base]))[0].min())
    if room < CLEAR_MM:
        raise ValueError(
            f"the skull base comes within {room:.2f} mm of the neck as the head moves, less than {CLEAR_MM}"
        )
    report["skull_base"] = {
        "vertices": len(zone),
        "lowered_mm": round(float(np.median(SCALES["skull"] * x[zone, 2] - y[zone, 2])), 1),
        "lowest": round(float(y[zone, 2].min()), 1),
        "neck_mm": round(room, 2),
    }
    out |= dict(zip(skull, np.split(y, np.cumsum(sizes)[:-1])))

    # the mandible: its condyles on the hinge, its chin on the box's bottom, its ridge GAP_MM under the maxillae's
    upper = np.vstack([out["L maxilla"], out["R maxilla"]])
    ridge = upper[upper[:, 2].argmin()]
    m = basis[JAW]
    top = m[np.abs(m[:, 0]) < 8]
    top = top[top[:, 2].argmax()]
    pairs = [
        *((lm[f"{s} condyle"], HINGE, (0, 1, 1)) for s in "LR"),
        (lm["menton"], (0, 0, LO[2]), (0, 0, 1)),
        (top, (0, ridge[1], ridge[2] - GAP_MM * SCALES["mandible"]), (1, 1, 1)),
    ]
    caps = budget.caps(JAW, m, ref)
    out[JAW], f, hit = solve(m, caps, pairs, SCALES["mandible"], (LO, HI))
    report["mandible"] = _region(f, caps, hit, pairs)

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
        )
        np.savez(dst, **{n: v + frame for n, v in out.items()})
        json.dump(report, open(rep, "w"))
        print(json.dumps(report), flush=True)
        blender("apply", dst, rep)


if __name__ == "__main__":
    import sys

    rewarp(sys.argv[1])
