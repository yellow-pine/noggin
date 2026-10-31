"""Mech-wide checks over the engine's poses (#24, #22), folded into the report by model/engine/run.py: dynamic torque
per horn (gravity plus the chain's inertia reflected to the horn axis times the peak horn acceleration of the clocked
gestures through the servo plant, eyes/replay.py and eyes/servo.py; for the untraced Core 2 horns, the acceleration
that keeps them under the limit), the clutch margin per pose, and over the pan x tilt grid the tip-over margin."""

import math

import numpy as np
from scipy.spatial import ConvexHull

from model import electrical
from model.engine import linkage, masses, stages

FRAME_S = 0.02  # 50 Hz PWM: the servo sees one new pulse per frame, so the plant is stepped per frame
KGF_CM = 0.0980665  # N.m
CLUTCH_KGF_CM, CLUTCH_MARGIN = 0.9, 1.5  # B-PG001 clutch protection at 4.8 V (docs/research/2026-10-31-electrical.md)
HORN_SERVO = {
    "L lid horn (inferred)": "l_lid",
    "L eye horn (inferred)": "l_eye",
    "R lid horn (inferred)": "r_lid",
    "R eye horn (inferred)": "r_eye",
    "tilt horn (inferred)": "tilt",
    "pan horn (inferred)": "rotate",
    "jaw horn (inferred)": "mouth",
}  # geometry.HORN_LIMITS keys


def peak_accel(cal):
    """deg/s2 per servo: every gesture line the eye program plays (eyes/replay.py's clock) fed through servo.Plant one
    PWM frame at a time; the peak second difference of the horn position. Core 2 has no choreography yet, so its
    servos (tilt, pan, mouth) are absent: their report gives the acceleration the choreography must stay under."""
    servo, replay = electrical.servo, electrical.replay
    eyes = replay._eyes()
    out = {}
    for gesture in eyes.Eyes.GESTURES:
        for level in (1, 2, 3):
            log, total = replay.play([f"{gesture} {level}"], cal)
            for pin, name in eyes.NAME.items():
                ev = [(t, a) for t, p, a in log if p == pin]
                if not ev:
                    continue
                plant = servo.Plant(ev[0][1])
                i, cmd, prev, v_prev, best = 0, ev[0][1], plant.pos, 0.0, 0.0
                for k in range(total // 20 + 50):  # past the last command until the plant has arrived
                    while i < len(ev) and ev[i][0] <= k * 20:
                        cmd, i = ev[i][1], i + 1
                    pos = plant.step(cmd, FRAME_S)
                    v = (pos - prev) / FRAME_S
                    best, prev, v_prev = max(best, abs(v - v_prev) / FRAME_S), pos, v
                out[name] = max(out.get(name, 0.0), best)
    return out


def inertia(mats_a, mats_b, table, dtheta_deg):
    """g.mm2 the horn feels: twice the chain's kinetic energy per unit horn speed squared, from two poses dtheta_deg
    apart (every part's centre-of-mass speed and spin, so a linkage's ratio is in it)."""
    dtheta = math.radians(dtheta_deg)
    out = 0.0
    for name, a in mats_a.items():
        b = mats_b[name]
        if name not in table or np.allclose(a, b):
            continue
        m = table[name]
        v = np.subtract(masses.com_at(m, b), masses.com_at(m, a)) / dtheta
        r = b[:3, :3] @ a[:3, :3].T
        w = np.array([r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]]) / 2 / dtheta  # small-angle spin
        out += m["g"] * float(v @ v) + float(w @ (a[:3, :3] @ np.array(m["inertia_g_mm2"]) @ a[:3, :3].T) @ w)
    return out


