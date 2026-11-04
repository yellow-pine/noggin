"""Gesture replay for the model (#20, #39, #663): the five gestures plus thinking recorded from the eye program on
CPython (machine stubbed by the root conftest, a virtual clock instead of sleeping) as the program's own commands before
its servo calibration (lid fraction 0 closed .. 1 open, eye position -1..1 of its range): `writes` gives them at their
own times, `commands` the same program's writes as the Mech's eyes Core takes them (#663): through the eye
gimbal's command map (model/gimbal.py), which model/trajectories.py plays in MuJoCo and the web viewer bakes
(web/build.py, docs/adr/0008)."""

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
from model import geometry, gimbal, neck  # noqa: E402

CAL = json.load(open(os.path.join(REPO, "eyes", "calibration.json")))
# each gesture the Core plays, at its normal level (the wink to the Mech's left, 1, not a random side), then thinking
GESTURES = {**{g: f"{g} {1 if g == 'wink' else 2}" for g in mod.Eyes.GESTURES}, "thinking": "thinking"}
FRAME_MS, THINK_MS = 100, 6000  # THINK_MS: how long a background mode (thinking, Rest) plays
MOTIONS = {**GESTURES, "rest": "rest"}  # the Mech's: today's gestures and Rest with its blinks (#663)
# the Mech's eyes Core calibration beside today's: its head carries 0.6 of a gaze shift past 15 deg (#688, [AND]'s
# head alignment; inferred, no build settles it)
HEAD_CAL = {"head_share": 0.6}
# ms each Core starts a line after the eyes Core: the noggin service sends the neck Core a FRAME after the eyes Core's
# ack, one Wi-Fi round trip (inferred: 20 ms) on top (#688, noggin/service.py send)
DELAY_MS = {"core1": 0, "core2": 40}
CORE = {servo: core for core, ports in geometry.CHANNELS.items() for servo in ports.values()}
_CORE = mod.Eyes()  # the Core's servo ranges under the calibration
_CORE.cal.update(CAL)


def writes(line, cal=CAL):
    """A command line as the Core writes it under `cal`, from rest: ([(ms, servo, command)] after every write, rest's own
    writes before ms 0, each command before the servo calibration: lid fraction, eye and head degrees from centre (the
    head in the eyes' degrees); the ms it ended)."""
    clock, log = [0], []  # virtual time; (ms, servo, command) after every write
    mod.sleep_ms = lambda ms: clock.__setitem__(0, clock[0] + ms)
    e = mod.Eyes()
    e.cal.update(cal)
    half = {p: (hi - lo) / 2 for p, (lo, hi) in ((p, e.range(p)) for p in (*mod.EYES, mod.PAN))}
    # The program's commands before its servo calibration: lid fraction, eye degrees from centre (clamped to its range).
    e._lid_angle = lambda pin, f: min(1.0, max(0.0, f))
    e._eye_angle = lambda pin, a: a - mod.EYE_CENTER
    e._pan_angle = lambda head: head
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


def commands(motion):
    """The motion as the eye program writes it, from rest, through the Mech's eye gimbal (#663): the L eye's
    position over the gimbal's yaw range to the yaw and pitch servos (gimbal.servos, the Hooke error taken out), the
    gaze level (the program turns the eyes about one axis); each lid level to its upper lid's edge, closed shut where
    the lower lid meets it (gimbal.LID_SHUT, #698), rest just over the pupil, open (gimbal.LID_EDGES), the lid following
    the pitch (#51); under its calibration
    (HEAD_CAL) the head joins wide gaze shifts (#688): the pan, in the eyes' degrees, scaled as the yaw, through the
    pan's four-bar (neck.servo_for), each Core's writes DELAY_MS late. ([(ms, horn, servo degrees from centre)] in time
    order, rest's writes before ms 0; the frame times), as commands()."""
    log, end = writes(MOTIONS[motion], CAL | HEAD_CAL)
    lo, hi = _CORE.range(mod.L_EYE)
    half = (hi - lo) / 2
    levels = [CAL[k] for k in ("lid_closed", "lid_rest", "lid_open")]
    edges = [gimbal.LID_SHUT, gimbal.LID_REST, gimbal.LID_EDGES[1]]
    pitch, out = 0.0, []
    for t, s, a in log:
        t += DELAY_MS[CORE[s]]
        if s == "l_eye":  # one yaw servo turns both eyes: the R eye's writes match the L's
            yaw, pitch_servo = gimbal.servos(a / half * gimbal.YAW, pitch)
            out += [(t, "yaw horn", round(yaw, 2)), (t, "pitch horn", round(pitch_servo, 2))]
        elif "lid" in s:
            edge = float(np.interp(a, levels, edges))
            out.append((t, f"{s[0].upper()} lid horn", round(edge - gimbal.LID_REST + gimbal.LID_FOLLOW * pitch, 2)))
        elif s == "pan":
            out.append((t, "pan horn", round(neck.servo_for("pan", a / half * gimbal.YAW), 2)))
    return sorted(out, key=lambda w: w[0]), range(0, end + max(DELAY_MS.values()) + FRAME_MS + 1, FRAME_MS)
