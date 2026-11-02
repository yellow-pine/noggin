"""The web viewer's GLBs (docs/adr/0008): one per Stage and the next Mech's (PUBLIC, the one the site serves, #649),
written into one folder that the site serves at viewer/ beside the viewer's page and its module
(site/src/pages/viewer.astro, `just site`, docs/adr/0009). Each GLB is Blender's (web/glb.py): the Stage's parts in the
pictures' look, one glTF clip per motion of its baked trajectories (model/trajectories.py, `just trajectories`); the
hero's Stage's also the hero picture's camera (model/render/pictures.py hero_camera). The next Mech's plays its gestures
and Rest (#663).
Usage: python -m web.build [out [doc ...]]   (default web/build, every GLB; `just web`, Blender at $BLENDER)"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

from model import geometry as g
from model import stages, trajectories
from model.render import pictures, scene

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "glb.py")
GLBS = {doc: doc.removeprefix("noggin-") + ".glb" for doc in g.STAGES | g.NEXT}
PUBLIC = {doc: GLBS[doc] for doc in g.NEXT}  # what the site serves: the next Mech alone (docs/adr/0019)


def glb(doc, path):
    """Blender writes the Stage's GLB: every part keyed per frame of each of its motions."""
    with tempfile.TemporaryDirectory() as tmp:
        parts = scene.export(stages.STAGES[doc], tmp)
        for p in parts.values():
            p["ply"] = os.path.join(tmp, p["ply"])
        motions = {
            m: [{n: x.tolist() for n, x in frame.items()} for frame in trajectories.poses(doc, m)]
            for m in trajectories.motions(doc)
        }
        rest = next(iter(motions.values()))[0]
        spec = {"parts": parts, "motions": motions, "rest": rest, "fps": trajectories.FPS, "out": path}
        if doc == pictures.HERO_STAGE:  # the hero picture's camera, for the page whose poster it is (#597)
            cam = pictures.hero_camera(pictures.hulls(parts))
            spec["camera"] = {"matrix": cam.matrix.tolist(), "lens": cam.lens, "size": pictures.HERO_SIZE}
        job = os.path.join(tmp, "job.json")
        json.dump(spec, open(job, "w"))
        r = subprocess.run([pictures.BLENDER, "-b", "-P", SCRIPT, "--", job], capture_output=True, text=True)
    if r.returncode or not os.path.isfile(path):
        sys.exit(f"Blender failed on {doc}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")


def build(out, docs=()):
    shutil.rmtree(out, ignore_errors=True)  # what an older build left would land on the site's
    os.makedirs(out)
    for doc in docs or GLBS:
        glb(doc, os.path.join(out, GLBS[doc]))
        print(f"{GLBS[doc]}: {os.path.getsize(os.path.join(out, GLBS[doc])) // 1024} KB")


if __name__ == "__main__":
    build(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "build")), sys.argv[2:])
