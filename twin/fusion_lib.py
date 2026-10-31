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
    if matrix:
        occ.transform2 = matrix
        capture_position(app)
    return occ


def capture_position(app):
    """Persist occurrence moves (transform2) in a parametric design; uncaptured moves are dropped."""
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()


def local(occ, point_mm, axis):
    """World point (mm) and axis as the occurrence's component sees them; axis as a Fusion unit vector."""
    inverse = occ.transform2.copy()
    inverse.invert()
    p, a = point(point_mm), vector(axis)
    p.transformBy(inverse); a.transformBy(inverse)
    return p, a


def sketch_point(occ, point_mm, axis="Z", name=None):
    """Named sketch holding one point at the world position, on the component plane normal to `axis`
    (world axis, mapped into the component). Returns (sketch, sketch point)."""
    p, a = local(occ, point_mm, (1, 0, 0) if axis == "X" else (0, 1, 0) if axis == "Y" else (0, 0, 1))
    comps = {"X": a.x, "Y": a.y, "Z": a.z}
    local_axis = max(comps, key=lambda k: abs(comps[k]))
    if abs(comps[local_axis]) < 0.999:
        raise ValueError(f"{occ.name}: axis {axis} is not along a component axis")
    sketch = occ.component.sketches.add(getattr(occ.component, _PLANE_FOR_AXIS[local_axis]))
    if name:
        sketch.name = name
    return sketch, sketch.sketchPoints.add(sketch.modelToSketchSpace(p))


def joint_origin(occ, point_mm, axis):
    """Joint origin on `occ` at the world point whose Z is the world axis ("X", "Y" or "Z"), in assembly context."""
    _, sp = sketch_point(occ, point_mm, axis)
    origin = occ.component.jointOrigins.add(occ.component.jointOrigins.createInput(adsk.fusion.JointGeometry.createByPoint(sp)))
    return origin.createForAssemblyContext(occ)


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
