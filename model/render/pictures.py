"""Every picture the site serves (published()), rendered in Blender (#47; rules in docs/model-notes.md), each document
posed from its baked trajectories (model/trajectories.py, `just trajectories`): MuJoCo's poses (#150). Each picture is a
WebP with a transparent background, its lines one grey for the site's light and dark themes (blender.py INK, #470).
`views` (`just render`): the panels (each Stage in each Preset at rest, #819, a trajectory's first frame, from the
side and isometric, framed among themselves: PANELS), the front doors' own (FRONT, #739) and each Stage at Explode's
Parts level (parts_exploded, #811). `site next` (`just pictures next`, Checks'
Render shards, each its share: SHARD): what the site serves into model/build/images (#649): those, the eye gimbal in
motion (NEXT_MOTIONS: its sweep, #656, and each motion it plays, #663) and a picture per part.
Usage: python -m model.render.pictures views | site next (Blender at $BLENDER)"""

import functools
import json
import math
import os
import shutil
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
import trimesh

from model import geometry as g
from model import gimbal, stages, trajectories
from model.render import camera, scene

OUT = os.path.join(stages.REPO, "model", "build", "pictures")
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
# "i/n" (from 0): `site next` renders shard i of n's share alone, Checks' Blender shards (#770)
SHARD = os.environ.get("PICTURES_SHARD")
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender.py")
# the panels (Cansin, #470): each document from its left side and isometric from its front left, by eye direction and
# up, at one scale on one ground line, framed tight: the largest panel's silhouette plus PAD of it each side
VIEWS = {"side": (g.X, g.Z), "isometric": ((1, -1, 1), g.Z)}
# the pictures per Preset alone (#819): {name: (document, Preset)}, each Stage in the Preset's Skeleton shape painted in
# its Palettes, named by the Stage as Bones, the default Preset's alone, another's -<its slug> (next-stage1-morty)
SUFFIX = {p: f"-{g.slug(p)}" if i else "" for i, p in enumerate(g.PRESETS)}
BONY = [d for d in g.STAGES if g.shape(d) == g.THEMES["Skeleton shape"][0]]  # the Stages in order, as Bones
DRAWN = {s + SUFFIX[p]: (s + g.SKELETON_SUFFIX[t["Skeleton shape"]], p) for p, t in g.PRESETS.items() for s in BONY}
PANELS = [(name, view) for name in DRAWN for view in VIEWS]
PANEL_WIDTH, PAD = 800, 0.03
LENS, MARGIN = 90, 1.06  # a long lens: little perspective distortion so close
# the motions' view (the old README hero's): from 15 deg to the Mech's right (right eye nearest), 15 deg up
_R = math.radians(15)
HERO = math.cos(_R) * np.array((-math.sin(_R), -math.cos(_R), 0)) + (0, 0, math.sin(_R))
HERO_FPS = 8
WEBP_QUALITY = 85  # lossy colour, lossless alpha
# the web viewer's exploded next Mech (macros.py explode, #482, #664), mm: the neck lifted off the base, the eyes off
# the neck (or Stage 1's stand), the boards off what carries them: the rack back with the head it rides, the jaw forward
EXPLODE = {
    "next-base": (0, 0, 0),
    "next-stand": (0, 0, 0),
    "next-neck": (0, 0, 45),
    "next-jaw": (0, -40, 45),
    "next-eyes": (0, 0, 95),
    "next-back": (0, 60, 95),
}
# Explode's Parts level (#811): each part out along its Assembly direction (GLOSSARY) on its sub-assembly's offset, at
# least GAP clear of every part's bounding box, mm (inferred); a seated part's direction off its seat: a Core and its
# Shield back out of its cradle (model/base.py back_boards) or off the test stand's face, the switch board and the pack
# up off the Torso's floor (stages.next_base)
GAP = 5.0
SEATS = {"receiver": g.Y, "core": g.Y, "switch": g.Z, "battery": g.Z}
# the front doors (#739: the README's top, the site's home), side by side in this order, in each Preset (#806, #819),
# the default's first: Stage 1 from the front, its eyes facing the camera; Stage 3 isometric, its panel (None); Stage 3
# from the side, exploded (EXPLODE); each (DRAWN's name, eye direction, exploded), framed tight on its own at the
# panels' size
STAGE1, STAGE3 = BONY[0], next(iter(g.NEXT))
FRONT = {
    f: how
    for s in SUFFIX.values()
    for f, how in {
        f"{STAGE1}{s}-front.webp": (STAGE1 + s, (0, -1, 0), False),
        f"{STAGE3}{s}-isometric.webp": None,
        f"{STAGE3}{s}-side-exploded.webp": (STAGE3 + s, VIEWS["side"][0], True),
    }.items()
}
IMAGES = os.path.join(stages.REPO, "model", "build", "images")
# what the site publishes (#649, docs/adr/0019): the next Mech's panels and a picture of each of its parts, alone at
# rest, isometric, framed on its own; every name next-
NEXT = "next"
PART_SIZE = (400, 400)
# the next Mech in motion, next-eyes alone in each Preset (#806, #819) through one camera at HERO_FPS: its eye gimbal's
# sweep through its whole range (#656), moved by its own kinematics (model/gimbal.py moved), keyed by hand as (seconds, yaw, pitch, L lid, R lid) in
# degrees, eased from key to key and looping from rest, the lids following the pitch (#51); then each motion it plays,
# its gestures and Rest (None: as MuJoCo baked it, next_played, #663)
_Y, _P = gimbal.YAW, gimbal.PITCH
NEXT_MOTIONS = {
    "sweep": [(0, 0, 0, 0, 0), (1, -_Y, 0, 0, 0), (2.5, _Y, 0, 0, 0), (3.5, 0, 0, 0, 0), (4.25, 0, _P, _P, _P),
              (5.5, 0, -_P, -_P, -_P), (6.25, 0, 0, 0, 0)],
    **dict.fromkeys(trajectories.traces.NEXT_MOTIONS),
}  # fmt: skip
MOTION_SIZE = (480, 320)


