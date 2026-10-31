"""Fusion helpers shared by the Stage scripts, inlined via `# include: model/fusion_lib.py` after
`# include: model/geometry.py`. Points and lengths come in as mm; Fusion's API takes cm and radians.
Verified calls: docs/research/2026-10-31-model.md."""
import adsk.core, adsk.fusion, hashlib, json, math, os, time, traceback

PROJECT_NAME = "Noggin"   # the hub's former Default Project, renamed; Stage documents sit at its root
_PLANE_FOR_AXIS = {"X": "yZConstructionPlane", "Y": "xZConstructionPlane", "Z": "xYConstructionPlane"}


def point(p):
    return adsk.core.Point3D.create(p[0] / 10, p[1] / 10, p[2] / 10)


def vector(v):
    return adsk.core.Vector3D.create(v[0], v[1], v[2])


# Rebuild bookkeeping, as attributes (STEP metadata overwrites a component's description on reopen): the
# timeline index after the last import, each component's part name and fingerprint, the last build summary.
PARTS_END_ATTR, SUMMARY_ATTR = ("noggin", "parts_end"), ("noggin", "summary")
PART_ATTR, FINGERPRINT_ATTR = ("noggin", "part"), ("noggin", "fingerprint")
FRESH = []   # names imported by the current build (reset by open_or_create; Fusion keeps globals between calls)


def open_or_create(app, name, keep_parts=False):
    """Open the design `name` in project Noggin (or a new one), parametric. Emptied of occurrences unless
    keep_parts: then the timeline is cut where the last build's parts_end() put it, so only the cheap features
    every build recreates (Ports, pivots, joints, rigid groups, canvases) go and the occurrences stay for
    insert_part to reuse.
    Returns (document, design, folder); pass the folder to save()."""
    folder = project_root(app)
    existing = next((f for f in folder.dataFiles if f.name == name), None)
    doc = app.documents.open(existing, True) if existing else app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType   # mesh convert only works here
    root = design.rootComponent
    FRESH.clear()
    timeline = design.timeline
    recorded = root.attributes.itemByName(*PARTS_END_ATTR)
    keep_parts = keep_parts and recorded is not None   # a document from before T9 is rebuilt in full
    cut = int(recorded.value) if keep_parts else 0
    if cut < timeline.count:           # one rollback + delete: per-feature deletes recompute the timeline each time
        timeline.markerPosition = cut
        timeline.deleteAllAfterMarker()
    if keep_parts:
        return doc, design, folder
    for occ in list(root.occurrences):
        occ.deleteMe()
    return doc, design, folder


def project_root(app):
    projects = app.data.activeHub.dataProjects
    project = next((p for p in projects if p.name == PROJECT_NAME), None) or projects.add(PROJECT_NAME)   # new hub/account
    return project.rootFolder


def parts_folder(app):
    """The `parts` folder of project Noggin (created when missing): one design per library part (model/parts.py)."""
    root = project_root(app)
    return next((f for f in root.dataFolders if f.name == "parts"), None) or root.dataFolders.add("parts")


def stored_fingerprint(app, data_file):
    """The FINGERPRINT_ATTR a library part's root carries, read from the saved design without showing it."""
    for attempt in range(3):   # right after a save the cloud copy can refuse the open ("Missing key for PIMOpenWorkflowTracker")
        try:
            doc = app.documents.open(data_file, False)
            break
        except RuntimeError:
            if attempt == 2:
                raise
            time.sleep(2)
    try:
        root = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType")).rootComponent
        a = root.attributes.itemByName(*FINGERPRINT_ATTR)
        return a.value if a else None
    finally:
        doc.close(False)


def parts_end(design):
    """Builds call this after their last import (and stale-part deletion): the next keep_parts build cuts here."""
    design.rootComponent.attributes.add(*PARTS_END_ATTR, str(design.timeline.count))


def fingerprint(paths, cells, key=""):
    """What a placed part depends on: sha256 of its source files (or `key`: the library part and its version) and
    the placement matrix (16 cells, rounded so float noise is not a change). Stored on the component
    (FINGERPRINT_ATTR); a match on rebuild keeps the occurrence."""
    h = hashlib.sha256(key.encode())
    for p in paths:
        h.update(open(p, "rb").read())
    h.update(json.dumps([float(round(c, 4)) for c in cells]).encode())
    return h.hexdigest()[:16]


