"""Every picture the site serves (SITE), rendered in Blender (#47; rules in docs/model-notes.md), each Stage posed from its
baked trajectories (model/trajectories.py, `make trajectories`): MuJoCo's poses (#150). Each picture has a light-theme
and a dark-theme render (THEMES: its lines' colour) with a transparent background, as WebP (#470).
`views` (`make render`): the Stage panels (each Stage at rest, a trajectory's first frame, from the side and isometric:
PANELS). `hero` (`make hero`): the README hero, stage 3 talking (model/render/hero.py), its
trajectory at 8 fps (at_fps) as one animation. `site` (`make pictures`): renders the site's pictures, motion by motion
(SITE; the gestures play in the web viewer, #468) into model/build/images, which the site serves at
yellowpine.com/noggin/images/. `list` (`make pictures-list`): the motions as JSON, Site Checks' render matrix
(one job per motion, #297).
Usage: python -m model.render.pictures views | hero | site [motion ...] | list (Blender at $BLENDER)"""

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
from model import stages, trajectories
from model.render import camera, scene

OUT = os.path.join(stages.REPO, "model", "build", "pictures")
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender.py")
# the Stage panels (Cansin, #470): each Stage from its left side and isometric from its front left, by eye direction
# and up, at one scale on one ground line, framed tight: the largest panel's silhouette plus PAD of it each side
VIEWS = {"side": (g.X, g.Z), "isometric": ((1, -1, 1), g.Z)}
PANELS = [(doc.removeprefix("noggin-"), view) for doc in g.STAGES for view in VIEWS]
PANEL_WIDTH, PAD = 800, 0.03
LAYERS = ("parts", "lines")  # Blender draws each shot twice: the parts, then their lines alone (blender.py)
THEMES = {"light": "#000000", "dark": "#C8CACF"}  # each theme's line colour: grey lines keep the black base readable
LENS, MARGIN = 90, 1.06  # a long lens: little perspective distortion so close
# the hero: stage 3 from 15 deg to its right (right eye nearest), 15 deg up
_R = math.radians(15)
HERO = math.cos(_R) * np.array((-math.sin(_R), -math.cos(_R), 0)) + (0, 0, math.sin(_R))
HERO_SIZE = (800, 400)  # 2:1, the whole motion fitted wide (Cansin, #278)
HERO_FPS, HERO_MAX_BYTES = 8, 3_000_000
WEBP_QUALITY = 85  # lossy colour, lossless alpha
# the web viewer's exploded stage 3 (macros.py explode, #482), mm: the neck lifted off the base, the eyes off the neck,
# the mouth forward off the eyes
EXPLODE = {
    "noggin-base": (0, 0, 0),
    "noggin-stack": (0, 0, 45),
    "noggin-eyes": (0, 0, 95),
    "noggin-mouth": (0, -45, 95),
}
IMAGES = os.path.join(stages.REPO, "model", "build", "images")
# what the site serves, by the motion that renders it (Site Checks render each on its own runner, #297)
SITE = {
    "views": [f"{name}-{view}-{theme}.webp" for name, view in PANELS for theme in THEMES],
    "hero": [f"hero-{theme}.webp" for theme in THEMES],
}


def motions():
    """Each motion of SITE with the Stages it draws, whose trajectories its runner bakes (make trajectories TRAJ_DOCS)."""
    stages_of = {"views": " ".join(g.STAGES), "hero": "noggin-stage3"}
    return [{"motion": m, "stages": stages_of[m]} for m in SITE]


def assembled(name, frames):
    """The picture's parts as model/stages.py assembles them, under its document's name (stages.assemble): a Stage clamps the
    eyes and mouth to the tilt arm so the neck carries the head, and the desk build (geometry.DESK) has its own bracket."""
    return stages.assemble(f"noggin-{name}", frames, 2)


def prepare(name, frames):
    """(stage, manifest with absolute PLY paths, hull points per part) for one picture's parts, exported once. Always
    our geometry (model/build/ours, `make ours`), never the designer's meshes."""
    stage = assembled(name, frames)
    folder = os.path.join(OUT, "meshes", name)
    os.makedirs(folder, exist_ok=True)
    manifest = scene.export(stage, folder)
    for p in manifest.values():
        p["ply"] = os.path.join(folder, p["ply"])
    hulls = {n: trimesh.load(p["ply"]).convex_hull.vertices for n, p in manifest.items()}
    return stage, manifest, hulls


def points(hulls, mats):
    return np.concatenate([trimesh.transform_points(hulls[n], np.array(m)) for n, m in mats.items()])


def shot(name, size, cam, poses):
    """A Blender shot (blender.py): one pose, a still (name.png), or several, an animation (name/NNN.png), drawn twice:
    the parts alone in OUT/parts, their lines alone in OUT/lines, which compose() lays over the parts per theme."""
    c = {"matrix": cam.matrix.tolist(), "lens": cam.lens, "ortho_scale": cam.ortho_scale}
    return {
        "out": {layer: os.path.join(OUT, layer, name) for layer in LAYERS},
        "size": list(size),
        "camera": c,
        "poses": [{n: np.asarray(m).tolist() for n, m in pose.items()} for pose in poses],
    }


