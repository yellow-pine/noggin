"""The Model's pass/fail gates along the Mech's motion (#627, #51): each four-bar's singularity margin and transmission
angle (loops(), docs/research/2026-11-02-literature-graphics.md 1) and the clearance of every pair of parts certified
along a played motion (certify(), docs/research/2026-11-02-literature-simulation.md 4). The sim report gates the
first over each horn's sweep (model/mujoco_report.py, model/test_report.py), model/test_trajectories.py the second over
every gesture and the hero, model/printed/gimbal.py over the next Mech's lid drives."""

import math

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


def certify(model, qpos, floors, excused=lambda pair, data: False, separation=separation):
    """{pair: (row, mm)} for each pair of bodies (names) in floors that reads under its floor (mm) anywhere along qpos
    (one row per sim step, every joint a hinge): one such reading. Adaptive, after Schwarzer, Saha and
    Latombe (T-RO 2005): a span is clear when the two readings at its ends together exceed how far any point of one
    body can move against the other across it (r * |dtheta| summed over the hinges between them, r from the hinge's
    axis to the far side of the body's farthest piece, dtheta the hinge's turn summed step by step); otherwise it is
    halved, down to one step, between which the sim has nothing. A reading excused(pair, data) at its row's pose is no
    failure; a span excused at both ends is taken as excused throughout. separation(model, data, pair) is the reading
    (mm): the pieces' by default, or another lower bound on the gap (model/printed/gimbal.py reads the exact solids)."""
    assert (model.jnt_type == mujoco.mjtJoint.mjJNT_HINGE).all(), "r * |dtheta| bounds a hinge's travel"
    data = mujoco.MjData(model)
    turned = np.vstack([np.zeros(model.njnt), np.cumsum(np.abs(np.diff(qpos[:, model.jnt_qposadr], axis=0)), axis=0)])
    pieces = {b: _pieces(model, b) for b in {model.body(n).id for pair in floors for n in pair}}
    hinges = {}  # pair: [(body, the hinges that turn it and not the other)] per side
    for pair in floors:
        a, b = (model.body(n).id for n in pair)
        da, db = _dofs(model, a), _dofs(model, b)
        hinges[pair] = [(a, sorted(model.dof_jntid[list(da - db)])), (b, sorted(model.dof_jntid[list(db - da)]))]
    read, out = {}, {}  # read: (row, pair) -> (mm above the floor, excused, [hinge radii per side])

    def at(row, pairs):
        todo = [p for p in pairs if (row, p) not in read]
        if not todo:
            return
        data.qpos[:] = qpos[row]
        mujoco.mj_kinematics(model, data)
        for p in todo:
            mm = separation(model, data, p)
            off = excused(p, data)
            radii = []
            for body, js in hinges[p]:
                g = pieces[body]
                arm = np.cross(data.geom_xpos[g][:, None] - data.xanchor[js][None], data.xaxis[js][None])
                radii.append((np.linalg.norm(arm, axis=2) + model.geom_rbound[g][:, None]).max(axis=0, initial=0))
            read[row, p] = mm - floors[p], off, radii
            if mm < floors[p] and not off and p not in out:
                out[p] = (row, round(mm, 3))

    def clear(r0, r1, p):
        (m0, off0, radii0), (m1, off1, radii1) = read[r0, p], read[r1, p]
        if p in out or (off0 and off1):
            return True
        travel = 0.0
        for (_, js), q0, q1 in zip(hinges[p], radii0, radii1):
            dtheta = turned[r1, js] - turned[r0, js]
            if dtheta.sum() >= 1:
                return False
            # a hinge's radius changes only as the hinges past it turn the point, which the 1 - sum bounds
            travel += 1000 * float(np.maximum(q0, q1) @ dtheta) / (1 - dtheta.sum())
        return travel < m0 + m1

    def walk(r0, r1, pairs):
        at(r0, pairs)
        at(r1, pairs)
        left = [p for p in pairs if not clear(r0, r1, p)]
        if left and r1 - r0 > 1:
            mid = (r0 + r1) // 2
            walk(r0, mid, left)
            walk(mid, r1, left)

    walk(0, len(qpos) - 1, list(floors))
    return out