def kept_parts(root):
    """Occurrences a previous build placed, by part name (open_or_create keep_parts leaves them in place).
    An untagged occurrence (hand-added, or from before T13) goes by its component name and is never reused."""
    parts = {}
    for o in root.occurrences:
        a = o.attributes.itemByName(*PART_ATTR)
        parts[a.value if a else o.component.name] = o
    return parts


def tag(occ, name, fp):
    """Name and fingerprint on the occurrence (a referenced component is shared and cannot be renamed)."""
    if occ.component.name != name:
        occ.component.name = name
    occ.attributes.add(*PART_ATTR, name)
    occ.attributes.add(*FINGERPRINT_ATTR, fp)


def reusable(reuse, name, paths, matrix, key=""):
    """The kept occurrence `name` when its fingerprint matches, else None (a stale one is deleted and the name
    goes on FRESH). Pops from `reuse`, so it ends up holding only the parts the build no longer places."""
    fp = fingerprint(paths, (matrix or adsk.core.Matrix3D.create()).asArray(), key)
    occ = reuse.pop(name, None) if reuse is not None else None
    if occ is not None:
        stored = occ.attributes.itemByName(*FINGERPRINT_ATTR)
        if stored and stored.value == fp:
            return occ, fp
        if not occ.isReferencedComponent:
            occ.component.name = name + " (stale)"   # else the re-insert is named "<name> (1)" until the component is gone
        occ.deleteMe()
    FRESH.append(name)
    return None, fp


def changes(old, new):
    """Human-readable differences between two build summaries ({section: {name: value}}); [] when equal."""
    if old is None:
        return ["no previous summary"]
    out = []
    for section in sorted(set(old) | set(new)):
        a, b = old.get(section, {}), new.get(section, {})
        for name in sorted(set(a) | set(b)):
            if name not in a:
                out.append(f"{section} {name}: added")
            elif name not in b:
                out.append(f"{section} {name}: removed")
            elif a[name] != b[name]:
                out.append(f"{section} {name}: {a[name]} -> {b[name]}")
    return out


def summary(root):
    """What the cheap, recreated features amount to: joints (limits, origin frames), ports (world points).
    Compared across builds to decide whether a new version is worth saving."""
    joints = {}
    for j in root.joints:
        lim = j.jointMotion.rotationLimits if j.jointMotion.jointType == adsk.fusion.JointTypes.RevoluteJointType else None
        joints[j.name] = {"limits": [round(math.degrees(lim.minimumValue), 2), round(math.degrees(lim.maximumValue), 2)] if lim and lim.isMinimumValueEnabled else None,
                          "origins": [origin_frame(o) for o in (j.geometryOrOriginOne, j.geometryOrOriginTwo)],
                          "parts": [o.name if o else None for o in (j.occurrenceOne, j.occurrenceTwo)]}
    ports = {}
    for o in root.occurrences:
        for sk in o.component.sketches:
            if sk.name.startswith("Port:"):
                p = sk.sketchPoints.item(sk.sketchPoints.count - 1).worldGeometry.copy(); p.transformBy(o.transform2)
                ports[sk.name[6:]] = [round(p.x * 10, 2), round(p.y * 10, 2), round(p.z * 10, 2)]
    return json.loads(json.dumps({"joints": joints, "ports": ports}))   # as it comes back from the attribute


def saved_summary(root):
    a = root.attributes.itemByName(*SUMMARY_ATTR)
    return json.loads(a.value) if a else None


def save(doc, message, name, folder):
    """Save a new version (saveAs on first save). Returns the version number."""
    if doc.dataFile:
        doc.save(message)
    else:
        doc.saveAs(name, folder, message, "")
    return doc.dataFile.versionNumber


