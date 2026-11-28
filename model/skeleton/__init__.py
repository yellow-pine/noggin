"""The realistic Skeleton's bones (docs/adr/0025): authored in the Skeleton scene (model/skeleton/skeleton.blend), its
bones in the Stage 3 document's frame, each finished by its own Geometry Nodes modifier (model/skeleton/build.py wrote
them: the skull's bones sealed into one, the cranium shelled to WALL, the orbits opened round the lids, everything
riding the bone cut out and everything moving against it CLEAR_MM round, crumbs dropped, meshed at PITCH).

finish() hands Blender the scene and the document just built: Blender (model/skeleton/export.py) deletes the Scene
Mech, puts each part of mech-back where the bone sees it, at rest and over each horn's range, runs every finish
and writes each bone's STL in the head's frame (model/build/ours), which model/stages.py places as before."""

import json
import os
import shutil
import subprocess

import numpy as np
import trimesh

from model import geometry as g
from model import gimbal as gm
from model import neck as nk
from model import skin as sk
from model import stages

SCENE, EXPORT = "model/skeleton/skeleton.blend", "model/skeleton/export.py"
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
DOC = "mech-back"  # the realistic document the bones are carved for
PITCH, CLEAR_MM, WALL = 0.8, 1.6, 4.0  # the finish's voxel; the room round every moving part; the cranium's shell
FLOOR = 2.0  # #838's print rules: nothing thinner; the skull opened by half of it (export.rounded)
# the skull's 21 bones are one bone across every gap under twice this (export.rounded): BodyParts3D's only abut, and
# the palate hangs on the R maxilla's back, 1.4 mm off the sphenoid's pterygoid process where the two can meet (#874)
SEAL = 1.5
# the vault's bones (fit.VAULT) are at least this thick, inward: the print floor and half the finish's voxel, which
# its remesh can thin a bone by. The parietals are 0.8 to 2.2 mm thick at the temples (#874)
THICK = FLOOR + PITCH / 2
KEEP = 0.02  # a piece carving leaves, of the bone's largest, under which it is dropped
# the orbits opened round each eye, ORBIT in radius (the lids' before #967 hid them, 47.5 mm, and the room round a
# moving part: the skull keeps the orbits it was fitted with, #874), back to where those lids' spokes reached
ORBIT, REACH = 49.1, 16.0
# #967's re-laid lids (Cansin, 2026-11-27, its comment 7208456325): they stow all round each eye centre (gimbal.EYE,
# on the Sculpt's own eyeballs' since #1035) in a shell of radius up to LID_SHELL (their band 36.3 to 37.5 mm and
# 0.5 over it, #967's comment 7209215753), and the yaw rails, the tie-bar's fingers and the pitch rods leave it through the belt behind
# the eye, between the stowed lids (their turn 174 to 214 deg). The skull keeps out of both before those parts exist
# (then the Finish carves round them as round every part). BELT, about an eye centre: its half-width along the lids'
# axis, and how far back it runs, to behind where the tie-bar and the bail's axis will stand (the paper sketch's, inferred)
LID_SHELL, BELT = 38.0, (22.0, 48.0)
BELT_Z = tuple(round(float(LID_SHELL * np.sin(np.radians(a))), 1) for a in (214.0, 174.0))
# The skull's calvaria (g.SKULL's CAP) comes off as a cap, so the head's mechanism can be reached (#874, docs/adr/0025):
# each skull's own Finish cut in two (export.capped) along a seam level in the head's frame at SEAM_Z. Flat, as a
# teaching skull's cut is, and the cap prints lying on it. It sits on three Seats (model/skin.py: the Skin's own, so
# a Shell's Seat in bone is cut the same way), each on a ball boss of skin.PAD_R on the vault's inner side, the wall
# there being 4 to 9 mm: a magnet flush in each face, three balls standing on the skull's and their V-grooves in
# the cap's, which take the shear and hold the faces skin.GAP apart, so a hair Shell seated on the cap lands where
# it was. SEAM_Z is the lowest whole ring with FLOOR of bone left over the lids' shell (the finished skull is open in
# front under z 50). SEATS (x, y in the head's frame) stand in front and to each side, behind the cap's centre of
# mass (y 75), each boss a mm inside the skull's outer faces, where the mechanism leaves 37 mm and more (the nod
# plate's sweep leaves 8 mm straight behind and 13 at 70 deg round). Measured on the uncut skull, 2026-11-28; inferred
CAP, CAPPED = "calvaria", "skull"
# How a bone comes off the part it rides (#968; Cansin, 2026-11-28, #893's sixth round: the mandible off its carrier
# in one piece): {bone: (the way it leaves, a unit vector in the head's frame at rest; how far, mm)}. One stiff U off
# another, so in the head's middle plane; the Finish cuts the carrier's way out of the bone as well as the carrier.
# The mandible's: down and 30 deg forward. Straight down its condyles run 2.2 mm into the skull's mastoids behind
# them (15 deg forward they still touch); this way nothing but the carrier stands in it, and 40 mm on the carrier's
# pivots are over the bone's top (measured on the finished bones, 2026-11-28; inferred)
OFF = {"mandible": ((0.0, -0.5, -0.8660254), 40.0)}
OFF_STEP = 1.0  # the carrier's places along that way, mm apart: under the Finish's voxel, so their cuts run together
SEAM_Z = 54.0
SEATS = ((0.0, 3.0), (76.0, 83.5), (-77.0, 83.5))
# A Skin's Seat in bone (model/skin.py SEATS, #850) is a flat cut into the bone, the Seat's pad and this much wider
# all round, so the Shell's boss stands in it clear of the bone beside it (inferred)
SEAT_ROOM = 0.5
# A bone's plain magnet pockets (#968), {bone: [(the pocket's mouth, the way out of the bone), ...]}, the head's frame:
# a magnet's flush pocket and nothing round it, cut from the mesh as a Seat's is. The mandible's two, face to face
# with the jaw's on the front of its bar (model/neck.py JAW_HOLD), which hold the bone on its carrier
POCKETS = {"mandible": [(at, (0.0, 1.0, 0.0)) for at in nk.JAW_HOLD]}


