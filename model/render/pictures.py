"""Every picture the site serves (published()), rendered in Blender (#47; rules in docs/model-notes.md), each document
posed from its baked trajectories (model/trajectories.py, `just trajectories`): MuJoCo's poses (#150). Each picture is a
WebP with a transparent background, its lines one grey for the site's light and dark themes (blender.py INK, #470).
`views` (`just render`): the panels (each document at rest, a trajectory's first frame, from the side and isometric,
framed among themselves: PANELS) and the front doors' own (FRONT, #739). `site next` (`just pictures next`, Checks'
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
PANELS = [(doc, view) for doc in g.STAGES for view in VIEWS]
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
# the front doors (#739: the README's top, the site's home), side by side in this order, in each Skeleton (#806), as
# Bones first (#704): Stage 1 from the front, its eyes facing the camera; Stage 3 isometric, its panel (None); Stage 3
# from the side, exploded (EXPLODE); each (document, eye direction, exploded), framed tight on its own at the panels'
# size
STAGE1, STAGE3 = next(iter(g.STAGES)), next(iter(g.NEXT))
FRONT = {
    f: how
    for s in g.SKELETON_SUFFIX.values()
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
# the next Mech in motion, next-eyes alone in each Skeleton (#806) through one camera at HERO_FPS: its eye gimbal's
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


@functools.cache
def next_parts():
    """{picture: (document, part)}: one per part of the next Mech's documents by its mesh, its first instance."""
    out = {}
    for doc in g.STAGES:
        for name, p in stages.STAGES[doc].parts.items():
            stem = stages.stem(p.file).removeprefix("next ")
            out.setdefault(f"next-{stem.lower().replace(' ', '-')}.webp", (doc, name))
    return out


def next_motion(motion, skeleton=g.THEME["Skeleton"]):
    return f"next-eyes{g.SKELETON_SUFFIX[skeleton]}-{motion}.webp"


def published():
    """Every picture the site serves (#649): the next Mech's panels, the front doors' own (#739), its motions (#656) in
    each Skeleton (#806), then its parts'."""
    front = [f for f, how in FRONT.items() if how]
    moving = [next_motion(m, s) for s in g.SKELETON_SUFFIX for m in NEXT_MOTIONS]
    return [*(picture(*p) for p in PANELS), *front, *moving, *next_parts()]


def exploded(doc, mats):
    """mats ({part: world 4x4}, metres) with each part moved by its sub-assembly's EXPLODE offset, as the viewer's
    Explode moves it (macros.py explode)."""
    sub = {n: s for s in g.STAGES[doc] for n in stages.SUBS[s]().parts}
    return {n: stages.translate(np.divide(EXPLODE[sub[n]], 1000)) @ m for n, m in mats.items()}


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


def prepare(doc):
    """(stage, manifest with absolute PLY paths, hull points per part) for one document's pictures, its parts as
    model/stages.py assembles them, exported once. Always our geometry (model/build/ours, `just ours`), never the
    designer's meshes."""
    stage = stages.STAGES[doc]
    folder = os.path.join(OUT, "meshes", doc)
    os.makedirs(folder, exist_ok=True)
    manifest = scene.export(doc, folder)  # in its Theme's colours (#805)
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
    """The panels (PANELS: each document at rest as MuJoCo settles it, where every gesture starts), at one scale and one
    frame: the largest silhouette among them; those in mine alone are rendered."""
    plans = {}
    for doc in g.STAGES:
        _, manifest, hulls = prepare(doc)
        mats = trajectories.poses(doc, "wink")[0]
        plans[doc] = (manifest, hulls, mats, points(hulls, mats))
    fits = {(n, v): camera.fit(plans[n][3], *VIEWS[v], 1) for n, v in PANELS}
    # one scale and one frame for every panel: the widest and the tallest silhouette, PAD of the larger round them
    w, h = np.max([[np.ptp(plans[n][3] @ c.matrix[:3, i]) for i in (0, 1)] for (n, _), c in fits.items()], axis=0)
    pad = PAD * max(w, h)
    w, h = w + 2 * pad, h + 2 * pad
    size = (PANEL_WIDTH, 2 * round(PANEL_WIDTH * h / w / 2))
    for name, (manifest, hull, mats, pts) in plans.items():
        shots = [shot(f"{name}-{v}", size, camera.stand(fits[name, v], pts, w, w / h, pad / h), [mats]) for v in VIEWS]
        for f, (doc, eye, apart) in ((f, how) for f, how in FRONT.items() if how and how[0] == name):
            pose = exploded(doc, mats) if apart else mats
            cam = camera.fit(points(hull, pose), eye, g.Z, size[0] / size[1], None, MARGIN)
            shots.append(shot(f.removesuffix(".webp"), size, cam, [pose]))
        render(name, manifest, shots, mine)


def part_pictures(mine):
    """Each part of the next Mech (next_parts) in mine alone, at rest as MuJoCo settles it, from VIEWS' isometric,
    framed tight on its own."""
    for doc in dict.fromkeys(d for d, _ in next_parts().values()):  # the documents a part is first drawn in
        _, manifest, hull = prepare(doc)
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
        render(doc, manifest, shots, mine)


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
    moving = {
        next_motion(m, s): len(f) for s in g.SKELETON_SUFFIX for m, f in motions(STAGE3 + g.SKELETON_SUFFIX[s]).items()
    }
    return dict.fromkeys(published(), 1) | moving


def motion_pictures(mine):
    """The next Mech's motions (motions()) in mine, its eye gimbal alone in each Skeleton, each a looping WebP at
    HERO_FPS through one camera from the hero's direction (HERO) fitted to every frame of a Skeleton's, so they share
    one framing."""
    for skeleton, s in g.SKELETON_SUFFIX.items():
        doc = STAGE3 + s
        _, manifest, hull = prepare(doc)
        moves = motions(doc)
        pts = np.concatenate([points(hull, f) for frames in moves.values() for f in frames])
        cam = camera.fit(pts, HERO, g.Z, MOTION_SIZE[0] / MOTION_SIZE[1], LENS, MARGIN)
        names = {m: next_motion(m, skeleton).removesuffix(".webp") for m in moves}
        for name in names.values():  # a motion keyed shorter leaves no frames of the last render behind
            shutil.rmtree(os.path.join(OUT, "frames", name), ignore_errors=True)
        shots = [shot(names[m], MOTION_SIZE, cam, frames) for m, frames in moves.items()]
        render(doc, manifest, shots, mine, HERO_FPS)


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
