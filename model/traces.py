"""Gesture replay for the model (#20, #39): the five gestures plus thinking recorded from the eye program on CPython
(machine stubbed by the root conftest, a virtual clock instead of sleeping) as the program's own commands before its
servo calibration (lid fraction 0 closed .. 1 open, eye position -1..1 of its range), mapped onto the model's horn
joint degrees per 100 ms frame: lids through the Core's own calibration (eyes/calibration.json) to the shared lid frame, then
the horn's spline tooth (model/sim.joint_deg, #134); eyes over geometry.HORN_LIMITS. The web viewer plays these frames (web/build.py, docs/adr/0008);
`commands` gives the writes at their own times, which model/trajectories.py plays in MuJoCo; `next_commands` the same
program's writes as the next Mech's eyes Core takes them (#663): through the eye gimbal's command map (model/gimbal.py)."""

import importlib.util
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


if "machine" not in sys.modules:  # under pytest the root conftest has done this
    _load("conftest", os.path.join(REPO, "conftest.py"))  # stubs `machine`, puts eyes/ on sys.path
if REPO not in sys.path:
    sys.path.insert(1, REPO)  # model; eyes/ stays first so `import eyes` is the Core program
import eyes as mod  # noqa: E402  the Core's eye program
from model import geometry, gimbal, sim  # noqa: E402

CAL = json.load(open(os.path.join(REPO, "eyes", "calibration.json")))
# each gesture the Core plays, at its normal level (the wink to the Mech's left, 1, not a random side), then thinking
GESTURES = {**{g: f"{g} {1 if g == 'wink' else 2}" for g in mod.Eyes.GESTURES}, "thinking": "thinking"}
SERVOS = geometry.EYES_SERVOS
PIN = {name: pin for pin, name in mod.NAME.items()}
FRAME_MS, THINK_MS = 100, 6000  # THINK_MS: how long a background mode (thinking, Rest) plays
NEXT_MOTIONS = {**GESTURES, "rest": "rest"}  # the next Mech's: today's gestures and Rest with its blinks (#663)
_CORE = mod.Eyes()  # the Core's lid mapping (fraction -> shared lid frame degrees) under the calibration
_CORE.cal.update(CAL)


def joint(servo, v):
    """Model horn degrees from neutral for a lid fraction or an eye position."""
    if "lid" in servo:
        return sim.joint_deg(servo, _CORE._lid_shared(PIN[servo], v))
    lo, hi = geometry.HORN_LIMITS[servo]
    return v * ((hi - 90) if v > 0 else (90 - lo))


def writes(line):
    """A command line as the Core writes it, from rest: ([(ms, servo, command)] after every write, rest's own writes
    before ms 0, each command before the servo calibration: lid fraction, eye degrees from centre; the ms it ended)."""
    clock, log = [0], []  # virtual time; (ms, servo, command) after every write
    mod.sleep_ms = lambda ms: clock.__setitem__(0, clock[0] + ms)
    e = mod.Eyes()
    e.cal.update(CAL)
    half = {p: (hi - lo) / 2 for p, (lo, hi) in ((p, e.range(p)) for p in mod.EYES)}
    # The program's commands before its servo calibration: lid fraction, eye degrees from centre (clamped to its range).
    e._lid_angle = lambda pin, f: min(1.0, max(0.0, f))
    e._eye_angle = lambda pin, a: a - mod.EYE_CENTER
    e.range = lambda pin: (0.0, 1.0) if pin in mod.LIDS else (-half[pin], half[pin])
    original = e.set

    def set_and_log(targets):
        original(targets)
        log.extend((clock[0], mod.NAME[p], a) for p, a in e.pos.items())

    e.set = set_and_log
    e.handle_line("rest")
    start = clock[0]  # every servo has a position from here on
    e.handle_line(line)
    if line in ("thinking", "rest"):
        for t in range(clock[0], clock[0] + THINK_MS, FRAME_MS):
            clock[0] = t
            e.tick(t)
    return [(t - start, s, a) for t, s, a in log], clock[0] - start


def commands(gesture):
    """The gesture as the Core writes it, from rest: ([(ms, servo, model horn degrees)] after every write, rest's own
    writes before ms 0; the frame times in ms, one per 100 ms from 0, a frame past the last write)."""
    log, end = writes(GESTURES[gesture])
    half = {p: (hi - lo) / 2 for p, (lo, hi) in ((p, _CORE.range(p)) for p in mod.EYES)}
    moved = [(t, s, round(joint(s, a if "lid" in s else a / half[PIN[s]]), 2)) for t, s, a in log]
    return moved, range(0, end + FRAME_MS + 1, FRAME_MS)


def record(gesture):
    """Model joint degrees per servo at each 100 ms frame of the gesture, from rest, per the current calibration."""
    writes, times = commands(gesture)
    frames, pos, i = [], {}, 0
    for t in times:  # frame 0 is rest: a write at t shows from the next frame
        while i < len(writes) and writes[i][0] < t:
            pos[writes[i][1]] = writes[i][2]
            i += 1
        frames.append({s: pos[s] for s in SERVOS})
    return frames


def next_commands(motion):
    """The motion as the eye program writes it, from rest, through the next Mech's eye gimbal (#663): the L eye's
    position over the gimbal's yaw range to the yaw and pitch servos (gimbal.servos, the Hooke error taken out), the
    gaze level (the program turns the eyes about one axis); each lid level to its edge, closed shut past the cap's rim,
    rest just over the pupil, open (gimbal.LID_EDGES), the lid following the pitch (#51). ([(ms, horn, servo degrees
    from centre)], rest's writes before ms 0; the frame times), as commands()."""
    log, end = writes(NEXT_MOTIONS[motion])
    half = (lambda lo, hi: (hi - lo) / 2)(*_CORE.range(mod.L_EYE))
    levels = [CAL[k] for k in ("lid_closed", "lid_rest", "lid_open")]
    edges = [gimbal.LID_EDGES[0], gimbal.LID_REST, gimbal.LID_EDGES[1]]
    pitch, out = 0.0, []
    for t, s, a in log:
        if s == "l_eye":  # one yaw servo turns both eyes: the R eye's writes match the L's
            yaw, pitch_servo = gimbal.servos(a / half * gimbal.YAW, pitch)
            out += [(t, "next yaw horn", round(yaw, 2)), (t, "next pitch horn", round(pitch_servo, 2))]
        elif "lid" in s:
            edge = float(np.interp(a, levels, edges))
            out.append(
                (t, f"next {s[0].upper()} lid horn", round(edge - gimbal.LID_REST + gimbal.LID_FOLLOW * pitch, 2))
            )
    return out, range(0, end + FRAME_MS + 1, FRAME_MS)
