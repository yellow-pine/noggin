"""Every picture of the model, rendered in Blender (#47; rules in docs/model-notes.md), each Stage posed from its
baked trajectories (model/trajectories.py, `make trajectories`): MuJoCo's poses (#150).
`views` (`make render`): top/side/front of each sub-assembly (at its placement: nothing moves it) and Stage (at rest:
a trajectory's first frame), the Stage strip and stage 3 exploded. `gifs` (`make gifs`): the six gestures on stage 1,
its trajectory at 8 fps (at_fps), each with a contact sheet. `hero` (`make hero`): the README hero, stage 3
talking (model/render/hero.py). `site` (`make pictures`): renders the README's pictures, part by part (SITE: the Stage
views, the hero, each gesture) into model/build/images, which the site serves at
yellowpine.com/noggin/images/.
`frames` renders one runner's shard of a part and `join` encodes the shards (the pages workflow splits each part's
frames over runners, #278).
Usage: python -m model.render.pictures views|gifs|hero [name ...] | site|join [part ...] | frames <part> <i>/<n>
(Blender at $BLENDER)"""

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
from model import stages, traces, trajectories
from model.render import camera, scene

OUT = os.path.join(stages.REPO, "model", "build", "pictures")
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender.py")
PT, EYES = ((0, 0, 0), g.X, g.Z), stages.EYES_FRAME
PT_VIEWS = {"top": (g.Z, g.Y), "side": (g.X, g.Z), "front": ((0, -1, 0), g.Z)}  # eye direction, up
EYES_VIEWS = {"top": (g.Y, g.Z), "side": ((-1, 0, 0), g.Y), "front": ((0, 0, -1), g.Y)}
DOCS = {  # picture name: (sub-assembly frames, views); the mouth is shown on the eyes it hangs from, as its document
    "base": ({"noggin-base": PT}, PT_VIEWS),
    "stack": ({"noggin-stack": PT}, PT_VIEWS),
    "eyes": ({"noggin-eyes": EYES}, EYES_VIEWS),
    "mouth": ({"noggin-mouth": EYES, "noggin-eyes": EYES}, EYES_VIEWS),
    **{doc[len("noggin-") :]: (frames, PT_VIEWS) for doc, frames in g.STAGES.items()},
}
VIEW_SIZE, GIF_SIZE, STRIP_PANEL = (1600, 1200), (400, 300), (800, 600)  # GIFs rendered at the size they ship (#276)
STRIP = [("stage1", "front"), ("stage2", "side"), ("stage3", "side"), ("stage3", "front")]  # the README's Stage strip
LENS, MARGIN = 90, 1.06  # a long lens: little perspective distortion so close
# gestures: the Mech's front-right (right eye nearest), 25 deg up, framed on the eyes
THREE_QUARTER = camera.three_quarter((0, -1, 0), (-1, 0, 0), g.Z, 25)
# the hero and the exploded view: stage 3 from 15 deg to its right (right eye nearest, as the gestures), 15 deg up
_R = math.radians(15)
HERO = math.cos(_R) * np.array((-math.sin(_R), -math.cos(_R), 0)) + (0, 0, math.sin(_R))
HERO_SIZE = (800, 400)  # 2:1, the whole motion fitted wide (Cansin, #278)
HERO_WIDTH, HERO_MAX_BYTES, HERO_COLOURS = 800, 3_000_000, 48  # 64 colours went to 3.2 MB with the servos' own motion
EXPLODE = {  # stage 3 exploded, mm: the neck lifted off the base, the eyes off the neck, the mouth forward off the eyes
    "noggin-base": (0, 0, 0),
    "noggin-stack": (0, 0, 45),
    "noggin-eyes": (0, 0, 95),
    "noggin-mouth": (0, -45, 95),
}
GIF_FPS, GIF_MAX_BYTES, GIF_WIDTH, GIF_COLOURS = 8, 1_000_000, 400, 64  # every GIF, the hero too (#276)
IMAGES = os.path.join(stages.REPO, "model", "build", "images")
# what the site serves, by the part of the pictures that renders it (the pages workflow splits each over runners)
SITE = {"views": ["stages.jpg", "exploded.jpg"], "hero": ["hero.gif"], **{g: [f"{g}.gif"] for g in traces.GESTURES}}


def metres(mats):
    out = {}
    for n, m in mats.items():
        m = np.array(m, float)
        m[:3, 3] *= 0.001
        out[n] = m.tolist()
    return out


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


def points(hulls, mats, names=None):
    return np.concatenate(
        [trimesh.transform_points(hulls[n], np.array(m)) for n, m in mats.items() if names is None or n in names]
    )


def shot(out, size, cam, mats):
    c = {"matrix": cam.matrix.tolist(), "lens": cam.lens, "ortho_scale": cam.ortho_scale}
    return {
        "out": os.path.join(OUT, out),
        "size": list(size),
        "camera": c,
        "pose": {n: np.asarray(m).tolist() for n, m in mats.items()},
    }


