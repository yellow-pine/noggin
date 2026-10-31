"""Build or rebuild the Fusion design `noggin-pan-tilt` (project Noggin): every 02-pan-tilt printed part (v2 upright)
as a faceted solid in the PT frame (pan axis Z through the origin, tilt axis X at (0,-13,33.4)), the tilt and pan
servos with their half-arm horns, the tilt and pan bars closing the two loops, the second receiver shield with its
Core, the switch board and the battery on the PandT base, Ports on the connectors, and the Pivots as joints.
Runs INSIDE Fusion: `make model-pan-tilt`. Components whose position is inferred rather than measured carry an
"(inferred)" suffix. Numbers live in model/geometry.py; reuse/patching as in eyes.py (fingerprints, fusion_lib).
The eyes Stage is NOT here: the bracket stem into the tilt arm window is the top assembly's job (#17)."""
# include: model/geometry.py
# include: model/fusion_lib.py
# include: model/contacts.py
import adsk.core, adsk.fusion, json, math, os

DOC = "noggin-pan-tilt"
FULL = False   # `FULL=1 make model-pan-tilt` flips this: empty the document and import everything again
REPO = os.path.expanduser("~/code/noggin")
MODELS = os.path.join(REPO, "docs/references/02-pan-tilt/models")
CAD = os.path.join(REPO, "docs/references/cyberbrick-cad")
SERVO_DIR = os.path.join(CAD, "servo/CAD_9g Servo Motor with Clutch Protection-PG002-PG001")
STEP = {
    "servo": os.path.join(SERVO_DIR, "9g Servo Motor with Clutch Protection-PG002-PG001.stp"),
    "horn": os.path.join(SERVO_DIR, "9g Servo Motor with Clutch Protection-half arm1-PG002-PG001.stp"),
    "receiver": os.path.join(CAD, "receiver/Remote Control Receiver-XA003-XA004/Remote Control Receiver-XA003-XA004.stp"),
    "switch": os.path.join(CAD, "switch/Power Switch Board with 2Pin XH2.54 Connector-XA007/Power Switch Board with 2Pin XH2.54 Connector-XA007.STEP"),
    "battery": os.path.join(CAD, "battery/14500 7.4V 800mAh Li-ion Battery-PC003/14500 7.4V 800mAh Li-ion Battery-PC003.stp"),
}
OUT = os.path.join(REPO, "model", "build")
PROXIES = os.path.join(OUT, "proxies")   # decimated STLs from `make model-proxies`, measured by the sweep

# (component name, STL stem, z shift mm): the designer exported these in the assembled PT frame, except the tilt arm,
# still at the v1 height (upright v2 raised the pivot 5 mm, docs/research/2026-10-31-model.md).
PARTS = [
    ("PandT base", "PandT base", 0), ("bearing block", "PandT bearing block", 0), ("pan base", "PandT pan base", 0),
    ("upright v2", "PandT upright v2", 0), ("tilt arm", "PandT tilt arm", TILT_ARM_SHIFT_Z),
    ("servo mount plain", "PandT servo mount plain", 0), ("servo mount cutout", "PandT servo mount cutout", 0),
    ("wire holder", "PandT wire holder", 0),
]
MOVING = {"pan base", "upright v2", "tilt servo", "tilt arm", "tilt horn (inferred)", "tilt bar (inferred)",
          "pan horn (inferred)", "pan bar (inferred)"}
BAR_STL = {"tilt": "tilt bar", "pan": "PandT bar"}
LEVER = {"tilt": "tilt arm", "pan": "upright v2"}
HORN_RANGE = {"tilt": "tilt", "pan": "rotate"}   # HORN_LIMITS keys: the remote config names the pan servo "rotate"
# Receiver STEP, local mm: the four servo headers and the XH power socket (top centres). Guide step 10: tilt on the
# top-left header, pan on the top-right; the PWM numbering of the headers is inferred (as in eyes.py).
RECEIVER_PORTS = {"servo PWM1 (tilt)": (4.2, 10.8, 0.4), "servo PWM2 (mouth)": (4.2, 10.8, 4.6), "servo PWM3 (pan)": (-4.2, 10.8, 0.4),
                  "servo PWM4": (-4.2, 10.8, 4.6), "XH power": (0.0, 9.62, -9.75)}
