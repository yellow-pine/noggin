"""Build or rebuild the Fusion design `noggin-eyes` (project Noggin): the parts the eyes sub-assembly owns (ADR 0004),
main bracket v2, the eye mech printed parts, the four servos with their horns, placed from the parts library
(`make model-parts`, fusion_lib.insert_part), and the Pivots as joints. The PandT base and the electronics live in
noggin-base; the Stage documents (model/stage.py) put the bracket on it. Runs INSIDE Fusion: `make model-eyes`.
Numbers live in model/geometry.py; this file only places things. Parts whose library version and placement are
unchanged since the saved version are reused (fingerprints, fusion_lib); joints are recreated, and
a new version is saved only when something differs from the last one."""

# include: model/geometry.py
# include: model/fusion_lib.py
# include: model/contacts.py
import json

import adsk.core
import adsk.fusion

DOC = "noggin-eyes"
FULL = False  # `FULL=1 make model-eyes` flips this: empty the document and import everything again
AXIS = {X: "X", Y: "Y", Z: "Z"}


def run(_context: str):
    app = adsk.core.Application.get()
    doc, design, folder = open_or_create(app, DOC, keep_parts=not FULL)
    root = design.rootComponent
    reuse = kept_parts(root)  # the build pops what it places; the rest is stale
    occs, steps = {}, []  # one chunk per part insert, then one for the joints (fusion_lib.chunked)

    def part(key, lib, name, matrix=None, referenced=False):
        steps.append(
            (
                name,
                lambda: occs.__setitem__(key, insert_part(root, lib, name, matrix, reuse=reuse, referenced=referenced)),
            )
        )

    for name, lib, dx in EYES_PARTS:
        part(name, lib, name, align((dx, 0, 0)))
    part("main bracket", "main bracket v2", "main bracket v2")

    # Servos and horns from the tab holes and the horn pivots (docs/research/2026-10-31-shafts.md); the horn's spline
    # side on the seat, its arm outermost. A Port at each servo's cable exit (SERVO_STEP lead), placed after parts_end.
    leads = {}
    for key in EYES_SERVOS:
        origin, tab_x, shaft = servo_frame(key)
        label = key.upper()[0] + (" lid" if "lid" in key else " eye")
        m = align(origin, tab_x, [-c for c in shaft], SERVO_STEP["shaft"])
        part(key + "_servo", "servo", f"{label} servo", m)
        leads[key + "_servo"] = (f"{label} servo lead", at(m, SERVO_STEP["lead"]))
        arm = Y if "lid" in key else (-1, 0, 0) if key == "l_eye" else X  # single arm: toward the bar pin
        seat = add(origin, tuple(SERVO_STEP["horn_seat"] * c for c in shaft))
        outer = add(seat, tuple(HORN_STEP["height"] * c for c in shaft))
        part(key + "_horn", "horn", f"{label} horn", align(outer, arm, [-c for c in shaft], HORN_STEP["hub"]))

    # Linkage parts (local-frame STLs) at their pins. The pins are also the joint points below.
    pins = {}
    for s in "LR":
        lid_horn = PIVOTS[s.lower() + "_lid_horn"]["point"]
        normal = (1, 0, 0) if s == "L" else (-1, 0, 0)  # inboard: the crank's step toward the lid ear
        for key, stl in (("eyelid_bar", "eyelid bar"), ("eyelid_crank", "eyelid bar crank")):
            spec = LID_LINKS[key]
            hx, lx = (side(s, (x, 0, 0))[0] for x in spec["x"])
            horn_pin = (hx, lid_horn[1] + HORN_STEP["pin"], lid_horn[2])
            lid_pin = (lx,) + side(s, LID_PINS[spec["lid"]])[1:]
            name = f"{s} {stl}"
            steps.append(
                (
                    name,
                    lambda name=name, stl=stl, a=horn_pin, b=lid_pin, n=normal: occs.__setitem__(
                        name, link(root, name, stl, a, b, n, reuse)
                    ),
                )
            )
            pins[s, key] = horn_pin, lid_pin

    def joints():
        for occ in reuse.values():  # kept parts the build no longer places
            occ.deleteMe()
        parts_end(design)  # everything below is cheap and recreated by every build: no insert may follow this line
        for key, (name, p) in leads.items():
            port(occs[key], name, p)
        occs["main bracket"].isGrounded = True
        for s in "LR":
            eye = PIVOTS[s.lower() + "_eye"]["point"]
            for key, stl in (("eyelid_bar", "eyelid bar"), ("eyelid_crank", "eyelid bar crank")):
                spec = LID_LINKS[key]
                horn_pin, lid_pin = pins[s, key]
                name = f"{s} {stl}"
                lid = occs[f"{s} {spec['lid']} lid"]
                pivot_joint(root, occs[name], occs[f"{s.lower()}_lid_horn"], horn_pin, "X", f"{s} {stl} / arm pin")
                close_loop(root, occs[name], lid, lid_pin, "X", f"{s} {stl} / {spec['lid']} lid pin")
            pivot_joint(root, occs[f"{s} inside lid"], occs["main bracket"], eye, "X", f"{s} inside lid pivot")
            pivot_joint(root, occs[f"{s} outside lid"], occs["main bracket"], eye, "X", f"{s} outside lid pivot")
            pivot_joint(root, occs[f"{s} eyeball"], occs["main bracket"], eye, "Y", f"{s} eyeball pivot")
            for part, axis in (("lid", "X"), ("eye", "Y")):
                lo, hi = HORN_LIMITS[f"{s.lower()}_{part}"]
                pivot_joint(
                    root,
                    occs[f"{s.lower()}_{part}_horn"],
                    occs[f"{s.lower()}_{part}_servo"],
                    PIVOTS[f"{s.lower()}_{part}_horn"]["point"],
                    axis,
                    f"{s} {part} horn",
                    (lo - 90, hi - 90),
                )
            arm_end, eye_end = (side(s, p) for p in EYEBALL_BAR_PINS)
            pivot_joint(
                root,
                occs[f"{s} eyeball bar"],
                occs[f"{s.lower()}_eye_horn"],
                arm_end,
                "Y",
                f"{s} eyeball bar / arm pin",
            )
            close_loop(
                root, occs[f"{s} eyeball bar"], occs[f"{s} eyeball"], eye_end, "Y", f"{s} eyeball bar / eyeball pin"
            )
            group = adsk.core.ObjectCollection.create()
            group.add(occs[f"{s} eyeball"])
            group.add(occs[f"{s} pupil"])
            root.rigidGroups.add(group, True)

    steps.append(("joints", joints))
    progress = chunked(steps)

    moving = {
        o.name
        for o in root.occurrences
        if "servo" not in o.component.name
        and any(w in o.component.name for w in ("lid", "eyeball", "pupil", "horn", "bar", "crank"))
    }
    for occ in root.occurrences:
        if occ.name not in moving:
            occ.isGrounded = True
    new_contacts = not design.contactSets.count  # one contact set per sub-assembly (#20): moving parts, bracket, servos
    if new_contacts:
        contact_set(
            design,
            root,
            moving
            | {
                o.name
                for o in root.occurrences
                if o.component.name == "main bracket v2" or o.component.name.endswith(" servo")
            },
        )

    now = summary(root)
    diff = (
        changes(saved_summary(root), now)
        + [f"imported {n}" for n in FRESH]
        + [f"removed {n}" for n in reuse]
        + (["contact set"] if new_contacts else [])
    )
    if diff:
        root.attributes.add(*SUMMARY_ATTR, json.dumps(now, sort_keys=True))
        version = save(doc, f"{DOC}: rebuilt by model/eyes.py", DOC, folder)
    else:
        version = doc.dataFile.versionNumber
    print("\n".join(progress))
    print(
        f"{DOC} v{version}: {root.occurrences.count} components, {root.joints.count} joints,",
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
