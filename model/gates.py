"""The Model's pass/fail gates along the Mech's motion (#627, #51): each four-bar's singularity margin and transmission
angle (loops(), docs/research/2026-11-02-literature-graphics.md 1) and the clearance of every pair of parts certified
along a played motion (certify(), docs/research/2026-11-02-literature-simulation.md 4). The sim report gates the
first over each horn's sweep (model/mujoco_report.py, model/test_report.py), model/test_trajectories.py the second over
every gesture and the hero, model/printed/gimbal.py over the next Mech's lid drives."""

import functools
import math
from collections import OrderedDict

import mujoco
import numpy as np


def _dofs(model, body):
    """The DOFs from the world down to `body`: every one that moves it."""
    out = set()
    while body:
        out.update(range(model.body_dofadr[body], model.body_dofadr[body] + model.body_dofnum[body]))
        body = model.body_parentid[body]
    return out


def loops(model, data):
    """{four-bar: (singularity margin, mm/rad; transmission angle, deg)} at data's pose (after mj_forward or a step): each
    connect's constraint Jacobian over the loop's free pivots (the coupler's and the rocker's: the horn is driven), its
    smallest singular value, and the angle between its two columns, which is the coupler's to the rocker's folded to
    0..90 (both are zero at the toggle)."""
    driven = {
        model.jnt_dofadr[j]
        for j, kind in zip(model.actuator_trnid[:, 0], model.actuator_trntype)
        if kind == mujoco.mjtTrn.mjTRN_JOINT
    }
    out = {}
    for i in range(model.neq):
        sites = model.eq_obj1id[i], model.eq_obj2id[i]
        jac = []
        for s in sites:
            jac.append(np.zeros((3, model.nv)))
            mujoco.mj_jacSite(model, data, jac[-1], None, s)
        free = sorted((_dofs(model, model.site_bodyid[sites[0]]) ^ _dofs(model, model.site_bodyid[sites[1]])) - driven)
        if len(free) != 2:  # a push-rod's spatial loop (stages.Rod), no four-bar: model/gimbal.py report() gates it
            continue
        J = (jac[0] - jac[1])[:, free] * 1000  # mm per rad
        coupler, rocker = J.T  # a four-bar: two free pivots
        cos = abs(coupler @ rocker) / (np.linalg.norm(coupler) * np.linalg.norm(rocker))
        out[model.eq(i).name] = (
            float(np.linalg.svd(J, compute_uv=False)[-1]),
            math.degrees(math.acos(min(cos, 1.0))),
        )
    return out


DISTMAX_MM = 5.0  # mj_geomDistance's cap: past it a pair reads the gap between its pieces' bounding spheres


def _pieces(model, body):
    """The body's colliding geoms (the visual ones collide with nothing)."""
    return np.flatnonzero((model.geom_bodyid == body) & ((model.geom_contype | model.geom_conaffinity) != 0))


def pairs(model):
    """Every pair of bodies (names, sorted) with colliding pieces on both that a hinge turns against each other: the
    pairs whose clearance a motion can change."""
    bodies = [b for b in range(1, model.nbody) if len(_pieces(model, b))]
    return [
        tuple(sorted((model.body(a).name, model.body(b).name)))
        for i, a in enumerate(bodies)
        for b in bodies[i + 1 :]
        if _dofs(model, a) != _dofs(model, b)
    ]


def separation(model, data, pair):
    """mm between two bodies' (names) colliding pieces at data's kinematics, negative when in: the least of
    mj_geomDistance over the pieces, which reads DISTMAX_MM for anything farther; pieces whose bounding spheres are
    farther apart than that read the spheres' gap, a lower bound, so far pairs read far without a narrow phase."""
    a, b = (_pieces(model, model.body(n).id) for n in pair)
    gap = (
        np.linalg.norm(data.geom_xpos[a][:, None] - data.geom_xpos[b][None], axis=2)
        - model.geom_rbound[a][:, None]
        - model.geom_rbound[b][None]
    ) * 1000
    far = gap >= DISTMAX_MM
    best = gap[far].min(initial=math.inf)
    for i, j in sorted(zip(*np.nonzero(~far)), key=lambda ij: gap[ij]):
        if gap[i, j] >= best:
            break
        best = min(best, 1000 * mujoco.mj_geomDistance(model, data, a[i], b[j], DISTMAX_MM / 1000, None))
    return float(best)


AXIS_M = 1e-6  # how far off a common point the hinges' axes may pass and still turn about it