def blender():
    """Whether the finish can run here: Blender found, or CI, which always has it (a missing one fails there, never
    skips). The native GX10 worker supplies its pinned Blender; another host without it leaves bones unfinished."""
    return bool(os.environ.get("CI") or shutil.which(BLENDER))


def poses(stage):
    """[{part: 4x4}]: the document at rest and each horn at points over its range (the lids' finer: they sweep the
    orbits)."""
    out = [{n: p.matrix for n, p in stage.parts.items()}]
    for horn, h in stage.horns.items():
        for deg in np.linspace(*h.limits, 9 if " lid " in horn else 5):
            out.append(stages.pose(stage, horn, deg).parts)
    return out


def seat(s):
    """A Skin's Seat in bone (model/skin.py SEATS, its carrier one of g.SKULL) as export.py cuts it: [its carrier's
    two copies, the bare and the worn; its frame in the head's (4x4 rows, z out of the bone); its pad, a ball on its
    axis (how far under the Seat's face its middle is, its radius), None for a Seat with no pad]. The pad makes the
    bone solid FLOOR round the magnet's pocket at its floor, and behind the pocket's whole bore to `s.pad` under the
    face: the ball through both rims, and half a voxel, which the Finish's grid may round off it."""
    pad = None
    if s.pad:
        bore, d = sk.MAGNET[0] / 2 + sk.FIT, sk.MAGNET[1]
        under = (bore**2 + s.pad**2 - (bore + FLOOR) ** 2 - d**2) / (2 * (s.pad - d))
        pad = [under, float(np.hypot(bore, s.pad - under)) + PITCH / 2]
    return [[s.carrier, g.WORN[s.carrier]], np.array(sk.frame(s)).tolist(), pad]


