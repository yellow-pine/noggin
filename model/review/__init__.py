"""The review file (#915): Cansin's one Blender file of the Mech, rebuilt the same way every time from what is committed
plus the local Morty reference, which Cansin's Blender reloads once it is written (docs' startup script, #886).

`just review [coarse|medium] [before]` (`python -m model.review`): the Skeleton scene (docs/adr/0025) with the Stage 3
document just built (just ours) in place of its Scene Mech, each of the document's bones finished at the quality's
voxel, one Blender process a bone under CEILING_KB, then three scenes on the same meshes (model/review/blender.py):
Assembled (Mech, Skeleton and Morty, each in Skull, Mechanism and Pedestal, at ALPHA; a looping motion through every
horn's range), Exploded (Explode's Parts level, model/render/pictures.py offsets) and Print bed (every printed part laid
on its largest flat face, packed on BED plates); `before` adds a scene of main's bones beside the branch's. Run it in a
branch's worktree to review that branch. Written beside OUT and renamed into place, under its lock: one writer at a time.

The private Morty reference is `docs/references/morty/chelscct-morty-smith/morty-review.blend` (NOGGIN_MORTY overrides
it): an arm-free mesh named Morty, in morty-fixed.stl's raw frame, with painted material slots named by Skin Colour
group. It stays local and editable; the recipe reads it without changing it, applies the Default Skin palette and
cuts it at the model's floor. Without this sectioned reference, Morty's layer stays empty, including in a fresh clone.
"""

import fcntl
import json
import os
import subprocess
import tempfile
import time

import numpy as np
import trimesh

from model import geometry as g
from model import gimbal as gm
from model import skeleton, skin, stages
from model.render import pictures, scene

OUT = os.environ.get("NOGGIN_REVIEW", os.path.expanduser("~/Desktop/noggin-stage3.blend"))  # Cansin's review file
# the laptop's one Blender slot: scripts/heavy.py's lock, which every heavy recipe takes
SLOT = os.environ.get("NOGGIN_HEAVY_LOCK", "/tmp/noggin-heavy.lock")  # noqa: S108 one path every worktree shares
DOC = skeleton.DOC  # Stage 3, the realistic document the bones are carved for
PRESET = g.PRESETS["Morty"] | {"Skin palette": "default"}  # anatomical bones and Cansin's owned Skin filaments
QUALITY = {"coarse": 1.6, "medium": skeleton.PITCH}  # the finish's voxel, mm
CEILING_KB = 3_000_000  # a Blender process's RSS past this is killed: the laptop swaps to a crash
ALPHA = {"Mech": 1.0, "Skeleton": 0.69, "Morty": 0.33}  # innermost to outermost
REGIONS = {
    "eyes": "Skull",
    "jaw": "Skull",
    "cranium": "Skull",
    "neck": "Mechanism",
}  # else Pedestal
FPS, FRAMES = 24, 240  # the loop: 10 s, frame 1 its rest pose
STEP = 2  # a pose keyed every STEP frames
BED, GAP, PLATE_GAP = 256.0, 6.0, 60.0  # the plates' side, the room round each piece, between plates, mm
BESIDE = 300.0  # before: main's bones this far along -x of the branch's, mm
# the Morty sculpt's eye centres, raw mm (#872's measure on its front depth map, inferred), z up, -y forward
MORTY_EYES = {"L": (84.36, 245.85, 107.2), "R": (74.16, 245.85, 107.4)}
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender.py")


def _main_checkout():
    """The repo's main checkout (a worktree's references live there alone: gitignored, never copied)."""
    common = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=stages.REPO,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return os.path.dirname(common) if common else stages.REPO


MORTY = os.environ.get(
    "NOGGIN_MORTY", os.path.join(_main_checkout(), "docs/references/morty/chelscct-morty-smith/morty-review.blend")
)


def regions(doc=DOC):
    """{part: Skull, Mechanism or Pedestal}: its sub-assembly's region, a rider its carrier's (stages.RIDES)."""
    owner = {n: s for s in stages.DOCS[doc] for n in stages.SUBS[s]().parts}
    for n, carrier in stages.RIDES.items():
        if n in owner and carrier in owner:
            owner[n] = owner[carrier]
    return {n: REGIONS.get(owner[n], "Pedestal") for n in stages.STAGES[doc].parts}


def layer(file):
    """A part's layer: Skeleton for a bone, Mech for the rest, None for a Skin's Shell (the Morty layer stands for the
    Skin; its Shells show on Print bed alone)."""
    s = stages.stem(file)
    return "Skeleton" if s in g.BONES else None if s in skin.SHELLS else "Mech"


