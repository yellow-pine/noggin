"""Every picture the site serves (SITE), rendered in Blender (#47; rules in docs/model-notes.md), each Stage posed from its
baked trajectories (model/trajectories.py, `just trajectories`): MuJoCo's poses (#150). Each picture is a WebP with a
transparent background, its lines one grey for the site's light and dark themes (blender.py INK, #470).
`views` (`just render`): the Stage panels (each Stage at rest, a trajectory's first frame, from the side and isometric:
PANELS). `hero` (`just hero`): the README hero, stage 3 talking (model/render/hero.py), its
trajectory at 8 fps (at_fps) as one animation. `site` (`just pictures`): renders the site's pictures, motion by motion
(SITE; the gestures play in the web viewer, #468) into model/build/images, which the site serves at
yellowpine.com/noggin/images/. Checks packs the motions into its Blender bins (model/shards.py, `just blender-bins`)
on main, the hero in frame shards (`hero:<first>-<end>`) that `join` encodes (#537); a PR renders the `preview`
motion alone, one panel (PREVIEW, #562).
Usage: python -m model.render.pictures views | hero | site [motion ...] | join (Blender at $BLENDER)"""

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
LENS, MARGIN = 90, 1.06  # a long lens: little perspective distortion so close
# the hero: stage 3 from 15 deg to its right (right eye nearest), 15 deg up
_R = math.radians(15)
HERO = math.cos(_R) * np.array((-math.sin(_R), -math.cos(_R), 0)) + (0, 0, math.sin(_R))
HERO_SIZE = (800, 400)  # 2:1, the whole motion fitted wide (Cansin, #278)
HERO_STAGE = "noggin-stage3"  # whose GLB carries the hero's camera too (hero_camera, web/build.py, #597)
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
# what the site serves, by the motion that renders it (Checks' Blender bins render them, #297, #496)
SITE = {
    "views": [f"{name}-{view}.webp" for name, view in PANELS],
    "hero": ["hero.webp"],
}
# a PR's picture in place of SITE, which main alone renders and deploys (#562): one panel, as the site frames it
PREVIEW = [("stage3", "isometric")]
MOTIONS = SITE | {"preview": [f"{name}-{view}.webp" for name, view in PREVIEW]}


def motions(preview=False):
    """Each motion of SITE (or the preview alone) with the Stages it draws, whose trajectories its runner bakes (just
    trajectories TRAJ_DOCS): the preview every Stage, for the panels' one scale."""
    stages_of = {"views": " ".join(g.STAGES), "hero": HERO_STAGE, "preview": " ".join(g.STAGES)}
    return [{"motion": m, "stages": stages_of[m]} for m in (["preview"] if preview else SITE)]


def assembled(name, frames):
    """The picture's parts as model/stages.py assembles them, under its document's name (stages.assemble): a Stage clamps the
    eyes and mouth to the tilt arm so the neck carries the head, and the desk build (geometry.DESK) has its own bracket."""
    return stages.assemble(f"noggin-{name}", frames, 2)


def prepare(name, frames):
    """(stage, manifest with absolute PLY paths, hull points per part) for one picture's parts, exported once. Always
    our geometry (model/build/ours, `just ours`), never the designer's meshes."""
    stage = assembled(name, frames)
    folder = os.path.join(OUT, "meshes", name)
    os.makedirs(folder, exist_ok=True)
    manifest = scene.export(stage, folder)
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
    print("".join(line for line in r.stdout.splitlines(True) if line.startswith("frame ")), end="")  # each frame's s


def views(panels=PANELS):
    """The Stage panels (PANELS, or those named: each Stage at rest as MuJoCo settles it, where every gesture starts),
    each framed as among all of them."""
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
            shot(f"{name}-{v}", size, camera.stand(fits[name, v], pts, w, w / h, pad / h), [mats])
            for v in VIEWS
            if (name, v) in panels
        ]
        if shots:
            blender(name, manifest, shots)
    for name, v in panels:
        encode(f"{name}-{v}")


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