def picture(name, view):
    return f"{name}-{view}.webp"


def parts_exploded(name):
    """A Stage's picture (DRAWN's name) at Explode's Parts level (#811): isometric, framed tight on its own at the
    panels' size."""
    return f"{name}-parts-exploded.webp"


@functools.cache
def next_parts():
    """{picture: (document, part)}: one per part of the next Mech's documents by its mesh, its first instance."""
    out = {}
    for doc in g.STAGES:
        for name, p in stages.STAGES[doc].parts.items():
            stem = stages.stem(p.file).removeprefix("next ")
            out.setdefault(f"next-{stem.lower().replace(' ', '-')}.webp", (doc, name))
    return out


def next_motion(motion, preset):
    return f"next-eyes{SUFFIX[preset]}-{motion}.webp"


def published():
    """Every picture the site serves (#649): the next Mech's panels, the front doors' own (#739), each Stage at the
    Parts level (#811), its motions (#656), each in each Preset (#806, #819), then its parts'."""
    front = [f for f, how in FRONT.items() if how]
    apart = map(parts_exploded, DRAWN)
    moving = [next_motion(m, p) for p in g.PRESETS for m in NEXT_MOTIONS]
    return [*(picture(*p) for p in PANELS), *front, *apart, *moving, *next_parts()]


def exploded(doc, mats, level=1):
    """mats ({part: world 4x4}, metres) with each part moved by its offset at the level (offsets), as the viewer's
    Explode moves it (web/build.py)."""
    apart = offsets(doc, level)
    return {n: stages.translate(apart[n] / 1000) @ m for n, m in mats.items()}


@functools.cache
def boxes(doc):
    """{part: (low, high corner)}: each part's world bounding box at rest, mm, its leads cut as the pictures draw it
    (scene.export)."""
    out = {}
    for n, p in stages.STAGES[doc].parts.items():
        mesh = trimesh.load(p.file, force="mesh")
        v, f = mesh.vertices, mesh.faces
        if p.clip:
            axis, cut = p.clip
            f = f[(v[f][:, :, "xyz".index(axis)] <= cut + 0.1).all(axis=1)]
        v = trimesh.transform_points(v[f.ravel()], p.matrix)
        out[n] = (v.min(axis=0), v.max(axis=0))
    return out


