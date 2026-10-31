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
    projects = app.data.activeHub.dataProjects
    project = next((p for p in projects if p.name == PROJECT_NAME), None) or projects.add(PROJECT_NAME)   # new hub/account
    folder = project.rootFolder
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


def import_stl(component, path, name, matrix=None, convert=True, proxy=None):
    """Mesh body in its own component (faceted solid when convert). `proxy`: a decimated STL of the same part,
    added as a hidden second body named "proxy" that the sweep measures instead. Returns the occurrence."""
    occ = component.occurrences.addNewComponent(matrix or adsk.core.Matrix3D.create())
    occ.component.name = name
    for p, body_name in ((path, None), (proxy, "proxy")):
        if p is None:
            continue
        mesh = occ.component.meshBodies.add(p, adsk.fusion.MeshUnits.MillimeterMeshUnit).item(0)
        if convert:
            features = occ.component.features.meshConvertFeatures
            if features.add(features.createInput([mesh])) is None:
                raise RuntimeError(f"mesh convert failed for {name}")
            if body_name:
                body = occ.component.bRepBodies.item(occ.component.bRepBodies.count - 1)
                body.name = body_name
                body.isLightBulbOn = False
    return occ


def proxy_body(occ):
    """The occurrence's hidden "proxy" body in assembly context, or None."""
    body = occ.component.bRepBodies.itemByName("proxy")
    return body.createForAssemblyContext(occ) if body else None


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