def blender(name, manifest, shots):
    job = os.path.join(OUT, "meshes", name, "job.json")
    json.dump({"parts": manifest, "shots": shots}, open(job, "w"))
    r = subprocess.run([BLENDER, "-b", "-P", SCRIPT, "--", job], capture_output=True, text=True)
    if r.returncode or not all(os.path.isfile(s["out"]) for s in shots):
        sys.exit(f"Blender failed on {name}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    print("".join(line for line in r.stdout.splitlines(True) if line.startswith("frame ")), end="")  # each frame's s


def render_shots(jobs, shard=None):
    """Blender over each (name, manifest, shots); with shard (i, n), 1-based, only the i-th of n even runs of all the
    shots in order: the pages workflow splits a part's frames over n runners and joins them in its site job (#278)."""
    if shard:
        flat = [(name, s) for name, _, shots in jobs for s in shots]
        i, n = shard
        mine = flat[len(flat) * (i - 1) // n : len(flat) * i // n]
        jobs = [(name, manifest, [s for m, s in mine if m == name]) for name, manifest, _ in jobs]
    for name, manifest, shots in jobs:
        if shots:
            blender(name, manifest, shots)


def views(names=None, shard=None):
    """Top/side/front of every picture document, stage 3 exploded and (all Stages present) the strip; with a shard,
    only its shard of the shots and nothing joined (render_shots)."""
    plans = {}
    for name, (frames, dirs) in DOCS.items():
        if not names or name in names:
            stage, manifest, hulls = prepare(name, frames)
            doc = f"noggin-{name}"
            # a Stage at rest as MuJoCo settles it: every gesture starts there (traces.commands)
            mats = (
                trajectories.poses(doc, "wink")[0]
                if doc in g.STAGES
                else metres({n: p.matrix for n, p in stage.parts.items()})
            )
            plans[name] = (manifest, hulls, mats, dirs)
    aspect, panel_aspect = VIEW_SIZE[0] / VIEW_SIZE[1], STRIP_PANEL[0] / STRIP_PANEL[1]
    panels = {}
    for doc, v in STRIP:
        if doc in plans:
            _, hulls, mats, dirs = plans[doc]
            panels[doc, v] = camera.fit(points(hulls, mats), *dirs[v], panel_aspect, margin=MARGIN)
    scale = max((c.ortho_scale for c in panels.values()), default=0)
    jobs = []
    for name, (manifest, hulls, mats, dirs) in plans.items():
        pts = points(hulls, mats)
        shots = [
            shot(f"{name}-{v}.png", VIEW_SIZE, camera.fit(pts, d, up, aspect, margin=MARGIN), mats)
            for v, (d, up) in dirs.items()
        ]
        for i, key in enumerate(STRIP):
            if key in panels and key[0] == name:
                shots.append(
                    shot(f"strip-{i}.png", STRIP_PANEL, camera.stand(panels[key], pts, scale, panel_aspect), mats)
                )
        if name == "stage3":
            apart = exploded(mats)
            cam = camera.fit(points(hulls, apart), HERO, g.Z, aspect, LENS, MARGIN)
            shots.append(shot("exploded.png", VIEW_SIZE, cam, apart))
        jobs.append((name, manifest, shots))
    render_shots(jobs, shard)
    if not shard:
        jpgs(len(panels) == len(STRIP), "stage3" in plans)


def jpgs(strip=True, apart=True):
    """stages.jpg (the strip's panels side by side) and exploded.jpg from the views' PNGs."""
    if strip:
        ins = [a for i in range(len(STRIP)) for a in ("-i", os.path.join(OUT, f"strip-{i}.png"))]
        ffmpeg(*ins, "-filter_complex", f"hstack=inputs={len(STRIP)}", "-q:v", "3", os.path.join(OUT, "stages.jpg"))
    if apart:
        ffmpeg("-i", os.path.join(OUT, "exploded.png"), "-q:v", "3", os.path.join(OUT, "exploded.jpg"))


def exploded(mats):
    """Stage 3's world matrices (metres) with each sub-assembly moved by its EXPLODE offset."""
    out = {}
    for sub, (dx, dy, dz) in EXPLODE.items():
        for n in stages.SUBS[sub]().parts:
            m = np.array(mats[n])
            m[:3, 3] += np.multiply((dx, dy, dz), 0.001)
            out[n] = m.tolist()
    return out


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


def gesture_camera(eye_points, aspect):
    """Stage 1 from its front-right, 25 deg up, framed on the eyes (the base's front shows below them)."""
    return camera.fit(eye_points, THREE_QUARTER, g.Z, aspect, LENS, 1.04)


def gifs(names=None, shard=None):
    """Each gesture's trajectory on stage 1 (model/trajectories.py: MuJoCo playing the Core program's writes, one frame
    per 100 ms, at_fps to GIF_FPS) through the three-quarter camera, encoded to <gesture>.gif (at most GIF_MAX_BYTES) with a
    contact sheet <gesture>-sheet.png; with a shard, only its shard of the frames, unencoded (render_shots)."""
    names = names or list(traces.GESTURES)
    _, manifest, hulls = prepare("stage1", g.STAGES["noggin-stage1"])
    poses = {name: trajectories.poses("noggin-stage1", name) for name in traces.GESTURES}
    eyes = set(stages.eyes().parts)
    # one camera for every gesture, fitted to the eyes in all their frames (whichever are rendered): lids at their
    # widest stay in
    cam = gesture_camera(
        np.concatenate([points(hulls, m, eyes) for frames in poses.values() for m in frames]), GIF_SIZE[0] / GIF_SIZE[1]
    )
    shots = []
    for name in names:
        frames = at_fps(poses[name], GIF_FPS)
        folder = os.path.join(OUT, "gifs", name)
        os.makedirs(folder, exist_ok=True)
        for old in os.listdir(folder):
            os.remove(os.path.join(folder, old))
        shots += [shot(os.path.join(folder, f"{i:03d}.png"), GIF_SIZE, cam, m) for i, m in enumerate(frames)]
    render_shots([("stage1", manifest, shots)], shard)
    for name in [] if shard else names:
        join(name)


def hero_gif(shard=None):
    """The hero's trajectory on stage 3 (its keys in model/render/hero.py, played by MuJoCo) through one three-quarter
    camera fitted to every pose, encoded to hero.gif: HERO_WIDTH wide, GIF_FPS, at most 3 MB (48 colours: the servos' own motion
    took 64 to 3.2 MB); with a shard, only its shard of the frames, unencoded (render_shots)."""
    _, manifest, hulls = prepare("stage3", g.STAGES["noggin-stage3"])
    poses = at_fps(trajectories.poses("noggin-stage3", "hero"), GIF_FPS)
    cam = camera.fit(
        np.concatenate([points(hulls, m) for m in poses]), HERO, g.Z, HERO_SIZE[0] / HERO_SIZE[1], LENS, MARGIN
    )
    folder = os.path.join(OUT, "gifs", "hero")
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        os.remove(os.path.join(folder, old))
    shots = [shot(os.path.join(folder, f"{i:03d}.png"), HERO_SIZE, cam, m) for i, m in enumerate(poses)]
    render_shots([("stage3", manifest, shots)], shard)
    if not shard:
        join("hero")


def join(part):
    """A part of the site's pictures (SITE) from its rendered frames: the views' JPEGs, else its GIF."""
    if part == "views":
        jpgs()
    elif part == "hero":
        encode(
            os.path.join(OUT, "gifs", "hero"),
            os.path.join(OUT, "hero"),
            GIF_FPS,
            HERO_WIDTH,
            HERO_MAX_BYTES,
            HERO_COLOURS,
        )
    else:
        encode(os.path.join(OUT, "gifs", part), os.path.join(OUT, part))


def encode(frames, out, fps=GIF_FPS, width=GIF_WIDTH, max_bytes=GIF_MAX_BYTES, colours=GIF_COLOURS):
    """frames/NNN.png -> out.gif (one shared palette, only changed rectangles stored) and out-sheet.png."""
    n = len(os.listdir(frames))
    pngs = os.path.join(frames, "%03d.png")
    palette = (  # 480 wide, 64 colours: bored's 117 frames fit 1 MB (600 wide or 96 colours did not)
        f"scale={width}:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors={colours}:stats_mode=diff[p];"
        "[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
    )
    ffmpeg("-framerate", str(fps), "-i", pngs, "-vf", palette, "-loop", "0", out + ".gif")
    size = os.path.getsize(out + ".gif")
    if size > max_bytes:
        sys.exit(f"{out}.gif is {size // 1024} KB, over {max_bytes // 1000} KB")
    step = math.ceil(n / 24)
    rows = math.ceil(math.ceil(n / step) / 6)
    sheet = f"select='not(mod(n\\,{step}))',scale=300:-2,tile=6x{rows}:padding=4:color=white"
    ffmpeg("-i", pngs, "-vf", sheet, "-frames:v", "1", "-update", "1", out + "-sheet.png")
    print(f"{os.path.basename(out)}.gif: {n} frames, {size // 1024} KB")


def ffmpeg(*args):
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", *args], check=True)


def render(part, shard=None):
    """A part of the site's pictures (SITE); with a shard, only its shard of the frames (render_shots)."""
    if part == "views":
        views(["stage1", "stage2", "stage3"], shard)
    elif part == "hero":
        hero_gif(shard)
    else:
        gifs([part], shard)


def main(what, names):
    os.makedirs(OUT, exist_ok=True)
    if what == "views":
        views(names)
    elif what == "gifs":
        gifs(names)
    elif what == "hero":
        hero_gif()
    elif what == "frames":
        part, shard = names
        render(part, tuple(int(k) for k in shard.split("/")))
    elif what in ("site", "join"):  # join: encode the parts' frames the runners rendered
        os.makedirs(IMAGES, exist_ok=True)
        for part in names or SITE:
            if what == "site":
                render(part)
            else:
                join(part)
            for f in SITE[part]:
                shutil.copy(os.path.join(OUT, f), IMAGES)
    else:
        sys.exit(f"unknown: {what}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
