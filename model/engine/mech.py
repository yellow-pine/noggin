"""Mech-wide checks over the engine's poses (#24, #22), folded into the report by model/engine/run.py: dynamic torque
per horn (gravity plus the chain's inertia reflected to the horn axis times the peak horn acceleration of the clocked
gestures through the servo plant, eyes/replay.py and eyes/servo.py; for the untraced Core 2 horns, the acceleration
that keeps them under the limit)."""

import math

import numpy as np

from model import electrical
from model.engine import linkage, masses, stages

FRAME_S = 0.02  # 50 Hz PWM: the servo sees one new pulse per frame, so the plant is stepped per frame
KGF_CM = 0.0980665  # N.m
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
    """{deg: {kgf_cm, inertia_g_mm2}}: gravity (masses.gravity_torque) plus the reflected inertia times the peak
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
            "inertia_g_mm2": i,
        }
    return out


def accel_limit(by_deg, limit_kgf_cm):
    """deg/s2 the horn may reach at every pose and stay under limit_kgf_cm: min over poses of (limit - gravity) / inertia,
    from dynamic_torque(..., accel 0)."""
    return min(
        math.degrees((limit_kgf_cm - t["kgf_cm"]) * KGF_CM / (t["inertia_g_mm2"] * 1e-9))
        for t in by_deg.values()
        if t["inertia_g_mm2"] > 0
    )