def _radii(model, data, pieces, centre):
    """mm from centre to the nearest and the farthest point of each piece: for a mesh, its farthest vertex, and no
    nearer than any of its faces' planes, or the plane square to the centre, stands off the centre (a convex piece lies
    behind each); for a primitive, its bounding sphere."""
    near, far = [], []
    for g in pieces:
        c = data.geom_xpos[g]
        if model.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH:
            r = np.linalg.norm(c - centre)
            near.append(r - model.geom_rbound[g])
            far.append(r + model.geom_rbound[g])
            continue
        m = model.geom_dataid[g]
        v = (
            c
            + model.mesh_vert[model.mesh_vertadr[m] : model.mesh_vertadr[m] + model.mesh_vertnum[m]]
            @ data.geom_xmat[g].reshape(3, 3).T
        )
        f = v[model.mesh_face[model.mesh_faceadr[m] : model.mesh_faceadr[m] + model.mesh_facenum[m]]]
        n = np.vstack([np.cross(f[:, 1] - f[:, 0], f[:, 2] - f[:, 0]), centre - c])
        n = n[np.linalg.norm(n, axis=1) > 0]
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        near.append((n @ centre - (v @ n.T).max(axis=0)).max())
        far.append(np.linalg.norm(v - centre, axis=1).max())
    return 1000 * np.maximum(near, 0), 1000 * np.array(far)