SWITCH_AT = (6.0, 80.5, 13.0)   # centred between the two switch standoffs (STANDOFFS pt_base, 24 apart along Y) [I]


def run(_context: str):
    app = adsk.core.Application.get()
    doc, design, folder = open_or_create(app, DOC, keep_parts=not FULL)
    root = design.rootComponent
    reuse = kept_parts(root)   # the build pops what it places; the rest is stale
    occs = {}
    def stl(stem, name, matrix=None):
        return import_stl(root, os.path.join(MODELS, stem + ".stl"), name, matrix, proxy=os.path.join(PROXIES, stem + ".stl"), reuse=reuse)
    def step(key, name, matrix):
        return import_step(root, STEP[key], name, matrix, reuse=reuse)
    for name, stem, dz in PARTS:
        occs[name] = stl(stem, name, align((0, 0, dz)) if dz else None)

    # Servos from the measured tab holes, horns at the inferred shaft, each bar on its horn pin and lever hole.
    pins = {}
    for key in ("tilt", "pan"):
        origin, tab_x, shaft = servo_frame(key)
        occs[f"{key} servo"] = step("servo", f"{key} servo", align(origin, tab_x, [-c for c in shaft], SERVO_STEP["shaft"]))
        seat = PIVOTS[key + "_horn"]["point"]
        pin, lever = horn_pin(key)
        occs[f"{key} horn (inferred)"] = step("horn", f"{key} horn (inferred)", align(seat, [p - q for p, q in zip(pin, seat)], shaft, HORN_STEP["hub"]))
        name = f"{key} bar (inferred)"
        occs[name] = link(root, name, BAR_STL[key], pin, lever, PIVOTS[key + "_horn"]["axis"], reuse, MODELS, PROXIES)
        pins[key] = pin, lever

    # Boards and battery on the PandT base, oriented as the eyes build (XH socket to the front, Core on top).
    stand = STANDOFFS["pt_base"]
    receiver_at = mean(stand["receiver_2"])
    receiver_m = align(receiver_at, (0, -1, 0), (-1, 0, 0))
    receiver = step("receiver", "receiver shield", receiver_m)
    for o in list(receiver.component.occurrences):
        if o.name.startswith("CORE"):
            o.deleteMe()
    flip = adsk.core.Matrix3D.create()
    flip.setToRotation(math.pi, vector(Z), point((0, 0.8, 0)))   # the STEP has the Core under the shield; the build has it on top
    core = step("receiver", "Core (flipped onto the shield top, per photo)", matmul(receiver_m, flip))
    for o in list(core.component.occurrences):
        if not o.name.startswith("CORE"):
            o.deleteMe()
    core_proxy = core.childOccurrences.item(0)
    usb = core_proxy.component.bRepBodies.itemByName("Body3").createForAssemblyContext(core_proxy).boundingBox
    assert min(b.boundingBox.minPoint.z for b in core_proxy.bRepBodies) * 10 > receiver_at[2], "Core must sit above the shield"
    usb_centre = tuple((getattr(usb.minPoint, c) + getattr(usb.maxPoint, c)) * 5 for c in "xyz")
    step("switch", "switch board (inferred)", align(SWITCH_AT, (-1, 0, 0), Y, (3.0, 0.0, 0.0)))   # PCB centre on the standoff tops
    pocket = BATTERY_POCKET_PT
    battery_at = (sum(pocket["x"]) / 2, pocket["y"][0], pocket["floor_z"] - BATTERY_STEP["floor_z"])
    battery = step("battery", "battery", align(battery_at, X, Z))
    strip_lead(battery)
    for occ in reuse.values():   # kept parts the build no longer places
        occ.deleteMe()
    parts_end(design)   # everything below is cheap and recreated by every build: no import may follow this line

    for name, p in RECEIVER_PORTS.items():
        w = point(p); w.transformBy(receiver_m)
        port(receiver, name, (w.x * 10, w.y * 10, w.z * 10))
    port(core, "USB-C", usb_centre)
    port(battery, "battery lead", add(battery_at, (3.5, 52.5, 3.5)))   # the pack's plug; wiring is out of scope
    # The pan base turns on the bearing block (18 x 5.5 in the base recess and the pan base recess, zero clearance by design)
    pivot_joint(root, occs["pan base"], occs["bearing block"], (0.0, 0.0, 3.5), "Z", "pan pivot")
    pivot_joint(root, occs["tilt arm"], occs["upright v2"], PIVOTS["tilt"]["point"], "X", "tilt pivot")
    for key in ("tilt", "pan"):
        axis = "X" if key == "tilt" else "Z"
        lo, hi = HORN_LIMITS[HORN_RANGE[key]]
        pivot_joint(root, occs[f"{key} horn (inferred)"], occs[f"{key} servo"], PIVOTS[key + "_horn"]["point"], axis, f"{key} horn (inferred)", (lo - 90, hi - 90))
        pin, lever = pins[key]
        pivot_joint(root, occs[f"{key} bar (inferred)"], occs[f"{key} horn (inferred)"], pin, axis, f"{key} bar / arm pin (inferred)")
        close_loop(root, occs[f"{key} bar (inferred)"], occs[LEVER[key]], lever, axis, f"{key} bar / lever screw")
    group = adsk.core.ObjectCollection.create()   # screwed together: the pan mechanism turns as one
    for name in ("pan base", "upright v2", "tilt servo"):
        group.add(occs[name])
    root.rigidGroups.add(group, True)

    moving = {o.name for o in root.occurrences if o.component.name in MOVING}
    for occ in root.occurrences:
        if occ.name not in moving:
            occ.isGrounded = True
    new_contacts = not design.contactSets.count   # one contact set per Stage (#20): moving parts, base, servos
    if new_contacts:
        contact_set(design, root, moving | {o.name for o in root.occurrences if o.component.name in ("PandT base", "pan servo")})

    os.makedirs(OUT, exist_ok=True)
    screenshot(app, os.path.join(OUT, "pan-tilt-top.png"), Z, Y)
    screenshot(app, os.path.join(OUT, "pan-tilt-side.png"), X, Z)
    screenshot(app, os.path.join(OUT, "pan-tilt-front.png"), (0, -1, 0), Z)
    now = summary(root)
    diff = changes(saved_summary(root), now) + [f"imported {n}" for n in FRESH] + [f"removed {n}" for n in reuse] + (["contact set"] if new_contacts else [])
    if diff:
        root.attributes.add(*SUMMARY_ATTR, json.dumps(now, sort_keys=True))
        version = save(doc, f"{DOC}: rebuilt by model/pan_tilt.py", DOC, folder)
    else:
        version = doc.dataFile.versionNumber
    print(f"{DOC} v{version}: {root.occurrences.count} components, {root.joints.count} joints, {len(now['ports'])} ports,",
          "saved: " + "; ".join(diff) if diff else "unchanged")
    for j in root.joints:
        state = "ok" if j.healthState == adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState else j.errorOrWarningMessage
        print(f"  joint {j.name}: {state}")
    for o in list(root.occurrences) + list(receiver.childOccurrences) + list(core.childOccurrences):
        lo, hi = body_box(o)
        print("  %-42s x %6.1f..%6.1f  y %6.1f..%6.1f  z %6.1f..%6.1f" % (o.name, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    for name, p in now["ports"].items():
        print("  Port: %-36s (%.1f, %.1f, %.1f)" % (name, *p))
