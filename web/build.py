"""The web viewer (docs/adr/0008): its module (viewer.mjs) and framing (frame.mjs), one GLB per Stage and three.js with
its Draco decoder (sha384-checked), written into one folder that the site serves at viewer/ beside the viewer's page
(`make site`, docs/adr/0009). Each GLB is Blender's (web/glb.py): the Stage's parts in the pictures' look, one glTF clip
per motion of its baked trajectories (model/trajectories.py, `make trajectories`).
Usage: python -m web.build [out]   (default web/build; `make web`, Blender at $BLENDER)"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import vendored
from model import geometry as g
from model import stages, trajectories
from model.render import pictures, scene

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "glb.py")
MODULES = ("viewer.mjs", "frame.mjs")  # the viewer's own, served beside its page
GLBS = {doc: doc.removeprefix("noggin-") + ".glb" for doc in g.STAGES}
# three.js and the addons the page imports, and its Draco decoder (which DRACOLoader fetches): the site serves each from
# viewer/three/ as the npm package lays it out, fetched and checked against its sha384 here (vendored.py)
THREE_VERSION = "0.186.1"
THREE = {
    "build/three.module.js": "sha384-m8JoFX52V6NGv2usipnlLJKnJfL7IE8dbniPDDCSGSQv3Hm4n6PjfV6syVwfuoRc",
    "build/three.core.js": "sha384-mdKeCwPEcbDvzaxwhm+MVuLoMou+E7jQqrs4tmu/n8HBYPGI1kZt0MkJxlMR4zFM",
    "examples/jsm/controls/OrbitControls.js": "sha384-LSqANrugPGTgf0eYsQTloqKWy926dOOXo2iZ9y6wLMIDEQoU9AaCLJF1Vcc7oJXr",
    "examples/jsm/loaders/GLTFLoader.js": "sha384-jmhN0si8z6E7+h0t9KiwQ71oyrC3PhTpols1FXeN/vODuFa/L4bPIe9sLbOlhjq7",
    "examples/jsm/loaders/DRACOLoader.js": "sha384-6vtmq3WPvctEi9PzdgMxiAGLRIRtWQSrgL9Pxy26rq+Lu2s8qY/tRpq2Ked1wfLW",
    "examples/jsm/utils/BufferGeometryUtils.js": "sha384-Rm97j4mcjlLkGsYC2LX3nZG9VU2R8lgK0QE+DmBr4thue+H7J+SHm+68If2ZLBVg",  # noqa: E501
    "examples/jsm/utils/SkeletonUtils.js": "sha384-Pozn8j5+YFr3ak8Pm90ayqDrGYn/DV7vVs/YIIqzJhzeJT0LQksoS1fZQ5lfsYlw",
    "examples/jsm/lines/LineSegments2.js": "sha384-PodS3f4Ob57FETbMdk39akLP+W9/ScGjH/bBDerYOTsUt6dZc/i2Cbx7GW47tr5u",
    "examples/jsm/lines/LineSegmentsGeometry.js": "sha384-c1W/XWY1D45CznDDaXT87QmzD1YKNwYHvQegG8dXjCyf5ZaKzaWqEUwHZTYfBw64",  # noqa: E501
    "examples/jsm/lines/LineMaterial.js": "sha384-ijlzWpc1yHwTvvgLgdhkrcd5RQTKG/twLNwGumhKSFZHITTXMnzRdHIrw8fmvM3o",
    "examples/jsm/libs/draco/gltf/draco_wasm_wrapper.js": "sha384-mpx8Y6zmHZEVxr3r2cZhLFOKjJscyKOeHFqkK/LrOh8wC3HGDgGcy6fB37yQntEz",  # noqa: E501
    "examples/jsm/libs/draco/gltf/draco_decoder.wasm": "sha384-gJ9GFHPLIX0iGgdYbwba9tNN3lQhBPDtvr64s9owC5NUXLC9oXiSxHT3JqpqgqEY",  # noqa: E501
}


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


def three(out):
    for f, integrity in THREE.items():
        os.makedirs(os.path.dirname(path := os.path.join(out, "three", f)), exist_ok=True)
        open(path, "wb").write(vendored.fetch(f"three@{THREE_VERSION}/{f}", integrity))


def build(out):
    shutil.rmtree(out, ignore_errors=True)  # what an older build left (its page) would land on the site's
    os.makedirs(out)
    for f in MODULES:
        shutil.copy(os.path.join(HERE, f), out)
    three(out)
    for doc, name in GLBS.items():
        glb(doc, os.path.join(out, name))
        print(f"{name}: {os.path.getsize(os.path.join(out, name)) // 1024} KB")


if __name__ == "__main__":
    build(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "build")))
