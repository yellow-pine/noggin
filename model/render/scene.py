"""A Stage for Blender: each part's mesh written once in its own frame with its colour (geometry.SPOOLS; electronics and
servos in greys), and the servos' horns by name (HORNS), which MuJoCo drives (model/trajectories.py)."""

import os

import trimesh

from model import geometry as g
from model import stages

HORNS = {
    "l_lid": "L lid horn",
    "l_eye": "L eye horn",
    "r_lid": "R lid horn",
    "r_eye": "R eye horn",
    "mouth": "jaw horn",
    "tilt": "tilt horn",
    "rotate": "pan horn",
}  # inner chains first: the tilt carries the eyes and mouth, the pan carries the tilt

GREYS = {
    "servo": "#7E8287",
    "horn": "#D4D6D9",
    "core": "#3A3D42",
    "receiver": "#55595E",
    "switch": "#55595E",
    "battery": "#9A9EA3",
}  # the hardware envelopes (by file name): neutral greys, darker for the boards


def colour(file):
    stem = stages.stem(file)
    if stem in GREYS:
        return GREYS[stem]
    return g.SPOOLS[next(spool for k, (spool, _) in g.PRINTED.items() if k.split(" (")[0] == stem)]


def export(stage, out):
    """Each part's mesh in its own frame, in metres, as out/NN.ply; returns {part: {"ply", "colour"}}."""
    manifest = {}
    for i, (name, part) in enumerate(stage.parts.items()):
        mesh = trimesh.load(part.file, force="mesh")  # merges the STL's repeated vertices: normals can be smoothed
        if part.clip:  # as mjcf._mesh: the flexible leads are cut off
            axis, cut = part.clip
            v = mesh.vertices
            mesh = trimesh.Trimesh(v, mesh.faces[(v[mesh.faces][:, :, "xyz".index(axis)] <= cut + 0.1).all(axis=1)])
        mesh.apply_scale(0.001)
        ply = f"{i:02d}.ply"
        mesh.export(os.path.join(out, ply))
        manifest[name] = {"ply": ply, "colour": colour(part.file)}
    return manifest