def job(stage=None):
    """What export.py needs, JSON-ready, for `stage` (DOC's own unless given: a document that wears more, as
    review.worn() wears every Shell): the head's frame in the document; each cutting part's STL; for each bone, the
    places (4x4, the document's frame) of every part as the bone sees it over every pose, sorted into what rides it
    (one place), what moves against it and the Shells (cut from the worn copy alone); the skull's openings (head's
    frame: each orbit a ball, cut off at y `back` where one is given, and each belt a box), its cap (CAP: which
    Finish it is cut off, the seam, and each Seat's boss, pocket, balls and grooves, head's frame), the Skin's Seats
    in bone (seat(), and their flats' radius), the bones' plain pockets (POCKETS: [a bone's two copies, the pocket's
    frame in the head's, z out of the bone at its mouth]) and the finish's numbers."""
    from model.skeleton import fit  # here: fit reads this module's numbers

    stage = stage or stages.STAGES[DOC]
    rest = {n: p.matrix for n, p in stage.parts.items()}
    files = {n: p.file for n, p in stage.parts.items() if stages.stem(p.file) not in g.BONES}
    shells = {n for n in files if stages.stem(files[n]) in sk.SHELLS}
    every = poses(stage)
    bones = {}
    for bone in (b for b in g.SKULL if b != CAP):  # the cap is carved with its skull, in the one Finish
        carrier, seen = stages.RIDES[bone + ":1"], {}
        for pose in every:
            back = rest[carrier] @ np.linalg.inv(pose[carrier])  # the document as the bone sees it there
            for n in files:
                at = back @ pose[n]
                places = seen.setdefault(n, [])
                if not any(np.allclose(at, q, atol=1e-6) for q in places):
                    places.append(at)
        sorted_ = {"rigid": [], "moving": [], "skins": []}
        for n, places in seen.items():
            kind = "skins" if n in shells else "rigid" if len(places) == 1 else "moving"
            sorted_[kind] += [[n, at.tolist()] for at in places]
        way, far = OFF.get(bone, ((0.0, 0.0, 0.0), 0.0))
        for mm in np.arange(OFF_STEP, far + OFF_STEP / 2, OFF_STEP):  # the bone that far on its way off
            at = rest[carrier].copy()
            at[:3, 3] -= mm * np.array(way)
            sorted_["rigid"].append([carrier, at.tolist()])
        bones[bone] = sorted_
    return {
        "frame": list(stages.DOCS[DOC]["eyes"][0]),
        "files": files,
        "rest": {n: rest[n].tolist() for n in files},
        "bones": bones,
        "worn": g.WORN,
        "orbits": [
            *([list(e), ORBIT, REACH] for e in gm.EYE.values()),
            *([list(e), LID_SHELL + CLEAR_MM, None] for e in gm.EYE.values()),
        ],
        "belts": [
            [[x - BELT[0], y, z + BELT_Z[0] - CLEAR_MM], [x + BELT[0], y + BELT[1], z + BELT_Z[1] + CLEAR_MM]]
            for x, y, z in gm.EYE.values()
        ],
        "cap": {
            "of": {CAPPED: CAP, g.WORN[CAPPED]: g.WORN[CAP]},
            "seam": SEAM_Z,
            "gap": sk.GAP,
            "seats": list(map(list, SEATS)),
            "boss": sk.PAD_R,
            "bore": [sk.MAGNET[0] / 2 + sk.FIT, sk.MAGNET[1]],
            "ball": [sk.RING, sk.BALL_R],
            "groove": [sk.GROOVE, sk.GROOVE_D],
        },
        "seats": {
            "at": [seat(s) for s in sk.SEATS if s.carrier in g.SKULL],
            "flat": sk.PAD_R + SEAT_ROOM,
            "back": sk.MAGNET[1] + FLOOR,
        },
        "pockets": [
            [[bone, g.WORN[bone]], np.array(g.align_rows(at, (1, 0, 0), out)).tolist()]
            for bone, pockets in POCKETS.items()
            for at, out in pockets
        ],
        "vault": {"bones": sorted(fit.VAULT), "middle": list(fit.MIDDLE)},
        "numbers": {
            "Thick": THICK,
            "Voxel": PITCH,
            "Clearance": CLEAR_MM,
            "Wall": WALL,
            "Keep": KEEP,
            "Seal": SEAL,
            "Round": FLOOR / 2,
        },
    }


def finish(out=stages.OURS, stage=None):
    """Each of g.BONES as an STL in `out`, the head's frame at rest, from the scene and job(stage)'s parts, built
    already."""
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "skeleton-job.json")
    with open(path, "w") as f:
        json.dump(job(stage) | {"out": out}, f)
    blend, script = (os.path.join(stages.REPO, p) for p in (SCENE, EXPORT))
    r = subprocess.run(
        [BLENDER, "-b", "--factory-startup", blend, "-P", script, "--", path], capture_output=True, text=True
    )
    if r.returncode or "export: done" not in r.stdout:
        raise RuntimeError(f"Blender's finish failed:\n{r.stdout[-4000:]}\n{r.stderr[-4000:]}")
    for stem in g.BONES:  # each written whole: a finish that met nothing still leaves a bone
        assert len(trimesh.load(os.path.join(out, stem + ".stl"), force="mesh").faces), stem
