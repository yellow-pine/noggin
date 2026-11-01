"""Trajectories (#179): each gesture (model/traces.py, the Core program's writes) and the README hero
(model/render/hero.py) played on each Stage by MuJoCo (model/mjcf.py) through the servos' own dynamics, every part's
place in the world per 100 ms frame: the one source of motion the pictures and GIFs render from (#150, poses()) and
the web viewer's GLBs bake (web/build.py).
Each servo slews its command at the rated no-load speed (eyes/servo.py Plant, at 4.8 V as mjcf's stall torque) and its
position actuator follows under the load, its torque limited to the stall torque; contacts are off, as in mjcf.pose.
`python -m model.trajectories` (`make trajectories`) writes model/build/trajectories/<doc>/<motion>.json for every
Stage, skipping a Stage whose files still carry its stamp: {"doc", "motion", "fps", "stamp", "parts": {part: {"pos":
[[x, y, z] metres per frame], "quat": [[w, x, y, z] per frame]}}}, each part's own frame (its mesh's, as model/build/ours
draws it) in MuJoCo's Z-up world, which for a Stage is the PT frame the pictures use."""

import glob
import hashlib
import json
import math
import os
import sys
from importlib.metadata import version

import mujoco
import numpy as np
import trimesh

from model import electrical, geometry, mjcf, stages, traces
from model.render import hero, scene

OUT = os.path.join(mjcf.BUILD, "trajectories")
FPS = 1000 // traces.FRAME_MS
PWM_MS = 20  # a hobby servo takes a new pulse every 20 ms (50 Hz): the hero is commanded at that rate
# what a trajectory is computed from besides the Stage's meshes (stamp; their test files skipped): the Core program
# and its calibration too, which model/traces.py plays
SOURCES = [
    "model/geometry.py",
    "model/stages.py",
    "model/linkage.py",
    "model/sim.py",
    "model/fits.py",
    "model/electrical.py",
    "model/mjcf.py",
    "model/cables.py",
    "model/mating.py",
    "model/printed/*.py",  # our parts and the features they declare (the mating sites)
    "model/envelopes.py",
    "eyes/servo.py",  # the servo's speed and torque
    "model/traces.py",
    "model/trajectories.py",
    "model/render/hero.py",
    "model/render/scene.py",
    "eyes/eyes.py",
    "eyes/gaze_trace.py",
    "eyes/calibration.json",
]


def hero_commands():
    """The hero as servo writes every PWM_MS, its first pose held from before ms 0 (the rest a gesture starts from)."""
    ms = round(hero.SECONDS * 1000)
    writes = [(t, s, d) for t in range(-PWM_MS, ms, PWM_MS) for s, d in hero.at(max(t, 0) / 1000).items()]
    return writes, range(0, ms, traces.FRAME_MS)


MOTIONS = {**{g: lambda g=g: traces.commands(g) for g in traces.GESTURES}, "hero": hero_commands}


def play(model, writes, times, read=lambda data: (data.xpos.copy(), data.xquat.copy())):
    """read(data) at each of times (ms), by default (xpos, xquat) per body: the Mech settled (mjcf.pose) at the writes
    before ms 0, then every write from ms 0 on sent to its servo at its time; writes to servos the model lacks are
    skipped."""
    horns = {s: h for s, h in scene.HORNS.items() if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, h) >= 0}
    writes = [(ms, horns[s], d) for ms, s, d in writes if s in horns]
    command = {h: d for ms, h, d in writes if ms < 0}
    data = mjcf.pose(model, command)
    assert all(h in command for _, h, _ in writes), "every servo is placed before ms 0"
    driven = list(command)
    ids = [model.actuator(h).id for h in driven]
    plants = [electrical.servo.Plant(command[h], electrical.SERVO_MIN_V) for h in driven]
    dt, per_ms = model.opt.timestep, round(0.001 / model.opt.timestep)
    i, step, out = sum(ms < 0 for ms, _, _ in writes), 0, []
    flags = model.opt.disableflags
    model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_CONTACT
    try:
        for t in times:
            while step < t * per_ms:
                while i < len(writes) and writes[i][0] <= step / per_ms:
                    command[writes[i][1]] = writes[i][2]
                    i += 1
                data.ctrl[ids] = [math.radians(p.step(command[h], dt)) for p, h in zip(plants, driven)]
                mujoco.mj_step(model, data)
                step += 1
            out.append(read(data))
    finally:  # the model is the caller's: its contacts come back on
        model.opt.disableflags = flags
    return out


def stamp(doc):
    """sha256 of SOURCES, the Stage's meshes and the MuJoCo and CoACD versions: a trajectory that no longer carries
    it is stale."""
    h = hashlib.sha256(f"mujoco {version('mujoco')} coacd {version('coacd')}".encode())
    paths = [p for pattern in SOURCES for p in sorted(glob.glob(os.path.join(stages.REPO, pattern)))]
    for path in [p for p in paths if not os.path.basename(p).startswith("test_")] + sorted(
        {p.file for p in stages.STAGES[doc].parts.values()}
    ):
        h.update(os.path.relpath(path, stages.REPO).encode() + b"\0" + open(path, "rb").read())
    return h.hexdigest()


def motions(doc):
    """The Stage's motions: every gesture, and the hero where it has the neck (Stages 2 and 3, #180)."""
    return [m for m in MOTIONS if m != "hero" or "pan horn" in stages.STAGES[doc].horns]


def bake(doc, names=None):
    """model/build/trajectories/<doc>/<motion>.json for each of names (default motions(doc)), the paths returned."""
    model, key, paths = mjcf.model(doc), stamp(doc), []
    os.makedirs(os.path.join(OUT, doc), exist_ok=True)
    for name in names or motions(doc):
        frames = play(model, *MOTIONS[name]())
        parts = {
            model.body(b).name: {
                "pos": [np.round(pos[b], 6).tolist() for pos, _ in frames],
                "quat": [np.round(quat[b], 6).tolist() for _, quat in frames],
            }
            for b in range(1, model.nbody)
        }
        paths.append(os.path.join(OUT, doc, name + ".json"))
        with open(paths[-1], "w") as f:
            json.dump({"doc": doc, "motion": name, "fps": FPS, "stamp": key, "parts": parts}, f)
    return paths


def stale(doc):
    """True when a motion's file of the Stage is missing or no longer carries its stamp."""
    key, files = stamp(doc), [os.path.join(OUT, doc, m + ".json") for m in motions(doc)]
    return not all(os.path.isfile(f) and json.load(open(f))["stamp"] == key for f in files)


def poses(doc, motion):
    """The baked motion as [{part: 4x4 world matrix, metres} per frame]: what Blender poses each picture from (#150) and
    the web viewer's GLBs are baked from (web/build.py)."""
    parts = json.load(open(os.path.join(OUT, doc, motion + ".json")))["parts"]
    frames = []
    for i in range(len(next(iter(parts.values()))["pos"])):
        frames.append({})
        for name, p in parts.items():
            m = trimesh.transformations.quaternion_matrix(p["quat"][i])  # w x y z, as MuJoCo's
            m[:3, 3] = p["pos"][i]
            frames[-1][name] = m
    return frames


if __name__ == "__main__":
    for doc in sys.argv[1:] or geometry.STAGES:
        print(f"{doc}: {len(bake(doc))} trajectories" if stale(doc) else f"{doc}: fresh")
