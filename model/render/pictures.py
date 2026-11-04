"""Every picture the site serves (published()), rendered in Blender (#47; rules in docs/model-notes.md), each document
posed from its baked trajectories (model/trajectories.py, `just trajectories`): MuJoCo's poses (#150). Each picture is a
WebP with a transparent background, its lines one grey for the site's light and dark themes (blender.py INK, #470).
Six stills alone (#898): the front doors (FRONT, #739: the README's three) and a poster per Stage (POSTERS: each at
rest, a trajectory's first frame, isometric in the default Preset, framed among themselves); the viewer stands in for
every other picture (#839, #898). `views` (`just render`) renders them; `site next` (`just pictures next`, Checks'
Render) also copies them where the site serves them from, model/build/images (#649).
Usage: python -m model.render.pictures views | site next (Blender at $BLENDER)"""

import functools
import json
import os
import shutil
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
import trimesh

from model import geometry as g
from model import skin, stages, trajectories
from model.render import camera, scene

OUT = os.path.join(stages.REPO, "model", "build", "pictures")
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender.py")
# the views (Cansin, #470): from the left side and isometric from the front left, by eye direction and up; the posters
# at one scale on one ground line, framed tight: the largest one's silhouette plus PAD of it each side
VIEWS = {"side": (g.X, g.Z), "isometric": ((1, -1, 1), g.Z)}
# the pictures per Preset alone (#819): {name: (document, Preset)}, each Stage in the Preset's Skeleton shape painted in
# its Palettes, named by the Stage as Bones, the default Preset's alone, another's -<its slug> (next-stage1-morty)
SUFFIX = {p: f"-{g.slug(p)}" if i else "" for i, p in enumerate(g.PRESETS)}
BONY = [d for d in g.STAGES if g.shape(d) == g.THEMES["Skeleton shape"][0]]  # the Stages in order, as Bones
DRAWN = {  # each Stage in each Preset's Skeleton shape, Stage 3 in its Skin shape where that is drawn (#813)
    s + SUFFIX[p]: (g.dressed(s + g.SKELETON_SUFFIX[t["Skeleton shape"]], t["Skin shape"]), p)
    for p, t in g.PRESETS.items()
    for s in BONY
}
PANEL_WIDTH, PAD = 800, 0.03
MARGIN = 1.06
WEBP_QUALITY = 85  # lossy colour, lossless alpha
# the web viewer's exploded next Mech (macros.py explode, #482, #664), mm: the neck lifted off the base, the eyes off
# the neck (or Stage 1's stand), the jaw forward, the cranium's boards up out of the head (#858)
EXPLODE = {
    "next-base": (0, 0, 0),
    "next-stand": (0, 0, 0),
    "next-neck": (0, 0, 45),
    "next-jaw": (0, -40, 45),
    "next-eyes": (0, 0, 95),
    "next-cranium": (0, 0, 160),
    **dict.fromkeys(g.SKINS.values(), (0, 0, 0)),  # the shirt's, with the Torso; every other Shell's its carrier's
}
# Explode's Parts level (#811): each part out along its Assembly direction (GLOSSARY) on its sub-assembly's offset, at
# least GAP clear of every part's bounding box, mm (inferred); a seated part's direction off its seat: a Core and its
# Shield off its pins' side (BOARDS: up off the cranium tray, #858, or off the test stand's face), the hub up off its
# riser, the switch board, the power-path board and the pack up off the Torso's floor (stages.next_base)
GAP = 5.0
SEATS = {
    "switch": g.Z,
    "battery": g.Z,
    "power": g.Z,
    "hub": g.Z,
    "capacitor": g.Z,
    "next torso lid": g.Z,
} | skin.DIRECTIONS  # a Shell off its Seats; the lid up
# out of the Torso's walls (#838)
BOARDS = ("receiver", "core")  # out along their local y, the Shield's pins' (model/envelopes.py)
# the front doors (#739: the README's top, the site's home), side by side in this order, in the default Preset alone,
# its mechanism without a Skin (bare) until a finished Skin exists (#843): Stage 1 from the front, its eyes facing
# the camera; Stage 3 isometric; Stage 3 from the side, exploded (EXPLODE); each (DRAWN's name, eye direction,
# exploded), framed tight on its own at the posters' size
STAGE1, STAGE3 = BONY[0], next(iter(g.NEXT))
FRONT = {
    f"{STAGE1}-front.webp": (STAGE1, (0, -1, 0), False),
    f"{STAGE3}-bare-isometric.webp": (STAGE3, VIEWS["isometric"][0], False),
    f"{STAGE3}-side-exploded.webp": (STAGE3, VIEWS["side"][0], True),
}
IMAGES = os.path.join(stages.REPO, "model", "build", "images")
NEXT = "next"


def picture(name, view):
    return f"{name}-{view}.webp"


# a poster per Stage (#898): its still until a viewer of it loads, the default Preset's (DRAWN's unsuffixed names)
POSTERS = [picture(s, "isometric") for s in BONY]


def published():
    """Every picture the site serves (#649, #898): the front doors' three (#739), then a poster per Stage."""
    return [*FRONT, *POSTERS]


