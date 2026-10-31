"""Clearance + placement check for one Stage document, run INSIDE Fusion by twin/sweep.py (`make twin-check`),
one call per horn: HORN = "?" prints the horn joint names; HORN = "<name>" drives that revolute joint from its
min to its max limit in 10-degree steps, measures the minimum distance between each occurrence in its moving
chain and every nearby occurrence (0 mm = overlap, which then gets a pairwise interference volume), compares
the placements in PLACEMENTS with the geometry tables, records top-level bounding boxes at neutral and writes
twin/build/<DOC>-<horn>.json. Each call stops at BUDGET_S and marks the horn incomplete. Never saves.
Angles are joint angles relative to the 90-degree neutral the STLs are modelled in. API units: cm."""
# include: twin/geometry.py
# include: twin/fusion_lib.py
import adsk.core, adsk.fusion, json, math, os, time

HORN = None                           # twin/sweep.py substitutes this line per call
BUDGET_S = 180

DOC = "noggin-eyes"                   # the coordinator edits this per Stage: noggin-eyes, noggin-pan-tilt, noggin-mouth
PROJECT_NAME = "Noggin"               # the hub's former Default Project; Stage documents sit at its root
REPO = os.path.expanduser("~/code/noggin")
OUT = os.path.join(REPO, "twin", "build")
STEP_DEG, CLEARANCE_MM = 10, 0.1   # below 0.1 mm the parts overlap: a collision (designed sliding gaps are ~0.5 mm)
TOL_MM, TOL_INFERRED_MM = 0.5, 3.0
NEAR_MM = 10.0   # pairs whose bounding boxes are further apart than this are not measured (keeps Fusion responsive)


def bbox_gap(a, b):
    """Distance between two occurrences' bounding boxes in mm (0 when they overlap)."""
    lo_a, hi_a, lo_b, hi_b = mm3(a.boundingBox.minPoint), mm3(a.boundingBox.maxPoint), mm3(b.boundingBox.minPoint), mm3(b.boundingBox.maxPoint)
    return math.sqrt(sum(max(0.0, lo_b[i] - hi_a[i], lo_a[i] - hi_b[i]) ** 2 for i in range(3)))


def open_doc(app):
    if app.activeDocument and app.activeDocument.name.split(" v")[0] == DOC:
        return app.activeDocument
    fld = next(p for p in app.data.activeHub.dataProjects if p.name == PROJECT_NAME).rootFolder
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


def interference(design, occs, pose):
    """Interference volumes between the bodies of the given occurrences (Fusion gives up on whole-design sets of
    large faceted bodies, so this is only called for pairs that measured 0 mm)."""
    coll = adsk.core.ObjectCollection.create()
    for occ in occs:
        for b in occ.bRepBodies:
            if b.isSolid:
                coll.add(b)
    results = design.analyzeInterference(design.createInterferenceInput(coll))
    if results is None:
        return [{"a": occs[0].name, "b": occs[1].name, "volume_mm3": None, "pose": pose, "note": "analyzeInterference returned None"}]
    return [{"a": name(r.entityOne), "b": name(r.entityTwo),
             "volume_mm3": round(r.interferenceBody.volume * 1000, 3) if r.interferenceBody else None, "pose": pose}
            for r in (results.item(i) for i in range(results.count))]


def _mean(pts):
    return tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))


# Per document: (component name, STEP-local points mm, expected world points mm, tolerance) for parts placed by
# transform, and (joint name, PIVOTS key) for pivots (expected point must lie on the joint axis, axis parallel).
PLACEMENTS = {
    "noggin-eyes": {
        "parts": [(f"{s} {part} servo", SERVO_STEP["tab_holes"], SERVOS[f"{s.lower()}_{part}"]["tab_holes"], TOL_INFERRED_MM)
                  for s in "LR" for part in ("lid", "eye")]
                 + [("receiver shield", [(0, 0, 0)], [_mean([pt_to_eyes_standalone(p) for p in STANDOFFS["pt_base"]["receiver_1"]])], TOL_MM),
                    ("switch board", [SWITCH_STEP["hole"]], [pt_to_eyes_standalone(STANDOFFS["pt_base"]["switch_post"][0])], TOL_INFERRED_MM)],
        "pivots": [(f"{s} inside lid pivot", f"{s.lower()}_lid") for s in "LR"]
                  + [(f"{s} eyeball pivot", f"{s.lower()}_eye") for s in "LR"]
                  + [(f"{s} {part} horn (inferred)", f"{s.lower()}_{part}_horn") for s in "LR" for part in ("lid", "eye")],
    },
}


def world(occ, local_mm):
    p = adsk.core.Point3D.create(*[c / 10 for c in local_mm])
    p.transformBy(occ.transform2)
    return (p.x * 10, p.y * 10, p.z * 10)


