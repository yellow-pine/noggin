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

from model.engine import stages
from model.render import scene

BUILD = os.path.join(stages.REPO, "model", "build")
CONVEX, MJCF = os.path.join(BUILD, "convex"), os.path.join(BUILD, "mjcf")
COACD = {"threshold": 0.05, "seed": 0}  # CoACD's default concavity; a fixed seed so the pieces repeat
VISUAL, COLLISION = 2, 3  # geom groups: the viewer shows 0-2, so the pieces stay hidden until group 3 is toggled
MM = 0.001


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
    for name, part in stage.parts.items():
        quat = np.zeros(4)
        mujoco.mju_mat2Quat(quat, part.matrix[:3, :3].flatten())
        body = s.worldbody.add_body(name=name, pos=part.matrix[:3, 3] * MM, quat=quat)
        stem = stages.stem(part.file)
        colour = scene.colour(part.file)  # the spool's, or the hardware's grey
        rgba = [*trimesh.visual.color.hex_to_rgba(colour)[:3] / 255, 1]
        if not s.material(colour):
            s.add_material(name=colour, rgba=rgba, specular=0.3, shininess=0.4)
        mesh = mujoco.mjtGeom.mjGEOM_MESH
        # the drawn mesh carries no mass and touches nothing: the pieces do both
        body.add_geom(type=mesh, meshname=stem, group=VISUAL, contype=0, conaffinity=0, density=0, material=colour)
        for p in pieces[stem]:
            # shortcut: MuJoCo's default density, the bodies are welded; part masses come with the joints in #148
            body.add_geom(type=mesh, meshname=f"{stem} {stages.stem(p)}", group=COLLISION, rgba=rgba)
    return s


def look(s, up, model):
    """For make view (pictures stay Blender's, ADR 0007): a pale sky, a key light over the front casting shadows, and a
    camera "front" on the document's up axis (the viewer's free camera is Z-up, the eyes documents are Y-up; ] steps to
    it). Front is -Z in the eyes frame and -Y in the PT frame (stages.BASE_IN_EYES)."""
    s.add_texture(
        name="sky",
        type=mujoco.mjtTexture.mjTEXTURE_SKYBOX,
        builtin=mujoco.mjtBuiltin.mjBUILTIN_GRADIENT,
        rgb1=[0.95, 0.96, 0.98],
        rgb2=[0.75, 0.78, 0.82],
        width=256,
        height=256,
    )
    s.visual.headlight.ambient, s.visual.headlight.diffuse = [0.35] * 3, [0.35] * 3
    s.visual.quality.shadowsize = 8192
    upward, front = np.eye(3)[up], -np.eye(3)[3 - up]
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    drawn = model.geom_group == VISUAL
    lo = (data.geom_xpos[drawn] - model.geom_rbound[drawn, None]).min(axis=0)
    hi = (data.geom_xpos[drawn] + model.geom_rbound[drawn, None]).max(axis=0)
    centre, extent = (lo + hi) / 2, np.linalg.norm(hi - lo) / 2  # the drawn parts' bounds (stat.center sits off them)
    key = upward * 1.5 + front + np.eye(3)[0] * 0.5
    s.worldbody.add_light(pos=centre + key * extent, dir=-key, diffuse=[0.6] * 3, castshadow=True)
    view = front + upward * 0.45 + np.eye(3)[0] * 0.6  # from the front, a little above and to the right
    view /= np.linalg.norm(view)
    x = np.cross(upward, view)
    x /= np.linalg.norm(x)
    s.worldbody.add_camera(name="front", pos=centre + view * 1.6 * extent, xyaxes=[*x, *np.cross(view, x)])


def write(doc):
    """model/build/mjcf/<doc>.xml (returned)."""
    os.makedirs(MJCF, exist_ok=True)
    s = spec(doc)
    s.modelfiledir = MJCF
    look(s, stages.STAGES[doc].up, s.compile())
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
