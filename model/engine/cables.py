"""Cable corridors (#49): every lead of the Mech (model/electrical.leads) as a tube of RADIUS_MM along a polyline from its
first Port through a few waypoints, each clipped to the part that holds it so it rides pan and tilt, to its second Port.
Over every pose the engine samples (each horn's sweep, the pan x tilt grid where the neck is present) a corridor's path
length must stay under the lead less the slack, and its tube must not enter a moving part (the parts it is clipped to
and their carriers are exempt). The union of the swept tubes is written as model/build/<doc>-corridors.ply: the
clearance the face shell must leave. Not full cables: leads are floppy, a corridor is the route the build clips them to."""

import functools

import numpy as np
import trimesh
from scipy.spatial import cKDTree

from model import electrical
from model.engine import linkage, mech, meshes, stages

RADIUS_MM = 2.0  # a servo lead is a ~3.5 mm wide three-wire ribbon, an XH lead a ~4 mm red/black pair
SAMPLE_MM = 1.0  # centreline spacing for clearance and the swept union
VOXEL_MM = 1.0  # the union's resolution

# Waypoints per lead (electrical.leads), from its first Port to its second: (part it is clipped to, point in that part's
# sub-assembly frame (eyes frame for the eyes and mouth, PT frame for the base and stack), why). A lead lists its routes
# in order and a document takes the first whose parts it has: the eyes on the neck (stages 2, 3) or on the desk (the
# stem in the base's pan recess: stage 1 and the eyes and mouth documents). Routing from the designer's guides (pan-tilt
# steps 8-10, 13, 17-18: the leads pass under the cable holders and are zip-tied, "make sure this is still sufficient
# length to allow for movement") and the eyes build photos (docs/build-photos: the leads leave the servos' backs and
# loop to the keeper and the shield); every point is placed by eye from those photos: inferred.
# On the neck (written in the eyes frame) the head tilts and pans over the stack: the leads leave the servos under the
# servo brackets, clear of the lid servos, gather behind the bracket stem and drop behind the tilt arm between the pan
# bar (-x) and the tilt bar (+x). On the desk (stage 1) they drop off the brackets' feet onto the plate.
UNDER = {
    s: (f"{s} servo bracket:1", (x, -38.5, 28.5), "under the servo bracket, below the lid servo (inferred)")
    for s, x in (("L", -8.5), ("R", 67.5))
}
BEHIND = {
    s: (f"{s} servo bracket:1", (x, -35.5, 49.5), "behind the lid servo, under the bracket's back (inferred)")
    for s, x in (("L", 21.5), ("R", 37.5))
}
GATHER = ("main bracket v2:1", (23.5, -38.5, 34.5), "gathered behind the bracket stem, guide step 18 photo (inferred)")
NECK = [
    ("tilt arm:1", (5.5, 36.0, 38.0), "zip-tied behind the tilt arm's back, guide step 18 photo (inferred)"),
    ("upright v2:1", (5.5, 36.0, 20.0), "down behind the upright, guide step 18 photo (inferred)"),
    ("wire holder:1", (0.0, 40.5, 6.0), "under the cable holder on the base, guide step 18 (inferred)"),
]
DESK = {
    s: [
        (
            f"{s} servo bracket:1",
            (x, -34.5, 48.5),
            "off the servo bracket's foot onto the plate, eyes build photos (inferred)",
        ),
        ("PandT base:1", (0.0, 40.5, 6.0), "under the wire keeper on the base, eyes guide step 2 (inferred)"),
    ]
    for s, x in (("L", 21.5), ("R", 37.5))
}
NECK_START = {
    "l_lid": [BEHIND["L"]],
    "r_lid": [BEHIND["R"], GATHER],
    "l_eye": [UNDER["L"], GATHER],
    "r_eye": [UNDER["R"], GATHER],
}
ROUTES = {
    **{
        f"{servo} servo -> Core 1 PWM{n}": [[*NECK_START[servo], *NECK], DESK[servo[0].upper()]]
        for n, servo in electrical.CHANNELS["core1"].items()
    },
    "tilt servo -> Core 2 PWM1": [
        [("tilt servo:1", (36.0, 32.0, 12.0), "bent down off the tilt servo's cable end, guide step 10 (inferred)")]
    ],
    "mouth servo -> Core 2 PWM2": [
        [
            (*UNDER["R"][:2], "joins the R eye lead under the R servo bracket (inferred)"),
            GATHER,
            *NECK,
        ]
    ],
    "pan servo -> Core 2 PWM3": [
        [("wire holder:1", (-5.0, 40.5, 6.0), "under the cable holder, guide steps 8-9 (inferred)")]
    ],
    **{
        f"pack {n} -> switch {n}": [
            [("PandT base:1", (-20.0, 118.0, 6.0), "out of the battery box's back corner onto the plate (inferred)")]
        ]
        for n in (1, 2)
    },
    "switch 1 -> shield 1": [
        [
            (
                "PandT base:1",
                (55.0, 85.0, 6.0),
                "from the back-edge holder along the plate's +x edge past shield 2 (inferred)",
            )
        ]
    ],
    "switch 2 -> shield 2": [
        [("PandT base:1", (25.0, 85.0, 6.0), "along the plate to the shield's XH socket (inferred)")]
    ],
}
# The part each clip is mounted on: exempt with it (a lead lies against what holds it).
CARRIER = {
    **{f"{s} {k} servo:1": f"{s} servo bracket:1" for s in "LR" for k in ("lid", "eye")},
    **{f"{s} servo bracket:1": "main bracket v2:1" for s in "LR"},
    "jaw servo:1": "jaws servo mount:1",
    "jaws servo mount:1": "main bracket v2:1",
    "tilt servo:1": "pan base:1",
    "tilt arm:1": "upright v2:1",
    "upright v2:1": "pan base:1",
    "pan servo:1": "servo mount plain:1",
}


