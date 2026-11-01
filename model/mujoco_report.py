"""The sim report's MuJoCo half (#149, ADR 0007): measure(doc, model) steps the document's MJCF through each horn's sweep
(geometry.LIMITS in STEP_DEG steps, the other horns at neutral) and, where the neck is, the pan x tilt grid, each pose
reached quasi-statically by mjcf.pose, and reports per pose: contacts and penetration per pair (MuJoCo's signed
distance between the convex pieces, within CLEARANCE_MM), the four-bars' residuals, the force each servo holds against
its rated and stall torque, and the centre of mass against the base footprint. Each horn is also swung to its ends at
the servo's rated speed, to see whether the joints land where the slow pose puts them. make sim writes it into
model/reports/<doc>-sim.json under "mujoco" (model/report.py), beside the committed MJCF model/reports/<doc>.xml;
model/test_report.py thresholds it (research note docs/research/2026-11-01-mujoco-report.md)."""

import math
from importlib.metadata import version

import mujoco
import numpy as np
from scipy.spatial import ConvexHull

from model import electrical, mjcf, sim, stages

STEP_DEG, CLEARANCE_MM = 10, 0.1  # below 0.1 mm the parts touch
KGF_CM = 0.0980665  # N.m
PAN, TILT = "pan horn", "tilt horn"
PENETRATION_MM, LOOP_MM, TURN_DEG = 0.05, 0.05, 1.0  # thresholds (model/test_report.py)
RATED_DEG_S = electrical.servo.rate(electrical.SERVO_MIN_V)  # 60 deg in 0.14 s at 4.8 V


def _degs(horn):
    lo, hi = horn.limits
    return [*range(lo, hi, STEP_DEG), hi]


def poses(doc):
    """Every pose measured, as servo commands {horn: deg}: each horn's sweep, then the pan x tilt grid."""
    horns = stages.STAGES[doc].horns
    out = [{h: d} for h, horn in horns.items() for d in _degs(horn)]
    if {PAN, TILT} <= set(horns):
        out += [{PAN: p, TILT: t} for p in _degs(horns[PAN]) for t in _degs(horns[TILT])]
    return out


def _contacts(model, data):
    """{(body, body): mm} the closest the two bodies' pieces come, for the pairs within CLEARANCE_MM (negative: in)."""
    # contacts only, inside the pieces' margin: no constraints (finely cut nested shells meet in thousands of pieces)
    mujoco.mj_kinematics(model, data)
    mujoco.mj_collision(model, data)
    assert not data.warning[mujoco.mjtWarning.mjWARN_CONTACTFULL].number, "contacts dropped: the arena is full"
    out = {}
    for c in data.contact[: data.ncon]:
        pair = tuple(sorted(model.body(model.geom_bodyid[g]).name for g in c.geom))
        out[pair] = min(out.get(pair, math.inf), c.dist * 1000)
    return out


def widen(model):
    """Contacts on `model` from CLEARANCE_MM out (the collision pieces' margin), the parent filter off, and multiccd off
    (one contact, the true distance, per pair of pieces)."""
    model.geom_margin[model.geom_group == mjcf.COLLISION] = CLEARANCE_MM / 1000
    # a part on a joint against the rigid group it hangs on (a lid on the eye bracket riding the tilt arm): measured too;
    # multiccd's extra points on two flat faces read up to 0.2 mm too deep (docs/research/2026-11-01-coacd-tuning.md 2)
    model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_FILTERPARENT | mujoco.mjtDisableBit.mjDSBL_MULTICCD


def _footprint(model, data):
    """The base plate's plan outline in MuJoCo's world (mm, footprint()): its drawn mesh's vertices where they are."""
    g = next(
        i
        for i in range(model.ngeom)
        if model.geom_group[i] == mjcf.VISUAL and model.body(model.geom_bodyid[i]).name == "base plate:1"
    )
    m = model.geom_dataid[g]
    v = model.mesh_vert[model.mesh_vertadr[m] : model.mesh_vertadr[m] + model.mesh_vertnum[m]]
    world = v @ data.geom_xmat[g].reshape(3, 3).T + data.geom_xpos[g]
    return footprint(world * 1000)


def footprint(points):
    """A plan outline: the convex hull of the points in XY as line equations, inside <= 0."""
    return ConvexHull(np.asarray(points, float)[:, :2]).equations


def margin(outline, xy):
    """mm from a plan point to the outline: positive inside (the nearest edge), negative outside."""
    return float(-(outline[:, :2] @ np.asarray(xy, float) + outline[:, 2]).max())


def _worst(old, value, at, key):
    return old if old and old[key] >= value else {key: round(value, 3), "at": at}


def measure(doc, model):
    """The document's MuJoCo report (a dict, in the shape model/test_report.py reads). Widens `model`, which is the
    report's own (widen())."""
    stage, todo = stages.STAGES[doc], poses(doc)
    widen(model)
    rest = _contacts(model, mjcf.pose(model, {}))
    pairs, residuals, actuators, slow = {}, {}, {}, {}
    tip = {} if {PAN, TILT} <= set(stage.horns) else None
    for ctrl in todo:
        data = mjcf.pose(model, ctrl)
        if len(ctrl) == 1:
            slow[tuple(ctrl.items())[0]] = data.qpos.copy()
        for loop, mm in mjcf.residuals(model, data).items():
            residuals[loop] = _worst(residuals.get(loop), mm, ctrl, "max_mm")
        for h in stage.horns:
            actuators[h] = _worst(actuators.get(h), abs(data.actuator(h).force[0]) / KGF_CM, ctrl, "hold_kgf_cm")
        if tip is not None:
            mm = margin(_footprint(model, data), data.subtree_com[0][:2] * 1000)
            if not tip or mm < tip["margin_mm"]:
                tip = {
                    "margin_mm": round(mm, 1),
                    "at": ctrl,
                    "com": [round(c * 1000, 1) for c in data.subtree_com[0]],
                }
        for pair, mm in _contacts(model, data).items():
            if pair not in pairs or mm < pairs[pair]["min_mm"]:
                pairs[pair] = {"pair": list(pair), "rest_mm": rest.get(pair), "min_mm": mm, "at": ctrl}
    for p in pairs.values():
        p["min_mm"] = round(p["min_mm"], 3)
        p["rest_mm"] = None if p["rest_mm"] is None else round(p["rest_mm"], 3)
    full_speed = {}
    for h, horn in stage.horns.items():
        for d in horn.limits:
            fast = mjcf.pose(model, {h: d}, RATED_DEG_S).qpos
            off = math.degrees(float(np.abs(fast - slow[(h, d)]).max()))  # every DOF is a hinge
            if h not in full_speed or off > full_speed[h]["off_deg"]:
                full_speed[h] = {"deg_s": round(RATED_DEG_S, 1), "off_deg": round(off, 2), "at": d}
    out = {
        "mujoco": version("mujoco"),
        "step_deg": STEP_DEG,
        "clearance_mm": CLEARANCE_MM,
        "poses": len(todo),
        "pairs": sorted(pairs.values(), key=lambda p: p["pair"]),
        "residuals": residuals,
        "actuators": {
            h: {**a, "rated_kgf_cm": sim.RATED_KGF_CM, "stall_kgf_cm": round(mjcf.STALL_NM / KGF_CM, 3)}
            for h, a in actuators.items()
        },
        "full_speed": full_speed,
    }
    if tip is not None:
        out["tip_over"] = tip
    return out
