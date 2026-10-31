"""Build or rebuild the Fusion design `noggin-eyes` (Default Project / noggin): every 01-eyes printed part as a
faceted solid, the four servos with line-arm horns, the receiver shield with its Core, the switch board and
the battery, Ports on the connectors, and the Pivots as joints. Runs INSIDE Fusion: `make twin-eyes`.
Components whose position is inferred rather than measured carry an "(inferred)" suffix.
Numbers live in twin/geometry.py; this file only places things."""
# include: twin/geometry.py
# include: twin/fusion_lib.py
import adsk.core, adsk.fusion, math, os

DOC = "noggin-eyes"
REPO = os.path.expanduser("~/code/noggin")
MODELS = os.path.join(REPO, "docs/references/01-eyes/models")
PT_MODELS = os.path.join(REPO, "docs/references/02-pan-tilt/models")
MOUTH_MODELS = os.path.join(REPO, "docs/references/03-mouth/models")
CAD = os.path.join(REPO, "docs/references/cyberbrick-cad")
SERVO_DIR = os.path.join(CAD, "servo/CAD_9g Servo Motor with Clutch Protection-PG002-PG001")
STEP = {
    "servo": os.path.join(SERVO_DIR, "9g Servo Motor with Clutch Protection-PG002-PG001.stp"),
    "horn": os.path.join(SERVO_DIR, "9g Servo Motor with Clutch Protection-half arm1-PG002-PG001.stp"),
    "receiver": os.path.join(CAD, "receiver/Remote Control Receiver-XA003-XA004/Remote Control Receiver-XA003-XA004.stp"),
    "switch": os.path.join(CAD, "switch/Power Switch Board with 2Pin XH2.54 Connector-XA007/Power Switch Board with 2Pin XH2.54 Connector-XA007.STEP"),
    "battery": os.path.join(CAD, "battery/14500 7.4V 800mAh Li-ion Battery-PC003/14500 7.4V 800mAh Li-ion Battery-PC003.stp"),
}
OUT = os.path.join(REPO, "twin", "build")
PHOTOS = os.path.join(REPO, "docs", "references", "build-photos")   # originals, background blurred (local only)
AXIS = {X: "X", Y: "Y", Z: "Z"}

# (component name, STL, x shift mm). Lids, eyeball bar and the pupil are modelled at one eye. The build uses
# the regular eye and the "updated main bracket and base" profile: main bracket v2 (03-mouth) on the PandT
# base (02-pan-tilt, placed below); the lizard and plain eye STLs and the v1 base are not imported.
PARTS = [
    ("L servo bracket", "L servo bracket", 0), ("R servo bracket", "R servo bracket", 0),
    ("L eyeball", "L eyeball regular", 0), ("R eyeball", "R eyeball regular", 0),
    ("L pupil", "regular pupil", -59), ("R pupil", "regular pupil", 0),
    ("L inside lid", "inside lid", 0), ("L outside lid", "outside lid", 0),
    ("R inside lid", "inside lid", 59), ("R outside lid", "outside lid", 59),
    ("L eyeball bar", "eyeball bar", 0), ("R eyeball bar", "eyeball bar", 79),
]
# Receiver STEP, local mm: the four servo headers and the XH power socket (top centres). PWM numbering is inferred.
RECEIVER_PORTS = {"servo PWM1": (4.2, 10.8, 0.4), "servo PWM2": (4.2, 10.8, 4.6), "servo PWM3": (-4.2, 10.8, 0.4),
                  "servo PWM4": (-4.2, 10.8, 4.6), "XH power": (0.0, 9.62, -9.75)}


