"""The realistic Skeleton's bones (docs/adr/0025): authored in the Skeleton scene (model/skeleton/skeleton.blend), its
bones in the Stage 3 document's frame, each finished by its own Geometry Nodes modifier (model/skeleton/build.py wrote
them: the cranium shelled to WALL, the orbits opened round the lids and the Cores' USB-C openings cut out, everything
riding the bone cut out and everything moving against it CLEAR_MM round, crumbs dropped, meshed at PITCH).

finish() hands Blender the scene and the document just built: Blender (model/skeleton/export.py) deletes the Scene
Mech, puts each part of next-mech-back where the bone sees it, at rest and over each horn's range, runs every finish
and writes each bone's STL in the head's frame (model/build/ours), which model/stages.py places as before."""

import json
import os
import subprocess

import numpy as np
import trimesh

from model import base, stages
from model import geometry as g
from model import gimbal as gm
from model import skin as sk

SCENE, EXPORT = "model/skeleton/skeleton.blend", "model/skeleton/export.py"
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
DOC = "next-mech-back"  # the realistic document the bones are carved for
PITCH, CLEAR_MM, WALL = 0.8, 1.6, 4.0  # the finish's voxel; the room round every moving part; the cranium's shell
KEEP = 0.02  # a piece carving leaves, of the bone's largest, under which it is dropped
REACH = 16.0  # the orbits opened round each eye to its lids' outer radius, back to where their spokes reach


def poses(stage):
    """[{part: 4x4}]: the document at rest and each horn at points over its range (the lids' finer: they sweep the
    orbits)."""
    out = [{n: p.matrix for n, p in stage.parts.items()}]
    for horn, h in stage.horns.items():
        for deg in np.linspace(*h.limits, 9 if " lid " in horn else 5):
            out.append(stages.pose(stage, horn, deg).parts)
    return out


def job():
    """What export.py needs, JSON-ready: the head's frame in the document; each cutting part's STL; for each bone, the
    places (4x4, the document's frame) of every part as the bone sees it over every pose, sorted into what rides it
    (one place), what moves against it and the Shells (cut from the worn copy alone); the skull's openings (the
    orbits, the USB-C boxes, head's frame) and the finish's numbers."""
    stage = stages.STAGES[DOC]
    rest = {n: p.matrix for n, p in stage.parts.items()}
    files = {n: p.file for n, p in stage.parts.items() if stages.stem(p.file) not in g.BONES}
    shells = {n for n in files if stages.stem(files[n]) in sk.SHELLS}
    every = poses(stage)
    bones = {}
    for bone in g.SKULL:
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
        bones[bone] = sorted_
    return {
        "frame": list(stages.DOCS[DOC]["next-eyes"][0]),
        "files": files,
        "rest": {n: rest[n].tolist() for n in files},
        "bones": bones,
        "worn": g.WORN,
        "orbits": [[list(e), gm.LOWER_R[1] + CLEAR_MM] for e in gm.EYE.values()],
        "reach": REACH,
        "openings": [[list(lo), list(hi)] for lo, hi in base.openings().values()],
        "numbers": {"Voxel": PITCH, "Clearance": CLEAR_MM, "Wall": WALL, "Keep": KEEP},
    }


def finish(out=stages.OURS):
    """Each of g.BONES as an STL in `out`, the head's frame at rest, from the scene and the parts already in `out`."""
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "skeleton-job.json")
    with open(path, "w") as f:
        json.dump(job() | {"out": out}, f)
    blend, script = (os.path.join(stages.REPO, p) for p in (SCENE, EXPORT))
    r = subprocess.run(
        [BLENDER, "-b", "--factory-startup", blend, "-P", script, "--", path], capture_output=True, text=True
    )
    if r.returncode or "export: done" not in r.stdout:
        raise RuntimeError(f"Blender's finish failed:\n{r.stdout[-4000:]}\n{r.stderr[-4000:]}")
    for stem in g.BONES:  # each written whole: a finish that met nothing still leaves a bone
        assert len(trimesh.load(os.path.join(out, stem + ".stl"), force="mesh").faces), stem