def directions(doc):
    """{part: its Assembly direction's axis, world}: a servo and its Horn out along the shaft (stages.mounted), a seated
    part off its seat (SEATS), any other the axis of the innermost joint that turns it in its own sub-assembly (of the
    Pivots and rod joints it is on, the one with fewest parts), signed later (offsets). What no joint turns (the Torso,
    the mounts, the frames, the rack) has none: the rest is assembled on it."""
    joints = []  # (the parts a joint turns, its world axis)
    for sub, frame in stages.DOCS[doc].items():
        turn = stages.align(*frame)[:3, :3]
        for horn in stages.SUBS[sub]().horns.values():
            for loop in horn.loops:
                axis = turn @ loop.rocker_pivot[1]
                joints += [([loop.coupler], axis), (loop.rockers, axis)]
            for rod in horn.rods:
                joints += [([rod.part], turn @ np.reshape(rod.axes, (-1, 3))[0]), (rod.driven, turn @ rod.hinge[2])]
    out = {}
    for n, p in stages.STAGES[doc].parts.items():
        s = stages.stem(p.file)
        if s in ("servo", "horn"):
            out[n] = (-p.matrix[:3, 2], True)  # its local z is the shaft's reverse (stages.mounted)
        elif s in SEATS:
            out[n] = (np.array(SEATS[s], float), True)
        elif on := [(len(parts), axis) for parts, axis in joints if n in parts]:
            out[n] = (min(on, key=lambda j: j[0])[1], False)
    return out


@functools.cache
def offsets(doc, level):
    """{part: its offset, mm} at an Explode level (#811): 0 assembled; 1 its sub-assembly's EXPLODE offset (#482);
    2 that and on out along its Assembly direction (directions; a joint's axis away from the document's middle) until
    its bounding box is GAP clear of its own there and of every part placed before it: what the rest is assembled on
    first (each on out along its sub-assembly's offset while it meets one placed), then the largest first, so what sits
    on a part comes off beyond it."""
    sub = {n: s for s in stages.DOCS[doc] for n in stages.SUBS[s]().parts}
    out = {n: np.array(EXPLODE[sub[n]] if level else (0, 0, 0), float) for n in stages.STAGES[doc].parts}
    if level < 2:
        return out
    box, axes = boxes(doc), directions(doc)
    middle = np.mean([lo + hi for lo, hi in box.values()], axis=0) / 2
    placed = []
    for n in sorted(box, key=lambda n: (n in axes, -np.prod(np.subtract(*box[n][::-1])))):
        lo, hi = box[n][0] + out[n], box[n][1] + out[n]
        if n in axes:
            d, signed = axes[n]
            d = np.round(d / np.linalg.norm(d), 9)
            if not signed and np.dot((lo + hi) / 2 - middle, d) < -0.5:  # a part on the middle goes the axis' way
                d = -d
            out[n] = out[n] + _clear(lo, hi, d, [(lo, hi), *placed]) * d
        elif any(d := EXPLODE[sub[n]]):  # one the rest goes on, among another's (the rack, #817): on out
            d = np.divide(d, np.linalg.norm(d))  # along its sub-assembly's offset until clear of what is placed
            out[n] = out[n] + _clear(lo, hi, d, placed) * d
        lo, hi = box[n][0] + out[n], box[n][1] + out[n]
        placed.append((lo, hi))
    return out


def _clear(lo, hi, d, blockers):
    """The least t >= 0 that moves the box (lo, hi) by t d at least GAP clear of every blocker box."""
    spans, moving = [], d != 0
    for blo, bhi in blockers:
        blo, bhi = blo - GAP, bhi + GAP
        if not np.all(moving | ((lo < bhi) & (hi > blo))):
            continue  # apart on an axis it does not move along: never meets it
        a, b = (blo[moving] - hi[moving]) / d[moving], (bhi[moving] - lo[moving]) / d[moving]
        t0, t1 = np.max(np.minimum(a, b)), np.min(np.maximum(a, b))
        if t0 < t1:
            spans.append((t0, t1))
    t = 0.0
    for t0, t1 in sorted(spans):  # each span it would overlap in, by its start: past each it is inside of
        if t0 < t < t1:
            t = t1
    return t


