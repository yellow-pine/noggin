"""PROTOTYPE (throwaway, #47 style pick): pose noggin-stage1 at the eureka peak with the engine and write one PLY per
part (world mm) plus manifest.json {ply: hex colour} for model/render/proto_blender.py.
Usage: .venv/bin/python -m model.render.proto_export <out_dir>"""

import json
import os
import sys

import numpy as np
import trimesh

from model import geometry as g
from model import traces
from model.engine import run, stages

HORNS = {"l_lid": "L lid horn (inferred)", "l_eye": "L eye horn (inferred)",
         "r_lid": "R lid horn (inferred)", "r_eye": "R eye horn (inferred)"}  # fmt: skip
GREYS = {
    "servo": "#7E8287",
    "horn": "#D4D6D9",
    "core": "#3A3D42",
    "receiver": "#55595E",
    "switch": "#55595E",
    "battery": "#9A9EA3",
}  # fmt: skip  electronics/servos: neutral greys, darker for boards


def peak():
    """The eureka frame with the lids widest and the eyes furthest aside (the replay's joint degrees)."""
    frames = traces.record("eureka")
    return max(frames, key=lambda f: f["l_lid"] + abs(f["l_eye"]))


def colour(file):
    stem = os.path.basename(file)[:-4]
    if file.startswith(stages.STEPS):
        return GREYS[stem]
    return g.SPOOLS[next(v[0] for k, v in g.PRINTED.items() if k.split(" (")[0] == stem)]


def main(out):
    os.makedirs(out, exist_ok=True)
    stage = stages.STAGES["noggin-stage1"]
    frame = peak()
    mats = {n: p.matrix for n, p in stage.parts.items()}
    for servo, h in HORNS.items():  # the four eye chains are disjoint: each horn's pose moves only its own chain
        posed = stages.pose(stage, h, frame[servo]).parts
        mats.update({n: posed[n] for n in run.chain(stage.horns[h])})
    manifest = {}
    for i, (name, part) in enumerate(stage.parts.items()):
        mesh = trimesh.load(part.file, force="mesh")  # merges duplicate STL vertices, so normals can be smoothed
        if part.clip:  # as meshes.load: the flexible leads are cut off
            axis, cut = part.clip
            f = mesh.faces[(mesh.vertices[mesh.faces][:, :, "xyz".index(axis)] <= cut + 0.1).all(axis=1)]
            mesh = trimesh.Trimesh(mesh.vertices, f)
        mesh.apply_transform(mats[name])
        if np.linalg.det(mats[name][:3, :3]) < 0:
            mesh.invert()
        ply = f"{i:02d}.ply"
        mesh.export(os.path.join(out, ply))
        manifest[ply] = {"name": name, "colour": colour(part.file)}
    json.dump({"frame": frame, "parts": manifest}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(f"{len(manifest)} parts at eureka peak {frame} -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
