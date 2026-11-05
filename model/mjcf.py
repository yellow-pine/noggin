"""The Mech as MuJoCo models (ADR 0007): one MJCF per document (stages.DOCS), every part a body placed by
model/stages.py, in metres. Each part is drawn with
its mesh from just ours and collides through its CoACD convex pieces, since MuJoCo collides a mesh by its convex hull;
the pieces are decomposed once per mesh and cached in model/build/convex. `python -m model.mjcf [doc ...]` writes
model/build/mjcf/<doc>.xml (every one physics runs on by default, geometry.SIMULATED: #809); `just view` opens one in MuJoCo's viewer.
Each horn is a hinge on its servo shaft driven by its servo (drive(): a DC motor behind its own position loop), each
coupler a hinge on its horn pin and each rocker a hinge on its pivot; the four-bars close by a connect at the coupler's
rocker pin (#148, research note docs/research/2026-11-01-mujoco-loops.md). pose() puts the Mech at servo commands."""

import collections
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

from model import electrical, neck, skin, stages
from model import geometry as g
from model.render import scene

BUILD = os.path.join(stages.REPO, "model", "build")
ANATOMY_LOADS = os.path.join(BUILD, "skeleton", "loads.json")
CONVEX, MJCF = os.path.join(BUILD, "convex"), os.path.join(BUILD, "mjcf")
COACD = {"threshold": 0.05, "seed": 0}  # CoACD's default concavity; a fixed seed so the pieces repeat
# The parts whose pieces meet another part closely, cut finer: CoACD's real-metric mode takes the threshold in the mesh's
# own units (mm here) where the default is normalised to the part's longest side (docs/research/2026-11-01-coacd-tuning.md)
FINE_MM = {
    "horn": 0.08,
    # the jaw's arms turn 2 mm outside its lugs and the plate's edge (model/neck.py JAW_X): pieces within 1 mm of the
    # frame, not chords across that gap, which read the opening jaw 0.22 mm into it while the solids never meet (#869)
    f"gimbal frame{g.MECHANICAL}": 1.0,
} | {
    # each lower lid's shell nests 1 mm outside the upper's (#698): pieces within 0.5 mm of it, not chords across the gap
    f"{s} lower lid{style}": 0.5
    for s in "LR"
    for style in ("", g.MECHANICAL)
}
# The mechanical parts that take their Bones in (model/printed/bone.py grown, #809): curved sections would cut into many
# pieces, so each one's capped and the sim stays fast; but the yaw yoke, whose capped pieces fill its cradle and read
# the core 1.6 mm deep in it
MAX_PIECES = dict.fromkeys((f"{p}{g.MECHANICAL}" for p in ("tie-bar", "bail")), 12)
VISUAL, COLLISION = 2, 3  # geom groups: the viewer shows 0-2, so the pieces stay hidden until group 3 is toggled
MM = 0.001
# the viewer draws no outlines: black and white pulled in so their shading reads (the pictures keep their own)
SKY = "#F7F4EE"  # a flat sky
VIEW = {"#000000": "#5A5A60", "#FFFFFF": "#E8E8E8"}
TIMESTEP, SETTLE_S = 0.0005, 0.5
# A life-size head still rings after two seconds near the pan's end: static readings wait for quiet, bounded at four.
SETTLE_MAX_S, SETTLE_DEG_S = 4.0, 0.1
# A connect holds to LOOP_SOLREF's time constant (4 steps, over refsafe's 2) at a constant impedance of 0.99 (the
# default's 0.9..0.95 lets the loaded tilt pin open 0.12 mm and the pan bar ring near its toggle): the violation at rest
# scales with (1 - d) tc^2 (docs/research/2026-11-01-mujoco-loops.md 2), microns here.
LOOP_SOLREF, LOOP_SOLIMP = (0.002, 1.0), (0.99, 0.99, 0.001, 0.5, 2.0)
# shortcut: pose() slews at a quarter of the servo's rated 428 deg/s by default: at the rated speed the position actuator
# once carried a head through its pan four-bar's toggle; the DC motor (#625) lands that swing (model/mujoco_report.py
# full_speed), so the rated speed may do now; revisit with Core 2's choreography.
SLEW_DEG_S = 100
# The 9 g servo as a DC motor behind its own P loop (#625, docs/research/2026-11-02-literature-simulation.md 1):
# its published stall torque and no-load speed at 4.8 V, the figures nearest the shield's 5 V servo rail
# (electrical.SERVO_RAIL_V), referred to the horn; full torque 0.5 deg off its command (a servo's deadband); the motor's
# inertia through the gears as the shaft's armature (eyes/servo.py; what keeps kp stable at TIMESTEP), critically
# damped on it; a new command waits up to one 20 ms PWM frame. All inferred until
# model/servo_fit.py fits the filmed servo into model/servo_fit.json, whose values then win.
SERVO_V = electrical.SERVO_MIN_V
STALL_NM = electrical.servo.SPEC[SERVO_V]["stall_kgfcm"] * 0.0980665
FIT = os.path.join(os.path.dirname(__file__), "servo_fit.json")
SERVO = {
    "stall_nm": STALL_NM,
    "no_load_rad_s": math.radians(electrical.servo.rate(SERVO_V)),
    "kp": STALL_NM / math.radians(0.5),
    "armature": electrical.servo.ARMATURE,
    "delay_s": 0.02,
    **(json.load(open(FIT)) if os.path.exists(FIT) else {}),
}


