"""Build or rebuild the Fusion design `noggin-stack` (project Noggin): the pan-tilt neck in the PT frame (pan axis Z through
the origin, tilt axis X at (0,-13,33.4)): bearing block, pan base, upright v2, tilt arm, the pan servo mounts and wire holder
from the parts library (`make model-parts`, fusion_lib.insert_part), the tilt and pan servos with their half-arm horns, the
tilt and pan bars closing the two loops, electronics set 2 (receiver shield 2 with its Core on the back standoffs, switch
board 2, battery 2) with Ports, and the Pivots as joints. The PandT base plate it sits on is `noggin-base`; the Stage
documents (model/stage.py) insert both by reference. Runs INSIDE Fusion: `make model-stack`. Components whose position
is inferred rather than measured carry an "(inferred)" suffix. Numbers live in model/geometry.py; reuse as in eyes.py."""

# include: model/geometry.py
# include: model/fusion_lib.py
# include: model/contacts.py
# include: model/electronics.py
import json
import os

import adsk.core
import adsk.fusion

DOC = "noggin-stack"
FULL = False  # `FULL=1 make model-stack` flips this: empty the document and import everything again
REPO = os.path.expanduser("~/code/noggin")
OUT = os.path.join(REPO, "model", "build")

# (component name, library part, z shift mm): the designer exported these in the assembled PT frame, except the tilt arm,
# still at the v1 height (upright v2 raised the pivot 5 mm, docs/research/2026-10-31-model.md).
PARTS = [
    ("bearing block", "PandT bearing block", 0),
    ("pan base", "PandT pan base", 0),
    ("upright v2", "PandT upright v2", 0),
    ("tilt arm", "PandT tilt arm", TILT_ARM_SHIFT_Z),
    ("servo mount plain", "PandT servo mount plain", 0),
    ("servo mount cutout", "PandT servo mount cutout", 0),
    ("wire holder", "PandT wire holder", 0),
]
MOVING = {
    "pan base",
    "upright v2",
    "tilt servo",
    "tilt arm",
    "tilt horn (inferred)",
    "tilt bar (inferred)",
    "pan horn (inferred)",
    "pan bar (inferred)",
}
BAR_STL = {"tilt": "tilt bar", "pan": "PandT bar"}
LEVER = {"tilt": "tilt arm", "pan": "upright v2"}
HORN_RANGE = {"tilt": "tilt", "pan": "rotate"}  # HORN_LIMITS keys: the remote config names the pan servo "rotate"


def run(_context: str):
    app = adsk.core.Application.get()
    doc, design, folder = open_or_create(app, DOC, keep_parts=not FULL)
    root = design.rootComponent
    reuse = kept_parts(root)  # the build pops what it places; the rest is stale
    occs, steps = (
        {},
        [],
    )  # one chunk per part insert (per electronics set), then one for the joints (fusion_lib.chunked)

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
        part(
            f"{key} horn (inferred)",
            "horn",
            f"{key} horn (inferred)",
            align(seat, [p - q for p, q in zip(pin, seat)], shaft, HORN_STEP["hub"]),
        )
        name = f"{key} bar (inferred)"
        steps.append(
            (
                name,
                lambda name=name, k=key, a=pin, b=lever: occs.__setitem__(
                    name, link(root, name, BAR_STL[k], a, b, PIVOTS[k + "_horn"]["axis"], reuse)
                ),
            )
        )
        pins[key] = pin, lever

    ports = []  # (occurrence, Port name, world point), placed after parts_end
    steps.append(("electronics set 2", lambda: electronics(root, 2, reuse, ports)))

    def joints():
        for occ in reuse.values():  # kept parts the build no longer places
            occ.deleteMe()
        parts_end(design)  # everything below is cheap and recreated by every build: no insert may follow this line
        for occ, name, p in ports:
            port(occ, name, p)
        # The pan base turns on the bearing block (18 x 5.5 in the base recess and the pan base recess, zero clearance by design)
        pivot_joint(root, occs["pan base"], occs["bearing block"], (0.0, 0.0, 3.5), "Z", "pan pivot")
        pivot_joint(root, occs["tilt arm"], occs["upright v2"], PIVOTS["tilt"]["point"], "X", "tilt pivot")
        for key in ("tilt", "pan"):
            axis = "X" if key == "tilt" else "Z"
            lo, hi = HORN_LIMITS[HORN_RANGE[key]]
            pivot_joint(
                root,
                occs[f"{key} horn (inferred)"],
                occs[f"{key} servo"],
                PIVOTS[key + "_horn"]["point"],
                axis,
                f"{key} horn (inferred)",
                (lo - 90, hi - 90),
            )
            pin, lever = pins[key]
            pivot_joint(
                root,
                occs[f"{key} bar (inferred)"],
                occs[f"{key} horn (inferred)"],
                pin,
                axis,
                f"{key} bar / arm pin (inferred)",
            )
            close_loop(root, occs[f"{key} bar (inferred)"], occs[LEVER[key]], lever, axis, f"{key} bar / lever screw")
        group = adsk.core.ObjectCollection.create()  # screwed together: the pan mechanism turns as one
        for name in ("pan base", "upright v2", "tilt servo"):
            group.add(occs[name])
        root.rigidGroups.add(group, True)

    steps.append(("joints", joints))
    progress = chunked(steps)

    moving = {o.name for o in root.occurrences if o.component.name in MOVING}
    for occ in root.occurrences:
        if occ.name not in moving:
            occ.isGrounded = True
    new_contacts = not design.contactSets.count  # one contact set per design (#20): moving parts, the pan servo
    if new_contacts:
        contact_set(design, root, moving | {o.name for o in root.occurrences if o.component.name in ("pan servo",)})

    os.makedirs(OUT, exist_ok=True)
    screenshots(app, root, OUT, "stack", {"top": (Z, Y), "side": (X, Z), "front": ((0, -1, 0), Z)})
    now = summary(root)
    diff = (
        changes(saved_summary(root), now)
        + [f"imported {n}" for n in FRESH]
        + [f"removed {n}" for n in reuse]
        + (["contact set"] if new_contacts else [])
    )
    if diff:
        root.attributes.add(*SUMMARY_ATTR, json.dumps(now, sort_keys=True))
        version = save(doc, f"{DOC}: rebuilt by model/stack.py", DOC, folder)
    else:
        version = doc.dataFile.versionNumber
    print("\n".join(progress))
    print(
        f"{DOC} v{version}: {root.occurrences.count} components, {root.joints.count} joints, {len(now['ports'])} ports,",
        "saved: " + "; ".join(diff) if diff else "unchanged",
    )
    for j in root.joints:
        state = (
            "ok"
            if j.healthState == adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState
            else j.errorOrWarningMessage
        )
        print(f"  joint {j.name}: {state}")
    for o in root.occurrences:
        lo, hi = body_box(o)
        print(
            "  %-42s x %6.1f..%6.1f  y %6.1f..%6.1f  z %6.1f..%6.1f"
            % (o.name, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])
        )
    for name, p in now["ports"].items():
        print("  Port: %-36s (%.1f, %.1f, %.1f)" % (name, *p))
