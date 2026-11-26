"""The Warp (docs/adr/0025, #874): BodyParts3D's original Basis fitted to the Mech, in the head's frame (mm, the eyes'
middle at the origin). Each region (the skull, the mandible, the neck) is resized uniformly about the eyes' middle and
placed, then the skull and the mandible each take one smooth field, a cubic B-spline lattice (LATTICE mm), solved so
the functional landmarks land on the Mech: the orbits on the eyes, the condyles on the jaw's hinge, the occipital
condyles on the tilt axis, the skull's box on the compact head's (base.DOME). Its local length factors, the singular
values of the field's Jacobian at every vertex, stay within the confirmed budget (budget.py) or the fit raises. The
neck's seven vertebrae are only resized and moved, each canal onto the cervical canal's path, C1's round the pan axis.

rewarp.py hands Blender's Basis over and writes the Warp back: `warp(basis, faces, landmarks)`."""

import numpy as np
import scipy.sparse as sp
import trimesh
from scipy import ndimage
from scipy.optimize import minimize

from model import base, gimbal, neck
from model import geometry as g
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
LO, HI = np.array(base.DOME).T  # the skull's box in the head's frame: the compact head's round the Mech
GAP_MM = 15.6  # the alveolar ridges' gap at rest in BodyParts3D's own articulation (it has no teeth), kept
SCALES = {"skull": 1.05, "mandible": 0.95}  # the regions' uniform resize (the neck's: neck_scale())


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


def solve(x, caps, pairs, scale, box, reach=()):
    """The field over the region's Basis `x` (n, 3): x -> scale * (x + u(x)). `pairs`: (Basis point, target, per-axis
    weight); `box` (lo, hi): the warped region inside it; `reach`: (axis, bound, +1 its max or -1 its min) to touch.
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

    skull = [n for n in basis if n not in (*NECK, JAW)]
    x = np.vstack([basis[n] for n in skull])
    caps = np.concatenate([budget.caps(n, basis[n], ref) for n in skull])
    pairs = [
        *((lm[f"{s} orbit"], (sign * gimbal.SPACING / 2, 0, 0), (1, 1, 1)) for s, sign in (("L", 1), ("R", -1))),
        *((lm[f"{s} condyle"], HINGE, (0, 1, 1)) for s in "LR"),
        *((p, (0, TILT[1], TILT[2] - C0_BELOW), (0, 1, 1)) for p in occ),
    ]
    y, f, hit = solve(x, caps, pairs, SCALES["skull"], (LO, HI), ((2, HI[2], 1), (1, LO[1], -1), (1, HI[1], 1)))
    report["skull"] = _region(f, caps, hit, pairs)
    out |= dict(zip(skull, np.split(y, np.cumsum([len(basis[n]) for n in skull])[:-1])))

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

    # the neck: resized about C1's top, under the occipital condyles; each canal onto the path, C1's round the pan axis
    s, top = neck_scale(basis), basis[NECK[0]][:, 2].max()
    report["scales"]["neck"] = s
    for n in NECK:
        v = basis[n]
        c, zc = canal(trimesh.Trimesh(v, faces[n], process=False)), (v[:, 2].min() + v[:, 2].max()) / 2
        z = TILT[2] - C0_BELOW - 0.5 + s * (zc - top)
        out[n] = s * (v - (*c, zc)) + (0.0, PAN[1] if n == NECK[0] else canal_y(z), z)
    return out, report


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