def placements(root, joints):
    """Violations for parts and pivots that are not where the geometry tables say."""
    out = []
    spec = PLACEMENTS.get(DOC, {"parts": [], "pivots": []})
    by_comp = {o.component.name: o for o in root.occurrences}
    for comp, local_pts, expected, tol in spec["parts"]:
        occ = by_comp.get(comp)
        if occ is None:
            out.append({"placement": comp, "missing": True}); continue
        actual = [world(occ, q) for q in local_pts]
        worst = max(min(math.dist(a, e) for a in actual) for e in expected)   # order-insensitive
        if worst > tol:
            out.append({"placement": comp, "mm": round(worst, 2), "tol": tol, "actual": [[round(c, 2) for c in a] for a in actual]})
    by_name = {j.name: j for j in joints}
    for jname, key in spec["pivots"]:
        j = by_name.get(jname)
        if j is None:
            out.append({"placement": jname, "missing": True}); continue
        pivot = PIVOTS[key]
        tol = TOL_INFERRED_MM if pivot.get("inferred") else TOL_MM
        origin, axis = world_frame(j.geometryOrOriginOne)
        d = [e - o for e, o in zip(pivot["point"], origin)]
        along = sum(a * b for a, b in zip(d, axis))
        off = math.sqrt(max(0.0, sum(c * c for c in d) - along * along))
        # shortcut: only the point is checked; the axis comes back in sketch space, and joint_origin() sets it by construction
        if off > tol:
            out.append({"placement": jname, "mm": round(off, 2), "tol": tol})
    return out


def run(_context: str):
    """Entry point for the Fusion MCP `script` tool (no exception handling by design: errors must surface)."""
    t0 = time.time()
    app = adsk.core.Application.get()
    doc = open_doc(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    joints = [j for j in root.allJoints if not j.isSuppressed]
    horns = [j for j in joints if j.jointMotion.jointType == adsk.fusion.JointTypes.RevoluteJointType
             and "horn" in j.name.lower()]
    if not horns:
        raise RuntimeError(f"{DOC}: no revolute joint named '... horn'")
    if HORN == "?":
        print(json.dumps([h.name for h in horns])); return
    horn = next(h for h in horns if h.name == HORN)
    for h in horns:                                     # neutral pose first
        h.jointMotion.rotationValue = 0.0
    report = {"doc": DOC, "version": doc.dataFile.versionNumber if doc.dataFile else None,
              "clearance_mm": CLEARANCE_MM, "step_deg": STEP_DEG, "horns": {}, "interference": [],
              "bboxes": {o.name: [mm3(o.boundingBox.minPoint), mm3(o.boundingBox.maxPoint)] for o in root.occurrences},
              "violations": placements(root, joints)}
    motion = horn.jointMotion
    lim = motion.rotationLimits
    lo, hi = round(math.degrees(lim.minimumValue)), round(math.degrees(lim.maximumValue))
    degs = list(range(lo, hi, STEP_DEG)) + [hi]
    chain = moving_chain(horn, joints)
    others = [o for o in root.allOccurrences if o.bRepBodies.count and o.fullPathName not in chain]
    linked = set()   # pairs that touch by construction: they share a joint or a rigid group
    for j in joints:
        if j.occurrenceOne and j.occurrenceTwo:
            linked.add(frozenset((j.occurrenceOne.fullPathName, j.occurrenceTwo.fullPathName)))
    for g in root.rigidGroups:
        names = [g.occurrences.item(i).fullPathName for i in range(g.occurrences.count)]
        linked.update(frozenset((a, b)) for a in names for b in names if a != b)
    worst, incomplete, measured = None, None, 0
    for deg in degs:
        if time.time() - t0 > BUDGET_S:
            incomplete = f"budget of {BUDGET_S} s spent at {deg} deg after {measured} measurements"; break
        motion.rotationValue = math.radians(deg)
        for mover in chain.values():
            for other in others:
                if frozenset((mover.fullPathName, other.fullPathName)) in linked or bbox_gap(mover, other) > NEAR_MM:
                    continue   # exact distance is at least the box gap: skip far pairs
                d = app.measureManager.measureMinimumDistance(proxy_body(mover) or mover, proxy_body(other) or other).value * 10
                measured += 1
                adsk.doEvents()   # let the UI repaint and take input between measurements
                if d < CLEARANCE_MM and (proxy_body(mover) or proxy_body(other)):   # decimation can close slots: confirm on the real bodies
                    d = app.measureManager.measureMinimumDistance(real_body(mover), real_body(other)).value * 10
                    measured += 1
                pair = [mover.name, other.name]
                if worst is None or d < worst["min_mm"]:
                    worst = {"min_mm": round(d, 2), "at_deg": deg, "pair": pair}
                if d < CLEARANCE_MM:
                    report["violations"].append({"horn": horn.name, "deg": deg, "mm": round(d, 2), "pair": pair})
                if d == 0:
                    report["interference"] += interference(design, [mover, other], f"{horn.name} {deg}")
    motion.rotationValue = 0.0
    report["horns"][horn.name] = worst or {"min_mm": NEAR_MM, "at_deg": None, "pair": None, "note": f"nothing within {NEAR_MM} mm"}
    if incomplete:
        report["horns"][horn.name]["incomplete"] = incomplete
    report["horns"][horn.name]["measurements"] = measured
    report["horns"][horn.name]["seconds"] = round(time.time() - t0, 1)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{DOC}-{horn.name.replace('/', '_')}.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(f"{horn.name}: {measured} measurements in {report['horns'][horn.name]['seconds']} s, "
          f"min {report['horns'][horn.name]['min_mm']} mm, {len(report['violations'])} violations"
          + (f", INCOMPLETE: {incomplete}" if incomplete else ""))
