"""The web viewer's site (docs/adr/0008): the page and one GLB per Stage, written into one folder that the Pages
workflow deploys as is. Usage: python -m web.build [out]   (default web/build; `make web`)"""

import os
import shutil
import sys
import tempfile

import numpy as np
import trimesh
from trimesh.visual.color import hex_to_rgba
from trimesh.visual.material import PBRMaterial

from model import geometry as g
from model.engine import stages
from model.render import pictures, scene

HERE = os.path.dirname(os.path.abspath(__file__))
Y_UP = trimesh.transformations.rotation_matrix(-np.pi / 2, (1, 0, 0))  # the model is Z-up, glTF is Y-up


def glb(doc, path):
    """shortcut: the Stage's parts at rest in their colours, no gestures, no hero; Blender's GLBs replace it (#182)."""
    stage = stages.STAGES[doc]
    mats = pictures.metres({n: p.matrix for n, p in stage.parts.items()})
    out = trimesh.Scene()
    with tempfile.TemporaryDirectory() as tmp:
        for name, p in scene.export(stage, tmp).items():
            mesh = trimesh.load(os.path.join(tmp, p["ply"]), force="mesh")
            material = PBRMaterial(baseColorFactor=hex_to_rgba(p["colour"]))
            mesh.visual = trimesh.visual.TextureVisuals(material=material)
            out.add_geometry(mesh, node_name=name, transform=Y_UP @ np.array(mats[name]))
    out.export(path)


def build(out):
    os.makedirs(out, exist_ok=True)
    shutil.copy(os.path.join(HERE, "index.html"), out)
    for doc in g.STAGES:
        glb(doc, os.path.join(out, doc.removeprefix("noggin-") + ".glb"))


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "build"))
