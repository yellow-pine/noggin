"""Build or rebuild the Fusion design `noggin-pan-tilt` (project Noggin): every 02-pan-tilt printed part (v2 upright)
from the parts library (`make model-parts`, fusion_lib.insert_part) in the PT frame (pan axis Z through the origin,
tilt axis X at (0,-13,33.4)), the tilt and pan servos with their half-arm horns, the tilt and pan bars closing the
two loops, and the electronics this Stage owns (ADR 0004): both receiver shields with their Cores on the base's two
standoff sets (receiver 1 front, 2 back: guide p.19), both switch boards and both batteries, Ports on the connectors,
and the Pivots as joints. Runs INSIDE Fusion: `make model-pan-tilt`. Components whose position is inferred rather than
measured carry an "(inferred)" suffix. Numbers live in model/geometry.py; reuse as in eyes.py (fingerprints, fusion_lib).
The eyes Stage is NOT here: the bracket stem into the tilt arm window is the top assembly's job (#17)."""
# include: model/geometry.py
# include: model/fusion_lib.py
# include: model/contacts.py
import adsk.core, adsk.fusion, json, math, os

DOC = "noggin-pan-tilt"
FULL = False   # `FULL=1 make model-pan-tilt` flips this: empty the document and import everything again
REPO = os.path.expanduser("~/code/noggin")
OUT = os.path.join(REPO, "model", "build")

# (component name, library part, z shift mm): the designer exported these in the assembled PT frame, except the tilt arm,
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
# Receiver STEP, local mm: the four servo headers and the XH power socket (top centres); the PWM numbering of the
# headers is inferred. Core 1 drives the eyes (docs/build-notes.md), Core 2 tilt/mouth/pan (guide step 10, config JSON).
HEADERS = {"PWM1": (4.2, 10.8, 0.4), "PWM2": (4.2, 10.8, 4.6), "PWM3": (-4.2, 10.8, 0.4), "PWM4": (-4.2, 10.8, 4.6)}
XH_POWER = (0.0, 9.62, -9.75)
CHANNELS = {1: {"PWM1": "L lid", "PWM2": "L eye", "PWM3": "R lid", "PWM4": "R eye"}, 2: {"PWM1": "tilt", "PWM2": "mouth", "PWM3": "pan"}}
# Our build runs one pack and one switch board per shield (docs/build-notes.md); the base has one battery box and one
# pair of switch standoffs, so set 2 is inferred: switch boards hang one per standoff (as the eyes-only build hangs
# its switch on a single post), battery 2 lies on top of battery 1 in the box.
SWITCH_AT = {1: STANDOFFS["pt_base"]["switch"][0], 2: STANDOFFS["pt_base"]["switch"][1]}   # [I]
BATTERY_STACK_Z = 16.3   # pack height: the second pack's floor sits on the first pack's top [I]


