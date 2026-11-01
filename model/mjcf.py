"""The Mech as MuJoCo models (ADR 0007): one MJCF per document (stages.DOCS: the sub-assemblies and the Stage
configurations), every part a body placed by model/geometry.py (through stages), in metres. Each part is drawn with
its mesh from make ours and collides through its CoACD convex pieces, since MuJoCo collides a mesh by its convex hull;
the pieces are decomposed once per mesh and cached in model/build/convex. `python -m model.mjcf [doc ...]` writes
model/build/mjcf/<doc>.xml (every document by default); `make view` opens one in MuJoCo's viewer.
Each horn is a hinge on its servo shaft driven by a position actuator, each coupler a hinge on its horn pin and each
rocker a hinge on its pivot; the four-bars close by a connect at the coupler's rocker pin, each lead is a spatial tendon
no longer than the real lead, and each screw or pin joint a site per part at one point (#148, research note
docs/research/2026-11-01-mujoco-loops.md). pose() puts the Mech at servo commands."""

import concurrent.futures
import glob
import hashlib
import json
import math
import multiprocessing
import os
import shutil
import sys
from importlib.metadata import version

import coacd
import mujoco
import numpy as np
import trimesh

from model import electrical
from model import geometry as g
from model.engine import cables, masses, stages
from model.engine import mating as pins
from model.render import scene

BUILD = os.path.join(stages.REPO, "model", "build")
CONVEX, MJCF = os.path.join(BUILD, "convex"), os.path.join(BUILD, "mjcf")
COACD = {"threshold": 0.05, "seed": 0}  # CoACD's default concavity; a fixed seed so the pieces repeat
VISUAL, COLLISION = 2, 3  # geom groups: the viewer shows 0-2, so the pieces stay hidden until group 3 is toggled
MM = 0.001
# the viewer draws no outlines: black and white pulled in so their shading reads (the pictures keep their own)
SKY = "#F7F4EE"  # the pictures' background (model/render/blender.py BG, which runs inside Blender: not importable)
VIEW = {g.SPOOLS["Absolute Black"]: "#5A5A60", g.SPOOLS["Pure White"]: "#E8E8E8"}
TIMESTEP, SETTLE_S = 0.0005, 0.5
# A connect holds to LOOP_SOLREF's time constant (4 steps, over refsafe's 2) at a constant impedance of 0.99 (the
# default's 0.9..0.95 lets the loaded tilt pin open 0.12 mm and the pan bar ring near its toggle): the violation at rest
# scales with (1 - d) tc^2 (docs/research/2026-11-01-mujoco-loops.md 2), microns here.
LOOP_SOLREF, LOOP_SOLIMP = (0.002, 1.0), (0.99, 0.99, 0.001, 0.5, 2.0)
# pose() slews each command at a quarter of the servo's rated 428 deg/s: quasi-static. At the rated speed the stage 3
# head's inertia carries the pan four-bar through its toggle at pan horn -40 (a dynamic question for #149).
SLEW_DEG_S = 100
# The 9 g servo: its published stall torque at 4.8 V, the figure nearest the shield's 5 V servo rail
# (electrical.SERVO_RAIL_V), as the actuator's force limit; full torque 0.5 deg off its command (a servo's deadband,
# inferred); the motor's inertia through the gears as the shaft's armature (inferred: a micro motor's rotor through
# ~1:300, and what keeps kp stable at TIMESTEP); critically damped on it.
STALL_NM = electrical.servo.SPEC[electrical.SERVO_MIN_V]["stall_kgfcm"] * 0.0980665
KP, ARMATURE = STALL_NM / math.radians(0.5), 1e-4
KV = 2 * math.sqrt(KP * ARMATURE)


def convex(file, clip=None):
    """The mesh's CoACD convex pieces as STLs (mm, the part's frame) in model/build/convex/<stem>, decomposed again
    only when the mesh, its clip or the CoACD settings change."""
    with open(file, "rb") as f:
        key = hashlib.sha256(f.read() + json.dumps([clip, COACD, version("coacd")]).encode()).hexdigest()
    folder = os.path.join(CONVEX, stages.stem(file))
    marker = os.path.join(folder, ".key")
    if not os.path.exists(marker) or open(marker).read() != key:
        mesh = _mesh(file, clip)
        coacd.set_log_level("error")
        pieces = coacd.run_coacd(coacd.Mesh(mesh.vertices, mesh.faces), **COACD)
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)
        for i, (pv, pf) in enumerate(pieces):
            trimesh.Trimesh(pv, pf).export(os.path.join(folder, f"{i}.stl"))
        with open(marker, "w") as out:
            out.write(key)  # last, so an interrupted run decomposes again
    return sorted(glob.glob(os.path.join(folder, "*.stl")), key=lambda p: int(stages.stem(p)))