def align(to_origin, to_x=None, to_z=None, from_origin=(0, 0, 0), from_x=(1, 0, 0), from_z=(0, 0, 1)):
    """Matrix3D taking the local frame (from_*) onto the world frame (to_*), mm. Axes default to identity."""
    def frame(origin, x, z):
        x, z = vector(x), vector(z)
        z.normalize()
        tilt = z.copy(); tilt.scaleBy(x.dotProduct(z)); x.subtract(tilt)   # x in the plane normal to z (stepped links)
        x.normalize()
        y = z.crossProduct(x)
        return point(origin), x, y, z
    m = adsk.core.Matrix3D.create()
    m.setToAlignCoordinateSystems(*frame(from_origin, from_x, from_z), *frame(to_origin, to_x or (1, 0, 0), to_z or (0, 0, 1)))
    return m


def matmul(a, b):
    """a x b as a new Matrix3D (explicit, since Matrix3D.transformBy's order is easy to get wrong)."""
    m = adsk.core.Matrix3D.create()
    for r in range(4):
        for c in range(4):
            m.setCell(r, c, sum(a.getCell(r, k) * b.getCell(k, c) for k in range(4)))
    return m


_PARTS = {}   # library DataFiles by name; refilled when a name is missing (Fusion keeps globals between calls)


def part_file(app, name):
    """The library design `name` (model/parts.py) or a Stage design at the project root, once the cloud has
    finished processing its last save."""
    if name not in _PARTS:
        _PARTS.clear()
        _PARTS.update({f.name: f for f in parts_folder(app).dataFiles})
        _PARTS.update({f.name: f for f in project_root(app).dataFiles})
    if name not in _PARTS:
        raise KeyError(f"{name}: not in the parts library (make model-parts)")
    df = _PARTS[name]
    while not df.isComplete:
        time.sleep(1)
        adsk.doEvents()
    return df


def insert_part(root, name, label, matrix=None, reuse=None, referenced=False):
    """Library part `name` inserted at `matrix` as component `label`: the stored solid loads without a mesh convert.
    A copy (default) can be renamed and carries the joint-origin sketches of its Pivots; a reference loads about
    twice as fast (measured 2026-10-31) but keeps the library name and would put those sketches into the shared
    library component, so `referenced` is for grounded context without joints. `reuse`: kept occurrences by part
    name; a fingerprint (library version + matrix) match returns the kept one. Returns the occurrence."""
    app = adsk.core.Application.get()
    df = part_file(app, name)
    kept, fp = reusable(reuse, label, [], matrix, f"{name}@v{df.versionNumber}")
    if kept:
        return kept
    adsk.doEvents()   # keep the UI responsive during long builds
    occ = root.occurrences.addByInsert(df, matrix or adsk.core.Matrix3D.create(), referenced)
    tag(occ, label, fp)
    return occ


def proxy_body(occ):
    """The occurrence's hidden "proxy" body in assembly context, or None."""
    body = occ.component.bRepBodies.itemByName("proxy")
    return body.createForAssemblyContext(occ) if body else None


def real_body(occ):
    """The occurrence's full-resolution body in assembly context when it carries a proxy (an occurrence-level
    measurement would include the proxy), else the occurrence itself."""
    if not occ.component.bRepBodies.itemByName("proxy"):
        return occ
    body = next(b for b in occ.component.bRepBodies if b.name != "proxy")
    return body.createForAssemblyContext(occ)


def world_frame(origin):
    """World (pivot point mm, Z axis) of a joint origin built by joint_origin(): the sketch point plus the
    offset along the (possibly flipped) plane normal, carried through the occurrence."""
    native = origin.nativeObject or origin
    g = native.geometry
    p, z = g.origin.copy(), g.primaryAxisVector.copy()
    if native.isFlipped:
        z.scaleBy(-1)
    step = z.copy(); step.scaleBy(native.offsetZ.value)
    p.translateBy(step)
    if origin.assemblyContext:
        p.transformBy(origin.assemblyContext.transform2); z.transformBy(origin.assemblyContext.transform2)
    return (p.x * 10, p.y * 10, p.z * 10), (z.x, z.y, z.z)   # axis: sketch space, see check.placements


