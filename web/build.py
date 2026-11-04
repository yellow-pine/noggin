"""The web viewer's GLBs (docs/adr/0008): one per next Mech document, a Stage in a Skeleton shape (PUBLIC, #649, #642,
#819: per Shape alone, the viewer paints each Palette), written into one folder that
the site serves at viewer/ beside the viewer's page and its module (site/src/pages/viewer.astro, `just site`,
docs/adr/0009). Each GLB is Blender's (web/glb.py): the document's parts in the pictures' look, one glTF clip per motion
of its baked trajectories (model/trajectories.py, `just trajectories`): its gestures, Rest (#663) and the next hero
(#642), and each part's Explode offsets in its node's extras (explode, #811). Stage 3 also bare (BARE, #876): the
viewer's Skin shape none, the stills' bare look (model/render/pictures.py bare); and in each other Skin shape drawn
(geometry.DRESSED, #813).
Usage: python -m web.build [out [doc ... | next]]   (default web/build, every GLB; `just web`, Blender at $BLENDER)"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

from model import geometry as g
from model import trajectories
from model.render import pictures, scene

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "glb.py")
BARE = "-bare"  # a Stage 3 GLB without its Skin, its full bones on (#876): the viewer's Skin shape none
# what the site serves: the next Mech's Stages (#720, ADR 0019), Stage 3 bare too
PUBLIC = {doc: doc + ".glb" for doc in g.STAGES} | {doc + BARE: doc + BARE + ".glb" for doc in g.NEXT}
PUBLIC |= {doc: doc + ".glb" for doc in g.DRESSED}  # Stage 3 in each other Skin shape drawn (#813)


def document(name):
    """The document a GLB named so draws: its name less BARE."""
    return name.removesuffix(BARE)


def shown(name, by_part):
    """by_part ({part: x}) as the GLB named shows its document's parts: a bare one's as the stills' bare look does."""
    return pictures.bare(document(name), by_part) if name.endswith(BARE) else by_part


def glb(name, path):
    """Blender writes the GLB named (PUBLIC): every part keyed per frame of each of its document's motions."""
    doc = document(name)
    with tempfile.TemporaryDirectory() as tmp:
        parts = scene.export(doc, tmp)  # in its Theme's colours, a material per Colour group the viewer repaints (#819)
        for p in parts.values():
            p["ply"] = os.path.join(tmp, p["ply"])
        if name.endswith(BARE):
            pictures.full_bones(parts, tmp)
        motions = {
            m: [shown(name, {n: x.tolist() for n, x in frame.items()}) for frame in trajectories.poses(doc, m)]
            for m in trajectories.motions(doc)
        }
        rest = next(iter(motions.values()))[0]
        parts = {n: parts[n] for n in rest}  # the full bones in a bare GLB alone
        spec = {"parts": parts, "motions": motions, "rest": rest, "fps": trajectories.FPS, "out": path}
        spec["explode"] = explode(name)
        job = os.path.join(tmp, "job.json")
        json.dump(spec, open(job, "w"))
        r = subprocess.run([pictures.BLENDER, "-b", "-P", SCRIPT, "--", job], capture_output=True, text=True)
    if r.returncode or not os.path.isfile(path):
        sys.exit(f"Blender failed on {doc}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")


def explode(name):
    """{part: its offsets at Explode's levels past assembled (model/render/pictures.py offsets, #811), each in glTF's
    metres and Y-up, one after another}: what the page moves each part of the GLB named by (its node's extras)."""
    levels = [pictures.offsets(document(name), level) for level in (1, 2)]
    return shown(name, {n: [c / 1000 for o in levels for c in (o[n][0], o[n][2], -o[n][1])] for n in levels[0]})


def build(out, docs=()):
    """The GLBs named (PUBLIC's; every one by default, as "next") in out, emptied first."""
    names = [d for a in docs for d in (PUBLIC if a == pictures.NEXT else [a])]
    shutil.rmtree(out, ignore_errors=True)  # what an older build left would land on the site's
    os.makedirs(out)
    for name in names or PUBLIC:
        glb(name, os.path.join(out, PUBLIC[name]))
        print(f"{PUBLIC[name]}: {os.path.getsize(os.path.join(out, PUBLIC[name])) // 1024} KB")


if __name__ == "__main__":
    build(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "build")), sys.argv[2:])
