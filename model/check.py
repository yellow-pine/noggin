"""Clearance + placement check for one Stage document, run INSIDE Fusion by model/sweep.py (`make model-check`),
one call per horn: HORN = "?" prints the horn joint names; HORN = "<name>" drives that revolute joint from its
min to its max limit in 10-degree steps, measures the minimum distance between each occurrence in its moving
chain and every nearby occurrence (0 mm = overlap, which then gets a pairwise interference volume), compares
the placements in PLACEMENTS with the geometry tables, records top-level bounding boxes at neutral and writes
model/build/<DOC>-<horn>.json. Each call stops at BUDGET_S and marks the horn incomplete. Never saves.
Also (#20): the mass and centre of mass of every part (the library's spool material for printed parts, documented masses for hardware),
the chain's centres of mass and driven joint angles at every pose (model/sim.py turns them into gravity torque and
transmission curves), and the two calibrated servo ends from eyes/calibration.json measured past the designer's limits.
Angles are joint angles relative to the 90-degree neutral the STLs are modelled in. API units: cm."""

# include: model/geometry.py
# include: model/fusion_lib.py
# include: model/sim.py
import json
import math
import os
import time

import adsk.core
import adsk.fusion

HORN = None  # model/sweep.py substitutes this line per call
BUDGET_S = 180

DOC = "noggin-eyes"  # model/sweep.py substitutes this line: `DOC=noggin-mouth make model-check`
PROJECT_NAME = "Noggin"  # the hub's former Default Project; Stage documents sit at its root
REPO = os.path.expanduser("~/code/noggin")
OUT = os.path.join(REPO, "model", "build")
STEP_DEG, CLEARANCE_MM = 10, 0.1  # below 0.1 mm the parts overlap: a collision (designed sliding gaps are ~0.5 mm)
TOL_MM, TOL_INFERRED_MM = 0.5, 3.0
NEAR_MM = 10.0  # pairs whose bounding boxes are further apart than this are not measured (keeps Fusion responsive)
HARDWARE_G = {"servo": 16.0}  # docs/research/2026-10-31-electrical.md; other hardware keeps its STEP material's mass
ACCURACY = adsk.fusion.CalculationAccuracy.LowCalculationAccuracy  # +-1 %


def bodies(occ):
    """Solid bodies of an occurrence and its children in assembly context, without the sweep proxies."""
    out = [b for b in occ.bRepBodies if b.isSolid and b.name != "proxy"]
    for child in occ.childOccurrences:
        out += bodies(child)
    return out


def mass_com(occ):
    """(g, [x, y, z] mm, source) of an occurrence: hardware by its documented mass, else the body material's (the
    parts library gives printed parts their spool's PLA, geometry.PRINTED; STEP parts keep the STEP material).
    Centre of mass is volume-weighted over the bodies (root context)."""
    bs = bodies(occ)
    vol = sum(b.volume for b in bs)
    if not vol:
        return 0.0, [0.0, 0.0, 0.0], "empty"
    com = [sum(getattr(b.physicalProperties.centerOfMass, c) * b.volume for b in bs) / vol * 10 for c in "xyz"]
    kind = next((k for k in HARDWARE_G if occ.component.name.endswith(" " + k)), None)
    if kind:
        return HARDWARE_G[kind], com, "documented"
    return round(sum(b.getPhysicalProperties(ACCURACY).mass for b in bs) * 1000, 2), com, "material"


def targets(occ, real=False):
    """What to measure for an occurrence: its proxy (the real body when `real`), else the occurrence when it holds
    bodies, else its bodies in assembly context (a STEP part's bodies sit in a nested occurrence, and measuring
    the bodiless top occurrence fails)."""
    if proxy_body(occ):
        return [real_body(occ) if real else proxy_body(occ)]
    return [occ] if occ.bRepBodies.count else bodies(occ)


def distance(app, a, b, real=False):
    """Minimum distance between two occurrences in mm (see targets)."""
    return (
        min(app.measureManager.measureMinimumDistance(x, y).value for x in targets(a, real) for y in targets(b, real))
        * 10
    )


def top_parts(root):
    """Top-level occurrences, an inserted Stage (noggin-eyes in the mouth) expanded into its parts so their proxies get measured."""
    out = []
    for o in root.occurrences:
        out += (
            list(o.childOccurrences)
            if o.isReferencedComponent and any(proxy_body(c) for c in o.childOccurrences)
            else [o]
        )
    return out