def local(occ, point_mm, axis):
    """World point (mm) and axis as the occurrence's component sees them; axis as a Fusion unit vector."""
    inverse = occ.transform2.copy()
    inverse.invert()
    p, a = point(point_mm), vector(axis)
    p.transformBy(inverse); a.transformBy(inverse)
    return p, a


_NEXT = {"X": "Y", "Y": "Z", "Z": "X"}
_UNIT = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}


def _local_axis(occ, axis):
    """(name, sign) of the component axis that the world axis maps onto."""
    _, a = local(occ, (0, 0, 0), _UNIT[axis])
    comps = {"X": a.x, "Y": a.y, "Z": a.z}
    name = max(comps, key=lambda k: abs(comps[k]))
    if abs(comps[name]) < 0.999:
        raise ValueError(f"{occ.name}: world {axis} is not along a component axis")
    return name, (1 if comps[name] > 0 else -1)


def sketch_point(occ, point_mm, axis="Z", name=None):
    """Named sketch on the component plane normal to the world `axis`, holding one point at the world position.
    Returns (sketch, sketch point)."""
    p, _ = local(occ, point_mm, _UNIT[axis])
    plane_axis, _ = _local_axis(occ, axis)
    sketch = occ.component.sketches.add(getattr(occ.component, _PLANE_FOR_AXIS[plane_axis]))
    if name:
        sketch.name = name
    return sketch, sketch.sketchPoints.add(sketch.modelToSketchSpace(p))


def joint_origin(occ, point_mm, axis):
    """Joint origin on `occ` at the world point, Z along the world axis ("X", "Y" or "Z") and X along the next
    world axis, in assembly context. Fusion aligns both frames when it adds a joint, so two origins built this
    way at the same point leave the parts where they are."""
    plane_axis, sign = _local_axis(occ, axis)
    p, _ = local(occ, point_mm, _UNIT[axis])
    _, ref = local(occ, (0, 0, 0), _UNIT[_NEXT[axis]])
    height = getattr(p, plane_axis.lower())
    setattr(p, plane_axis.lower(), 0.0)          # in-plane point; the out-of-plane part goes in offsetZ
    sketch = occ.component.sketches.add(getattr(occ.component, _PLANE_FOR_AXIS[plane_axis]))
    start = sketch.sketchPoints.add(sketch.modelToSketchSpace(p))
    q = p.copy(); q.translateBy(ref)
    line = sketch.sketchCurves.sketchLines.addByTwoPoints(start, sketch.modelToSketchSpace(q))
    inp = occ.component.jointOrigins.createInput(adsk.fusion.JointGeometry.createByPoint(start))
    inp.xAxisEntity = line
    inp.isFlipped = sign < 0                     # Z along the world axis; offsetZ then runs along the flipped Z
    inp.offsetZ = adsk.core.ValueInput.createByReal(height * sign)
    origin = occ.component.jointOrigins.add(inp)
    return origin.createForAssemblyContext(occ)


def origin_frame(origin):
    """World (origin mm, Z, X) of a joint origin proxy, for checks."""
    t = origin.transform
    o = t.translation
    return (round(o.x * 10, 2), round(o.y * 10, 2), round(o.z * 10, 2)), tuple(round(c, 2) for c in origin.primaryAxisVector.asArray()), tuple(round(c, 2) for c in origin.secondaryAxisVector.asArray())


def _joint(root, origin_a, origin_b, name, motion):
    adsk.doEvents()
    inp = root.joints.createInput(origin_a, origin_b)
    getattr(inp, motion)(adsk.fusion.JointDirections.ZAxisJointDirection)
    joint = root.joints.add(inp)
    joint.name = name
    return joint


def revolute(root, origin_a, origin_b, name, limits_deg=None):
    """Revolute joint; origin_a's occurrence is the moving side. limits_deg are relative to neutral."""
    joint = _joint(root, origin_a, origin_b, name, "setAsRevoluteJointMotion")
    if limits_deg:
        limits = joint.jointMotion.rotationLimits
        limits.isMinimumValueEnabled = limits.isMaximumValueEnabled = True
        limits.minimumValue, limits.maximumValue = math.radians(limits_deg[0]), math.radians(limits_deg[1])
    return joint


def cylindrical(root, origin_a, origin_b, name):
    return _joint(root, origin_a, origin_b, name, "setAsCylindricalJointMotion")


