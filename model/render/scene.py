"""A document for Blender: each part's mesh written once in its own frame with its Colour group (a hardware envelope's
file name) and colour (the group's filament in the document's Theme, or the one given, geometry.THEMES; electronics and
servos in greys), and the servos' horns by name (HORNS), which MuJoCo drives (model/trajectories.py)."""

import os

import trimesh

from model import geometry as g
from model import stages

HORNS = {"mouth": "jaw horn", "tilt": "tilt horn", "rotate": "pan horn"}  # the neck Core's servos' horns (the hero's)

GREYS = {
    "servo": "#7E8287",
    "horn": "#D4D6D9",
    "core": "#3A3D42",
    "receiver": "#55595E",
    "switch": "#55595E",
    "battery": "#9A9EA3",
}  # the hardware envelopes (by file name): neutral greys, darker for the boards


def colour(file, theme):
    """A part's hex: its Colour group's filament in the Theme (geometry.filament), a hardware envelope's grey."""
    stem = stages.stem(file)
    return GREYS[stem] if stem in GREYS else g.filament(g.PRINTED[stem][0], theme)[3]


def export(doc, out, theme=None):
    """Each part of the document's mesh in its own frame, in metres, as out/NN.ply, in the Theme's colours (#805: the
    document's by default; a Preset's, #819); returns {part: {"ply", "group", "colour"}}."""
    stage, theme, manifest = stages.STAGES[doc], theme or g.theme(doc), {}
    for i, (name, part) in enumerate(stage.parts.items()):
        mesh = trimesh.load(part.file, force="mesh")  # merges the STL's repeated vertices: normals can be smoothed
        if part.clip:  # as mjcf._mesh: the flexible leads are cut off
            axis, cut = part.clip
            v = mesh.vertices
            mesh = trimesh.Trimesh(v, mesh.faces[(v[mesh.faces][:, :, "xyz".index(axis)] <= cut + 0.1).all(axis=1)])
        mesh.apply_scale(0.001)
        ply = f"{i:02d}.ply"
        mesh.export(os.path.join(out, ply))
        stem = stages.stem(part.file)
        group = stem if stem in GREYS else g.PRINTED[stem][0]
        manifest[name] = {"ply": ply, "group": group, "colour": colour(part.file, theme)}
    return manifest