def _mesh(file, clip):
    mesh = trimesh.load(file, force="mesh")
    v, f = mesh.vertices, mesh.faces
    if clip:  # as model/engine/meshes.py: the flexible battery and servo leads are not rigid
        axis, cut = clip
        f = f[(v[f][:, :, "xyz".index(axis)] <= cut + 0.1).all(axis=1)]
    return trimesh.Trimesh(v, f)


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


def _joints(stage):
    """The document's hinges, in its frame (mm): ({joint: (point, axis)}: each horn (named as the horn) on its servo
    shaft, each coupler (named as its part) on its horn pin, each rocker (named as the old engine's joint) on its pivot;
    {part: the joints that move it}; [(loop joint, coupler, rocker, the rocker pin)] where the four-bars close)."""
    hinges, moves, closures = {}, {n: set() for n in stage.parts}, []
    for h, horn in stage.horns.items():
        f = horn.frame  # the chain's points are in its sub-assembly's frame

        def at(p, axis):
            return (f @ [*p, 1])[:3], f[:3, :3] @ axis

        hinges[h] = at(horn.pivot["point"], horn.pivot["axis"])
        moves[horn.crank].add(h)
        for loop in horn.loops:
            _, a0, b0 = loop.solve(0)
            pivot, axis = loop.rocker_pivot
            hinges[loop.coupler], hinges[loop.joint] = at(a0, axis), at(pivot, axis)
            moves[loop.coupler] |= {h, loop.coupler}
            for r in loop.rockers:
                moves[r].add(loop.joint)
            closures.append((loop.joint, loop.coupler, loop.rockers[0], at(b0, axis)[0]))
    return hinges, moves, closures


def spec(doc):
    """The document as an MjSpec: a body per part at its placement, its mesh drawn in its colour, its convex pieces
    colliding and weighing the part's mass (model/engine/masses.py); the parts a joint moves hang under it (_joints())."""
    stage = stages.STAGES[doc]
    meshes = {stages.stem(p.file): (p.file, p.clip) for p in stage.parts.values()}
    # spawn, not fork: CadQuery's OCCT threads may be running in the caller (model/ours.py)
    with concurrent.futures.ProcessPoolExecutor(mp_context=multiprocessing.get_context("spawn")) as pool:
        pieces = dict(zip(meshes, pool.map(_convex, meshes.values())))
    volumes = {stem: [trimesh.load(p).volume for p in ps] for stem, ps in pieces.items()}
    s = mujoco.MjSpec()
    s.modelname = doc
    s.meshdir = os.path.relpath(BUILD, MJCF)
    s.compiler.degree = False
    s.option.timestep = TIMESTEP
    for stem, (file, _) in meshes.items():
        s.add_mesh(name=stem, file=os.path.relpath(file, BUILD), scale=[MM] * 3)
        for p in pieces[stem]:
            s.add_mesh(name=f"{stem} {stages.stem(p)}", file=os.path.relpath(p, BUILD), scale=[MM] * 3)
    rgb = trimesh.visual.color.hex_to_rgba(SKY)[:3] / 255
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
    hinges, moves, closures = _joints(stage)
    groups = {}  # parts moved by the same joints are one rigid group: the first carries the joint, the rest hang on it
    for name, js in moves.items():
        groups.setdefault(frozenset(js), []).append(name)
    bodies = {}

    def local(part, p):
        return (np.linalg.inv(stage.parts[part].matrix) @ [*p, 1])[:3]

    def add(parent, parent_m, name):
        m = stage.parts[name].matrix
        rel = np.linalg.inv(parent_m) @ m
        body = bodies[name] = parent.add_body(name=name, pos=rel[:3, 3] * MM, quat=_quat(rel))
        file, clip = stage.parts[name].file, stage.parts[name].clip
        stem = stages.stem(file)
        # make view only has to tell the parts apart: the part's colour, black and white pulled in (VIEW)
        colour = scene.colour(file)
        rgba = [*trimesh.visual.color.hex_to_rgba(VIEW.get(colour, colour))[:3] / 255, 1]
        # the drawn mesh carries no mass and touches nothing: the pieces do both, the part's mass spread by volume
        body.add_geom(type=mesh, meshname=stem, group=VISUAL, contype=0, conaffinity=0, density=0, rgba=rgba)
        kg = masses.mass(_mesh(file, clip), stage.parts[name].material)["g"] / 1000
        for p, v in zip(pieces[stem], volumes[stem]):
            piece = f"{stem} {stages.stem(p)}"
            body.add_geom(type=mesh, meshname=piece, group=COLLISION, rgba=rgba, mass=kg * v / sum(volumes[stem]))
        return body

    def hang(moved, parent, parent_m):
        """The groups one joint deeper than `moved`, each on its joint, and theirs under them."""
        for js, names in groups.items():
            if len(js) == len(moved) + 1 and moved < js:
                (j,) = js - moved
                body = add(parent, parent_m, names[0])
                point, axis = hinges[j]
                inv = np.linalg.inv(stage.parts[names[0]].matrix)
                hinge = body.add_joint(name=j, type=mujoco.mjtJoint.mjJNT_HINGE, pos=local(names[0], point) * MM)
                hinge.axis = inv[:3, :3] @ axis
                if j in stage.horns:
                    hinge.armature = ARMATURE
                for n in names[1:]:
                    add(body, stage.parts[names[0]].matrix, n)
                hang(js, body, stage.parts[names[0]].matrix)

    mesh = mujoco.mjtGeom.mjGEOM_MESH
    for name in groups.get(frozenset(), []):
        add(frame, np.eye(4), name)
    hang(frozenset(), frame, np.eye(4))
    assert set(bodies) == set(stage.parts), set(stage.parts) - set(bodies)  # every joint set nests under one joint less
    # a four-bar closes by a connect at its rocker pin (XMLreference.html#equality-connect): a ball joint outside the
    # tree, the rocker's own hinge keeps it turning; a weld would lock it (computation/index.html#coequality)
    for joint, coupler, rocker, pin in closures:
        for part in coupler, rocker:
            bodies[part].add_site(name=f"{joint} pin: {part}", pos=local(part, pin) * MM)
        s.add_equality(
            name=joint,
            type=mujoco.mjtEq.mjEQ_CONNECT,
            objtype=mujoco.mjtObj.mjOBJ_SITE,
            name1=f"{joint} pin: {coupler}",
            name2=f"{joint} pin: {rocker}",
            solref=LOOP_SOLREF,
            solimp=LOOP_SOLIMP,
        )
    for h in stage.horns:
        servo = s.add_actuator(name=h, target=h, trntype=mujoco.mjtTrn.mjTRN_JOINT)
        servo.set_to_position(kp=KP, kv=KV)
        servo.forcerange, servo.ctrlrange = [-STALL_NM, STALL_NM], [-math.pi / 2, math.pi / 2]  # the servo's 0..180
    # each lead from its first Port through the clips of its route (model/engine/cables.py) to its second, as a cable:
    # a one-sided limit at the real lead's length (XMLreference.html#tendon-spatial)
    for lead, a, b, mm in electrical.leads():
        if a in stage.ports and b in stage.ports:
            route = next(r for r in cables.ROUTES[lead] if all(p in stage.parts for p, _, _ in r))
            clips = [stage.ports[a], *((p, cables._local(p, q)) for p, q, _ in route), stage.ports[b]]
            tendon = s.add_tendon(name=lead, range=[0, mm * MM], limited=mujoco.mjtLimited.mjLIMITED_TRUE)
            for i, (part, q) in enumerate(clips):
                bodies[part].add_site(name=f"{lead} {i}", pos=np.multiply(q, MM))
                tendon.wrap_site(f"{lead} {i}")
    # each screw or pin joint: a site per part at its first part's feature (the mating check's circle fit)
    for joint, feats in pins.JOINTS:
        if all(p in stage.parts for p, _ in feats):
            found = pins.feature(stage.parts[feats[0][0]], feats[0][1])
            assert found is not None, joint
            for part, _ in feats:
                bodies[part].add_site(name=f"{joint}: {part}", pos=local(part, found[0]) * MM)
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