def sample(polyline, step=SAMPLE_MM):
    """Points along the polyline no more than `step` apart, its corners kept."""
    p = np.asarray(polyline, float)
    out = [p[:1]]
    for a, b in zip(p[:-1], p[1:], strict=False):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        out.append(a + (b - a) * np.arange(1, n + 1)[:, None] / n)
    return np.vstack(out)


def length(pts):
    return float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())


def clearance(pts, part, radius):
    """mm from the surface of the tube of `radius` around the sampled centreline to the Placed part, negative once the
    tube is inside it (a centreline point inside counts its depth plus the radius); NEAR_MM when nothing is near."""
    near = meshes.NEAR_MM
    pts = pts[((pts > part.lo - near) & (pts < part.hi + near)).all(axis=1)]
    if not len(pts):
        return near
    d, _ = part.tree.query(pts, distance_upper_bound=near + part.reach)  # a surface within NEAR has a vertex this close
    ok = np.isfinite(d)
    if not ok.any():
        return near
    dist, depth = meshes.to_surface(pts[ok], part, d[ok])
    return min(near, float((np.where(depth > 0, -dist, dist) - radius).min()))


def union(tubes, radius, voxel=VOXEL_MM):
    """One closed mesh holding every tube (sampled centrelines): voxels within reach of a centreline, their boundary faces.
    A voxel is filled when any point of it can be within `radius`, so the union never undercuts a tube."""
    pts = np.unique(np.round(np.vstack(tubes) / (voxel / 4)), axis=0) * (voxel / 4)  # dedupe the overlapping sweeps
    pad = radius + 2 * voxel
    lo = pts.min(axis=0) - pad
    shape = np.ceil((pts.max(axis=0) + pad - lo) / voxel).astype(int)
    centres = lo + voxel * (np.indices(shape).reshape(3, -1).T + 0.5)
    d, _ = cKDTree(pts).query(centres, distance_upper_bound=radius + voxel * 3**0.5 / 2)
    occ = np.pad(_manifold(np.isfinite(d).reshape(shape)).astype(np.int8), 1)
    quads = []
    for axis in range(3):
        u, v = np.eye(3, dtype=int)[[(axis + 1) % 3, (axis + 2) % 3]]
        step = np.diff(occ, axis=axis)  # -1: full to empty along +axis (face looks +axis), +1: the reverse
        for sign, order in ((-1, (0, 1, 2, 3)), (1, (3, 2, 1, 0))):
            base = np.argwhere(step == sign)
            base[:, axis] += 1
            corners = np.stack([base, base + u, base + u + v, base + v], axis=1)[:, order]
            quads.append(corners)
    corners = np.concatenate(quads)
    vertices = lo + voxel * (corners.reshape(-1, 3) - 1)  # -1: the padding layer
    n = np.arange(len(corners))[:, None] * 4
    faces = np.vstack([n + [0, 1, 2], n + [0, 2, 3]])
    return trimesh.Trimesh(vertices, faces)