def share(frames, i, n):
    """The pictures shard i of n (from 0) renders, of {picture: its frames}: each, longest first, to the shard with the
    fewest frames so far (as model/shards.py deals the model's units)."""
    loads = [[] for _ in range(n)]
    for f in sorted(frames, key=lambda f: -frames[f]):
        min(loads, key=lambda load: sum(frames[p] for p in load)).append(f)
    return loads[i]


def next_motions(rest):
    """{motion: [{next-eyes part: world 4x4, metres} per frame]} for each keyed motion of NEXT_MOTIONS, from `rest`,
    those parts at rest as MuJoCo settles the next Mech: each moved in its own frame as model/gimbal.py moves it in
    next-eyes'."""
    local = {n: p.matrix for n, p in stages.next_eyes().parts.items()}
    out = {}
    for motion, keys in NEXT_MOTIONS.items():
        if keys is None:  # played: next_played
            continue
        keys = np.array(keys, float)
        t = np.arange(round(keys[-1, 0] * HERO_FPS)) / HERO_FPS
        i = np.searchsorted(keys[:, 0], t, "right") - 1
        ease = (1 - np.cos(np.pi * (t - keys[i, 0]) / (keys[i + 1, 0] - keys[i, 0]))) / 2
        out[motion] = []
        for yaw, pitch, left, right in keys[i, 1:] + (keys[i + 1, 1:] - keys[i, 1:]) * ease[:, None]:
            m, frame = gimbal.moved({"L": left, "R": right}, pitch, yaw), {}
            for n, p in local.items():
                turn = np.linalg.inv(p) @ m[n] @ p if n in m else np.eye(4)
                turn[:3, 3] /= 1000  # mm, as the meshes are drawn in metres
                frame[n] = rest[n] @ turn
            out[motion].append(frame)
    return out


def prepare(name, doc=None):
    """(stage, manifest with absolute PLY paths, hull points per part) for one document's pictures under name: DRAWN's,
    in its Preset's colours (#819), or a document's own in its Theme's (#805), its parts as model/stages.py assembles
    them, exported once. Always our geometry (model/build/ours, `just ours`), never the designer's meshes."""
    doc, preset = (doc, None) if doc else DRAWN[name]
    stage = stages.STAGES[doc]
    folder = os.path.join(OUT, "meshes", name)
    os.makedirs(folder, exist_ok=True)
    manifest = scene.export(doc, folder, g.PRESETS.get(preset))
    for p in manifest.values():
        p["ply"] = os.path.join(folder, p["ply"])
    return stage, manifest, hulls(manifest)


def hulls(manifest):
    """Each part's convex hull vertices, in its own frame: what a camera fits (camera.fit) as it would every vertex."""
    return {n: trimesh.load(p["ply"]).convex_hull.vertices for n, p in manifest.items()}


def points(hulls, mats):
    return np.concatenate([trimesh.transform_points(hulls[n], np.array(m)) for n, m in mats.items()])


def shot(name, size, cam, poses, first=0):
    """A Blender shot (blender.py), one frame per pose in OUT/frames/<name>/frameNNNN.png, numbered from first."""
    c = {"matrix": cam.matrix.tolist(), "lens": cam.lens, "ortho_scale": cam.ortho_scale}
    return {
        "out": os.path.join(OUT, "frames", name),
        "size": list(size),
        "camera": c,
        "first": first,
        "poses": [{n: np.asarray(m).tolist() for n, m in pose.items()} for pose in poses],
    }