def run(_context: str):
    app = adsk.core.Application.get()
    doc, design, folder = open_or_create(app, DOC, keep_parts=not FULL)
    root = design.rootComponent
    reuse = kept_parts(root)   # the build pops what it places; the rest is stale
    occs, steps = {}, []   # one chunk per part insert (per electronics set), then one for the joints (fusion_lib.chunked)
    def part(key, lib, name, matrix=None):
        steps.append((name, lambda: occs.__setitem__(key, insert_part(root, lib, name, matrix, reuse=reuse))))
    for name, lib, dz in PARTS:
        part(name, lib, name, align((0, 0, dz)) if dz else None)

    # Servos from the measured tab holes, horns at the inferred shaft, each bar on its horn pin and lever hole.
    pins = {}
    for key in ("tilt", "pan"):
        origin, tab_x, shaft = servo_frame(key)
        part(f"{key} servo", "servo", f"{key} servo", align(origin, tab_x, [-c for c in shaft], SERVO_STEP["shaft"]))
        seat = PIVOTS[key + "_horn"]["point"]
        pin, lever = horn_pin(key)
        part(f"{key} horn (inferred)", "horn", f"{key} horn (inferred)", align(seat, [p - q for p, q in zip(pin, seat)], shaft, HORN_STEP["hub"]))
        name = f"{key} bar (inferred)"
        steps.append((name, lambda name=name, k=key, a=pin, b=lever: occs.__setitem__(name, link(root, name, BAR_STL[k], a, b, PIVOTS[k + "_horn"]["axis"], reuse))))
        pins[key] = pin, lever

    # Both electronics sets on the PandT base, oriented as the designer's build (XH socket to the front, Core on top:
    # the STEP has the Core under the shield, flipped about the PCB mid-plane). Port points are taken now, placed after parts_end.
    stand = STANDOFFS["pt_base"]
    ports = []   # (occurrence, Port name, world point)
    flip = adsk.core.Matrix3D.create()
    flip.setToRotation(math.pi, vector(Z), point((0, 0.8, 0)))
    def electronics(n):
        receiver_m = align(mean(stand[f"receiver_{n}"]), (0, -1, 0), (-1, 0, 0))
        receiver = insert_part(root, "receiver shield", f"receiver shield {n}", receiver_m, reuse=reuse)
        core = insert_part(root, "Core", f"Core {n} (flipped onto the shield top, per photo)", matmul(receiver_m, flip), reuse=reuse)
        core_pcb = descendant(core, "CORE")
        usb = core_pcb.component.bRepBodies.itemByName("Body3").createForAssemblyContext(core_pcb).boundingBox
        assert usb.minPoint.z * 10 > receiver_m.translation.z * 10, "Core must sit above the shield"
        for header, p in HEADERS.items():
            w = point(p); w.transformBy(receiver_m)
            ports.append((receiver, f"Core {n} servo {header}" + (f" ({CHANNELS[n][header]})" if header in CHANNELS[n] else ""), (w.x * 10, w.y * 10, w.z * 10)))
        w = point(XH_POWER); w.transformBy(receiver_m)
        ports.append((receiver, f"Core {n} XH power", (w.x * 10, w.y * 10, w.z * 10)))
        ports.append((core, f"Core {n} USB-C", tuple((getattr(usb.minPoint, c) + getattr(usb.maxPoint, c)) * 5 for c in "xyz")))
        insert_part(root, "switch board", f"switch board {n} (inferred)", align(SWITCH_AT[n], (-1, 0, 0), Y, SWITCH_STEP["hole"]), reuse=reuse)   # hole on the standoff top
        pocket = BATTERY_POCKET_PT
        battery_at = (sum(pocket["x"]) / 2, pocket["y"][0], pocket["floor_z"] - BATTERY_STEP["floor_z"] + (n - 1) * BATTERY_STACK_Z)
        battery = insert_part(root, "battery", "battery 1" if n == 1 else "battery 2 (inferred)", align(battery_at, X, Z), reuse=reuse)
        ports.append((battery, f"battery {n} lead", add(battery_at, (3.5, 52.5, 3.5))))   # the pack's plug; wiring is out of scope
    for n in (1, 2):
        steps.append((f"electronics set {n}", lambda n=n: electronics(n)))

    def joints():
        for occ in reuse.values():   # kept parts the build no longer places
            occ.deleteMe()
        parts_end(design)   # everything below is cheap and recreated by every build: no insert may follow this line
        for occ, name, p in ports:
            port(occ, name, p)
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
    steps.append(("joints", joints))
    progress = chunked(steps)

    moving = {o.name for o in root.occurrences if o.component.name in MOVING}
    for occ in root.occurrences:
        if occ.name not in moving:
            occ.isGrounded = True
    new_contacts = not design.contactSets.count   # one contact set per Stage (#20): moving parts, base, servos
    if new_contacts:
        contact_set(design, root, moving | {o.name for o in root.occurrences if o.component.name in ("PandT base", "pan servo")})

    os.makedirs(OUT, exist_ok=True)
    screenshots(app, root, OUT, "pan-tilt", {"top": (Z, Y), "side": (X, Z), "front": ((0, -1, 0), Z)})
    now = summary(root)
    diff = changes(saved_summary(root), now) + [f"imported {n}" for n in FRESH] + [f"removed {n}" for n in reuse] + (["contact set"] if new_contacts else [])
    if diff:
        root.attributes.add(*SUMMARY_ATTR, json.dumps(now, sort_keys=True))
        version = save(doc, f"{DOC}: rebuilt by model/pan_tilt.py", DOC, folder)
    else:
        version = doc.dataFile.versionNumber
    print("\n".join(progress))
    print(f"{DOC} v{version}: {root.occurrences.count} components, {root.joints.count} joints, {len(now['ports'])} ports,",
          "saved: " + "; ".join(diff) if diff else "unchanged")
    for j in root.joints:
        state = "ok" if j.healthState == adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState else j.errorOrWarningMessage
        print(f"  joint {j.name}: {state}")
    for o in root.occurrences:
        lo, hi = body_box(o)
        print("  %-42s x %6.1f..%6.1f  y %6.1f..%6.1f  z %6.1f..%6.1f" % (o.name, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    for name, p in now["ports"].items():
        print("  Port: %-36s (%.1f, %.1f, %.1f)" % (name, *p))