def dynamic_torque(stage, table, horn_name, degs, accel_deg_s2, half_step=0.5):
    """{deg: {kgf_cm, gravity_kgf_cm, inertia_g_mm2}}: gravity (masses.gravity_torque) plus the reflected inertia times the peak
    acceleration, at each sampled horn angle. The inertia is a central difference, one-sided where the loop cannot
    close."""
    gravity = masses.gravity_torque(stage, horn_name, table, degs)
    lo, hi = stage.horns[horn_name].limits
    out = {}
    for d in degs:
        a, b = max(d - half_step, lo), min(d + half_step, hi)
        try:
            pa = stages.pose(stage, horn_name, a).parts
        except linkage.Unreachable:
            a, pa = d, stages.pose(stage, horn_name, d).parts
        try:
            pb = stages.pose(stage, horn_name, b).parts
        except linkage.Unreachable:
            b, pb = d, stages.pose(stage, horn_name, d).parts
        i = inertia(pa, pb, table, b - a)
        out[d] = {
            "kgf_cm": gravity[d] + i * 1e-9 * math.radians(accel_deg_s2) / KGF_CM,
            "gravity_kgf_cm": gravity[d],
            "inertia_g_mm2": i,
        }
    return out


def accel_limit(by_deg, limit_kgf_cm):
    """deg/s2 the horn may reach at every pose and stay under limit_kgf_cm: min over poses of (limit - gravity) /
    inertia, from dynamic_torque."""
    return min(
        math.degrees((limit_kgf_cm - t["gravity_kgf_cm"]) * KGF_CM / (t["inertia_g_mm2"] * 1e-9))
        for t in by_deg.values()
        if t["inertia_g_mm2"] > 0
    )


def clutch(by_deg):
    """Holding load per pose against the clutch: gravity at rest only. A horn held against its stop (a lid closed) adds
    the servo's own stall-limited push, which the clutch does not see as a back-driving load, so a stop is its static
    load too. Poses over 0.9 / 1.5 kgf.cm are flagged as a decalibration risk."""
    limit = CLUTCH_KGF_CM / CLUTCH_MARGIN
    deg = max(by_deg, key=lambda d: by_deg[d]["gravity_kgf_cm"])
    return {
        "hold_kgf_cm": round(by_deg[deg]["gravity_kgf_cm"], 3),
        "at_deg": deg,
        "limit_kgf_cm": round(limit, 3),
        "flagged": [d for d in sorted(by_deg) if by_deg[d]["gravity_kgf_cm"] > limit],
    }


def footprint(points):
    """The base plate's plan outline: the convex hull of its vertices in XY as line equations, inside <= 0."""
    return ConvexHull(np.asarray(points, float)[:, :2]).equations


def margin(outline, xy):
    """mm from a plan point to the outline: positive inside (the nearest edge), negative outside."""
    return float(-(outline[:, :2] @ np.asarray(xy, float) + outline[:, 2]).max())


PAN, TILT = "pan horn (inferred)", "tilt horn (inferred)"


def mech_poses(stage, step):
    """(pan deg, tilt deg, {part: 4x4}) over the pan x tilt grid at `step` within the limits (unreachable angles
    skipped): the tilt pose carried by the pan's turn, which moves every tilt-chain part rigidly."""
    neutral = {n: p.matrix for n, p in stage.parts.items()}

    def sampled(h):
        lo, hi = stage.horns[h].limits
        out = {}
        for d in [*range(lo, hi, step), hi]:
            try:
                out[d] = stages.pose(stage, h, d).parts
            except linkage.Unreachable:
                pass
        return out

    tilts = sampled(TILT)
    for p, pm in sampled(PAN).items():
        carry = {n: pm[n] @ np.linalg.inv(neutral[n]) for n in pm}
        for t, tm in tilts.items():
            yield p, t, {n: carry[n] @ tm[n] for n in tm}


def tip_over(stage, table, outline, step):
    """The Mech's centre of mass against the base footprint at every pan/tilt pose: the smallest margin (mm)."""
    total = sum(m["g"] for m in table.values())
    best = None
    for p, t, mats in mech_poses(stage, step):
        com = sum(m["g"] * (mats[n][:3, :3] @ m["com"] + mats[n][:3, 3]) for n, m in table.items()) / total
        mm = margin(outline, com[:2])
        if best is None or mm < best["margin_mm"]:
            best = {"margin_mm": round(mm, 1), "at": {"pan": p, "tilt": t}, "com": [round(c, 1) for c in com]}
    return best