def hero_frames():
    """The hero's frame count, without MuJoCo: its trajectory's frames (trajectories.hero_commands) at HERO_FPS."""
    return len(at_fps([{}] * len(trajectories.hero_commands()[1]), HERO_FPS))


def hero(frames=None):
    """The hero's trajectory on stage 3 (its keys in model/render/hero.py, played by MuJoCo) through one three-quarter
    camera fitted to every pose, rendered as one animation and joined into hero.webp. frames: (first, end) renders those
    alone, a CI frame shard (#537), whose frames the Hero job joins."""
    _, manifest, hull = prepare(HERO_STAGE.removeprefix("noggin-"), g.STAGES[HERO_STAGE])
    poses = hero_poses()
    cam = hero_camera(hull)
    first, end = frames or (0, len(poses))
    if not frames:
        shutil.rmtree(os.path.join(OUT, "frames", "hero"), ignore_errors=True)
    blender("stage3", manifest, [shot("hero", HERO_SIZE, cam, poses[first:end], first)])
    if not frames:
        join()


def hero_poses():
    return at_fps(trajectories.poses(HERO_STAGE, "hero"), HERO_FPS)


def hero_camera(hull):
    """The hero's one three-quarter camera (HERO), fitted to every pose of its trajectory; the web viewer starts from it
    (web/build.py), so its first frame holds the Mech where the hero picture, its poster, did (#597)."""
    pts = np.concatenate([points(hull, m) for m in hero_poses()])
    return camera.fit(pts, HERO, g.Z, HERO_SIZE[0] / HERO_SIZE[1], LENS, MARGIN)


def join():
    """OUT/frames/hero, every frame of the hero's (a CI run's from its shards, #537), as hero.webp: HERO_FPS,
    looping, at most HERO_MAX_BYTES."""
    n, folder = hero_frames(), os.path.join(OUT, "frames", "hero")
    if sorted(os.listdir(folder)) != [f"frame{i:04d}.png" for i in range(n)]:
        sys.exit(f"the hero's frames in {folder} are not frame0000.png to frame{n - 1:04d}.png")
    encode("hero", HERO_FPS)
    size = os.path.getsize(os.path.join(OUT, "hero.webp"))
    if size > HERO_MAX_BYTES:
        sys.exit(f"hero.webp is {size // 1024} KB, over {HERO_MAX_BYTES // 1000} KB")
    print(f"hero.webp: {n} frames, {size // 1024} KB")


def encode(name, fps=None):
    """OUT/frames/<name> as OUT/<name>.webp with its alpha: a still, or with fps a looping animation."""
    rate, codec = (["-framerate", str(fps)], ["libwebp_anim", "-loop", "0"]) if fps else ([], ["libwebp"])
    frames = os.path.join(OUT, "frames", name, "frame%04d.png")
    ffmpeg(*rate, "-i", frames, "-c:v", *codec, "-quality", str(WEBP_QUALITY), os.path.join(OUT, f"{name}.webp"))


def ffmpeg(*args):
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", *args], check=True)


def render(motion):
    """A motion of the site's pictures (SITE), the preview, or a hero frame shard `hero:<first>-<end>` (#537)."""
    if motion.startswith("hero"):
        hero(tuple(map(int, motion.removeprefix("hero:").split("-"))) if ":" in motion else None)
    else:
        views(PREVIEW if motion == "preview" else PANELS)


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
            for f in MOTIONS.get(motion, []):  # a hero frame shard's frames stay in OUT/frames/hero, for join
                shutil.copy(os.path.join(OUT, f), IMAGES)
    elif what == "join":
        join()
        os.makedirs(IMAGES, exist_ok=True)
        shutil.copy(os.path.join(OUT, "hero.webp"), IMAGES)
    else:
        sys.exit(f"unknown: {what}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
