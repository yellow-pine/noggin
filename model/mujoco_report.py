"""The sim report's MuJoCo half (#149, ADR 0007): measure(doc, model) steps the document's MJCF through each horn's sweep
(geometry.LIMITS in STEP_DEG steps, the other horns at neutral) and, where the neck is, the pan x tilt grid, each pose
reached quasi-statically by mjcf.pose, and reports per pose: contacts and penetration per pair (MuJoCo's signed
distance between the convex pieces, within CLEARANCE_MM), the four-bars' residuals, singularity margins and transmission
angles (model/gates.py), the force each servo holds against
its rated and stall torque, and the centre of mass against the base footprint. Each horn is also swung to its ends at
the servo's rated speed, to see whether the joints land where the slow pose puts them. Every motion the Mech plays (each
gesture, and the hero where the neck is: model/trajectories.py) is played through the servos' dynamics, and MuJoCo's
inverse dynamics reads each servo's torque along it, held against gravity and turning its load, beside its hold at
Rest; the centre of mass, shifted by its acceleration, against the footprint (and the footprint's size); and, for
ranking the next Mech (#51), the neck's vibration figures (vibration()). just sim writes it into
model/build/reports/<doc>-sim.json under "mujoco" (model/report.py), beside the MJCF model/build/reports/<doc>.xml;
model/test_report.py thresholds it (research note docs/research/2026-11-01-mujoco-report.md)."""

import math
from importlib.metadata import version

import mujoco
import numpy as np
from scipy.spatial import ConvexHull

from model import electrical, fits, gates, mjcf, sim, stages, traces, trajectories

STEP_DEG, CLEARANCE_MM = 10, 0.1  # below 0.1 mm the parts touch
KGF_CM = 0.0980665  # N.m
PAN, TILT = "pan horn", "tilt horn"
PENETRATION_MM, LOOP_MM, TURN_DEG = 0.05, 0.05, 1.0  # thresholds (model/test_report.py)
RATED_DEG_S = electrical.servo.rate(electrical.SERVO_MIN_V)  # 60 deg in 0.14 s at 4.8 V
# the four-bars' gates (#627, model/test_report.py): the tightest pin fit we print (fits.CLEARANCE) lets a loop's free
# pivots turn up to clearance / margin rad, held to PLAY_DEG (#51's gaze error, play included), so the singularity
# margin stays over MARGIN_MM_RAD; the bar meets its lever at TRANSMISSION_DEG or more (docs/research/2026-10-31-neck.md)
PLAY_DEG, TRANSMISSION_DEG = 2.0, 40.0
MARGIN_MM_RAD = fits.CLEARANCE[0] / math.radians(PLAY_DEG)


def _degs(horn):
    lo, hi = horn.limits  # a lid's closed end is fractional (geometry.LIMITS)
    return [*np.arange(lo, hi, STEP_DEG).tolist(), hi]


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


def vertices(model, data, body):
    """The body's (its id) drawn mesh's vertices in MuJoCo's world (mm), where they are."""
    i = next(i for i in range(model.ngeom) if model.geom_group[i] == mjcf.VISUAL and model.geom_bodyid[i] == body)
    m = model.geom_dataid[i]
    v = model.mesh_vert[model.mesh_vertadr[m] : model.mesh_vertadr[m] + model.mesh_vertnum[m]]
    return (v @ data.geom_xmat[i].reshape(3, 3).T + data.geom_xpos[i]) * 1000


def _plate(model, data):
    """The base's (today's base plate or the next Mech's Torso) drawn mesh's vertices in MuJoCo's world (mm), where they
    are: its outline is the footprint."""
    foot = ("base plate:1", "next torso:1")
    return vertices(model, data, next(b for b in range(model.nbody) if model.body(b).name.endswith(foot)))


def footprint(points):
    """A plan outline: the convex hull of the points in XY as line equations, inside <= 0."""
    return ConvexHull(np.asarray(points, float)[:, :2]).equations


def margin(outline, xy):
    """mm from a plan point to the outline: positive inside (the nearest edge), negative outside."""
    return float(-(outline[:, :2] @ np.asarray(xy, float) + outline[:, 2]).max())


