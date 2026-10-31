"""Fusion helpers shared by the Stage scripts, inlined via `# include: twin/fusion_lib.py` after
`# include: twin/geometry.py`. Points and lengths come in as mm; Fusion's API takes cm and radians.
Verified calls: docs/research/2026-10-31-twin.md."""
import adsk.core, adsk.fusion, math

PROJECT_NAME = "Noggin"   # the hub's former Default Project, renamed; Stage documents sit at its root
_PLANE_FOR_AXIS = {"X": "yZConstructionPlane", "Y": "xZConstructionPlane", "Z": "xYConstructionPlane"}


def point(p):
    return adsk.core.Point3D.create(p[0] / 10, p[1] / 10, p[2] / 10)


def vector(v):
    return adsk.core.Vector3D.create(v[0], v[1], v[2])


def open_or_create(app, name):
    """Open the design `name` in project Noggin (or a new one), parametric, emptied of occurrences.
    Returns (document, design, folder); pass the folder to save()."""
    folder = next(p for p in app.data.activeHub.dataProjects if p.name == PROJECT_NAME).rootFolder
    existing = next((f for f in folder.dataFiles if f.name == name), None)
    doc = app.documents.open(existing, True) if existing else app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType   # mesh convert only works here
    if design.timeline.count:          # one rollback + delete: per-occurrence deletes recompute the timeline each time
        design.timeline.markerPosition = 0
        design.timeline.deleteAllAfterMarker()
    for occ in list(design.rootComponent.occurrences):
        occ.deleteMe()
    return doc, design, folder


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
        x.normalize(); z.normalize()
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


def import_stl(component, path, name, matrix=None, convert=True):
    """Mesh body in its own component (faceted solid when convert). Returns the occurrence."""
    occ = component.occurrences.addNewComponent(matrix or adsk.core.Matrix3D.create())
    occ.component.name = name
    mesh = occ.component.meshBodies.add(path, adsk.fusion.MeshUnits.MillimeterMeshUnit).item(0)
    if convert:
        features = occ.component.features.meshConvertFeatures
        if features.add(features.createInput([mesh])) is None:
            raise RuntimeError(f"mesh convert failed for {name}")
    return occ


def import_step(component, path, name, matrix=None):
    app = adsk.core.Application.get()
    options = app.importManager.createSTEPImportOptions(path)
    options.isViewFit = False
    occ = app.importManager.importToTarget2(options, component).item(0)
    occ.component.name = name
    return reoccur(occ, matrix) if matrix else occ


def reoccur(occ, matrix):
    """The same component as a new occurrence at `matrix`, replacing `occ` (setting transform2 on an imported
    occurrence is silently dropped for the first STEP in a design; a fresh occurrence keeps its transform)."""
    parent = occ.assemblyContext.component if occ.assemblyContext else occ.sourceComponent
    placed = parent.occurrences.addExistingComponent(occ.component, matrix)
    occ.deleteMe()
    return placed


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


def port(occ, name, point_mm):
    """Named Port: a sketch point where a cable plugs in."""
    return sketch_point(occ, point_mm, name=f"Port: {name}")[1]


def body_box(occ):
    """World bounding box (mm) of the occurrence's solid bodies only (occ.boundingBox also counts sketches and planes)."""
    lo, hi = [1e9] * 3, [-1e9] * 3
    for b in occ.bRepBodies:
        for i, c in enumerate("xyz"):
            lo[i] = min(lo[i], getattr(b.boundingBox.minPoint, c) * 10)
            hi[i] = max(hi[i], getattr(b.boundingBox.maxPoint, c) * 10)
    return lo, hi


def screenshot(app, path, eye_dir, up, width=1600, height=1200):
    """Orthographic view of the whole design looking back along eye_dir, saved to path."""
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