def motor(horn):
    """Per-axis motor on the actual 5 V rail; the micro's filmed fit never fits the standard tilt."""
    p = electrical.servo.profile(horn.removesuffix(" horn"), electrical.SERVO_RAIL_V)
    stall = p["stall_kgfcm"] * 0.0980665
    return {
        "volts": p["volts"],
        "stall_nm": stall,
        "no_load_rad_s": math.radians(60 / p["s_per_60"]),
        "kp": stall / math.radians(0.5),
        "armature": p["armature"],
        "delay_s": 0.02,
        "travel_deg": p["travel_deg"],
        **(json.load(open(FIT)) if horn != "tilt horn" and os.path.exists(FIT) else {}),
    }


def drive(s, joint, values=None, delay_max_s=None, *, name=None, gear=1):
    """A servo on the spec's hinge `joint` (an actuator of its name): a dcmotor at SERVO_V whose position loop commands
    torque (MuJoCo's controller adds back-EMF to its voltage, as a current-driven motor: optimistic for the servo's
    voltage H-bridge below the clamp), its voltage clamped at SERVO_V, so it stalls at stall_nm and runs no faster than
    no_load_rad_s; its command read delay_s late from a history of delay_max_s (default delay_s)."""
    values = motor(name or joint) if values is None else values
    volts = values.get("volts", SERVO_V)
    kd = 2 * math.sqrt(values["kp"] * values["armature"])
    s.joint(joint).armature = values["armature"]
    servo = s.add_actuator(name=name or joint, target=joint, trntype=mujoco.mjtTrn.mjTRN_JOINT)
    servo.set_to_dcmotor(
        motorconst=[0, 0],
        resistance=0,
        nominal=[volts, values["stall_nm"], values["no_load_rad_s"]],
        controller=[values["kp"], 0, kd, 0, 0, volts],
        ctrlspec=mujoco.mjtCtrlInput.mjINPUT_POS,
    )
    travel = math.radians(values.get("travel_deg", 180) / 2)
    servo.ctrlrange = [-travel, travel]
    servo.gear = [gear, 0, 0, 0, 0, 0]
    servo.nsample = math.ceil((delay_max_s or values["delay_s"]) / s.option.timestep - 1e-9)
    servo.delay, servo.interp = values["delay_s"], 1  # linear (XMLreference actuator interp), so the fit can move it