def bbox_gap(a, b):
    """Distance between two occurrences' bounding boxes in mm (0 when they overlap)."""
    lo_a, hi_a, lo_b, hi_b = (
        mm3(a.boundingBox.minPoint),
        mm3(a.boundingBox.maxPoint),
        mm3(b.boundingBox.minPoint),
        mm3(b.boundingBox.maxPoint),
    )
    return math.sqrt(sum(max(0.0, lo_b[i] - hi_a[i], lo_a[i] - hi_b[i]) ** 2 for i in range(3)))


def open_doc(app):
    if app.activeDocument and app.activeDocument.name.split(" v")[0] == DOC:
        return app.activeDocument
    fld = next(p for p in app.data.activeHub.dataProjects if p.name == PROJECT_NAME).rootFolder
    return app.documents.open(next(f for f in fld.dataFiles if f.name == DOC), True)


def moving_chain(horn, joints, groups=()):
    """Occurrences that move with the horn: Fusion's occurrenceOne is the moving side of a joint; walk the
    other joints and the rigid groups from it, never through grounded occurrences or the horn's fixed side
    (occurrenceTwo)."""
    stop = {horn.occurrenceTwo.fullPathName} if horn.occurrenceTwo else set()
    chain, todo = {}, [horn.occurrenceOne]
    while todo:
        occ = todo.pop()
        if (
            occ is None
            or occ.assemblyContext
            or occ.isGrounded
            or occ.fullPathName in stop
            or occ.fullPathName in chain
        ):
            continue  # nested occurrences (a STEP part's inner assembly, via includeChildren rigid groups) ride with their top-level parent
        chain[occ.fullPathName] = occ
        for g in groups:
            if any(m.fullPathName == occ.fullPathName for m in g):
                todo.extend(g)
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
        for b in bodies(occ):
            coll.add(b)
    results = design.analyzeInterference(design.createInterferenceInput(coll))
    if results is None:
        return [
            {
                "a": occs[0].name,
                "b": occs[1].name,
                "volume_mm3": None,
                "pose": pose,
                "note": "analyzeInterference returned None",
            }
        ]
    return [
        {
            "a": name(r.entityOne),
            "b": name(r.entityTwo),
            "volume_mm3": round(r.interferenceBody.volume * 1000, 3) if r.interferenceBody else None,
            "pose": pose,
        }
        for r in (results.item(i) for i in range(results.count))
    ]


def penetrates(occ_a, occ_b, samples=300):
    """True when sampled vertices of either part's real body lie inside the other's: a collision, as opposed
    to a designed contact (coincident faces measure 0 mm too, e.g. the eyeball bar riding on the bracket rail)."""

    def body(occ):
        x = real_body(occ)
        return x if x.objectType.endswith("BRepBody") else max(bodies(occ), key=lambda b: b.faces.count)

    a, b = body(occ_a), body(occ_b)
    for src, dst in ((a, b), (b, a)):
        verts = src.vertices
        for i in range(0, verts.count, max(1, verts.count // samples)):
            if dst.pointContainment(verts.item(i).geometry) == adsk.fusion.PointContainment.PointInsidePointContainment:
                return True
    return False


def _mean(pts):
    return tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))


