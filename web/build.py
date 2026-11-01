"""The web viewer's site (docs/adr/0008): the page and one GLB per Stage, written into one folder that the Pages
workflow deploys as is. Each GLB is Blender's (web/glb.py): the Stage's parts in the pictures' look, one glTF clip
per motion of its baked trajectories (model/trajectories.py, `make trajectories`).
Usage: python -m web.build [out]   (default web/build; `make web`, Blender at $BLENDER)"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

from model import geometry as g
from model import trajectories
from model.engine import stages
from model.render import pictures, scene

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "glb.py")
GLBS = {doc: doc.removeprefix("noggin-") + ".glb" for doc in g.STAGES}


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
        job = os.path.join(tmp, "job.json")
        json.dump({"parts": parts, "motions": motions, "fps": trajectories.FPS, "out": path}, open(job, "w"))
        r = subprocess.run([pictures.BLENDER, "-b", "-P", SCRIPT, "--", job], capture_output=True, text=True)
    if r.returncode or not os.path.isfile(path):
        sys.exit(f"Blender failed on {doc}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")


def build(out):
    os.makedirs(out, exist_ok=True)
    shutil.copy(os.path.join(HERE, "index.html"), out)
    for doc, name in GLBS.items():
        glb(doc, os.path.join(out, name))
        print(f"{name}: {os.path.getsize(os.path.join(out, name)) // 1024} KB")


if __name__ == "__main__":
    build(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "build")))