def blender(name, manifest, shots):
    job = os.path.join(OUT, "meshes", name, "job.json")
    json.dump({"parts": manifest, "shots": shots}, open(job, "w"))
    r = subprocess.run([BLENDER, "-b", "-P", SCRIPT, "--", job], capture_output=True, text=True)
    files = [os.path.join(s["out"], f"frame{s['first'] + i:04d}.png") for s in shots for i in range(len(s["poses"]))]
    missing = [f for f in files if not os.path.isfile(f)]
    if r.returncode or missing:
        sys.exit(f"Blender failed on {name}, missing {missing[:3]}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    frames = [line for line in r.stdout.splitlines(True) if line.startswith("frame ")]
    print("".join(frames), end="")
    return [float(line.split()[2]) for line in frames]  # each frame's seconds


def render(name, manifest, shots, mine, fps=None):
    """The shots of the pictures in mine alone (published(), or a Blender shard's share: share, #770), in one Blender
    run, each encoded."""
    shots = [s for s in shots if os.path.basename(s["out"]) + ".webp" in mine]
    if shots:
        blender(name, manifest, shots)
    for s in shots:
        encode(os.path.basename(s["out"]), fps)


def views(mine):
    """The panels (PANELS: each Stage in each Preset at rest as MuJoCo settles it, where every gesture starts), at one
    scale and one frame: the largest silhouette among them; those in mine alone are rendered."""
    plans = {}
    for name, (doc, _) in DRAWN.items():
        _, manifest, hulls = prepare(name)
        mats = trajectories.poses(doc, "wink")[0]
        plans[name] = (manifest, hulls, mats, points(hulls, mats))
    fits = {(n, v): camera.fit(plans[n][3], *VIEWS[v], 1) for n, v in PANELS}
    # one scale and one frame for every panel: the widest and the tallest silhouette, PAD of the larger round them
    w, h = np.max([[np.ptp(plans[n][3] @ c.matrix[:3, i]) for i in (0, 1)] for (n, _), c in fits.items()], axis=0)
    pad = PAD * max(w, h)
    w, h = w + 2 * pad, h + 2 * pad
    size = (PANEL_WIDTH, 2 * round(PANEL_WIDTH * h / w / 2))
    for name, (manifest, hull, mats, pts) in plans.items():
        shots = [shot(f"{name}-{v}", size, camera.stand(fits[name, v], pts, w, w / h, pad / h), [mats]) for v in VIEWS]
        for f, (_, eye, apart) in ((f, how) for f, how in FRONT.items() if how and how[0] == name):
            pose = exploded(DRAWN[name][0], mats) if apart else mats
            cam = camera.fit(points(hull, pose), eye, g.Z, size[0] / size[1], None, MARGIN)
            shots.append(shot(f.removesuffix(".webp"), size, cam, [pose]))
        pose = exploded(DRAWN[name][0], mats, 2)
        cam = camera.fit(points(hull, pose), *VIEWS["isometric"], size[0] / size[1], None, MARGIN)
        shots.append(shot(parts_exploded(name).removesuffix(".webp"), size, cam, [pose]))
        render(name, manifest, shots, mine)


def part_pictures(mine):
    """Each part of the next Mech (next_parts) in mine alone, at rest as MuJoCo settles it, from VIEWS' isometric,
    framed tight on its own."""
    for doc in dict.fromkeys(d for d, _ in next_parts().values()):  # the documents a part is first drawn in
        _, manifest, hull = prepare(f"parts-{doc}", doc)  # in its Theme, the first Preset's in its Shape
        mats = trajectories.poses(doc, "wink")[0]
        shots = [
            shot(
                f.removesuffix(".webp"),
                PART_SIZE,
                camera.fit(points(hull, pose), *VIEWS["isometric"], 1, None, MARGIN),
                [pose],
            )
            for f, (d, name) in next_parts().items()
            if d == doc
            for pose in [{name: mats[name]}]
        ]
        render(f"parts-{doc}", manifest, shots, mine)


def next_played(doc=STAGE3):
    """{motion: [{next-eyes part: world 4x4, metres} per frame]} for each motion the next Mech (doc, in its Skeleton)
    plays (NEXT_MOTIONS' None, #663): its baked trajectory (just trajectories) at HERO_FPS (at_fps), its eye gimbal
    alone."""
    eyes = stages.next_eyes().parts
    return {
        m: [{n: f[n] for n in eyes} for f in at_fps(trajectories.poses(doc, m), HERO_FPS)]
        for m, keys in NEXT_MOTIONS.items()
        if keys is None
    }


def motions(doc=STAGE3):
    """{motion: [{next-eyes part: world 4x4, metres} per frame]} of doc: the keyed ones (next_motions), then the
    played."""
    return next_motions(trajectories.poses(doc, "wink")[0]) | next_played(doc)


def frames():
    """{picture: its frames} of published(): a still's one, a motion's as many as it plays."""
    moving = {next_motion(m, p): len(f) for p in g.PRESETS for m, f in motions(DRAWN[STAGE3 + SUFFIX[p]][0]).items()}
    return dict.fromkeys(published(), 1) | moving


def motion_pictures(mine):
    """The next Mech's motions (motions()) in mine, its eye gimbal alone in each Preset, each a looping WebP at
    HERO_FPS through one camera from the hero's direction (HERO) fitted to every frame of a Preset's, so they share
    one framing."""
    for preset, s in SUFFIX.items():
        doc = DRAWN[STAGE3 + s][0]
        _, manifest, hull = prepare(STAGE3 + s)
        moves = motions(doc)
        pts = np.concatenate([points(hull, f) for frames in moves.values() for f in frames])
        cam = camera.fit(pts, HERO, g.Z, MOTION_SIZE[0] / MOTION_SIZE[1], LENS, MARGIN)
        names = {m: next_motion(m, preset).removesuffix(".webp") for m in moves}
        for name in names.values():  # a motion keyed shorter leaves no frames of the last render behind
            shutil.rmtree(os.path.join(OUT, "frames", name), ignore_errors=True)
        shots = [shot(names[m], MOTION_SIZE, cam, frames) for m, frames in moves.items()]
        render(STAGE3 + s, manifest, shots, mine, HERO_FPS)


def at_fps(frames, fps):
    """Trajectory frames (trajectories.FPS a second) resampled to fps: per output frame the nearest one, unless a key
    frame lies within half an output frame, where a horn turns back or settles into a hold: toon timing's shut blinks
    and holds (#258) survive the resampling (#276)."""
    step, keys = trajectories.FPS / fps, set()
    for n in (n for n in frames[0] if "horn" in n):
        # each frame's turn from the first as sin(angle) times its axis: one signed number along the horn's own axis
        v = []
        for f in frames:
            r = np.asarray(f[n])[:3, :3] @ np.asarray(frames[0][n])[:3, :3].T
            v.append((r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]))
        v = np.array(v) / 2
        axis = v[np.argmax(np.linalg.norm(v, axis=1))]
        d = np.diff(v @ axis)
        moving = np.abs(d) > 1e-4
        keys |= {j for j in range(1, len(d)) if moving[j - 1] and (not moving[j] or d[j - 1] * d[j] < 0)}
    out = []
    for k in range(math.ceil(len(frames) / step)):
        near = [j for j in keys if (k - 0.5) * step <= j < (k + 0.5) * step]
        out.append(
            frames[min(near, key=lambda j: abs(j - k * step)) if near else min(round(k * step), len(frames) - 1)]
        )
    return out


def encode(name, fps=None):
    """OUT/frames/<name> as OUT/<name>.webp with its alpha: a still, or with fps a looping animation."""
    rate, codec = (["-framerate", str(fps)], ["libwebp_anim", "-loop", "0"]) if fps else ([], ["libwebp"])
    frames = os.path.join(OUT, "frames", name, "frame%04d.png")
    ffmpeg(*rate, "-i", frames, "-c:v", *codec, "-quality", str(WEBP_QUALITY), os.path.join(OUT, f"{name}.webp"))


def ffmpeg(*args):
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", *args], check=True)


def main(what, names):
    os.makedirs(OUT, exist_ok=True)
    if what == "views":
        views(set(published()))
    elif what == "site" and set(names) <= {NEXT}:
        mine = published()
        if SHARD:
            mine = share(frames(), *map(int, SHARD.split("/")))
        views(mine)
        part_pictures(mine)
        motion_pictures(mine)
        os.makedirs(IMAGES, exist_ok=True)
        for f in mine:
            shutil.copy(os.path.join(OUT, f), IMAGES)
    else:
        sys.exit(f"unknown: {what} {' '.join(names)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