def torques(model, data, moving=True):
    """N.m each actuator's servo turns its load with at data's pose, by MuJoCo's inverse dynamics (mj_rne, which leaves
    out the servo's own rotor, its armature) with the four-bars rigid: the servos' torques and the rocker pins' forces
    that balance it, by least squares. moving: at data's speed and acceleration; else held, against gravity alone."""
    mujoco.mj_kinematics(model, data)
    mujoco.mj_comPos(model, data)
    qvel, need = data.qvel.copy(), np.zeros(model.nv)
    if not moving:
        data.qvel[:] = 0
    mujoco.mj_rne(model, data, int(moving), need)
    data.qvel[:] = qvel
    cols = [np.eye(model.nv)[:, model.jnt_dofadr[model.actuator_trnid[:, 0]]]]
    for i in range(model.neq):  # each connect: its two sites' Jacobians apart (mjcf.spec's closures)
        a, b = np.zeros((3, model.nv)), np.zeros((3, model.nv))
        mujoco.mj_jacSite(model, data, a, None, model.eq_obj1id[i])
        mujoco.mj_jacSite(model, data, b, None, model.eq_obj2id[i])
        cols.append((a - b).T)
    return np.linalg.lstsq(np.hstack(cols), need, rcond=None)[0][: model.nu]


def shifted(com, acc, floor, g=9.81):
    """The plan point (mm) a centre of mass at com (mm) accelerating at acc (m/s2) bears on the floor at z floor (mm)
    through: shifted by h*a/g against its horizontal acceleration (docs/research/2026-11-02-literature-mechanical.md 6)."""
    return np.asarray(com[:2], float) - (com[2] - floor) * np.asarray(acc[:2], float) / g


def _motions(doc, model, plate):
    """Each motion played through the servos' dynamics (trajectories.play), read every ms: per servo the most it holds
    against gravity and turns its load with (torques()) and where, and its hold at Rest (every gesture starts there);
    with the base plate's vertices (mm), the worst margin of the centre of mass shifted by its acceleration (shifted())."""
    names = trajectories.motions(doc)
    assert names[0] in traces.GESTURES  # the first starts from Rest
    servos, moving = {}, None
    outline, floor, g = (
        (None, None, None) if plate is None else (footprint(plate), plate[:, 2].min(), -model.opt.gravity[2])
    )

    def read(data):
        return torques(model, data, moving=False), torques(model, data), data.subtree_com[0] * 1000  # mm, as just posed

    for name in names:
        writes, times = trajectories.commands(doc, name)
        hold, turn, com = (np.array(r) for r in zip(*trajectories.play(model, writes, range(times[-1] + 1), read)))
        for k in range(model.nu):
            h = model.actuator(k).name
            s = servos.setdefault(h, {"rest_kgf_cm": round(abs(hold[0, k]) / KGF_CM, 3)})
            for key, at, series in (("hold_kgf_cm", "hold_at", hold), ("peak_kgf_cm", "peak_at", turn)):
                ms = int(np.abs(series[:, k]).argmax())
                if abs(series[ms, k]) / KGF_CM > s.get(key, -1):
                    s[key], s[at] = round(abs(series[ms, k]) / KGF_CM, 3), {"motion": name, "ms": ms}
        if outline is not None:
            # the model's own peaks, every ms: the four-bars' stiff pins ring in them too, so it errs on the safe side
            acc = (com[2:] - 2 * com[1:-1] + com[:-2]) * 1000  # mm/ms2 to m/s2
            for ms, (c, a) in enumerate(zip(com[1:-1], acc), 1):
                at = shifted(c, a, floor, g)
                mm = margin(outline, at)
                if moving is None or mm < moving["margin_mm"]:
                    shift = float(np.linalg.norm(at - c[:2]))
                    moving = {"margin_mm": round(mm, 1), "at": {"motion": name, "ms": ms}, "shift_mm": round(shift, 1)}
    stall = round(mjcf.STALL_NM / KGF_CM, 3)
    out = {h: {**s, "rated_kgf_cm": sim.RATED_KGF_CM, "stall_kgf_cm": stall} for h, s in servos.items()}
    return {"names": names, "servos": out}, moving


