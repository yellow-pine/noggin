"""Build or rebuild the Fusion design `noggin-mouth` (project Noggin): the 03-mouth printed parts the mouth Stage owns
(top and bottom jaw, plain; the jaws servo mount; the connector bar) from the parts library (`make model-parts`,
fusion_lib.insert_part) in the eyes frame, the jaw servo with its half-arm horn, and the saved `noggin-eyes` design
inserted as a grounded reference (main bracket v2 and the eyes belong to that Stage: one part, one document). Pivots as joints: the jaw hinge (bottom jaw on the top jaw's pins,
X through (29.5, -49.6, 8)), the horn on the servo (HORN_LIMITS mouth), the bar on the horn pin and the loop closed at
the jaw's pivot lug. Runs INSIDE Fusion: `make model-mouth`. Components placed from inferred positions carry an
"(inferred)" suffix: the horn seat, the bar plane and which bar hole is the jaw end (model/geometry.py)."""
# include: model/geometry.py
# include: model/fusion_lib.py
# include: model/contacts.py
import adsk.core, adsk.fusion, json, os

DOC = "noggin-mouth"
EYES_DOC = "noggin-eyes"
FULL = False   # `FULL=1 make model-mouth` flips this: empty the document and import everything again
REPO = os.path.expanduser("~/code/noggin")
OUT = os.path.join(REPO, "model", "build")

# (component name, library part): the designer exported the mouth parts in the assembled eyes frame (jaws closed).
# Plain jaws: the guide's first variant; the teeth jaws are the same build (guide p.1).
PARTS = [("top jaw", "top jaw plain"), ("bottom jaw", "bottom jaw plain"), ("jaws servo mount", "jaws servo mount")]
MOVING = {"bottom jaw", "jaw horn (inferred)", "connector bar (inferred)"}


def run(_context: str):
    app = adsk.core.Application.get()
    doc, design, folder = open_or_create(app, DOC, keep_parts=not FULL)
    root = design.rootComponent
    reuse = kept_parts(root)   # the build pops what it places; the rest is stale
    occs, steps = {}, []   # one chunk per part insert, then one for the joints (fusion_lib.chunked)
    def part(key, lib, name, matrix=None, referenced=False):
        steps.append((name, lambda: occs.__setitem__(key, insert_part(root, lib, name, matrix, reuse=reuse, referenced=referenced))))
    for name, lib in PARTS:
        part(name, lib, name)
    # The saved noggin-eyes design by reference at identity (both Stages share the eyes frame), grounded below;
    # re-inserted when noggin-eyes has a newer version (its fingerprint is the version).
    part("eyes", EYES_DOC, EYES_DOC, referenced=True)

    # Jaw servo from the measured mount-lug holes, horn at the inferred seat, the connector bar on the horn pin and the jaw lug.
    origin, tab_x, shaft = servo_frame("jaw")
    part("jaw servo", "servo", "jaw servo", align(origin, tab_x, [-c for c in shaft], SERVO_STEP["shaft"]))
    seat = PIVOTS["jaw_horn"]["point"]
    pin, lever = horn_pin("jaw")
    part("jaw horn (inferred)", "horn", "jaw horn (inferred)", align(seat, [p - q for p, q in zip(pin, seat)], shaft, HORN_STEP["hub"]))
    steps.append(("connector bar (inferred)", lambda: occs.__setitem__("connector bar (inferred)", link(root, "connector bar (inferred)", "jaws connector bar", pin, lever, X, reuse))))

    def joints():
        for occ in reuse.values():   # kept parts the build no longer places
            occ.deleteMe()
        parts_end(design)   # everything below is cheap and recreated by every build: no insert may follow this line
        # The top jaw is screwed to the bracket (4 screws); the bottom jaw clips onto its pins: the hinge is between the two jaws.
        pivot_joint(root, occs["bottom jaw"], occs["top jaw"], PIVOTS["jaw_hinge"]["point"], "X", "jaw hinge")
        lo, hi = HORN_LIMITS["mouth"]
        pivot_joint(root, occs["jaw horn (inferred)"], occs["jaw servo"], seat, "X", "jaw horn (inferred)", (lo - 90, hi - 90))
        pivot_joint(root, occs["connector bar (inferred)"], occs["jaw horn (inferred)"], pin, "X", "connector bar / horn pin (inferred)")
        close_loop(root, occs["connector bar (inferred)"], occs["bottom jaw"], lever, "X", "connector bar / jaw lug screw")
    steps.append(("joints", joints))
    progress = chunked(steps)
    eyes = occs["eyes"]

    moving = {o.name for o in root.occurrences if o.component.name in MOVING}
    for occ in root.occurrences:
        if occ.name not in moving:
            occ.isGrounded = True   # the top jaw, mount and servo are screwed to the bracket; the eyes reference is static here
    new_contacts = not design.contactSets.count   # one contact set per Stage (#20): moving parts, their mount and servo
    if new_contacts:   # the eyes reference is left out: untested whether a referenced occurrence can join a contact set
        contact_set(design, root, moving | {o.name for o in root.occurrences if o.component.name in ("top jaw", "jaws servo mount", "jaw servo")})

    os.makedirs(OUT, exist_ok=True)
    screenshots(app, root, OUT, "mouth", {"top": (Y, Z), "side": ((-1, 0, 0), Y), "front": ((0, 0, -1), Y)})
    now = summary(root)
    diff = changes(saved_summary(root), now) + [f"imported {n}" for n in FRESH] + [f"removed {n}" for n in reuse] + (["contact set"] if new_contacts else [])
    if diff:
        root.attributes.add(*SUMMARY_ATTR, json.dumps(now, sort_keys=True))
        version = save(doc, f"{DOC}: rebuilt by model/mouth.py", DOC, folder)
    else:
        version = doc.dataFile.versionNumber
    print("\n".join(progress))
    print(f"{DOC} v{version}: {root.occurrences.count} components, {root.joints.count} joints,",
          "saved: " + "; ".join(diff) if diff else "unchanged")
    for j in root.joints:
        state = "ok" if j.healthState == adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState else j.errorOrWarningMessage
        print(f"  joint {j.name}: {state}")
    for o in root.occurrences:
        lo, hi = body_box(o)
        print("  %-42s x %6.1f..%6.1f  y %6.1f..%6.1f  z %6.1f..%6.1f" % (o.name, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    print(f"  reference: {eyes.name} ({eyes.childOccurrences.count} eyes parts, grounded)")