def convex(file, clip=None):
    """The mesh's CoACD convex pieces as STLs (mm, the part's frame) in model/build/convex/<stem>, decomposed again
    only when the mesh CoACD gets (_mesh) or the CoACD settings change."""
    mesh, stem = _mesh(file, clip), stages.stem(file)
    settings = {**COACD, "threshold": FINE_MM[stem], "real_metric": True} if stem in FINE_MM else COACD
    if stem in MAX_PIECES:
        settings = {**settings, "max_convex_hull": MAX_PIECES[stem]}
    seen = mesh.vertices.tobytes() + mesh.faces.tobytes() + json.dumps([settings, version("coacd")]).encode()
    key = hashlib.sha256(seen).hexdigest()
    folder = os.path.join(CONVEX, stem)
    marker = os.path.join(folder, ".key")
    if not os.path.exists(marker) or open(marker).read() != key:
        coacd.set_log_level("error")
        pieces = [trimesh.Trimesh(*p) for p in coacd.run_coacd(coacd.Mesh(mesh.vertices, mesh.faces), **settings)]
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)
        # a fine cut leaves a few flat slivers, which MuJoCo cannot hull (it needs 4 vertices and a volume)
        for i, piece in enumerate(p for p in pieces if len(p.vertices) >= 4 and abs(p.volume) > 1e-6):
            piece.export(os.path.join(folder, f"{i}.stl"))
        with open(marker, "w") as out:
            out.write(key)  # last, so an interrupted run decomposes again
    return sorted(glob.glob(os.path.join(folder, "*.stl")), key=lambda p: int(stages.stem(p)))


def _mesh(file, clip):
    mesh = trimesh.load(file, force="mesh")
    v, f = mesh.vertices, mesh.faces
    if clip:  # shortcut: faces past the cut dropped, no cap: the flexible battery and servo leads are not rigid
        axis, cut = clip
        f = f[(v[f][:, :, "xyz".index(axis)] <= cut + 0.1).all(axis=1)]
    mesh = trimesh.Trimesh(v, f)
    # OCCT leaves a zero-area sliver on a few seams (the lids, the eyeballs): without it the mesh is a closed 2-manifold,
    # so CoACD skips its voxel remesh (preprocess_mode "auto"), which smears the part by ~1 mm
    mesh.update_faces(mesh.nondegenerate_faces())
    return mesh


def mass(mesh, material):
    """g of a mesh of `material` (stages.Part): (g/cm3, label) at the mesh's volume, or (g, 'documented') for hardware
    whose mass is known (the servo)."""
    density, source = material
    return round(density if source == "documented" else density * abs(mesh.volume) / 1000, 3)


def _convex(args):
    return convex(*args)


def _quat(m):
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, np.ascontiguousarray(m[:3, :3]).flatten())
    return q


def anatomy(spec, stage, bodies):
    """Finished-export mass/COM/inertia on rigid carriers; realistic meshes remain excluded from collisions (ADR0020)."""
    with open(ANATOMY_LOADS) as file:
        loads = json.load(file)
    required = set(g.SKULL)  # #874 derives this from its one canonical Bone-output registry
    if (
        not isinstance(loads.get("source"), str)
        or not loads["source"].strip()
        or not required <= loads.get("parts", {}).keys()
    ):
        raise ValueError("finished anatomy loads need their export stamp and every head/cervical part")
    head = stage.horns["tilt horn"].frame
    for stem, load in loads["parts"].items():
        role = load["carrier"]
        if role not in neck.BONE_CARRIERS:
            raise ValueError(f"invalid anatomical carrier for {stem}")
        grams, com, tensor = load["mass_g"], np.asarray(load["com_mm"], float), np.asarray(load["inertia_g_mm2"], float)
        if (
            not math.isfinite(grams)
            or grams <= 0
            or com.shape != (3,)
            or tensor.shape != (3, 3)
            or not np.isfinite(com).all()
            or not np.isfinite(tensor).all()
            or not np.allclose(tensor, tensor.T)
        ):
            raise ValueError(f"invalid finished mass properties for {stem}")
        carrier = neck.BONE_CARRIERS[role]
        matrix = np.linalg.inv(stage.parts[carrier].matrix) @ head
        inertia, axes = np.linalg.eigh(matrix[:3, :3] @ tensor @ matrix[:3, :3].T)
        if min(inertia) <= 0 or 2 * max(inertia) > sum(inertia) * (1 + 1e-8):
            raise ValueError(f"nonphysical finished inertia for {stem}")
        if np.linalg.det(axes) < 0:
            axes[:, -1] *= -1
        orientation = np.eye(4)
        orientation[:3, :3] = axes
        body = bodies[carrier].add_body(name=f"anatomy {stem}", pos=(matrix @ [*com, 1])[:3] * MM)
        body.explicitinertial, body.mass = True, grams / 1000
        body.ipos = [0, 0, 0]  # the explicit inertia is about this child's own origin, already placed at the COM
        body.inertia, body.iquat = inertia * 1e-9, _quat(orientation)  # g.mm² -> kg.m²


