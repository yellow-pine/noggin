"""The 9 g servo's values fitted to filmed takes (#625, docs/research/2026-11-02-literature-simulation.md 1 and Practice 2):
MuJoCo's sysid toolbox (mujoco.sysid: least squares over batched rollouts) moves mjcf.SERVO's stall torque, no-load
speed, armature and delay until a one-servo rig driven by mjcf.drive plays each take's commands as the filmed horn
moved. kp stays inferred: it acts only within the half degree of the servo's deadband, finer than a video reads.

A take is one JSON file, filmed at the phone's slow-motion rate with a marker on the horn, the shaft upright so gravity
does not turn it: {"load_g": the mass taped to the horn, "arm_mm": its distance from the shaft, "t_s": [each frame's
time], "command_deg": [the command the Core held at that frame, degrees from neutral], "horn_deg": [the marker's
angle at that frame, degrees from neutral]}, the horn at rest at its first command when the take starts. Film the bare
horn and a load a few times the gear train's inertia (docs/build/tests.md: ten 2 euro coins at 50 mm), moves both
ways: the motor's run-up differs between them while the delay does not, which tells the armature from the delay (with
one coin at the tip they trade off, and the stall torque comes out 40 % off).

`python -m model.servo_fit take.json ...` fits and writes model/servo_fit.json, whose values mjcf.SERVO then takes over
the inferred ones (the model's sources change, so CI builds its outputs again)."""

import json
import math
import sys

import mujoco
import numpy as np
from mujoco import sysid

from model import mjcf

FIT = mjcf.FIT
HORN = "servo"
DELAY_MAX_S = 0.05  # the history the rig keeps, so the fit can move the delay up to it
# Gauss-Newton finds the delay only from near it: a start every 10 ms, the best fit kept
DELAYS_S = (0.005, 0.015, 0.025, 0.035, 0.045)
# the other values fitted as factors on the start's (they differ by 1e4 in size), within these bounds
FACTORS = {"stall_nm": (0.25, 4), "no_load_rad_s": (0.25, 4), "armature": (0.1, 10)}


def rig(values, take, torque=False):
    """The take's rig as an MjSpec: the horn on an upright hinge, the load a point at arm_mm, driven by mjcf.drive;
    a sensor on the horn's angle (and on the servo's torque)."""
    s = mujoco.MjSpec()
    s.compiler.degree = False
    s.option.timestep = mjcf.TIMESTEP
    horn = s.worldbody.add_body(name=HORN)
    horn.add_joint(name=HORN, type=mujoco.mjtJoint.mjJNT_HINGE, axis=[0, 0, 1])
    sphere = mujoco.mjtGeom.mjGEOM_SPHERE
    horn.add_geom(type=sphere, size=[0.001, 0, 0], mass=1e-4)  # the horn's own inertia is the servo's armature
    if take["load_g"]:
        horn.add_geom(type=sphere, size=[0.001, 0, 0], pos=[take["arm_mm"] * mjcf.MM, 0, 0], mass=take["load_g"] / 1000)
    mjcf.drive(s, HORN, values, DELAY_MAX_S)
    s.add_sensor(type=mujoco.mjtSensor.mjSENS_JOINTPOS, objtype=mujoco.mjtObj.mjOBJ_JOINT, objname=HORN)
    if torque:
        s.add_sensor(type=mujoco.mjtSensor.mjSENS_ACTUATORFRC, objtype=mujoco.mjtObj.mjOBJ_ACTUATOR, objname=HORN)
    return s


def _control(take):
    """The take's commands (rad) held from frame to frame at the sim's step, as the Core's PWM holds them."""
    t, rad = np.asarray(take["t_s"]), np.radians(take["command_deg"])[:, None]
    return sysid.TimeSeries(t - t[0], rad).resample(target_dt=mjcf.TIMESTEP, method="zoh")


def _start(model, take):
    """The full physics state at rest at the first command, the command's history full of it."""
    data, rad = mujoco.MjData(model), math.radians(take["command_deg"][0])
    data.qpos[:] = data.ctrl[:] = rad
    hist = np.full((model.actuator_history[0][0], 1), rad)
    mujoco.mj_initCtrlHistory(model, data, 0, None, hist)
    state = np.empty(mujoco.mj_stateSize(model, mujoco.mjtState.mjSTATE_FULLPHYSICS))
    mujoco.mj_getState(model, data, state, mujoco.mjtState.mjSTATE_FULLPHYSICS)
    return state


def play(values, take, torque=False):
    """(t_s, horn_deg[, torque N.m]) at the take's frames: the rig played through the take's commands with values."""
    model = rig(values, take, torque).compile()
    (out,) = sysid.sysid_rollout(model, mujoco.MjData(model), _control(take), _start(model, take))
    t = np.asarray(take["t_s"]) - take["t_s"][0]
    sensed = out.sensordata
    cols = [np.interp(t, sensed.times, sensed.data[:, i]) for i in range(sensed.data.shape[1])]
    return (t, np.degrees(cols[0]), *cols[1:])


def fit(takes, start=mjcf.SERVO):
    """The values (mjcf.SERVO's keys) under which the rig plays every take closest to its filmed horn_deg."""
    params = sysid.ParameterDict()
    for key, (lo, hi) in [*FACTORS.items(), ("delay_s", (0, 1))]:  # the delay as a fraction of DELAY_MAX_S
        params.add(sysid.Parameter(key, nominal=1.0, min_value=lo, max_value=hi, modifier=lambda s, p: None))

    def values(p):
        fitted = {k: start[k] * p[k].value[0] for k in FACTORS}
        return {**start, **fitted, "delay_s": p["delay_s"].value[0] * DELAY_MAX_S}

    def build(p, spec):  # the drive's values are tied (kd from kp and armature), so the rig is built again
        return rig(values(p), of[id(spec)]).compile()

    groups, of = [], {}
    for i, take in enumerate(takes):
        spec = rig(start, take)
        of[id(spec)] = take
        model = spec.compile()
        t = np.asarray(take["t_s"]) - take["t_s"][0]
        horn = sysid.TimeSeries.from_names(t, np.radians(take["horn_deg"])[:, None], model)
        groups.append(sysid.ModelSequences(f"take {i}", spec, f"take {i}", _start(model, take), _control(take), horn))
    residual = sysid.build_residual_fn(models_sequences=groups, build_model=build)

    def cost(p):
        return float(np.sum(np.concatenate(residual(p.as_vector(), p.copy())[0]) ** 2))

    fits = []
    for delay_s in DELAYS_S:
        p = params.copy()
        p["delay_s"].value[:] = delay_s / DELAY_MAX_S
        fits.append(sysid.optimize(initial_params=p, residual_fn=residual, verbose=False, optimizer="scipy")[0])
    return values(min(fits, key=cost))


if __name__ == "__main__":
    assert sys.argv[1:], "usage: python -m model.servo_fit take.json ..."
    values = fit([json.load(open(p)) for p in sys.argv[1:]])
    with open(FIT, "w") as f:
        json.dump(values, f, indent=2)
        f.write("\n")
    print(json.dumps(values, indent=2))