def rigid(root, occ_a, occ_b, name):
    """As-built rigid joint: no geometry, the parts stay where they were placed, so nothing is added to a referenced
    component (joint_origin would write its sketch into the shared design). Lives in root.asBuiltJoints, not root.joints."""
    adsk.doEvents()
    inp = root.asBuiltJoints.createInput(occ_a, occ_b, None)
    inp.setAsRigidJointMotion()
    joint = root.asBuiltJoints.add(inp)
    joint.name = name
    return joint


# Chunked builds: one part insert (or joint group) per custom event. Custom events are only dispatched while the
# script pumps adsk.doEvents() (measured 2026-10-31: nothing fires once the MCP call has returned), so chunked()
# fires the first chunk, each chunk fires the next, and the call returns after the last one; between chunks Fusion
# repaints and takes input. Progress: Text Commands palette (app.log) and the returned lines.
EVENT_ID = "noggin-build"
STALL_S = 600
_JOB = {}


def chunked(steps):
    """Run the (label, fn) steps one per custom event; returns the progress lines, raises on the first failing chunk."""
    class Chunk(adsk.core.CustomEventHandler):   # defined here: the Mac tests stub adsk
        def notify(self, args):
            app = adsk.core.Application.get()
            ui = app.userInterface
            if ui.activeCommand != "SelectCommand":   # a chunk adds undo steps: end whatever command the user is in
                ui.commandDefinitions.itemById("SelectCommand").execute()
            label, fn = _JOB["steps"][_JOB["i"]]
            t = time.time()
            try:
                fn()
            except Exception:
                _JOB["error"] = f"chunk {label}: " + traceback.format_exc()
                return
            _JOB["i"] += 1
            _JOB["at"] = time.time()
            line = f"[{_JOB['i']}/{len(_JOB['steps'])}] {label}: {time.time() - t:.1f} s"
            _JOB["lines"].append(line)
            app.log("noggin " + line)
            if _JOB["i"] < len(_JOB["steps"]):
                app.fireCustomEvent(EVENT_ID, "")
    app = adsk.core.Application.get()
    app.unregisterCustomEvent(EVENT_ID)
    event = app.registerCustomEvent(EVENT_ID)
    handler = Chunk()
    event.add(handler)
    _JOB.clear()
    _JOB.update(steps=steps, i=0, lines=[], error=None, at=time.time(), event=event, handler=handler)   # kept alive here
    app.fireCustomEvent(EVENT_ID, "")
    while _JOB["i"] < len(steps) and not _JOB["error"]:
        adsk.doEvents()
        time.sleep(0.02)
        if time.time() - _JOB["at"] > STALL_S:
            _JOB["error"] = f"no chunk finished in {STALL_S} s (after {_JOB['i']}/{len(steps)})"
    app.unregisterCustomEvent(EVENT_ID)
    if _JOB["error"]:
        raise RuntimeError(_JOB["error"])
    return _JOB["lines"]


# Shared by the sub-assembly builds (eyes.py, stack.py): linkage placement, pivots and loop closure, the battery lead.
def add(a, b):
    return tuple(p + q for p, q in zip(a, b))


def mean(points):
    return tuple(sum(c) / len(points) for c in zip(*points))


def side(s, p):
    return p if s == "L" else mirror_x(p)


def pivot_joint(root, occ_a, occ_b, point_mm, axis, name, limits=None):
    return revolute(root, joint_origin(occ_a, point_mm, axis), joint_origin(occ_b, point_mm, axis), name, limits)


def close_loop(root, occ_a, occ_b, point_mm, axis, name):
    """Last pivot of a four-bar: revolute if Fusion accepts it, else cylindrical (one freed DOF, named)."""
    a, b = joint_origin(occ_a, point_mm, axis), joint_origin(occ_b, point_mm, axis)
    try:
        joint = revolute(root, a, b, name)
    except Exception:            # over-constrained loop: the fallback agreed in #11
        joint = None
    if joint is not None and joint.healthState == adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        return joint
    if joint is not None:
        joint.deleteMe()
    return cylindrical(root, a, b, name + " (cylindrical: loop)")