# Reference photos (background removed, docs/references/build-photos, local only) as canvases on the camera
# side of the model: (file, root plane, plane offset mm, 2x3 transform taking the unit image square to the
# plane in cm; u runs right, v runs UP from the image's bottom-left). Fusion's canvas rows per plane (measured
# 2026-10-31): xZ -> (z, x), yZ -> (y, z), xY -> (x, y). Anchored on the eye centres measured in each image
# (top 2993x2154 at 17.2 px/mm along z (plate end at z=150.5) and 18.5 across; side 1336x3901 at 22 px/mm;
# front 1911x1371 at 17.1 px/mm). Perspective remains: parts nearer the camera read larger.
CANVASES = {
    "photo top (reference)": ("eyes-top.png", "xZConstructionPlane", 50.0, [[17.4, 0, -2.36], [0, 11.64, -2.97]]),
    "photo side (reference)": ("eyes-side.png", "yZConstructionPlane", -45.0, [[-6.07, 0, 2.28], [0, 17.73, -2.53]]),
    "photo front (reference)": ("eyes-front.png", "xYConstructionPlane", -45.0, [[-11.18, 0, 8.46], [0, 8.02, -3.95]]),
}


def canvas(root, name, path, plane_name, offset_mm, cells):
    cut = root.constructionPlanes.createInput()
    cut.setByOffset(getattr(root, plane_name), adsk.core.ValueInput.createByReal(offset_mm / 10))
    plane = root.constructionPlanes.add(cut)
    plane.name = name + " plane"
    inp = root.canvases.createInput(path, plane)
    m = adsk.core.Matrix2D.create()
    for r, row in enumerate(cells):
        for c, v in enumerate(row):
            m.setCell(r, c, v)
    inp.transform = m
    inp.opacity = 60
    inp.isDisplayedThrough = False
    root.canvases.add(inp).name = name


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


def link(root, name, stl_key, hole_a, hole_b, normal):
    """Place a local-frame link STL so its two holes land on hole_a/hole_b (world mm), hole axis along normal."""
    spec = STL_LOCAL[stl_key]
    la, lb = spec["holes"]
    m = align(hole_a, [q - p for p, q in zip(hole_a, hole_b)], normal, la, [q - p for p, q in zip(la, lb)], spec["hole_axis"])
    return import_stl(root, os.path.join(MODELS, stl_key + ".stl"), name, m)


def strip_lead(battery):
    """The battery STEP fuses the lead into the pack body: split at the pack end and drop the lead."""
    comp = battery.component
    cut = comp.constructionPlanes.createInput()
    cut.setByOffset(comp.xZConstructionPlane, adsk.core.ValueInput.createByReal(BATTERY_STEP["lead_y"] / 10))
    plane = comp.constructionPlanes.add(cut)
    plane.isLightBulbOn = False
    split = comp.features.splitBodyFeatures
    split.add(split.createInput(comp.bRepBodies.itemByName("Body1"), plane, True))
    for body in list(comp.bRepBodies):
        if body.boundingBox.minPoint.y * 10 >= BATTERY_STEP["lead_y"] - 0.1:
            comp.features.removeFeatures.add(body)