# Per document: (component name, STEP-local points mm, expected world points mm, tolerance) for parts placed by
# transform, and (joint name, PIVOTS key) for pivots (expected point must lie on the joint axis, axis parallel).
PLACEMENTS = {
    "noggin-eyes": {
        "parts": [
            (f"{s} {part} servo", SERVO_STEP["tab_holes"], SERVOS[f"{s.lower()}_{part}"]["tab_holes"], TOL_INFERRED_MM)
            for s in "LR"
            for part in ("lid", "eye")
        ]
        + [("PandT base", [(0, 0, 0)], [pt_to_eyes_standalone((0, 0, 0))], TOL_MM)],  # context, by reference
        "pivots": [(f"{s} inside lid pivot", f"{s.lower()}_lid") for s in "LR"]
        + [(f"{s} eyeball pivot", f"{s.lower()}_eye") for s in "LR"]
        + [(f"{s} {part} horn (inferred)", f"{s.lower()}_{part}_horn") for s in "LR" for part in ("lid", "eye")],
    },
    "noggin-pan-tilt": {
        "parts": [
            (f"{key} servo", SERVO_STEP["tab_holes"], SERVOS[key]["tab_holes"], TOL_INFERRED_MM)
            for key in ("tilt", "pan")
        ]
        + [
            (f"receiver shield {n}", [(0, 0, 0)], [_mean(STANDOFFS["pt_base"][f"receiver_{n}"])], TOL_MM)
            for n in (1, 2)
        ]
        + [
            (
                f"switch board {n} (inferred)",
                [SWITCH_STEP["hole"]],
                [STANDOFFS["pt_base"]["switch"][n - 1]],
                TOL_INFERRED_MM,
            )
            for n in (1, 2)
        ],
        "pivots": [
            ("pan pivot", "pan"),
            ("tilt pivot", "tilt"),
            ("tilt horn (inferred)", "tilt_horn"),
            ("pan horn (inferred)", "pan_horn"),
        ],
    },
    "noggin-mouth": {
        "parts": [("jaw servo", SERVO_STEP["tab_holes"], SERVOS["jaw"]["tab_holes"], TOL_INFERRED_MM)],
        "pivots": [("jaw hinge", "jaw_hinge"), ("jaw horn (inferred)", "jaw_horn")],
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
            out.append({"placement": comp, "missing": True})
            continue
        actual = [world(occ, q) for q in local_pts]
        worst = max(min(math.dist(a, e) for a in actual) for e in expected)  # order-insensitive
        if worst > tol:
            out.append(
                {
                    "placement": comp,
                    "mm": round(worst, 2),
                    "tol": tol,
                    "actual": [[round(c, 2) for c in a] for a in actual],
                }
            )
    by_name = {j.name: j for j in joints}
    for jname, key in spec["pivots"]:
        j = by_name.get(jname)
        if j is None:
            out.append({"placement": jname, "missing": True})
            continue
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
    joints = [
        j for j in root.joints if not j.isSuppressed
    ]  # the document's own: a referenced Stage's horns are swept in its own document
    horns = [
        j
        for j in joints
        if j.jointMotion.jointType == adsk.fusion.JointTypes.RevoluteJointType and "horn" in j.name.lower()
    ]
    if not horns:
        raise RuntimeError(f"{DOC}: no revolute joint named '... horn'")
    if HORN == "?":
        print(json.dumps([h.name for h in horns]))
        return
    horn = next(h for h in horns if h.name == HORN)
    contact_was = (
        design.isContactAnalysisEnabled
    )  # the Stage's contact set would stop the drive at the designed contacts
    design.isContactAnalysisEnabled = False
    for h in horns:  # neutral pose first
        h.jointMotion.rotationValue = 0.0
    report = {
        "doc": DOC,
        "version": doc.dataFile.versionNumber if doc.dataFile else None,
        "clearance_mm": CLEARANCE_MM,
        "step_deg": STEP_DEG,
        "horns": {},
        "interference": [],
        "contacts": [],
        "bboxes": {o.name: [mm3(o.boundingBox.minPoint), mm3(o.boundingBox.maxPoint)] for o in root.occurrences},
        "violations": placements(root, joints),
    }
    motion = horn.jointMotion
    lim = motion.rotationLimits
    lo, hi = round(math.degrees(lim.minimumValue)), round(math.degrees(lim.maximumValue))
    degs = list(range(lo, hi, STEP_DEG)) + [hi]
    groups = [[g.occurrences.item(i) for i in range(g.occurrences.count)] for g in root.rigidGroups]
    chain = moving_chain(horn, joints, groups)
    others = [o for o in top_parts(root) if o.fullPathName not in chain and (proxy_body(o) or bodies(o))]
    linked = set()  # pairs that touch by construction: they share a joint or a rigid group
    for j in joints:
        if j.occurrenceOne and j.occurrenceTwo:
            linked.add(frozenset((j.occurrenceOne.fullPathName, j.occurrenceTwo.fullPathName)))
    for g in root.rigidGroups:
        names = [g.occurrences.item(i).fullPathName for i in range(g.occurrences.count)]
        linked.update(frozenset((a, b)) for a in names for b in names if a != b)
    driven = [
        j
        for j in joints
        if j is not horn
        and j.jointMotion.jointType == adsk.fusion.JointTypes.RevoluteJointType
        and "pivot" in j.name
        and any(e is not None and e.fullPathName in chain for e in (j.occurrenceOne, j.occurrenceTwo))
    ]
    parts = {o.name: mass_com(o) for o in root.occurrences if o.bRepBodies.count or o.childOccurrences.count}
    report["mass"] = {n: m[0] for n, m in parts.items()}
    report["mass_source"] = {n: m[2] for n, m in parts.items()}
    total = sum(m[0] for m in parts.values())
    report["stage"] = {
        "total_g": round(total, 1),
        "com": [round(sum(m[0] * m[1][i] for m in parts.values()) / total, 1) for i in range(3)],
    }
    state = {"worst": None, "measured": 0}
    poses = {}
    neutral_inv, axes = (
        {},
        {},
    )  # driven pivots keep rotationValue 0 when another joint drives: read the angle off transform2
    for j in driven:
        m = j.occurrenceOne.transform2.copy()
        m.invert()
        neutral_inv[j.name] = m
        axes[j.name] = j.geometryOrOriginOne.primaryAxisVector.asArray()  # world axis of the joint origin at neutral

    def driven_deg(j):
        m = matmul(
            j.occurrenceOne.transform2, neutral_inv[j.name]
        )  # rotation about the pivot axis k: signed angle from the axial part of R - R^T
        k = axes[j.name]
        s = (
            (m.getCell(2, 1) - m.getCell(1, 2)) * k[0]
            + (m.getCell(0, 2) - m.getCell(2, 0)) * k[1]
            + (m.getCell(1, 0) - m.getCell(0, 1)) * k[2]
        )
        c = m.getCell(0, 0) + m.getCell(1, 1) + m.getCell(2, 2) - 1
        return round(math.degrees(math.atan2(s, c)), 2)

    def measure(deg, calibrated=False):
        motion.rotationValue = math.radians(deg)
        poses[deg] = {
            "com": {m.name: [round(c, 2) for c in mass_com(m)[1]] for m in chain.values()},
            "joints": {j.name: driven_deg(j) for j in driven},
        }
        for mover in chain.values():
            for other in others:
                if frozenset((mover.fullPathName, other.fullPathName)) in linked or bbox_gap(mover, other) > NEAR_MM:
                    continue  # exact distance is at least the box gap: skip far pairs
                d = distance(app, mover, other)
                state["measured"] += 1
                adsk.doEvents()  # let the UI repaint and take input between measurements
                if d < CLEARANCE_MM and (
                    proxy_body(mover) or proxy_body(other)
                ):  # decimation can close slots: confirm on the real bodies
                    d = distance(app, mover, other, real=True)
                    state["measured"] += 1
                pair = [mover.name, other.name]
                if not calibrated and (state["worst"] is None or d < state["worst"]["min_mm"]):
                    state["worst"] = {"min_mm": round(d, 2), "at_deg": deg, "pair": pair}
                if d < CLEARANCE_MM:
                    hit = {"horn": horn.name, "deg": deg, "pair": pair}
                    if calibrated:
                        hit["calibrated"] = True
                    if penetrates(mover, other):
                        report["violations"].append({**hit, "mm": round(d, 2)})
                        if not calibrated:
                            report["interference"] += interference(design, [mover, other], f"{horn.name} {deg}")
                    else:
                        report["contacts"].append(hit)

    incomplete = None
    for deg in degs:
        if time.time() - t0 > BUDGET_S:
            incomplete = f"budget of {BUDGET_S} s spent at {deg} deg after {state['measured']} measurements"
            break
        measure(deg)
    # The calibrated servo ends (eyes/calibration.json, eyes Stage only) lie outside the designer's limits: measure
    # them with the limits off, then put the limits back (nothing is saved).
    key = horn.name[0].lower() + ("_lid" if "lid" in horn.name else "_eye")
    ends = calibrated_extremes(json.load(open(os.path.join(REPO, "eyes", "calibration.json")))).get(key)
    lim.isMinimumValueEnabled = lim.isMaximumValueEnabled = False
    for deg in ends or ():
        if deg not in poses and not incomplete:
            measure(deg, calibrated=True)
    lim.isMinimumValueEnabled = lim.isMaximumValueEnabled = True
    motion.rotationValue = 0.0
    design.isContactAnalysisEnabled = contact_was
    worst, measured = state["worst"], state["measured"]
    report["horns"][horn.name] = worst or {
        "min_mm": NEAR_MM,
        "at_deg": None,
        "pair": None,
        "note": f"nothing within {NEAR_MM} mm",
    }
    report["horns"][horn.name]["poses"] = {d: p for d, p in poses.items() if lo <= d <= hi}
    if ends:
        report["calibrated"] = {horn.name: {"lo": ends[0], "hi": ends[1]}}
    if incomplete:
        report["horns"][horn.name]["incomplete"] = incomplete
    report["horns"][horn.name]["measurements"] = measured
    report["horns"][horn.name]["seconds"] = round(time.time() - t0, 1)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{DOC}-{horn.name.replace('/', '_')}.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(
        f"{horn.name}: {measured} measurements in {report['horns'][horn.name]['seconds']} s, "
        f"min {report['horns'][horn.name]['min_mm']} mm, {len(report['violations'])} violations"
        + (f", INCOMPLETE: {incomplete}" if incomplete else "")
    )
