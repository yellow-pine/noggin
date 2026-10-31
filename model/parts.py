"""Build or update the parts library: one Fusion design per printed part (STL, faceted solid) and per hardware STEP
in folder `parts` of project Noggin, so the builds insert stored solids (fusion_lib.insert_part) instead of converting
meshes (docs/research/2026-10-31-fusion-throughput.md section 4). The design's root carries the sha256 of its source
files (FINGERPRINT_ATTR); a part whose sources are unchanged is skipped, `FULL=1 make model-parts` reconverts
everything. Runs INSIDE Fusion: `make model-parts`."""

# include: model/geometry.py
# include: model/fusion_lib.py
import hashlib
import os
import time

import adsk.core
import adsk.fusion

FULL = False  # `FULL=1 make model-parts` flips this
REPO = os.path.expanduser("~/code/noggin")
REF = os.path.join(REPO, "docs/references")
SERVO_DIR = os.path.join(REF, "cyberbrick-cad/servo/CAD_9g Servo Motor with Clutch Protection-PG002-PG001")
RECEIVER = os.path.join(
    REF, "cyberbrick-cad/receiver/Remote Control Receiver-XA003-XA004/Remote Control Receiver-XA003-XA004.stp"
)
STLS = {  # designer folder: the STL stems the sub-assembly builds place (the lizard/plain eyes, v1 bracket and bases are not built)
    "01-eyes": [
        "L servo bracket",
        "R servo bracket",
        "L eyeball regular",
        "R eyeball regular",
        "regular pupil",
        "inside lid",
        "outside lid",
        "eyeball bar",
        "eyelid bar",
        "eyelid bar crank",
    ],
    "02-pan-tilt": [
        "PandT base",
        "PandT bearing block",
        "PandT pan base",
        "PandT upright v2",
        "PandT tilt arm",
        "PandT servo mount plain",
        "PandT servo mount cutout",
        "PandT wire holder",
        "tilt bar",
        "PandT bar",
    ],
    "03-mouth": ["main bracket v2", "top jaw plain", "bottom jaw plain", "jaws servo mount", "jaws connector bar"],
}
STEPS = {
    "servo": os.path.join(SERVO_DIR, "9g Servo Motor with Clutch Protection-PG002-PG001.stp"),
    "horn": os.path.join(SERVO_DIR, "9g Servo Motor with Clutch Protection-half arm1-PG002-PG001.stp"),
    "receiver shield": RECEIVER,  # the receiver STEP minus the Core
    "Core": RECEIVER,  # the receiver STEP stripped to the Core
    "switch board": os.path.join(
        REF,
        "cyberbrick-cad/switch/Power Switch Board with 2Pin XH2.54 Connector-XA007/Power Switch Board with 2Pin XH2.54 Connector-XA007.STEP",
    ),
    "battery": os.path.join(
        REF, "cyberbrick-cad/battery/14500 7.4V 800mAh Li-ion Battery-PC003/14500 7.4V 800mAh Li-ion Battery-PC003.stp"
    ),
}
LIBRARY = {stem: [os.path.join(REF, stage, "models", stem + ".stl")] for stage, stems in STLS.items() for stem in stems}
LIBRARY.update({name: [path] for name, path in STEPS.items()})


def source_fingerprint(paths):
    h = hashlib.sha256()
    for p in paths:
        h.update(open(p, "rb").read())
    return h.hexdigest()[:16]


def stale(library, stored):
    """Library names whose stored fingerprint is missing or differs from their sources, in library order."""
    return [name for name, paths in library.items() if stored.get(name) != source_fingerprint(paths)]


def strip(occ, keep_core):
    """The receiver STEP holds the shield and the Core: keep one of them."""
    for o in list(occ.component.occurrences):
        if o.name.startswith("CORE") != keep_core:
            o.deleteMe()


def spool(design, name):
    """The spool's appearance (a matte plastic from the Fusion Appearance Library in the spool colour) and the
    material (an ABS copy from the Fusion Material Library at the PRINTED density) for printed part `name`."""
    key = next(k for k in PRINTED if k.split(" (")[0] == name)
    colour, material = PRINTED[key]
    libs = adsk.core.Application.get().materialLibraries
    appearance = design.appearances.addByCopy(
        libs.itemByName("Fusion Appearance Library").appearances.itemByName("Plastic - Matte (White)"),
        key.replace(name, colour),
    )
    props = appearance.appearanceProperties
    rgb = bytes.fromhex(SPOOLS[colour][1:])
    next(props.item(i) for i in range(props.count) if props.item(i).name == "Color").value = adsk.core.Color.create(
        *rgb, 255
    )
    physical = design.materials.addByCopy(
        libs.itemByName("Fusion Material Library").materials.itemByName("ABS Plastic"), material
    )
    physical.materialProperties.itemByName("Density").value = MATERIALS[material]["density_g_cm3"] * 1000  # kg/m3
    return appearance, physical


def convert(design, name):
    """The part's solids in the design root: STL -> faceted body in the spool's appearance and material; STEP -> its
    occurrence, edited, keeping the STEP appearances."""
    root = design.rootComponent
    paths = LIBRARY[name]
    if paths[0].lower().endswith(".stl"):
        appearance, physical = spool(design, name)
        mesh = root.meshBodies.add(paths[0], adsk.fusion.MeshUnits.MillimeterMeshUnit).item(0)
        features = root.features.meshConvertFeatures
        if features.add(features.createInput([mesh])) is None:
            raise RuntimeError(f"mesh convert failed for {name}")
        body = root.bRepBodies.item(root.bRepBodies.count - 1)
        body.appearance, body.material = appearance, physical
        return
    app = adsk.core.Application.get()
    options = app.importManager.createSTEPImportOptions(paths[0])
    options.isViewFit = False
    occ = app.importManager.importToTarget2(options, root).item(0)
    if name in ("receiver shield", "Core"):
        strip(occ, name == "Core")
    elif name == "battery":
        strip_lead(occ)


def run(_context: str):
    app = adsk.core.Application.get()
    folder = parts_folder(app)
    files = {f.name: f for f in folder.dataFiles}
    stored = {} if FULL else {n: stored_fingerprint(app, f) for n, f in files.items() if n in LIBRARY}
    todo = stale(LIBRARY, stored)
    print(f"parts library: {len(LIBRARY)} parts, {len(todo)} to convert")
    for name in todo:
        t = time.time()
        adsk.doEvents()
        doc = (
            app.documents.open(files[name], True)
            if name in files
            else app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        )
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType  # mesh convert only works here
        root = design.rootComponent
        design.timeline.markerPosition = 0
        design.timeline.deleteAllAfterMarker()
        for item in list(root.occurrences) + list(root.bRepBodies) + list(root.meshBodies):
            item.deleteMe()
        convert(design, name)
        root.attributes.add(*FINGERPRINT_ATTR, source_fingerprint(LIBRARY[name]))
        save(doc, f"parts: {name} converted by model/parts.py", name, folder)
        bodies = root.bRepBodies.count
        doc.close(False)
        print(f"  {name}: {bodies} bodies, {time.time() - t:.1f} s")
