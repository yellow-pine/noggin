"""Every picture of the model, rendered in Blender (#47; rules in docs/model-notes.md), each Stage posed from its
baked trajectories (model/trajectories.py, `make trajectories`): MuJoCo's poses (#150).
`views` (`make render`): top/side/front of each sub-assembly (at its placement: nothing moves it) and Stage (at rest:
a trajectory's first frame), the Stage strip and stage 3 exploded. `gifs` (`make gifs`): the six gestures on stage 1,
one trajectory frame per 100 ms, at 10 fps, each with a contact sheet. `hero` (`make hero`): the README hero, stage 3
talking (model/render/hero.py).
Usage: python -m model.render.pictures views|gifs|hero [name ...]   (Blender at $BLENDER)"""

import json
import math
import os
import subprocess
import sys

import numpy as np
import trimesh

from model import geometry as g
from model import traces, trajectories
from model.engine import stages
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
VIEW_SIZE, GIF_SIZE, STRIP_PANEL = (1600, 1200), (600, 450), (800, 600)
STRIP = [("stage1", "front"), ("stage2", "side"), ("stage3", "side"), ("stage3", "front")]  # the README's Stage strip
LENS, MARGIN = 90, 1.06  # a long lens: little perspective distortion so close
# gestures: the Mech's front-right (right eye nearest), 25 deg up, framed on the eyes
THREE_QUARTER = camera.three_quarter((0, -1, 0), (-1, 0, 0), g.Z, 25)
# the hero and the exploded view: stage 3 from 15 deg to its right (right eye nearest, as the gestures), 15 deg up
_R = math.radians(15)
HERO = math.cos(_R) * np.array((-math.sin(_R), -math.cos(_R), 0)) + (0, 0, math.sin(_R))
HERO_SIZE = (800, 600)
HERO_GIF = 640, 3_000_000, 48  # encode's width, max_bytes, colours (64 went to 3.2 MB with the servos' own motion)
EXPLODE = {  # stage 3 exploded, mm: the neck lifted off the base, the eyes off the neck, the mouth forward off the eyes
    "noggin-base": (0, 0, 0),
    "noggin-stack": (0, 0, 45),
    "noggin-eyes": (0, 0, 95),
    "noggin-mouth": (0, -45, 95),
}
GIF_FPS, GIF_MAX_BYTES = 10, 1_000_000


def metres(mats):
    out = {}
    for n, m in mats.items():
        m = np.array(m, float)
        m[:3, 3] *= 0.001
        out[n] = m.tolist()
    return out


def assembled(name, frames):
    """The picture's parts as the engine assembles them, under its document's name (stages.assemble): a Stage clamps the
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


def views(names=None):
    """Top/side/front of every picture document, stage 3 exploded and (all Stages present) the strip."""
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
        blender(name, manifest, shots)
        print(f"{name}: {len(shots)} pictures")
    if len(panels) == len(STRIP):
        ins = [a for i in range(len(STRIP)) for a in ("-i", os.path.join(OUT, f"strip-{i}.png"))]
        stack = f"hstack=inputs={len(STRIP)}"
        ffmpeg(*ins, "-filter_complex", stack, "-q:v", "3", os.path.join(OUT, "stages.jpg"))


def exploded(mats):
    """Stage 3's world matrices (metres) with each sub-assembly moved by its EXPLODE offset."""
    out = {}
    for sub, (dx, dy, dz) in EXPLODE.items():
        for n in stages.SUBS[sub]().parts:
            m = np.array(mats[n])
            m[:3, 3] += np.multiply((dx, dy, dz), 0.001)
            out[n] = m.tolist()
    return out


def gesture_camera(eye_points, aspect):
    """Stage 1 from its front-right, 25 deg up, framed on the eyes (the base's front shows below them)."""
    return camera.fit(eye_points, THREE_QUARTER, g.Z, aspect, LENS, 1.04)


def gifs(names=None):
    """Each gesture's trajectory on stage 1 (model/trajectories.py: MuJoCo playing the Core program's writes, one frame
    per 100 ms) through the three-quarter camera, encoded to <gesture>.gif at 10 fps (at most GIF_MAX_BYTES) with a
    contact sheet <gesture>-sheet.png."""
    names = names or list(traces.GESTURES)
    _, manifest, hulls = prepare("stage1", g.STAGES["noggin-stage1"])
    poses = {name: trajectories.poses("noggin-stage1", name) for name in names}
    eyes = set(stages.eyes().parts)
    # one camera for every gesture, fitted to the eyes in all their frames: lids at their widest stay in
    cam = gesture_camera(
        np.concatenate([points(hulls, m, eyes) for frames in poses.values() for m in frames]), GIF_SIZE[0] / GIF_SIZE[1]
    )
    shots = []
    for name, frames in poses.items():
        folder = os.path.join(OUT, "gifs", name)
        os.makedirs(folder, exist_ok=True)
        for old in os.listdir(folder):
            os.remove(os.path.join(folder, old))
        shots += [shot(os.path.join(folder, f"{i:03d}.png"), GIF_SIZE, cam, m) for i, m in enumerate(frames)]
    blender("stage1", manifest, shots)
    for name in names:
        encode(os.path.join(OUT, "gifs", name), os.path.join(OUT, name))


def hero_gif():
    """The hero's trajectory on stage 3 (its keys in model/render/hero.py, played by MuJoCo) through one three-quarter
    camera fitted to every pose, encoded to hero.gif: 640 wide, 10 fps, at most 3 MB (48 colours: the servos' own motion
    took 64 to 3.2 MB)."""
    _, manifest, hulls = prepare("stage3", g.STAGES["noggin-stage3"])
    poses = trajectories.poses("noggin-stage3", "hero")
    cam = camera.fit(np.concatenate([points(hulls, m) for m in poses]), HERO, g.Z, 4 / 3, LENS, MARGIN)
    folder = os.path.join(OUT, "gifs", "hero")
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        os.remove(os.path.join(folder, old))
    blender(
        "stage3", manifest, [shot(os.path.join(folder, f"{i:03d}.png"), HERO_SIZE, cam, m) for i, m in enumerate(poses)]
    )
    encode(folder, os.path.join(OUT, "hero"), trajectories.FPS, *HERO_GIF)


def encode(frames, out, fps=GIF_FPS, width=480, max_bytes=GIF_MAX_BYTES, colours=64):
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
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def main(what, names):
    os.makedirs(OUT, exist_ok=True)
    if what == "views":
        views(names)
    elif what == "gifs":
        gifs(names)
    elif what == "hero":
        hero_gif()
    else:
        sys.exit(f"unknown: {what}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