def link(root, name, stl_key, hole_a, hole_b, normal, reuse):
    """Place the local-frame link part `stl_key` (STL_LOCAL) so its two holes land on hole_a/hole_b (world mm),
    hole axis along normal."""
    spec = STL_LOCAL[stl_key]
    la, lb = spec["holes"]
    m = align(hole_a, [q - p for p, q in zip(hole_a, hole_b)], normal, la, [q - p for p, q in zip(la, lb)], spec["hole_axis"])
    return insert_part(root, stl_key, name, m, reuse=reuse)


def strip_lead(battery):
    """The battery STEP fuses the lead into the pack body: split at the pack end and drop the lead."""
    comp = battery.component
    cut = comp.constructionPlanes.createInput()
    cut.setByOffset(comp.xZConstructionPlane, adsk.core.ValueInput.createByReal(BATTERY_STEP["lead_y"] / 10))
    plane = comp.constructionPlanes.add(cut)
    plane.isLightBulbOn = False
    split = comp.features.splitBodyFeatures
    if split.count:   # reused part: already stripped
        return
    split.add(split.createInput(comp.bRepBodies.itemByName("Body1"), plane, True))
    for body in list(comp.bRepBodies):
        if body.boundingBox.minPoint.y * 10 >= BATTERY_STEP["lead_y"] - 0.1:
            comp.features.removeFeatures.add(body)



def port(occ, name, point_mm):
    """Named Port: a sketch point where a cable plugs in."""
    return sketch_point(occ, point_mm, name=f"Port: {name}")[1]


def descendant(occ, prefix):
    """The first nested occurrence (assembly context) whose name starts with `prefix`, depth first."""
    for child in occ.childOccurrences:
        if child.name.startswith(prefix):
            return child
        found = descendant(child, prefix)
        if found:
            return found
    return None


def body_box(occ):
    """World bounding box (mm) of the occurrence's solid bodies only, children included (occ.boundingBox also counts
    sketches and planes)."""
    lo, hi = [1e9] * 3, [-1e9] * 3
    def bodies(o):
        return list(o.bRepBodies) + [b for c in o.childOccurrences for b in bodies(c)]
    for b in bodies(occ):
        for i, c in enumerate("xyz"):
            lo[i] = min(lo[i], getattr(b.boundingBox.minPoint, c) * 10)
            hi[i] = max(hi[i], getattr(b.boundingBox.maxPoint, c) * 10)
    return lo, hi


def screenshots(app, root, out, stage, views, width=1600, height=1200):
    """Every view of `views` ({name: (eye_dir, up)}) saved as out/<stage>-<name>.png with the reference canvases
    (the design's own and those of inserted Stages) hidden and, when there are any, as <stage>-<name>-overlay.png
    with them shown. The canvases stay hidden afterwards, so the saved document opens clean (`make model-canvases`
    toggles them)."""
    canvases = list(root.canvases) + [c for o in root.allOccurrences for c in o.component.canvases]
    for name, (eye_dir, up) in views.items():
        for c in canvases:
            c.isLightBulbOn = True
        if canvases:
            screenshot(app, os.path.join(out, f"{stage}-{name}-overlay.png"), eye_dir, up, width, height)
        for c in canvases:
            c.isLightBulbOn = False
        screenshot(app, os.path.join(out, f"{stage}-{name}.png"), eye_dir, up, width, height)


def screenshot(app, path, eye_dir, up, width=1600, height=1200):
    """Orthographic shaded view (no mesh edges: the spool appearances carry the shape) of the whole design looking
    back along eye_dir, saved to path."""
    viewport = app.activeViewport
    viewport.visualStyle = adsk.core.VisualStyles.ShadedVisualStyle
    camera = viewport.camera
    camera.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    target = camera.target
    camera.eye = adsk.core.Point3D.create(target.x + eye_dir[0] * 100, target.y + eye_dir[1] * 100, target.z + eye_dir[2] * 100)
    camera.upVector = vector(up)
    camera.isFitView = True
    viewport.camera = camera
    viewport.refresh()
    viewport.saveAsImageFile(path, width, height)
