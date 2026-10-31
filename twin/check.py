"""Clearance check for one Stage document, run INSIDE Fusion (scripts/fusion_run.py twin/check.py).
Drives every revolute joint named "... horn" from its min to its max limit in 10-degree steps, measures
the minimum distance between each occurrence in the horn's moving chain and every other occurrence,
runs interference at neutral and at both extremes, records top-level bounding boxes at neutral and
writes twin/build/<DOC>-report.json plus twin/build/<DOC>.png. twin/test_report.py reads the report.
Angles are joint angles relative to the 90-degree neutral the STLs are modelled in. API units: cm."""
# include: twin/geometry.py
import adsk.core, adsk.fusion, json, math, os

DOC = "noggin-eyes"                   # the coordinator edits this per Stage: noggin-eyes, noggin-pan-tilt, noggin-mouth
PROJECT_NAME, FOLDER_NAME = "Default Project", "noggin"
REPO = os.path.expanduser("~/code/noggin")
OUT = os.path.join(REPO, "twin", "build")
STEP_DEG, CLEARANCE_MM = 10, 3.0


def open_doc(app):
    if app.activeDocument and app.activeDocument.name.split(" v")[0] == DOC:
        return app.activeDocument
    project = next(p for p in app.data.activeHub.dataProjects if p.name == PROJECT_NAME)
    fld = next(f for f in project.rootFolder.dataFolders if f.name == FOLDER_NAME)
    return app.documents.open(next(f for f in fld.dataFiles if f.name == DOC), True)


def moving_chain(horn, joints):
    """Occurrences that move with the horn: Fusion's occurrenceOne is the moving side of a joint; walk the
    other joints from it, never through grounded occurrences or the horn's fixed side (occurrenceTwo)."""
    stop = {horn.occurrenceTwo.fullPathName} if horn.occurrenceTwo else set()
    chain, todo = {}, [horn.occurrenceOne]
    while todo:
        occ = todo.pop()
        if occ is None or occ.isGrounded or occ.fullPathName in stop or occ.fullPathName in chain:
            continue
        chain[occ.fullPathName] = occ
        for j in joints:
            if j is horn or j.isSuppressed:
                continue
            ends = [j.occurrenceOne, j.occurrenceTwo]
            if any(e is not None and e.fullPathName == occ.fullPathName for e in ends):
                todo.extend(ends)
    return chain


def mm3(p):
    return [round(p.x * 10, 2), round(p.y * 10, 2), round(p.z * 10, 2)]


def name(body):
    return body.assemblyContext.name if body.assemblyContext else body.name


def interference(design, root, pose):
    coll = adsk.core.ObjectCollection.create()
    for occ in root.allOccurrences:
        for b in occ.bRepBodies:
            coll.add(b)
    out = []
    results = design.analyzeInterference(design.createInterferenceInput(coll))
    for i in range(results.count):
        r = results.item(i)
        body = r.interferenceBody
        out.append({"a": name(r.entityOne), "b": name(r.entityTwo),
                    "volume_mm3": round(body.volume * 1000, 3) if body else None, "pose": pose})
    return out


def run(_context: str):
    """Entry point for the Fusion MCP `script` tool (no exception handling by design: errors must surface)."""
    app = adsk.core.Application.get()
    doc = open_doc(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    joints = [j for j in root.allJoints if not j.isSuppressed]
    horns = [j for j in joints if j.jointMotion.jointType == adsk.fusion.JointTypes.RevoluteJointType
             and "horn" in j.name.lower()]
    if not horns:
        raise RuntimeError(f"{DOC}: no revolute joint named '... horn'")
    for h in horns:                                     # neutral pose first
        h.jointMotion.rotationValue = 0.0
    report = {"doc": DOC, "version": doc.dataFile.versionNumber if doc.dataFile else None,
              "clearance_mm": CLEARANCE_MM, "step_deg": STEP_DEG, "horns": {},
              "interference": interference(design, root, "neutral"),
              "bboxes": {o.name: [mm3(o.boundingBox.minPoint), mm3(o.boundingBox.maxPoint)] for o in root.occurrences},
              "violations": []}
    for horn in horns:
        motion = horn.jointMotion
        lim = motion.rotationLimits
        lo, hi = round(math.degrees(lim.minimumValue)), round(math.degrees(lim.maximumValue))
        degs = list(range(lo, hi, STEP_DEG)) + [hi]
        chain = moving_chain(horn, joints)
        others = [o for o in root.allOccurrences if o.bRepBodies.count and o.fullPathName not in chain]
        worst = None
        for deg in degs:
            motion.rotationValue = math.radians(deg)
            for mover in chain.values():
                for other in others:
                    d = app.measureManager.measureMinimumDistance(mover, other).value * 10
                    pair = [mover.name, other.name]
                    if worst is None or d < worst["min_mm"]:
                        worst = {"min_mm": round(d, 2), "at_deg": deg, "pair": pair}
                    if d < CLEARANCE_MM:
                        report["violations"].append({"horn": horn.name, "deg": deg, "mm": round(d, 2), "pair": pair})
            if deg in (lo, hi):
                report["interference"] += interference(design, root, f"{horn.name} {deg}")
        motion.rotationValue = 0.0
        report["horns"][horn.name] = worst or {"min_mm": None, "at_deg": None, "pair": None, "note": "empty chain"}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{DOC}-report.json"), "w") as f:
        json.dump(report, f, indent=1)
    app.activeViewport.fit(); app.activeViewport.saveAsImageFile(os.path.join(OUT, f"{DOC}.png"), 1200, 900)
    print(json.dumps(report, indent=1))
