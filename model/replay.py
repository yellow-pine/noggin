"""Calibration replay, run INSIDE Fusion by model/traces.py, one call per gesture: GESTURE = "<name>" drives the four
horn joints of DOC through that gesture's frames (model/build/traces.json, joint degrees per 100 ms) with the joint
limits off, since the calibrated servo ends lie outside the designer's limits, and saves a front-view screenshot per
frame to model/build/replay/<gesture>/NNN.png. Limits and the neutral pose are put back; never saves."""
# include: model/geometry.py
# include: model/fusion_lib.py
import adsk.core, adsk.fusion, glob, json, math, os

GESTURE = None                        # model/traces.py substitutes this line per call
DOC = "noggin-eyes"
REPO = os.path.expanduser("~/code/noggin")
OUT = os.path.join(REPO, "model", "build")
SERVOS = ("l_lid", "l_eye", "r_lid", "r_eye")


def open_doc(app):
    if app.activeDocument and app.activeDocument.name.split(" v")[0] == DOC:
        return app.activeDocument
    fld = next(p for p in app.data.activeHub.dataProjects if p.name == PROJECT_NAME).rootFolder
    return app.documents.open(next(f for f in fld.dataFiles if f.name == DOC), True)


def run(_context: str):
    app = adsk.core.Application.get()
    open_doc(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    joints = {j.name: j for j in design.rootComponent.allJoints if not j.isSuppressed}
    horns = {s: next(j for n, j in joints.items() if n.startswith(f"{s[0].upper()} {'lid' if 'lid' in s else 'eye'} horn")) for s in SERVOS}
    frames = json.load(open(os.path.join(OUT, "traces.json")))[GESTURE]
    folder = os.path.join(OUT, "replay", GESTURE)
    os.makedirs(folder, exist_ok=True)
    for old in glob.glob(os.path.join(folder, "*.png")):
        os.remove(old)
    contact_was = design.isContactAnalysisEnabled       # the contact set would stop the drive at the designed contacts
    design.isContactAnalysisEnabled = False
    limits = [h.jointMotion.rotationLimits for h in horns.values()]
    for lim in limits:
        lim.isMinimumValueEnabled = lim.isMaximumValueEnabled = False
    try:
        for i, frame in enumerate(frames):
            for s, h in horns.items():
                h.jointMotion.rotationValue = math.radians(frame[s])
            adsk.doEvents()
            screenshot(app, os.path.join(folder, f"{i:03d}.png"), (0, 0, -1), Y, 800, 600)
    finally:
        for h in horns.values():
            h.jointMotion.rotationValue = 0.0
        for lim in limits:
            lim.isMinimumValueEnabled = lim.isMaximumValueEnabled = True
        design.isContactAnalysisEnabled = contact_was
    print(f"{GESTURE}: {len(frames)} frames to {folder}\n")