def bare(doc, mats):
    """mats ({part: world 4x4}) without the document's Shells (skin.SHELLS): its mechanism alone (#843), the skull's
    bones as they show bare (g.SKULL) where a Skin's worn ones sit (g.WORN, #838; prepare adds them)."""
    full = {f"{w}:1": f"{s}:1" for s, w in g.WORN.items()}
    stage = stages.STAGES[doc]
    return {full.get(n, n): m for n, m in mats.items() if stages.stem(stage.parts[n].file) not in skin.SHELLS}


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
    the mounts, the frames) has none: the rest is assembled on it."""
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
        elif s in BOARDS:
            out[n] = (p.matrix[:3, 1], True)
        elif (seat := s.removesuffix(g.MECHANICAL)) in SEATS:
            out[n] = (np.array(SEATS[seat], float), True)
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
    sub |= {n: sub[c] for n, c in stages.RIDES.items() if n in sub and c in sub}  # a Shell with what carries it
    out = {n: np.array(EXPLODE[sub[n]] if level else (0, 0, 0), float) for n in stages.STAGES[doc].parts}
    if level < 2:
        return out
    box, axes = boxes(doc), directions(doc)
    middle = np.mean([lo + hi for lo, hi in box.values()], axis=0) / 2
    placed = []
    for n in sorted(box, key=lambda n: (n in axes, -np.prod(np.subtract(*box[n][::-1])))):
        if (servo := n.replace(" horn:1", " servo:1")) != n and servo in out:  # from where its servo went (#858)
            out[n] = out[servo].copy()
        lo, hi = box[n][0] + out[n], box[n][1] + out[n]
        if n in axes:
            d, signed = axes[n]
            d = np.round(d / np.linalg.norm(d), 9)
            if not signed and np.dot((lo + hi) / 2 - middle, d) < -0.5:  # a part on the middle goes the axis' way
                d = -d
            out[n] = out[n] + _clear(lo, hi, d, [(lo, hi), *placed]) * d
        elif any(d := EXPLODE[sub[n]]):  # one the rest goes on, among another's (#817): on out
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


def prepare(name):
    """(stage, manifest with absolute PLY paths, hull points per part) for one document's pictures under name: DRAWN's,
    in its Preset's colours (#819), its parts as model/stages.py assembles them, exported once. Always our geometry
    (model/build/ours, `just ours`), never the designer's meshes."""
    doc, preset = DRAWN[name]
    stage = stages.STAGES[doc]
    folder = os.path.join(OUT, "meshes", name)
    os.makedirs(folder, exist_ok=True)
    manifest = scene.export(doc, folder, g.PRESETS.get(preset))
    for p in manifest.values():
        p["ply"] = os.path.join(folder, p["ply"])
    full_bones(manifest, folder)
    return stage, manifest, hulls(manifest)


def full_bones(manifest, folder):
    """Adds to manifest (scene.export's, absolute PLY paths) the bare look's bones (bare), each a PLY in folder,
    coloured as the worn one it stands in for; the GLBs' too (web/build.py, #876)."""
    for full, worn in g.WORN.items():
        if f"{worn}:1" in manifest:
            ply = os.path.join(folder, f"{full}.ply")
            trimesh.load(stages.stl(full), force="mesh").apply_scale(0.001).export(ply)
            manifest[f"{full}:1"] = {**manifest[f"{worn}:1"], "ply": ply}


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


def render(name, manifest, shots):
    """The shots in one Blender run, each encoded (a still is one frame)."""
    blender(name, manifest, shots)
    for s in shots:
        encode(os.path.basename(s["out"]))


def views():
    """The posters (each Stage in the default Preset at rest as MuJoCo settles it, where every gesture starts), at one
    scale and one frame: the largest silhouette among them; and the front doors (FRONT) at their size."""
    plans = {}
    for name in BONY:  # the default Preset's names (DRAWN)
        _, manifest, hulls = prepare(name)
        mats = trajectories.poses(DRAWN[name][0], "wink")[0]
        plans[name] = (manifest, hulls, mats, points(hulls, mats))
    fits = {n: camera.fit(plans[n][3], *VIEWS["isometric"], 1) for n in plans}
    # one scale and one frame for every poster: the widest and the tallest silhouette, PAD of the larger round them
    w, h = np.max([[np.ptp(plans[n][3] @ c.matrix[:3, i]) for i in (0, 1)] for n, c in fits.items()], axis=0)
    pad = PAD * max(w, h)
    w, h = w + 2 * pad, h + 2 * pad
    size = (PANEL_WIDTH, 2 * round(PANEL_WIDTH * h / w / 2))
    for name, (manifest, hull, mats, pts) in plans.items():
        shots = [shot(f"{name}-isometric", size, camera.stand(fits[name], pts, w, w / h, pad / h), [mats])]
        for f, (_, eye, apart) in ((f, how) for f, how in FRONT.items() if how[0] == name):
            pose = bare(DRAWN[name][0], exploded(DRAWN[name][0], mats) if apart else mats)
            cam = camera.fit(points(hull, pose), eye, g.Z, size[0] / size[1], None, MARGIN)
            shots.append(shot(f.removesuffix(".webp"), size, cam, [pose]))
        render(name, manifest, shots)


def encode(name):
    """OUT/frames/<name> as OUT/<name>.webp, a still with its alpha."""
    frames = os.path.join(OUT, "frames", name, "frame%04d.png")
    ffmpeg("-i", frames, "-c:v", "libwebp", "-quality", str(WEBP_QUALITY), os.path.join(OUT, f"{name}.webp"))


def ffmpeg(*args):
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", *args], check=True)


def main(what, names):
    os.makedirs(OUT, exist_ok=True)
    if what == "views":
        views()
    elif what == "site" and set(names) <= {NEXT}:
        views()
        os.makedirs(IMAGES, exist_ok=True)
        for f in published():
            shutil.copy(os.path.join(OUT, f), IMAGES)
    else:
        sys.exit(f"unknown: {what} {' '.join(names)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
