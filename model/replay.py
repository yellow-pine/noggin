"""Gesture replay, run INSIDE Fusion by model/traces.py, one call per gesture: GESTURE = "<name>" drives the four eyes
horn joints of noggin-stage1 (base + eyes, as on the desk) through that gesture's frames (model/build/traces.json,
model joint degrees per 100 ms) and saves two transparent captures per frame: the README view (perspective, front-left
three-quarter, VIEW) to model/build/replay/<gesture>/NNN.png and the straight front view (orthographic, for symmetry
checks) to model/build/replay/<gesture>-front/NNN.png. The eyes are a reference in the Stage, so their link is broken
in memory and their static parts grounded to drive the joints, and the document is closed without saving: the saved Stage never changes."""

# include: model/geometry.py
# include: model/fusion_lib.py
import glob
import json
import math
import os

import adsk.core
import adsk.fusion

GESTURE = None  # model/traces.py substitutes this line per call
DOC = "noggin-stage1"
REPO = os.path.expanduser("~/code/noggin")
OUT = os.path.join(REPO, "model", "build")
SERVOS = ("l_lid", "l_eye", "r_lid", "r_eye")
# The README camera (docs/model-notes.md): from the viewer's front-left (the mech's right, -X in the PT frame) at 45
# degrees, 25 degrees above the eye centre line, aimed between the eye centre and the base plate's middle so the eyes
# fill the frame with the base behind them.
EL, AZ = math.radians(25), math.radians(45)
VIEW = ((-math.cos(EL) * math.sin(AZ), -math.cos(EL) * math.cos(AZ), math.sin(EL)), Z)
EYE_CENTRE = in_frame(EYES_ON_BASE, (CENTRE_X, 0.0, 0.0))
AIM = (tuple((e + b) / 2 for e, b in zip(EYE_CENTRE, (0.0, 50.0, 3.0))), 450.0)
FRONT = ((0, -1, 0), Z)
STEP_DEG = 4.0


def open_fresh(app):
    for d in [d for d in app.documents if d.name.split(" v")[0] == DOC]:
        d.close(False)  # a broken-link copy left by an interrupted run
    fld = next(p for p in app.data.activeHub.dataProjects if p.name == PROJECT_NAME).rootFolder
    return app.documents.open(next(f for f in fld.dataFiles if f.name == DOC), True)


def folder(name):
    path = os.path.join(OUT, "replay", name)
    os.makedirs(path, exist_ok=True)
    for old in glob.glob(os.path.join(path, "*.png")):
        os.remove(old)
    return path


def run(_context: str):
    app = adsk.core.Application.get()
    doc = open_fresh(app)
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        eyes = next(o for o in root.occurrences if o.name.startswith("noggin-eyes"))
        eyes.breakLink()
        for occ in eyes.childOccurrences:  # the eyes' own grounds (model/eyes.py) do not survive the insert
            name = occ.component.name
            occ.isGrounded = "servo" in name or not any(w in name for w in ("lid", "eyeball", "pupil", "horn", "bar"))
        design.isContactAnalysisEnabled = False  # the contact set would stop the drive at the designed contacts
        joints = {j.name: j for j in root.allJoints if not j.isSuppressed}
        horns = {s: next(j for n, j in joints.items() if n.startswith(f"{s[0].upper()} {s[2:]} horn")) for s in SERVOS}
        for h in horns.values():  # the model's lid ends lie past the designer's limits
            lim = h.jointMotion.rotationLimits
            lim.isMinimumValueEnabled = lim.isMaximumValueEnabled = False
        frames = json.load(open(os.path.join(OUT, "traces.json")))[GESTURE]
        view, front = folder(GESTURE), folder(GESTURE + "-front")
        at = {s: 0.0 for s in SERVOS}  # the document opens at neutral
        for i, frame in enumerate(frames):
            # Small steps keep Fusion's solver on the four-bars' branch: a 50 degree jump can flip the lids over.
            n = math.ceil(max(abs(frame[s] - at[s]) for s in SERVOS) / STEP_DEG) or 1
            for k in range(1, n + 1):
                for s, h in horns.items():
                    h.jointMotion.rotationValue = math.radians(at[s] + (frame[s] - at[s]) * k / n)
                adsk.doEvents()
            at = dict(frame)
            screenshot(app, os.path.join(view, f"{i:03d}.png"), *VIEW, 960, 720, aim=AIM)
            screenshot(app, os.path.join(front, f"{i:03d}.png"), *FRONT, 800, 600)
    finally:
        doc.close(False)
    print(f"{GESTURE}: {len(frames)} frames to {view} and {front}\n")