def _joints(stage):
    """The document's hinges, in its frame (mm): ({joint: (point, axis)}: each horn (named as the horn) on its servo
    shaft, each coupler (named as its part) on its horn pin, each rocker (named as its stages.Loop joint) on its pivot,
    each rod (stages.Rod) on its arm, axes (two: a universal joint) on its carrier, and the parts it drives on their hinge;
    {part: the joints that move it}; [(loop joint, coupler, rocker, the rocker pin)] where the four-bars and the
    push-rods close)."""
    hinges, moves, closures = {}, collections.defaultdict(set), []  # a horn drives a bone too, which is no body
    for h, horn in stage.horns.items():
        f = horn.frame  # the chain's points are in its sub-assembly's frame

        def at(p, axis):
            return (f @ [*p, 1])[:3], np.asarray(axis, float) @ f[:3, :3].T

        if horn.direct:
            hinges[horn.direct.joint] = at(horn.pivot["point"], horn.pivot["axis"])
            for name in horn.direct.driven:
                moves[name].add(horn.direct.joint)
            if reaction := horn.direct.reaction:
                axis = horn.pivot["axis"]
                hinges[h] = at(reaction.point, axis)
                for name in reaction.driven:
                    moves[name].add(h)
                bar_joint = reaction.bar + " pivot"
                hinges[bar_joint] = at(reaction.anchor, axis)
                moves[reaction.bar].add(bar_joint)
                closures.append((h + " reaction", reaction.bar, reaction.driven[0], at(reaction.pin, axis)[0]))
            continue
        hinges[h] = at(horn.pivot["point"], horn.pivot["axis"])
        for crank in (horn.crank,) if isinstance(horn.crank, str) else horn.crank:
            moves[crank].add(h)
        for loop in horn.loops:
            _, a0, b0 = loop.solve(0)
            pivot, axis = loop.rocker_pivot
            hinges[loop.coupler], hinges[loop.joint] = at(a0, axis), at(pivot, axis)
            moves[loop.coupler] |= {h, loop.coupler}
            for r in loop.rockers:
                moves[r].add(loop.joint)
            closures.append((loop.joint, loop.coupler, loop.rockers[0], at(b0, axis)[0]))
        for rod in horn.rods:
            joint, point, axis = rod.hinge
            hinges[rod.joint], hinges[joint] = at(rod.arm, rod.axes), at(point, axis)
            moves[rod.part] |= moves[rod.carrier] | {rod.joint}
            for p in rod.driven:
                moves[p].add(joint)
            closures.append((rod.joint, rod.part, rod.driven[0], at(rod.lever, axis)[0]))
    return hinges, {n: moves[n] for n in stage.parts}, closures