def run(_context: str):
    app = adsk.core.Application.get()
    doc, design, folder = open_or_create(app, DOC)
    root = design.rootComponent
    occs = {}
    for name, stl, dx in PARTS:
        occs[name] = import_stl(root, os.path.join(MODELS, stl + ".stl"), name, align((dx, 0, 0)))
    occs["main bracket"] = import_stl(root, os.path.join(MOUTH_MODELS, "main bracket v2.stl"), "main bracket v2")
    occs["main bracket"].isGrounded = True
    pt0 = pt_to_eyes_standalone((0, 0, 0))
    import_stl(root, os.path.join(PT_MODELS, "PandT base.stl"), "PandT base",
               align(pt0, (-1, 0, 0), Y))
    keeper_y = pt_to_eyes_standalone(STANDOFFS["pt_base"]["wire_keeper"][0])[1]
    import_stl(root, os.path.join(MODELS, "wire keeper.stl"), "wire keeper (inferred)", align((0, keeper_y + 22.6, 0)))

    # Servos and horns from the measured tab holes; the shaft axis is the inferred horn pivot.
    for key in ("l_lid", "r_lid", "l_eye", "r_eye"):
        origin, tab_x, shaft = servo_frame(key)
        label = key.upper()[0] + (" lid" if "lid" in key else " eye")
        occs[key + "_servo"] = import_step(root, STEP["servo"], f"{label} servo", align(origin, tab_x, [-c for c in shaft], SERVO_STEP["shaft"]))
        arm = Y if "lid" in key else (-1, 0, 0) if key == "l_eye" else X   # single arm: toward the bar pin
        seat = add(origin, tuple(SERVO_STEP["horn_seat"] * c for c in shaft))
        occs[key + "_horn"] = import_step(root, STEP["horn"], f"{label} horn (inferred)", align(seat, arm, shaft, HORN_STEP["hub"]))

    # Boards and battery on the base: shield on its standoffs with the Core flipped on top (the STEP has it
    # underneath; the build photo shows it on top), switch board centred on its standoffs, battery in its pocket.
    stand = STANDOFFS["pt_base"]
    receiver_at = mean([pt_to_eyes_standalone(p) for p in stand["receiver_1"]])
    # Shield turned a quarter about Y so the XH socket faces -X and the Core's USB-C the side (build photos).
    receiver_m = align(receiver_at, (0, 0, -1), X)
    receiver = import_step(root, STEP["receiver"], "receiver shield", receiver_m)
    next(o for o in receiver.component.occurrences if o.name.startswith("CORE")).deleteMe()
    # The Core as a second import of the receiver STEP stripped to the Core, flipped about the PCB mid-plane
    # (the STEP has it under the shield; the build photos show it on top).
    flip = adsk.core.Matrix3D.create()
    flip.setToRotation(math.pi, vector(Z), point((0, 0.8, 0)))   # about Z: the USB-C keeps facing -X (side photo)
    core = import_step(root, STEP["receiver"], "Core (flipped onto the shield top, per photo)", matmul(receiver_m, flip))
    for o in list(core.component.occurrences):
        if not o.name.startswith("CORE"):
            o.deleteMe()
    core_proxy = core.childOccurrences.item(0)
    usb = core_proxy.component.bRepBodies.itemByName("Body3").createForAssemblyContext(core_proxy).boundingBox
    assert core_proxy.boundingBox.minPoint.y * 10 > receiver_at[1], "Core must sit above the shield"
    for name, p in RECEIVER_PORTS.items():
        w = point(p); w.transformBy(receiver_m)
        port(receiver, name, (w.x * 10, w.y * 10, w.z * 10))
    usb_centre = tuple((getattr(usb.minPoint, c) + getattr(usb.maxPoint, c)) * 5 for c in "xyz")
    port(core, "USB-C", usb_centre)
    import_step(root, STEP["switch"], "switch board", align(pt_to_eyes_standalone(stand["switch_post"][0]), (0, 0, -1), X, SWITCH_STEP["hole"]))
    pocket = BATTERY_POCKET_PT
    near, far = pt_to_eyes_standalone((pocket["x"][1], pocket["y"][0], pocket["floor_z"])), pt_to_eyes_standalone((pocket["x"][0], pocket["y"][1], pocket["floor_z"]))
    battery_at = ((near[0] + far[0]) / 2, near[1] - BATTERY_STEP["floor_z"], near[2])
    battery = import_step(root, STEP["battery"], "battery", align(battery_at, (-1, 0, 0), Y))
    strip_lead(battery)
    port(battery, "battery lead", add(battery_at, (-3.5, 3.5, 52.5)))   # the pack's plug; wiring is out of scope

    # Linkage parts (local-frame STLs) at their pins, then the joints.
    for s in "LR":
        eye = PIVOTS[s.lower() + "_eye"]["point"]
        lid_horn = PIVOTS[s.lower() + "_lid_horn"]["point"]
        eye_horn = PIVOTS[s.lower() + "_eye_horn"]["point"]
        normal = (-1, 0, 0) if s == "L" else (1, 0, 0)
        for key, stl in (("eyelid_bar", "eyelid bar"), ("eyelid_crank", "eyelid bar crank")):
            spec = LID_LINKS[key]
            x = side(s, (spec["x"], 0, 0))[0]
            horn_pin = (x, lid_horn[1] + HORN_STEP["pin"], lid_horn[2])
            lid_pin = (x,) + side(s, LID_PINS[spec["lid"]])[1:]
            name = f"{s} {stl} (inferred)"
            occs[name] = link(root, name, stl, horn_pin, lid_pin, normal)
            lid = occs[f"{s} {spec['lid']} lid"]
            pivot_joint(root, occs[name], occs[f"{s.lower()}_lid_horn"], horn_pin, "X", f"{s} {stl} / arm pin (inferred)")
            close_loop(root, occs[name], lid, lid_pin, "X", f"{s} {stl} / {spec['lid']} lid pin")
        pivot_joint(root, occs[f"{s} inside lid"], occs["main bracket"], eye, "X", f"{s} inside lid pivot")
        pivot_joint(root, occs[f"{s} outside lid"], occs["main bracket"], eye, "X", f"{s} outside lid pivot")
        pivot_joint(root, occs[f"{s} eyeball"], occs["main bracket"], eye, "Y", f"{s} eyeball pivot")
        for part, axis in (("lid", "X"), ("eye", "Y")):
            lo, hi = HORN_LIMITS[f"{s.lower()}_{part}"]
            pivot_joint(root, occs[f"{s.lower()}_{part}_horn"], occs[f"{s.lower()}_{part}_servo"], PIVOTS[f"{s.lower()}_{part}_horn"]["point"],
                        axis, f"{s} {part} horn (inferred)", (lo - 90, hi - 90))
        arm_end, eye_end = (side(s, p) for p in EYEBALL_BAR_PINS)
        pivot_joint(root, occs[f"{s} eyeball bar"], occs[f"{s.lower()}_eye_horn"], arm_end, "Y", f"{s} eyeball bar / arm pin (inferred)")
        close_loop(root, occs[f"{s} eyeball bar"], occs[f"{s} eyeball"], eye_end, "Y", f"{s} eyeball bar / eyeball pin")
        group = adsk.core.ObjectCollection.create()
        group.add(occs[f"{s} eyeball"]); group.add(occs[f"{s} pupil"])
        root.rigidGroups.add(group, True)

    moving = {o.name for o in root.occurrences if "servo" not in o.component.name and any(w in o.component.name for w in ("lid", "eyeball", "pupil", "horn", "bar", "crank"))}
    for occ in root.occurrences:
        if occ.name not in moving:
            occ.isGrounded = True

    for name, (photo, plane, offset_mm, cells) in CANVASES.items():
        canvas(root, name, os.path.join(PHOTOS, photo), plane, offset_mm, cells)

    os.makedirs(OUT, exist_ok=True)
    screenshot(app, os.path.join(OUT, "eyes-top.png"), Y, Z)
    screenshot(app, os.path.join(OUT, "eyes-side.png"), (-1, 0, 0), Y)
    screenshot(app, os.path.join(OUT, "eyes-front.png"), (0, 0, -1), Y)
    version = save(doc, f"{DOC}: rebuilt by twin/eyes.py", DOC, folder)
    ports = sum(1 for o in root.occurrences for sk in o.component.sketches if sk.name.startswith("Port:"))
    print(f"{DOC} v{version}: {root.occurrences.count} components, {root.joints.count} joints, {ports} ports")
    print("  project files:", [(f.name, f.versionNumber) for f in folder.dataFiles])
    for j in root.joints:
        state = "ok" if j.healthState == adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState else j.errorOrWarningMessage
        print(f"  joint {j.name}: {state}")
    for o in list(root.occurrences) + list(receiver.childOccurrences) + list(core.childOccurrences):
        lo, hi = body_box(o)
        print("  %-42s x %6.1f..%6.1f  y %6.1f..%6.1f  z %6.1f..%6.1f" % (o.name, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    for o in root.occurrences:
        for sk in o.component.sketches:
            if sk.name.startswith("Port:"):
                p = sk.sketchPoints.item(sk.sketchPoints.count - 1).worldGeometry.copy(); p.transformBy(o.transform2)
                print("  %-42s (%.1f, %.1f, %.1f)" % (sk.name, p.x * 10, p.y * 10, p.z * 10))