def pose(model, ctrl):
    """MjData with each horn's servo at ctrl[horn] degrees from neutral (the others at neutral): from rest, each
    command slews there at SLEW_DEG_S (a step flings a light linkage through its toggle), then is held under gravity for
    SETTLE_S. Contacts are off: the parts' contacts are measured as distances (#149), not pushed apart."""
    data = mujoco.MjData(model)
    flags = model.opt.disableflags
    model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_CONTACT
    rate = math.radians(SLEW_DEG_S) * model.opt.timestep  # rad per step
    target = {h: math.radians(deg) for h, deg in ctrl.items()}
    steps = math.ceil(max(map(abs, target.values()), default=0) / rate)
    for k in range(1, steps + 1):
        for h, rad in target.items():
            data.actuator(h).ctrl = rad * k / steps
        mujoco.mj_step(model, data)
    mujoco.mj_step(model, data, nstep=round(SETTLE_S / model.opt.timestep))
    model.opt.disableflags = flags
    return data


def residuals(model, data):
    """{four-bar: mm its rocker pin's two sites are apart}."""
    return {
        model.eq(i).name: 1000
        * float(np.linalg.norm(data.site_xpos[model.eq_obj1id[i]] - data.site_xpos[model.eq_obj2id[i]]))
        for i in range(model.neq)
    }


def mating(model, data):
    """{screw or pin joint: mm its parts' sites are apart at most}, for the joints whose parts the document has."""
    out = {}
    for joint, feats in pins.JOINTS:
        ids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"{joint}: {p}") for p, _ in feats]
        if -1 not in ids:
            pts = data.site_xpos[ids]
            out[joint] = 1000 * float(np.linalg.norm(pts - pts[0], axis=1).max())
    return out


if __name__ == "__main__":
    for doc in sys.argv[1:] or stages.DOCS:
        print(os.path.relpath(write(doc), stages.REPO))