def keys(stage):
    """{horn: [(frame, degrees)]}: the loop, one horn at a time to each end of its range and back (the lids together,
    then a wink), every horn at 0 on frame 1 and FRAMES."""
    h = {n: x.limits for n, x in stage.horns.items()}
    lids = [n for n in h if " lid " in n]
    plan = [  # (frame, {horn: its end: 0 low, 1 high}); a horn left out is at rest
        (20, {"pan horn": 1}),
        (50, {"pan horn": 0}),
        (64, {}),
        (76, {"tilt horn": 1}),
        (100, {"tilt horn": 0}),
        (114, {}),
        (122, {"jaw horn": 0}),  # open
        (130, {}),
        (138, {"jaw horn": 0}),
        (146, {}),
        (156, {"yaw horn": 0}),
        (172, {"yaw horn": 1}),
        (180, {}),
        (188, {"pitch horn": 1}),
        (200, {"pitch horn": 0}),
        (208, {}),
        (214, dict.fromkeys(lids, 1)),  # wide
        (220, dict.fromkeys(lids, 0)),  # the blink (shut: the low end, inferred)
        (226, {}),
        (232, {lids[0]: 0}),  # the wink
        (FRAMES, {}),
    ]
    out = {n: [(1, 0.0)] for n in h}
    for frame, ends in plan:
        for n in h:
            out[n].append((frame, float(h[n][ends[n]]) if n in ends else 0.0))
    return out


def motion(stage, curves):
    """[(frame, {part: 4x4})] every STEP frames and on FRAMES: each horn at its curve's angle (linear between keys),
    each part where the horn that moves it puts it (the horns move disjoint parts)."""
    rest = {n: p.matrix for n, p in stage.parts.items()}
    out = []
    for frame in [*range(1, FRAMES, STEP), FRAMES]:
        mats = dict(rest)
        for horn, pts in curves.items():
            deg = float(np.interp(frame, *zip(*pts, strict=True)))
            if deg:
                for n, m in stages.pose(stage, horn, deg).parts.items():
                    if not np.allclose(m, rest[n], atol=1e-9):
                        mats[n] = m
        out.append((frame, mats))
    return out


def flat(mesh):
    """4x4 laying `mesh` on its largest flat face (its convex hull's), its long side along x, its box's low corner at
    the origin."""
    hull = mesh.convex_hull
    down = hull.facets_normal[np.argmax(hull.facets_area)]
    turn = trimesh.geometry.align_vectors(down, [0, 0, -1])
    v = trimesh.transform_points(hull.vertices, turn)
    lo, hi = v.min(axis=0), v.max(axis=0)
    if hi[1] - lo[1] > hi[0] - lo[0]:
        turn = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]) @ turn
        v = trimesh.transform_points(hull.vertices, turn)
        lo = v.min(axis=0)
    return trimesh.transformations.translation_matrix(-lo) @ turn


def pack(sizes, bed=BED, gap=GAP):
    """[(plate, x, y)] for each (width, depth): shelves, deepest first, each piece gap clear of the plate's edge and of
    each other; raises ValueError for one no plate holds."""
    out = [None] * len(sizes)
    plate, x, y, row = 0, gap, gap, 0.0
    for i in sorted(range(len(sizes)), key=lambda i: -sizes[i][1]):
        w, d = sizes[i]
        if w > bed - 2 * gap or d > bed - 2 * gap:
            raise ValueError(f"a {w:.0f} x {d:.0f} mm piece is past a {bed:.0f} mm plate")
        if x + w > bed - gap:
            x, y, row = gap, y + row + gap, 0.0
        if y + d > bed - gap:
            plate, x, y, row = plate + 1, gap, gap, 0.0
        out[i] = (plate, x, y)
        x, row = x + w + gap, max(row, d)
    return out


def plates(stage):
    """{part: (its plate, the 4x4 taking it from rest onto it)}, every printed part, plate n's corner at
    n (BED + PLATE_GAP) on x."""
    printed = [n for n, p in stage.parts.items() if stages.stem(p.file) in g.PRINTED]
    lay, sizes = {}, []
    for n in printed:
        p = stage.parts[n]
        mesh = trimesh.load(p.file, force="mesh").apply_transform(p.matrix)
        lay[n] = flat(mesh)
        size = trimesh.transform_points(mesh.convex_hull.vertices, lay[n]).max(axis=0)
        sizes.append(size[:2])
    out = {}
    for n, (plate, x, y) in zip(printed, pack(sizes), strict=True):
        out[n] = plate, trimesh.transformations.translation_matrix([plate * (BED + PLATE_GAP) + x, y, 0]) @ lay[n]
    return out


def _morty(stage):
    """Morty's place and section colours: eyes on the Mech's, scaled to their spacing; regions at the head's bottom
    and Pedestal's top, with one flat cut at the Pedestal's floor."""
    eyes = stages.align(*stages.DOCS[DOC]["eyes"])
    mech = {s: (eyes @ [*e, 1])[:3] for s, e in gm.EYE.items()}
    raw = {s: np.array(e) for s, e in MORTY_EYES.items()}
    scale = np.linalg.norm(mech["L"] - mech["R"]) / np.linalg.norm(raw["L"] - raw["R"])
    mid, raw_mid = (mech["L"] + mech["R"]) / 2, (raw["L"] + raw["R"]) / 2
    at = (
        trimesh.transformations.translation_matrix(mid)
        @ np.diag([scale] * 3 + [1])
        @ (trimesh.transformations.translation_matrix(-raw_mid))
    )
    region, box = regions(), pictures.boxes(DOC)
    bare = [n for n, p in stage.parts.items() if stages.stem(p.file) not in (*g.BONES, *skin.SHELLS)]
    skull = min(box[n][0][2] for n in bare if region[n] == "Skull")
    pedestal = max(box[n][1][2] for n in bare if region[n] == "Pedestal")
    return {
        "blend": MORTY,
        "at": at.tolist(),
        "planes": [float(pedestal), float(skull)],
        "floor": float(min(box[n][0][2] for n in bare if region[n] == "Pedestal")),
        "colours": {k: g.filament(k, PRESET)[3] for k in g.THEMES["Skin palette"][PRESET["Skin palette"]]},
    }