def _manifold(occ):
    """Fill voxels until no two filled ones meet only along an edge (a non-manifold edge in the boundary mesh); the
    fill only adds clearance."""
    while True:
        changed = False
        for a, b in ((0, 1), (0, 2), (1, 2)):

            def at(i, j):
                s = [slice(None)] * 3
                s[a], s[b] = slice(i, occ.shape[a] - 1 + i), slice(j, occ.shape[b] - 1 + j)
                return tuple(s)

            v00, v01, v10, v11 = (occ[at(i, j)].copy() for i, j in ((0, 0), (0, 1), (1, 0), (1, 1)))
            fill01, fill00 = v00 & v11 & ~v01 & ~v10, v01 & v10 & ~v00 & ~v11
            if fill01.any() or fill00.any():
                occ[at(0, 1)] |= fill01
                occ[at(0, 0)] |= fill00
                changed = True
        if not changed:
            return occ


@functools.cache
def _home():
    """Every part's matrix in its own sub-assembly's frame: where ROUTES' points are written."""
    return {n: p.matrix for build in stages.SUBS.values() for n, p in build().parts.items()}


def poses(stage, step):
    """({horn: deg}, {part: 4x4}) for neutral, every horn's sweep at `step` and, where the neck is present, the pan x tilt
    grid in place of the pan and tilt sweeps (mech.mech_poses)."""
    neutral = {n: p.matrix for n, p in stage.parts.items()}
    yield {}, neutral
    grid = {mech.PAN, mech.TILT} <= set(stage.horns)
    for h, horn in stage.horns.items():
        if grid and h in (mech.PAN, mech.TILT):
            continue
        lo, hi = horn.limits
        for d in [*range(lo, hi, step), hi]:
            try:
                yield {h: d}, stages.pose(stage, h, d).parts
            except linkage.Unreachable:
                pass
    if grid:
        for p, t, mats in mech.mech_poses(stage, step):
            yield {mech.PAN: p, mech.TILT: t}, mats


def corridors(stage, placed, step, routes=None):
    """({lead: path length extremes, limit, worst clearance and the waypoints' reasons}, [every sampled centreline]) for
    each lead whose two Ports are in the document, over poses(); `placed` holds every part at neutral (run.neutral)."""
    routes = ROUTES if routes is None else routes
    moving = {
        n for h in stage.horns.values() for n in (h.crank, *(m for lp in h.loops for m in (lp.coupler, *lp.rockers)))
    }
    leads = {}
    for name, a, b, mm in electrical.leads():
        if a in stage.ports and b in stage.ports:
            route = next(r for r in routes[name] if all(p in stage.parts for p, _, _ in r))
            clips = [stage.ports[a], *((p, _local(p, q)) for p, q, _ in route), stage.ports[b]]
            held = {p for p, _ in clips}
            exempt = held | {CARRIER[p] for p in held if p in CARRIER}
            leads[name] = clips, sorted(moving - exempt), mm, [w for _, _, w in route]
    out, centrelines = {}, []
    for at, mats in poses(stage, step):
        to_home = {m: stage.parts[m].matrix @ np.linalg.inv(mats[m]) for m in moving}
        for name, (clips, check, mm, reasons) in leads.items():
            pts = sample([mats[p][:3, :3] @ q + mats[p][:3, 3] for p, q in clips])
            centrelines.append(pts)
            now = round(length(pts), 1)
            c = out.setdefault(
                name,
                {
                    "max_mm": now,
                    "at": at,
                    "min_mm": now,
                    "min_at": at,
                    "length_mm": mm,
                    "limit_mm": mm - electrical.SLACK_MM,
                    "clearance_mm": meshes.NEAR_MM,
                    "clearance_at": None,
                    "clearance_part": None,
                    "waypoints": reasons,
                },
            )
            if now > c["max_mm"]:
                c.update(max_mm=now, at=at)
            if now < c["min_mm"]:
                c.update(min_mm=now, min_at=at)
            for m in check:
                home = pts @ to_home[m][:3, :3].T + to_home[m][:3, 3]  # into the part's neutral place
                gap = round(clearance(home, placed[m], RADIUS_MM), 2)
                if gap < c["clearance_mm"]:
                    c.update(clearance_mm=gap, clearance_at=at, clearance_part=m)
    return out, centrelines


def _local(part, point):
    return (np.linalg.inv(_home()[part]) @ np.array([*point, 1.0]))[:3]
