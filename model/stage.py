"""Build or rebuild a Stage document (project Noggin): the sub-assembly designs STAGES[DOC] lists (model/geometry.py),
each inserted ONCE by reference at its frame in the PT frame, the base grounded and the rest held by as-built rigid
joints as the real build clamps them: the stack screwed on the base plate, the bracket v2 stem in STEM_IN[DOC] (the
pan recess of the base on the desk build, the tilt arm window on the neck; depth inferred), the top jaw screwed on the
bracket. noggin-stage1 = base + eyes, stage2 = base + stack + eyes, stage3 = stage2 + mouth (the full Mech). The mouth's
own context copy of the eyes (ADR 0004) is hidden so every physical part shows once; the component count printed at the
end proves it. Runs INSIDE Fusion: `make model-stage1|2|3` (the Makefile substitutes DOC). Each sub-assembly's
fingerprint is its saved version plus the frame, so a rebuilt sub-assembly is re-inserted, an unchanged one kept."""
# include: model/geometry.py
# include: model/fusion_lib.py
import adsk.core, adsk.fusion, json, os
from collections import Counter

DOC = "noggin-stage1"
FULL = False   # `FULL=1 make model-stage2` flips this: empty the document and insert everything again
REPO = os.path.expanduser("~/code/noggin")
OUT = os.path.join(REPO, "model", "build")


def run(_context: str):
    app = adsk.core.Application.get()
    _PARTS.clear()   # fresh DataFiles: a sub-assembly saved earlier in this Fusion session is newer than the cached one
    doc, design, folder = open_or_create(app, DOC, keep_parts=not FULL)
    root = design.rootComponent
    reuse = kept_parts(root)   # the build pops what it places; the rest is stale
    occs, steps = {}, []   # one chunk per sub-assembly insert, then one for the joints (fusion_lib.chunked)
    for name, frame in STAGES[DOC].items():
        steps.append((name, lambda name=name, frame=frame: occs.__setitem__(name, insert_part(root, name, name, align(*frame), reuse=reuse, referenced=True))))

    def joints():
        for occ in reuse.values():   # kept sub-assemblies the Stage no longer inserts
            occ.deleteMe()
        parts_end(design)   # everything below is cheap and recreated by every build: no insert may follow this line
        occs["noggin-base"].isGrounded = True
        if "noggin-stack" in occs:
            rigid(root, occs["noggin-stack"], occs["noggin-base"], "stack on the base plate")
        holder = next(h for o in occs.values() if (h := descendant(o, STEM_IN[DOC])))
        rigid(root, occs["noggin-eyes"], holder, f"bracket stem in the {STEM_IN[DOC]} (depth inferred)")
        if "noggin-mouth" in occs:
            rigid(root, occs["noggin-mouth"], occs["noggin-eyes"], "top jaw on the bracket")
            descendant(occs["noggin-mouth"], "noggin-eyes").isLightBulbOn = False   # context copy; the eyes reference above is the one
    steps.append(("joints", joints))
    progress = chunked(steps)

    os.makedirs(OUT, exist_ok=True)
    screenshots(app, root, OUT, DOC[len("noggin-"):], {"top": (Z, Y), "side": (X, Z), "front": ((0, -1, 0), Z)})
    now = json.loads(json.dumps({"joints": {j.name: [j.occurrenceOne.name, j.occurrenceTwo.name] for j in root.asBuiltJoints},
                                 "frames": {o.name: [round(c, 4) for c in o.transform2.asArray()] for o in root.occurrences}}))
    diff = changes(saved_summary(root), now) + [f"inserted {n}" for n in FRESH] + [f"removed {n}" for n in reuse]
    if diff:
        root.attributes.add(*SUMMARY_ATTR, json.dumps(now, sort_keys=True))
        version = save(doc, f"{DOC}: rebuilt by model/stage.py", DOC, folder)
    else:
        version = doc.dataFile.versionNumber
    print("\n".join(progress))
    # Every physical part once: the visible children of the sub-assembly references, by component name.
    shown, hidden = [], []
    for occ in root.occurrences:
        for child in occ.childOccurrences:
            (shown if child.isLightBulbOn else hidden).append(child.component.name)
    dups = sorted(n for n, k in Counter(shown).items() if k > 1)
    print(f"{DOC} v{version}: {root.occurrences.count} sub-assemblies ({', '.join(f'{o.name}@v{part_file(app, o.component.name).versionNumber}' for o in root.occurrences)}),",
          f"{len(shown)} parts, duplicates: {dups or 'none'}, hidden context: {hidden or 'none'},", "saved: " + "; ".join(diff) if diff else "unchanged")
    for j in root.asBuiltJoints:   # as-built joints carry no health state; a bad pair raises at add
        print(f"  joint {j.name}: {j.occurrenceOne.name} -> {j.occurrenceTwo.name}" + (" (suppressed)" if j.isSuppressed else ""))
    for occ in root.occurrences:
        lo, hi = body_box(occ)
        print("  %-42s x %6.1f..%6.1f  y %6.1f..%6.1f  z %6.1f..%6.1f" % (occ.name, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    for name in ("main bracket v2", "L eyeball", STEM_IN[DOC]):   # the stem and eye centres against STAGES
        occ = next(h for o in root.occurrences if (h := descendant(o, name)))
        lo, hi = body_box(occ)
        print("    %-40s x %6.1f..%6.1f  y %6.1f..%6.1f  z %6.1f..%6.1f" % (occ.name, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