def job(quality="coarse", before=None):
    """What blender.py needs, JSON-ready: skeleton.job() (the parts, the carving, the finish's numbers at the quality's
    voxel), each part's region, layer, colour, Exploded offset and plate, the motion's horn curves and poses, Morty
    (None without the local reference) and main's scene for `before`."""
    stage = stages.STAGES[DOC]
    out = skeleton.job()
    out["numbers"]["Voxel"] = QUALITY[quality]
    region, offsets = regions(), pictures.offsets(DOC, 2)
    curves = keys(stage)
    out |= {
        "parts": {
            n: {
                "file": p.file,
                "region": region[n],
                "layer": layer(p.file),
                "colour": scene.colour(p.file, PRESET),
                "offset": list(map(float, offsets[n])),
            }
            for n, p in stage.parts.items()
        },
        "plates": {n: [i, m.tolist()] for n, (i, m) in plates(stage).items()},
        "alpha": ALPHA,
        "fps": FPS,
        "frames": FRAMES,
        "horns": curves,
        "motion": [[f, {n: m.tolist() for n, m in mats.items()}] for f, mats in motion(stage, curves)],
        "morty": _morty(stage) if os.path.isfile(MORTY) else None,
        "bed": [BED, PLATE_GAP],
        "before": before,
        "beside": BESIDE,
    }
    return out


def _blender(args, ceiling_kb=CEILING_KB):
    """One headless Blender on `args`, killed once its RSS passes ceiling_kb; raises on a failure or a kill."""
    log = tempfile.TemporaryFile("w+")  # a file, not a pipe: a full pipe would stall Blender
    p = subprocess.Popen([skeleton.BLENDER, "-b", "--factory-startup", *args], stdout=log, stderr=subprocess.STDOUT)
    peak = 0
    while p.poll() is None:
        rss = subprocess.run(["ps", "-o", "rss=", "-p", str(p.pid)], capture_output=True, text=True).stdout.strip()
        peak = max(peak, int(rss or 0))
        if peak > ceiling_kb:
            p.kill()
            p.wait()
            raise RuntimeError(f"Blender passed {ceiling_kb // 1000} MB on {args[-1]}: killed")
        time.sleep(0.5)
    log.seek(0)
    log = log.read()
    if p.returncode or "review: done" not in log:
        raise RuntimeError(f"Blender failed on {args[-1]}:\n{log[-4000:]}")
    print(f"review: {args[-1]} in {peak // 1000} MB", flush=True)


def lock(path, wait=False):
    """flock(2) on `path`, held (an open file) until it is closed or the process ends: waited for, or SystemExit when
    another process holds it."""
    f = open(path, "a+")  # noqa: SIM115 held by the caller
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        if not wait:
            f.close()
            raise SystemExit(f"review: another writer holds {path}; try again once it is done") from None
        print(f"review: waiting for {path}, the laptop's one Blender slot", flush=True)
        fcntl.flock(f, fcntl.LOCK_EX)
    return f


def build(out=OUT, quality="coarse", before=False):
    """The review file at `out`: written beside it and renamed into place, under its lock (one writer) and the Blender
    slot (one Blender)."""
    held, part = [lock(out + ".lock")], out.removesuffix(".blend") + ".tmp.blend"  # beside it: one disk's rename
    try:
        held.append(lock(SLOT, wait=True))
        with tempfile.TemporaryDirectory() as tmp:
            main = None
            if before:
                main = os.path.join(tmp, "main.blend")
                with open(main, "wb") as f:
                    subprocess.run(
                        ["git", "show", f"origin/main:{skeleton.SCENE}"], cwd=stages.REPO, stdout=f, check=True
                    )
            path = os.path.join(tmp, "job.json")
            with open(path, "w") as f:
                json.dump(job(quality, main), f)
            scene_ = os.path.join(stages.REPO, skeleton.SCENE)
            _blender([scene_, "-P", SCRIPT, "--", path, part, "assemble"])
            for stem in g.BONES:
                if f"{stem}:1" in stages.STAGES[DOC].parts:
                    _blender([part, "-P", SCRIPT, "--", path, part, stem])
            _blender([part, "-P", SCRIPT, "--", path, part, "scenes"])
            os.replace(part, out)
    finally:
        if os.path.exists(part):  # a failed run's half
            os.remove(part)
        for f in held:
            f.close()
    print(f"review: wrote {out}", flush=True)
