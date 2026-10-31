"""Gesture replay for the model (#20, #39): the five gestures plus thinking recorded from the eye program on CPython
(machine stubbed by the root conftest, a virtual clock instead of sleeping) as the program's own commands before its
servo calibration (lid fraction 0 closed .. 1 open, eye position -1..1 of its range), mapped onto the model's horn
joint degrees per 100 ms frame: lids between the model's closed and open angles (model/engine/lids.py), eyes over
geometry.HORN_LIMITS. No servo degrees: the real servo ends and horn spline offsets are not the model's. Then played
in Fusion by model/replay.py (one call per gesture, noggin-stage1, a 3/4 and a front capture per frame), the front
frames inked and the 3/4 frames assembled into one cartoon GIF per gesture in model/build (docs/model-notes.md).
`python model/traces.py [gesture...] [--no-fusion]` (Fusion open with its MCP; --no-fusion re-assembles only)."""

import glob
import importlib.util
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "build")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


if "machine" not in sys.modules:  # under pytest the root conftest has done this
    _load("conftest", os.path.join(REPO, "conftest.py"))  # stubs `machine`, puts eyes/ on sys.path
if REPO not in sys.path:
    sys.path.insert(1, REPO)  # model.engine; eyes/ stays first so `import eyes` is the Core program
import eyes as mod  # noqa: E402  the Core's eye program
from model import geometry  # noqa: E402
from model.engine import lids  # noqa: E402

CAL = json.load(open(os.path.join(REPO, "eyes", "calibration.json")))
GESTURES = {
    "eureka": "eureka 2",
    "attention": "attention 2",
    "bored": "bored 2",
    "wince": "wince 2",
    "wink": "wink 1",
    "thinking": "thinking",
}
SERVOS = ("l_lid", "l_eye", "r_lid", "r_eye")
PIN = {name: pin for pin, name in mod.NAME.items()}
FRAME_MS, THINK_MS = 100, 6000


def joint(servo, v):
    """Model horn degrees from neutral for a lid fraction or an eye position."""
    if "lid" in servo:
        closed, opened = lids.ends(servo[0].upper())
        return closed + v * (opened - closed)
    lo, hi = geometry.HORN_LIMITS[servo]
    return v * ((hi - 90) if v > 0 else (90 - lo))


def record(gesture):
    """Model joint degrees per servo at each 100 ms frame of the gesture, from rest, per the current calibration."""
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
    frames, pos, i = [], {}, 0
    for t in range(start, clock[0] + FRAME_MS + 1, FRAME_MS):  # frame 0 is rest: a write at t shows from the next frame
        while i < len(log) and log[i][0] < t:
            pos[log[i][1]] = log[i][2]
            i += 1
        frames.append({s: round(joint(s, pos[s] if "lid" in s else pos[s] / half[PIN[s]]), 2) for s in SERVOS})
    return frames


def gif(name):
    """The README GIF from the gesture's transparent 3/4 captures: cartoon style (model/cartoon.py), cropped to the
    model over all frames, 480 wide, 10 fps, at most 128 colours."""
    from model import cartoon

    raw = sorted(glob.glob(os.path.join(OUT, "replay", name, "*.png")))
    imgs = [cartoon.read(p) for p in raw]
    ys, xs = np.nonzero(np.any([im[..., 3] > 0 for im in imgs], axis=0))
    m = round(0.05 * max(np.ptp(xs), np.ptp(ys)))
    y0, y1, x0, x1 = max(ys.min() - m, 0), ys.max() + m, max(xs.min() - m, 0), xs.max() + m
    out = os.path.join(OUT, "replay", name + "-cartoon")
    os.makedirs(out, exist_ok=True)
    for p, im in zip(raw, imgs, strict=True):
        cartoon.write(os.path.join(out, os.path.basename(p)), cartoon.cartoon(im[y0:y1, x0:x1]))
    palette = "split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=none"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", "10", "-i", os.path.join(out, "%03d.png")]
    subprocess.run([*cmd, "-vf", f"scale=480:-2:flags=area,{palette}", os.path.join(OUT, f"{name}.gif")], check=True)


def main(names, fusion=True):
    """Record, play in Fusion (one call per gesture), ink the front frames, assemble the GIFs. fusion=False only
    re-assembles from the captures already in model/build/replay."""
    from model import cartoon

    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import fusion_run

    os.makedirs(OUT, exist_ok=True)
    if fusion:
        json.dump({g: record(g) for g in GESTURES}, open(os.path.join(OUT, "traces.json"), "w"))
    replay = open(os.path.join(HERE, "replay.py")).read()
    for g in names:
        if fusion:
            print(fusion_run.run_script(replay.replace("GESTURE = None", f"GESTURE = {g!r}"))["message"], end="")
        cartoon.main("ink", sorted(glob.glob(os.path.join(OUT, "replay", g + "-front", "*.png"))))
        gif(g)
        print(f"  {g}.gif: {os.path.getsize(os.path.join(OUT, g + '.gif')) // 1024} KB")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--no-fusion"]
    main(args or list(GESTURES), fusion="--no-fusion" not in sys.argv)
