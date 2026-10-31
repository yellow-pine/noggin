"""The Mech as MuJoCo models (ADR 0007): one MJCF per document (stages.DOCS: the sub-assemblies and the Stage
configurations), every part a body placed by model/geometry.py (through stages), in metres. Each part is drawn with
its mesh from make ours and collides through its CoACD convex pieces, since MuJoCo collides a mesh by its convex hull;
the pieces are decomposed once per mesh and cached in model/build/convex. `python -m model.mjcf [doc ...]` writes
model/build/mjcf/<doc>.xml (every document by default); `make view` opens one in MuJoCo's viewer."""

import concurrent.futures
import glob
import hashlib
import json
import multiprocessing
import os
import shutil
import sys
from importlib.metadata import version

import coacd
import mujoco
import numpy as np
import trimesh

from model import geometry as g
from model.engine import stages
from model.render import scene

BUILD = os.path.join(stages.REPO, "model", "build")
CONVEX, MJCF = os.path.join(BUILD, "convex"), os.path.join(BUILD, "mjcf")
COACD = {"threshold": 0.05, "seed": 0}  # CoACD's default concavity; a fixed seed so the pieces repeat
VISUAL, COLLISION = 2, 3  # geom groups: the viewer shows 0-2, so the pieces stay hidden until group 3 is toggled
MM = 0.001
VIEW_BLACK = "#5A5A60"  # the viewer draws no outlines: Absolute Black lifted past the pictures' #2B2B2E to read


def convex(file, clip=None):
    """The mesh's CoACD convex pieces as STLs (mm, the part's frame) in model/build/convex/<stem>, decomposed again
    only when the mesh, its clip or the CoACD settings change."""
    with open(file, "rb") as f:
        key = hashlib.sha256(f.read() + json.dumps([clip, COACD, version("coacd")]).encode()).hexdigest()
    folder = os.path.join(CONVEX, stages.stem(file))
    marker = os.path.join(folder, ".key")
    if not os.path.exists(marker) or open(marker).read() != key:
        mesh = trimesh.load(file, force="mesh")
        v, f = mesh.vertices, mesh.faces
        if clip:  # as model/engine/meshes.py: the flexible battery and servo leads are not rigid
            axis, cut = clip
            f = f[(v[f][:, :, "xyz".index(axis)] <= cut + 0.1).all(axis=1)]
        coacd.set_log_level("error")
        pieces = coacd.run_coacd(coacd.Mesh(v, f), **COACD)
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)
        for i, (pv, pf) in enumerate(pieces):
            trimesh.Trimesh(pv, pf).export(os.path.join(folder, f"{i}.stl"))
        with open(marker, "w") as out:
            out.write(key)  # last, so an interrupted run decomposes again
    return sorted(glob.glob(os.path.join(folder, "*.stl")), key=lambda p: int(stages.stem(p)))


def _convex(args):
    return convex(*args)


def root(doc):
    """4x4 from the document's frame to MuJoCo's world: the Y-up eyes-frame documents (noggin-eyes, noggin-mouth) are
    carried into the PT frame (stages.BASE_IN_EYES undone), so every model is Z-up with its base plate where the
    Stages have it, and the viewer and gravity agree with it."""
    return np.linalg.inv(stages.align(*stages.BASE_IN_EYES)) if stages.STAGES[doc].up == 1 else np.eye(4)


def _quat(m):
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, np.ascontiguousarray(m[:3, :3]).flatten())
    return q


def spec(doc):
    """The document as an MjSpec: a body per part at its placement (welded to the world: joints come in #148), its
    mesh drawn in its colour, its convex pieces colliding."""
    stage = stages.STAGES[doc]
    meshes = {stages.stem(p.file): (p.file, p.clip) for p in stage.parts.values()}
    # spawn, not fork: CadQuery's OCCT threads may be running in the caller (model/ours.py)
    with concurrent.futures.ProcessPoolExecutor(mp_context=multiprocessing.get_context("spawn")) as pool:
        pieces = dict(zip(meshes, pool.map(_convex, meshes.values())))
    s = mujoco.MjSpec()
    s.modelname = doc
    s.meshdir = os.path.relpath(BUILD, MJCF)
    for stem, (file, _) in meshes.items():
        s.add_mesh(name=stem, file=os.path.relpath(file, BUILD), scale=[MM] * 3)
        for p in pieces[stem]:
            s.add_mesh(name=f"{stem} {stages.stem(p)}", file=os.path.relpath(p, BUILD), scale=[MM] * 3)
    rgb = trimesh.visual.color.hex_to_rgba(scene.BG)[:3] / 255
    # the pictures' background as the sky: a flat skybox (XMLreference.html#asset-texture, builtin "flat")
    s.add_texture(
        type=mujoco.mjtTexture.mjTEXTURE_SKYBOX,
        builtin=mujoco.mjtBuiltin.mjBUILTIN_FLAT,
        rgb1=rgb,
        rgb2=rgb,
        width=32,
        height=32,
    )
    # MuJoCo's default headlight (ambient 0.1, diffuse 0.4, specular 0.5) dims every colour by half and greys it; this
    # one draws a face toward the camera in its exact colour (XMLreference.html#visual-headlight)
    s.visual.headlight.ambient, s.visual.headlight.diffuse, s.visual.headlight.specular = [0.5] * 3, [0.5] * 3, [0] * 3
    r = root(doc)
    frame = s.worldbody.add_frame(pos=r[:3, 3] * MM, quat=_quat(r))  # the bodies keep the document's own numbers
    mesh = mujoco.mjtGeom.mjGEOM_MESH
    for name, part in stage.parts.items():
        body = frame.add_body(name=name, pos=part.matrix[:3, 3] * MM, quat=_quat(part.matrix))
        stem = stages.stem(part.file)
        # make view only has to tell the parts apart: the colour the pictures draw it in (black lifted further)
        drawn = scene.drawn(part.file)
        drawn = VIEW_BLACK if drawn == scene.DRAWN[g.SPOOLS["Absolute Black"]] else drawn
        rgba = [*trimesh.visual.color.hex_to_rgba(drawn)[:3] / 255, 1]
        # the drawn mesh carries no mass and touches nothing: the pieces do both
        body.add_geom(type=mesh, meshname=stem, group=VISUAL, contype=0, conaffinity=0, density=0, rgba=rgba)
        for p in pieces[stem]:
            # shortcut: MuJoCo's default density, the bodies are welded; part masses come with the joints in #148
            body.add_geom(type=mesh, meshname=f"{stem} {stages.stem(p)}", group=COLLISION, rgba=rgba)
    return s


def write(doc):
    """model/build/mjcf/<doc>.xml (returned)."""
    os.makedirs(MJCF, exist_ok=True)
    s = spec(doc)
    s.modelfiledir = MJCF
    s.compile()
    path = os.path.join(MJCF, doc + ".xml")
    with open(path, "w") as f:
        f.write(s.to_xml())
    return path


def model(doc):
    """The document as MuJoCo loads it from its MJCF."""
    return mujoco.MjModel.from_xml_path(write(doc))


if __name__ == "__main__":
    for doc in sys.argv[1:] or stages.DOCS:
        print(os.path.relpath(write(doc), stages.REPO))