def spec(doc, collide=True):
    """The document as an MjSpec: a body per part at its placement, its mesh drawn in its colour, its convex pieces
    colliding and weighing the part's mass (mass()); the parts a joint moves hang under it (_joints()). Without collide
    there are no pieces (no CoACD): the drawn mesh weighs the part and nothing collides, enough for what plays with
    contacts off (model/trajectories.py, #276). The realistic skull's bones (g.BONES) are none of its bodies: physics runs
    on the mechanical documents (#809), and their meshes pass MuJoCo's STL limit (model/trajectories.py poses() carries
    them on their carriers)."""
    stage = stages.STAGES[doc]
    stage = stage._replace(parts={n: p for n, p in stage.parts.items() if stages.stem(p.file) not in g.BONES})
    meshes = {stages.stem(p.file): (p.file, p.clip) for p in stage.parts.values()}
    pieces = {stem: [] for stem in meshes}
    cut = {stem: m for stem, m in meshes.items() if stem not in skin.DRAWN}  # a Skin's Shells are drawn alone
    if collide:  # spawn, not fork: CadQuery's OCCT threads may be running in the caller (model/ours.py)
        with concurrent.futures.ProcessPoolExecutor(mp_context=multiprocessing.get_context("spawn")) as pool:
            pieces |= dict(zip(cut, pool.map(_convex, cut.values())))
    volumes = {stem: [trimesh.load(p).volume for p in ps] for stem, ps in pieces.items()}
    s = mujoco.MjSpec()
    s.modelname = doc
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
    # on top (#150): a key light from the Mech's upper front-left that casts shadows, and satin plastic as the pictures'
    # (XMLreference.html#body-light, #asset-material); lights and materials only draw, nothing in the physics reads them
    s.worldbody.add_light(
        type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL,
        dir=[-0.5, 0.7, -1],
        castshadow=True,
        ambient=[0] * 3,
        diffuse=[0.3] * 3,
        specular=[0.3] * 3,
    )
    s.add_material(name="satin", specular=0.3, shininess=0.5)
    frame = s.worldbody.add_frame()  # the document's frame is MuJoCo's world: z up
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
        # just view only has to tell the parts apart: the part's colour, black and white pulled in (VIEW)
        colour = scene.colour(file, g.theme(doc))
        rgba = [*trimesh.visual.color.hex_to_rgba(VIEW.get(colour, colour))[:3] / 255, 1]
        # the drawn mesh touches nothing and carries no mass where the pieces do both, the part's mass spread by volume
        kg = mass(_mesh(file, clip), stage.parts[name].material) / 1000
        weight = {"density": 0} if pieces[stem] else {"mass": kg}
        body.add_geom(
            type=mesh, meshname=stem, group=VISUAL, contype=0, conaffinity=0, rgba=rgba, material="satin", **weight
        )
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
                point, axes = hinges[j]
                axes = np.reshape(axes, (-1, 3))  # two: a universal joint, its hinges named "<joint> <n>"
                for n, axis in enumerate(axes):
                    name = j if len(axes) == 1 else f"{j} {n}"
                    hinge = body.add_joint(name=name, type=mujoco.mjtJoint.mjJNT_HINGE, pos=local(names[0], point) * MM)
                    hinge.axis = stage.parts[names[0]].matrix[:3, :3].T @ axis  # a rotation's inverse is its transpose
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
    for h, horn in stage.horns.items():
        if horn.direct and not horn.direct.reaction:
            drive(s, horn.direct.joint, name=h, gear=horn.direct.sign)
        else:
            drive(s, h)
    if neck.HEAD_CARRIERS["fixed"] in bodies and neck.HEAD_CARRIERS["jaw"] in bodies:
        anatomy(s, stage, bodies)  # missing finished exports must never silently remove anatomical head weight
    if "tilt horn" in stage.horns and (neck.HEAD_CARRIERS["fixed"] not in bodies or neck.SPRING_VERIFIED):
        balance(s, doc)
    return s


KGF_CM = 0.0980665  # N.m


def head(doc, model, bare=False):
    """(grams, centre of mass in the head's frame, mm) of what the Mech's tilt turns (neck.HEAD, the eye gimbal
    and what rides the head mount), as the MJCF weighs and places them; bare: less its Skin's Shells (skin.DRAWN)."""
    data = mujoco.MjData(model)
    mujoco.mj_kinematics(model, data)
    horn = stages.STAGES[doc].horns["tilt horn"]
    rockers = horn.direct.driven if horn.direct else horn.loops[0].rockers
    rockers = [n for n in rockers if stages.stem(stages.STAGES[doc].parts[n].file) not in g.BONES]  # no body: spec()
    ids = [model.body(n).id for n in rockers if not (bare and n.removesuffix(":1") in skin.DRAWN)]
    ids += [
        i for i in range(1, model.nbody) if model.body(i).name.startswith("anatomy ") and model.body_parentid[i] in ids
    ]
    kg = model.body_mass[ids]
    com = (kg @ data.xipos[ids]) / kg.sum() * 1000  # the MJCF's root is the document's frame (up is z)
    return float(kg.sum() * 1000), tuple(float(c) for c in com - np.array(stages.DOCS[doc]["neck"][0]))


