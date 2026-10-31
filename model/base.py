"""Build or rebuild the Fusion design `noggin-base` (project Noggin): the PandT base plate in the PT frame with electronics
set 1 (receiver shield 1 with its Core on the front standoffs, switch board 1, battery 1) and Ports on its connectors.
What the desk build sits on and every Stage document (model/stage.py) inserts by reference; all grounded, no joints.
Runs INSIDE Fusion: `make model-base`. Reuse as in eyes.py (fingerprints, fusion_lib)."""
# include: model/geometry.py
# include: model/fusion_lib.py
# include: model/electronics.py
import adsk.core, adsk.fusion, json, os

DOC = "noggin-base"
FULL = False   # `FULL=1 make model-base` flips this: empty the document and import everything again
REPO = os.path.expanduser("~/code/noggin")
OUT = os.path.join(REPO, "model", "build")


def run(_context: str):
    app = adsk.core.Application.get()
    doc, design, folder = open_or_create(app, DOC, keep_parts=not FULL)
    root = design.rootComponent
    reuse = kept_parts(root)   # the build pops what it places; the rest is stale
    ports = []   # (occurrence, Port name, world point), placed after parts_end
    def finish():
        for occ in reuse.values():   # kept parts the build no longer places
            occ.deleteMe()
        parts_end(design)   # everything below is cheap and recreated by every build: no insert may follow this line
        for occ, name, p in ports:
            port(occ, name, p)
    progress = chunked([("PandT base", lambda: insert_part(root, "PandT base", "PandT base", reuse=reuse)),
                        ("electronics set 1", lambda: electronics(root, 1, reuse, ports)), ("ports", finish)])
    for occ in root.occurrences:
        occ.isGrounded = True

    os.makedirs(OUT, exist_ok=True)
    screenshots(app, root, OUT, "base", {"top": (Z, Y), "side": (X, Z), "front": ((0, -1, 0), Z)})
    now = summary(root)
    diff = changes(saved_summary(root), now) + [f"imported {n}" for n in FRESH] + [f"removed {n}" for n in reuse]
    if diff:
        root.attributes.add(*SUMMARY_ATTR, json.dumps(now, sort_keys=True))
        version = save(doc, f"{DOC}: rebuilt by model/base.py", DOC, folder)
    else:
        version = doc.dataFile.versionNumber
    print("\n".join(progress))
    print(f"{DOC} v{version}: {root.occurrences.count} components, {len(now['ports'])} ports,",
          "saved: " + "; ".join(diff) if diff else "unchanged")
    for o in root.occurrences:
        lo, hi = body_box(o)
        print("  %-42s x %6.1f..%6.1f  y %6.1f..%6.1f  z %6.1f..%6.1f" % (o.name, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    for name, p in now["ports"].items():
        print("  Port: %-36s (%.1f, %.1f, %.1f)" % (name, *p))