def vibration(doc, model, data, slow):
    """The neck's figures for ranking the next Mech's candidates (#51), at data's pose: the head's mass times its centre
    of mass's height above the tilt axis, and per neck servo the inertia its output joint turns, its gain (the output's
    span over the servo's, from the slow sweep's ends) and the servo loop's own mode through it (the servo's kp on its
    rotor plus the load referred to its shaft). Not the lowest mode: the printed parts' compliance and the gears' backlash,
    which the rigid model lacks, set that; it is measured on a print."""
    stage, full, out = stages.STAGES[doc], np.zeros((model.nv, model.nv)), {}
    mujoco.mj_fullM(model, data, full)
    for h in (TILT, PAN):
        lo, hi = stage.horns[h].limits
        j = model.joint(stage.horns[h].loops[0].joint)
        q = model.jnt_qposadr[j.id]
        gain = abs(slow[(h, hi)][q] - slow[(h, lo)][q]) / math.radians(hi - lo)
        inertia = full[model.jnt_dofadr[j.id], model.jnt_dofadr[j.id]]
        rotor = model.dof_armature[model.jnt_dofadr[model.actuator(h).trnid[0]]]
        hz = math.sqrt(mjcf.SERVO["kp"] / (rotor + gain**2 * inertia)) / (2 * math.pi)
        out[h] = {"inertia_g_cm2": round(inertia * 1e7, 1), "gain": round(gain, 3), "servo_loop_hz": round(hz, 1)}
        if h == TILT:
            body = model.jnt_bodyid[j.id]
            grams, above = model.body_subtreemass[body] * 1000, (data.subtree_com[body] - data.xanchor[j.id])[2] * 1000
            out |= {"head_g": round(grams, 1), "head_above_tilt_mm": round(above, 1), "mh_g_mm": round(grams * above)}
    return out


def _worst(old, value, at, key):
    return old if old and old[key] >= value else {key: round(value, 3), "at": at}


def measure(doc, model):
    """The document's MuJoCo report (a dict, in the shape model/test_report.py reads). Widens `model`, which is the
    report's own (widen())."""
    stage, todo = stages.STAGES[doc], poses(doc)
    widen(model)
    still = mjcf.pose(model, {})
    rest = _contacts(model, still)
    pairs, residuals, loops, actuators, slow = {}, {}, {}, {}, {}
    neck = {PAN, TILT} <= set(stage.horns)
    plate = _plate(model, still) if neck else None  # static: its outline holds for every pose
    outline = footprint(plate) if neck else None
    tip = {} if neck else None
    for ctrl in todo:
        data = mjcf.pose(model, ctrl)
        if len(ctrl) == 1:
            slow[tuple(ctrl.items())[0]] = data.qpos.copy()
        for loop, mm in mjcf.residuals(model, data).items():
            residuals[loop] = _worst(residuals.get(loop), mm, ctrl, "max_mm")
        for loop, (mm_rad, deg) in gates.loops(model, data).items():  # margin() is the footprint's
            least = loops.setdefault(loop, {"margin_mm_rad": math.inf, "transmission_deg": math.inf})
            if mm_rad < least["margin_mm_rad"]:
                least["margin_mm_rad"], least["margin_at"] = round(mm_rad, 2), ctrl
            if deg < least["transmission_deg"]:
                least["transmission_deg"], least["transmission_at"] = round(deg, 1), ctrl
        for h in stage.horns:
            actuators[h] = _worst(actuators.get(h), abs(data.actuator(h).force[0]) / KGF_CM, ctrl, "hold_kgf_cm")
        if tip is not None:
            mm = margin(outline, data.subtree_com[0][:2] * 1000)
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
        "loops": loops,
        "actuators": {
            h: {**a, "rated_kgf_cm": sim.RATED_KGF_CM, "stall_kgf_cm": round(mjcf.STALL_NM / KGF_CM, 3)}
            for h, a in actuators.items()
        },
        "full_speed": full_speed,
    }
    out["motions"], moving = _motions(doc, model, plate)
    if neck:
        size = [round(float(mm), 1) for mm in np.ptp(plate[:, :2], axis=0)]
        out["tip_over"] = {**tip, "moving": moving, "footprint_mm": size}  # the base's x by y
        out["vibration"] = vibration(doc, model, still, slow)
    return out