def certify(model, qpos, floors, excused=lambda pair, data: False, separation=None):
    """{pair: (row, mm)} for each pair of bodies (names) in floors that reads under its floor (mm) anywhere along qpos
    (one row per sim step, every joint a hinge): one such reading. Adaptive, after Schwarzer, Saha and Latombe (T-RO
    2005), pair of pieces by pair of pieces (#667): a span is clear for two pieces when their two readings at its ends
    together exceed how far they can move against each other across it (r * |dtheta| summed over the hinges between
    the bodies, r from the hinge's axis to the piece's far side, dtheta the hinge's turn summed step by step);
    otherwise it is halved for them, down to one step, between which the sim has nothing. Two pieces read their
    bounding spheres' gap, and mj_geomDistance only where that is too close to clear the span. When every hinge between
    the bodies turns about one point, two pieces whose distances from it (_radii) keep them over the floor are clear
    throughout, unread: an eye's lids round its ball. A reading excused(pair, data) at its row's pose is no failure; a
    span excused at both ends is taken as excused throughout. separation(model, data, pair), when given, reads the two
    bodies whole instead (mm, a lower bound on their gap), each body one piece reaching as far as its farthest:
    model/printed/gimbal.py reads the exact solids."""
    assert (model.jnt_type == mujoco.mjtJoint.mjJNT_HINGE).all(), "r * |dtheta| bounds a hinge's travel"
    data, posed = mujoco.MjData(model), [None]
    turned = np.vstack([np.zeros(model.njnt), np.cumsum(np.abs(np.diff(qpos[:, model.jnt_qposadr], axis=0)), axis=0)])
    sides = {}  # pair: [(its pieces, the hinges that turn it and not the other)] per side
    for pair in floors:
        a, b = (model.body(n).id for n in pair)
        da, db = _dofs(model, a), _dofs(model, b)
        sides[pair] = [
            (_pieces(model, a), sorted(model.dof_jntid[list(da - db)])),
            (_pieces(model, b), sorted(model.dof_jntid[list(db - da)])),
        ]
    rbound = {p: [1000 * model.geom_rbound[g] for g, _ in two] for p, two in sides.items()}  # mm
    rows, out = OrderedDict(), {}  # rows: the latest rows' kinematics and readings (the walk goes depth first)

    def at(row):
        if row not in rows:
            pose(row)
            rows[row] = {"x": data.geom_xpos.copy(), "anchor": data.xanchor.copy(), "axis": data.xaxis.copy()}
            if len(rows) > 64:
                rows.popitem(last=False)
        rows.move_to_end(row)
        return rows[row]

    def pose(row):
        if posed[0] != row:
            data.qpos[:] = qpos[row]
            mujoco.mj_kinematics(model, data)
            posed[0] = row

    def off(row, p):
        r = at(row)
        if ("off", p) not in r:
            pose(row)
            r["off", p] = excused(p, data)
        return r["off", p]

    def side(row, p, s):
        """The pair's side s at row: its pieces' centres (m) and their reach (mm from each hinge's axis to the piece's far
        side, pieces x hinges; whole: one piece, the farthest)."""
        r = at(row)
        if ("side", p, s) not in r:
            g, js = sides[p][s]
            arm = np.cross(r["x"][g][:, None] - r["anchor"][js][None], r["axis"][js][None])
            mm = 1000 * (np.linalg.norm(arm, axis=2) + model.geom_rbound[g][:, None])
            r["side", p, s] = r["x"][g], mm.max(axis=0, initial=0, keepdims=True) if separation else mm
        return r["side", p, s]

    def gaps(row, p, i, j):
        """mm between the pieces i, j (indices into the pair's sides): the bounding spheres' gap (whole: the reading)."""
        if separation:
            r = at(row)
            if ("whole", p) not in r:
                pose(row)
                r["whole", p] = separation(model, data, p)
            return np.full(len(i), r["whole", p])
        (xa, _), (xb, _) = side(row, p, 0), side(row, p, 1)
        d = xa[i] - xb[j]
        return 1000 * np.sqrt(np.einsum("ij,ij->i", d, d)) - rbound[p][0][i] - rbound[p][1][j]

    def exact(row, p, i, j, gap):
        """gap raised to mj_geomDistance's reading of each pair of pieces (capped at DISTMAX_MM)."""
        if separation:
            return gap
        read = at(row).setdefault(("exact", p), {})
        (a, _), (b, _) = sides[p]
        keys = (i * len(b) + j).tolist()
        if any(k not in read for k in keys):
            pose(row)
            a, b, n = a.tolist(), b.tolist(), len(b)
            for k in keys:
                if k not in read:
                    read[k] = 1000 * mujoco.mj_geomDistance(model, data, a[k // n], b[k % n], DISTMAX_MM / 1000, None)
        return np.maximum(gap, [read[k] for k in keys])

    def left(r0, r1, p, ij):
        """The pairs of pieces (i, j) the span [r0, r1] does not clear, recording a reading under the floor."""
        i, j = ij
        if p in out or (off(r0, p) and off(r1, p)):
            return i[:0], j[:0]
        travel = 0.0
        for s, k in enumerate((i, j)):
            dtheta = turned[r1, sides[p][s][1]] - turned[r0, sides[p][s][1]]
            if dtheta.sum() >= 1:
                return ij
            # a hinge's radius changes only as the hinges past it turn the piece, which the 1 - sum bounds
            reach = np.maximum(side(r0, p, s)[1], side(r1, p, s)[1])
            travel = travel + (reach @ dtheta)[0 if separation else k] / (1 - dtheta.sum())
        g0, g1 = gaps(r0, p, i, j), gaps(r1, p, i, j)
        room = 2 * floors[p] + travel
        # a reading could clear it (whole: every reading is one)
        maybe = (np.maximum(g0, DISTMAX_MM) + np.maximum(g1, DISTMAX_MM) > room) | bool(separation)
        k = np.flatnonzero((g0 + g1 <= room) & maybe)
        g0[k], g1[k] = exact(r0, p, i[k], j[k], g0[k]), exact(r1, p, i[k], j[k], g1[k])
        for row, g in ((r0, g0[k]), (r1, g1[k])):
            if len(g) and g.min() < floors[p] and not off(row, p) and p not in out:
                out[p] = (row, round(float(g.min()), 3))
        keep = g0 + g1 <= room
        return i[keep], j[keep]

    def walk(r0, r1, todo):
        todo = {p: kept for p, ij in todo.items() if len((kept := left(r0, r1, p, ij))[0])}
        if todo and r1 - r0 > 1:
            mid = (r0 + r1) // 2
            walk(r0, mid, todo)
            walk(mid, r1, todo)

    every, radii = {}, functools.cache(lambda body, point: _radii(model, data, _pieces(model, body), np.array(point)))
    pose(0)
    for p, ((a, ja), (b, jb)) in sides.items():
        i, j = np.indices((1, 1) if separation else (len(a), len(b))).reshape(2, -1)
        js = ja + jb
        centre = data.xanchor[js[0]].copy() if js else None
        off_axis = [np.linalg.norm(np.cross(centre - data.xanchor[h], data.xaxis[h])) for h in js]
        if not separation and js and max(off_axis) < AXIS_M:
            # every hinge between the two turns about centre, so each piece keeps its distance from it all along
            (near_a, far_a), (near_b, far_b) = (radii(model.body(n).id, tuple(centre)) for n in p)
            apart = np.maximum(near_a[i] - far_b[j], near_b[j] - far_a[i]) - 2000 * AXIS_M
            i, j = i[apart <= floors[p]], j[apart <= floors[p]]
        every[p] = i, j
    walk(0, len(qpos) - 1, every)
    return out
