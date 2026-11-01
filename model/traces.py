"""Gesture replay for the model (#20, #39): the five gestures plus thinking recorded from the eye program on CPython
(machine stubbed by the root conftest, a virtual clock instead of sleeping) as the program's own commands before its
servo calibration (lid fraction 0 closed .. 1 open, eye position -1..1 of its range), mapped onto the model's horn
joint degrees per 100 ms frame: lids through the Core's own calibration (eyes/calibration.json) to the shared lid frame, then
the horn's spline tooth (model/sim.joint_deg, #134); eyes over geometry.HORN_LIMITS. The GIFs are rendered from these frames by model/render/pictures.py (`make gifs`, docs/model-notes.md);
`commands` gives the writes at their own times, which model/trajectories.py plays in MuJoCo."""

import importlib.util
import json
import os
import sys

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
from model import geometry, sim  # noqa: E402

CAL = json.load(open(os.path.join(REPO, "eyes", "calibration.json")))
# each gesture the Core plays, at its normal level (the wink to the Mech's left, 1, not a random side), then thinking
GESTURES = {**{g: f"{g} {1 if g == 'wink' else 2}" for g in mod.Eyes.GESTURES}, "thinking": "thinking"}
SERVOS = geometry.EYES_SERVOS
PIN = {name: pin for pin, name in mod.NAME.items()}
FRAME_MS, THINK_MS = 100, 6000
_CORE = mod.Eyes()  # the Core's lid mapping (fraction -> shared lid frame degrees) under the calibration
_CORE.cal.update(CAL)


def joint(servo, v):
    """Model horn degrees from neutral for a lid fraction or an eye position."""
    if "lid" in servo:
        return sim.joint_deg(servo, _CORE._lid_shared(PIN[servo], v))
    lo, hi = geometry.HORN_LIMITS[servo]
    return v * ((hi - 90) if v > 0 else (90 - lo))


def commands(gesture):
    """The gesture as the Core writes it, from rest: ([(ms, servo, model horn degrees)] after every write, rest's own
    writes before ms 0; the frame times in ms, one per 100 ms from 0, a frame past the last write)."""
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
    if gesture == "thinking":
        e.handle_line("thinking")
        for t in range(clock[0], clock[0] + THINK_MS, FRAME_MS):
            clock[0] = t
            e.tick(t)
    else:
        e.handle_line(GESTURES[gesture])
    writes = [(t - start, s, round(joint(s, a if "lid" in s else a / half[PIN[s]]), 2)) for t, s, a in log]
    return writes, range(0, clock[0] - start + FRAME_MS + 1, FRAME_MS)


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