def blender(name, manifest, shots):
    job = os.path.join(OUT, "meshes", name, "job.json")
    json.dump({"parts": manifest, "shots": shots}, open(job, "w"))
    r = subprocess.run([BLENDER, "-b", "-P", SCRIPT, "--", job], capture_output=True, text=True)
    frames = [len(s["poses"]) for s in shots]
    files = [
        p if k == 1 else os.path.join(p, f"{i:03d}.png")
        for s, k in zip(shots, frames)
        for p in s["out"].values()
        for i in range(k)
    ]
    if r.returncode or not all(os.path.isfile(f) for f in files):
        sys.exit(f"Blender failed on {name}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    print("".join(line for line in r.stdout.splitlines(True) if line.startswith("frame ")), end="")  # each frame's s


def views():
    """The Stage panels (PANELS: each Stage at rest as MuJoCo settles it, where every gesture starts)."""
    plans = {}
    for doc, frames in g.STAGES.items():
        name = doc.removeprefix("noggin-")
        _, manifest, hulls = prepare(name, frames)
        mats = trajectories.poses(doc, "wink")[0]
        plans[name] = (manifest, hulls, mats, points(hulls, mats))
    fits = {(n, v): camera.fit(plans[n][3], *VIEWS[v], 1) for n, v in PANELS}
    # one scale and one frame for every panel: the widest and the tallest silhouette, PAD of the larger round them
    w, h = np.max([[np.ptp(plans[n][3] @ c.matrix[:3, i]) for i in (0, 1)] for (n, _), c in fits.items()], axis=0)
    pad = PAD * max(w, h)
    w, h = w + 2 * pad, h + 2 * pad
    size = (PANEL_WIDTH, 2 * round(PANEL_WIDTH * h / w / 2))
    for name, (manifest, _, mats, pts) in plans.items():
        shots = [
            shot(f"{name}-{v}.png", size, camera.stand(fits[name, v], pts, w, w / h, pad / h), [mats]) for v in VIEWS
        ]
        blender(name, manifest, shots)
    for name, v in PANELS:
        compose(f"{name}-{v}.png", os.path.join(OUT, f"{name}-{v}"))


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


def hero():
    """The hero's trajectory on stage 3 (its keys in model/render/hero.py, played by MuJoCo) through one three-quarter
    camera fitted to every pose, rendered as one animation and encoded to hero-<theme>.webp: HERO_FPS, looping, each at
    most HERO_MAX_BYTES."""
    _, manifest, hulls = prepare("stage3", g.STAGES["noggin-stage3"])
    poses = at_fps(trajectories.poses("noggin-stage3", "hero"), HERO_FPS)
    cam = camera.fit(
        np.concatenate([points(hulls, m) for m in poses]), HERO, g.Z, HERO_SIZE[0] / HERO_SIZE[1], LENS, MARGIN
    )
    for layer in LAYERS:
        shutil.rmtree(os.path.join(OUT, layer, "hero"), ignore_errors=True)
    blender("stage3", manifest, [shot("hero", HERO_SIZE, cam, poses)])
    out = os.path.join(OUT, "hero")
    compose("hero", out, HERO_FPS)
    for theme in THEMES:
        size = os.path.getsize(f"{out}-{theme}.webp")
        if size > HERO_MAX_BYTES:
            sys.exit(f"{out}-{theme}.webp is {size // 1024} KB, over {HERO_MAX_BYTES // 1000} KB")
        print(f"hero-{theme}.webp: {len(poses)} frames, {size // 1024} KB")


def compose(name, out, fps=None):
    """OUT/lines/<name> in each theme's line colour (THEMES) over OUT/parts/<name>, as <out>-<theme>.webp with its
    alpha: a still, or with fps an animation of <name>/NNN.png."""
    ins = []
    for layer in LAYERS:
        path = os.path.join(OUT, layer, name)
        ins += ["-framerate", str(fps), "-i", os.path.join(path, "%03d.png")] if fps else ["-i", path]
    n = len(THEMES)
    graph = [
        f"[0]split={n}{''.join(f'[p{i}]' for i in range(n))}",
        f"[1]split={n}{''.join(f'[l{i}]' for i in range(n))}",
    ]
    outs = []
    for i, (theme, colour) in enumerate(THEMES.items()):
        red, green, blue = (int(colour[k : k + 2], 16) for k in (1, 3, 5))
        # format=auto: the output keeps the parts' alpha (#489's review: overlay's default is yuv420)
        graph.append(f"[l{i}]lutrgb=r={red}:g={green}:b={blue}[c{i}];[p{i}][c{i}]overlay=format=auto[o{i}]")
        codec = ["libwebp_anim", "-loop", "0"] if fps else ["libwebp"]
        outs += ["-map", f"[o{i}]", "-c:v", *codec, "-quality", str(WEBP_QUALITY), f"{out}-{theme}.webp"]
    ffmpeg(*ins, "-filter_complex", ";".join(graph), *outs)


def ffmpeg(*args):
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", *args], check=True)


def render(motion):
    """A motion of the site's pictures (SITE)."""
    views() if motion == "views" else hero()


def main(what, names):
    os.makedirs(OUT, exist_ok=True)
    if what == "views":
        views()
    elif what == "hero":
        hero()
    elif what == "site":
        os.makedirs(IMAGES, exist_ok=True)
        for motion in names or SITE:
            render(motion)
            for f in SITE[motion]:
                shutil.copy(os.path.join(OUT, f), IMAGES)
    elif what == "list":
        print(json.dumps(motions()))
    else:
        sys.exit(f"unknown: {what}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
