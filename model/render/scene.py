"""A Stage for Blender: every part's world matrix at the eye program's joint degrees (model/traces.py frames), and
each part's mesh written once in its own frame with its colour (geometry.SPOOLS; electronics and servos in greys)."""

import os

import trimesh

from model import geometry as g
from model.engine import run, stages

HORNS = {
    "l_lid": "L lid horn",
    "l_eye": "L eye horn",
    "r_lid": "R lid horn",
    "r_eye": "R eye horn",
}

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
        if part.clip:  # as meshes.load: the flexible leads are cut off
            axis, cut = part.clip
            v = mesh.vertices
            mesh = trimesh.Trimesh(v, mesh.faces[(v[mesh.faces][:, :, "xyz".index(axis)] <= cut + 0.1).all(axis=1)])
        mesh.apply_scale(0.001)
        ply = f"{i:02d}.ply"
        mesh.export(os.path.join(out, ply))
        manifest[name] = {"ply": ply, "colour": colour(part.file)}
    return manifest


def pose(stage, joints):
    """{part: 4x4 world mm} with each servo's horn at joints[servo] degrees; servos the Stage lacks are skipped.
    The eye chains are disjoint, so each horn's own pose places its own chain."""
    mats = {n: p.matrix for n, p in stage.parts.items()}
    for servo, deg in joints.items():
        horn = HORNS[servo]
        if horn in stage.horns and deg:
            posed = stages.pose(stage, horn, deg).parts
            mats.update({n: posed[n] for n in run.chain(stage.horns[horn])})
    return mats