def balance(s, doc):
    """The balance spring on the tilt pivot (#838, neck.balance) for the head as `s` weighs it, in its Skin and bare
    (#830): its rate as the joint's stiffness, its torque at rest as the angle it is wound from (MuJoCo's passive force
    -stiffness (q - springref))."""
    s.modelfiledir, s.meshdir = BUILD, "."  # the meshes' paths are BUILD's (write() puts them beside its MJCF)
    model = s.compile()
    rest, rate = neck.balance(head(doc, model), head(doc, model, bare=True))
    joint = s.joint("tilt pivot")
    joint.stiffness = [rate * KGF_CM, 0.0, 0.0]
    joint.springref = rest / rate


def write(doc, folder=MJCF, *, collide=True):
    """<folder>/<doc>.xml (returned; <doc>-drawn.xml without collide): model/build/mjcf by default, model/build/reports
    for the sim report's (just sim)."""
    os.makedirs(folder, exist_ok=True)
    s = spec(doc, collide)
    s.meshdir = os.path.relpath(BUILD, folder)
    s.modelfiledir = folder
    s.compile()
    path = os.path.join(folder, doc + ("" if collide else "-drawn") + ".xml")
    with open(path, "w") as f:
        f.write(s.to_xml())
    return path


def model(doc, collide=True):
    """The document as MuJoCo loads it from its MJCF (spec: without collide, no convex pieces)."""
    return mujoco.MjModel.from_xml_path(write(doc, collide=collide))


def pose(model, ctrl, deg_s=SLEW_DEG_S):
    """MjData with each horn's servo at ctrl[horn] degrees from neutral (the others at neutral): from rest, each
    command slews there at deg_s (a step flings a light four-bar through its toggle). The default quasi-static slew
    waits for quiet within SETTLE_MAX_S; a custom speed keeps its fixed SETTLE_S observation (the rated swing gate).
    Contacts are off: the parts' contacts are measured as distances (model/mujoco_report.py), not pushed apart."""
    data = mujoco.MjData(model)
    rate = math.radians(deg_s) * model.opt.timestep  # rad per step
    target = {h: math.radians(deg) for h, deg in ctrl.items()}
    steps = math.ceil(max(map(abs, target.values()), default=0) / rate)
    flags = model.opt.disableflags
    model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_CONTACT
    try:
        for k in range(1, steps + 1):
            for h, rad in target.items():
                data.actuator(h).ctrl = rad * k / steps
            mujoco.mj_step(model, data)
        quasi = deg_s == SLEW_DEG_S
        speed = error = math.inf
        for _ in range(round(SETTLE_MAX_S / SETTLE_S) if quasi else 1):
            mujoco.mj_step(model, data, nstep=round(SETTLE_S / model.opt.timestep))
            if not quasi:
                break
            speed = float(np.max(np.abs(data.qvel), initial=0))
            positions = data.actuator_length
            error = float(np.max(np.abs(data.ctrl - positions), initial=0))
            if speed <= math.radians(SETTLE_DEG_S) and error <= SERVO["stall_nm"] / SERVO["kp"]:
                break
        else:
            raise RuntimeError(
                f"quasi-static pose {ctrl} did not settle in {SETTLE_MAX_S} s: "
                f"{math.degrees(speed):.3f} deg/s, {math.degrees(error):.3f} deg off command"
            )
    finally:  # the model is the caller's: its contacts come back on
        model.opt.disableflags = flags
    return data


def residuals(model, data):
    """{four-bar: mm its rocker pin's two sites are apart}."""
    return {
        model.eq(i).name: 1000
        * float(np.linalg.norm(data.site_xpos[model.eq_obj1id[i]] - data.site_xpos[model.eq_obj2id[i]]))
        for i in range(model.neq)
    }


if __name__ == "__main__":
    for doc in sys.argv[1:] or g.SIMULATED:
        print(os.path.relpath(write(doc), stages.REPO))
