"""Checks' model shards (`just model-shards-list`, #305, #474, #496): N runners, balanced on measured seconds. The units
are the hero's collision sweep, each document (stages.DOCS, picked by its id: pytest -k on the parameter), the rest of
the model tests, just sim and just mech (the Mech stand-in); each goes, longest first, to the lightest shard. Their
seconds are the CI runs' own (model/durations.json, pytest-split's --store-durations plus just sim's and just mech's
core-seconds: `just model-durations`), so a new document needs no workflow edit and no list of names. MODEL=false or
MECH=false (the Changes job's filters) leaves that group's units out.
And Checks' Blender bins (`just blender-bins`): each motion of the pictures (PICTURES) and the viewer's GLBs (VIEWER)
when not false, packed longest first into bins no longer than the longest unit (#496), on the seconds
"blender <unit>" that main's last rendering run measured (MEASURED, #569), else those typed in
model/durations.json; PREVIEW=true (a PR's, #562) makes the pictures the preview alone. The hero splits into frame
shards of about a minute each, from its frame count and "blender hero frame", each paying "blender hero setup"
(#537)."""

import glob
import json
import os
import shlex

from model import stages

N = 4  # runners (#496)
SHARD_SECONDS = 60  # a hero frame shard's render, about a minute (Cansin, #537)
HERO = "test_hero.py"  # -k on its module, model/render/test_hero.py
JUST = {"sim": "just sim", "mech": "just mech"}  # their keys in DURATIONS
DURATIONS = os.path.join(stages.REPO, "model", "durations.json")
# the Blender seconds main's last rendering run measured, a folder a bin (Changes downloads them, #569)
MEASURED = os.path.join(stages.REPO, "model", "build", "main-seconds")


def units(model=True, mech=True):
    """{unit: its pytest -k expression}, None for just sim and just mech: the model's units, mech's, or both."""
    docs = {d.removeprefix("noggin-"): d for d in stages.DOCS}
    rest = " and ".join(f"not {k}" for k in [HERO, *docs.values()])
    return ({"hero": HERO, **docs, "rest": rest, "sim": None} if model else {}) | ({"mech": None} if mech else {})


def seconds(durations):
    """{unit: seconds}: each test's under the unit whose -k picks it (the rest otherwise); an unmeasured unit, the mean."""
    expr = units()
    just = {v: k for k, v in JUST.items()}
    took = dict.fromkeys(expr, 0.0)
    for test, s in durations.items():
        if not test.startswith("blender "):
            took[just.get(test) or next((u for u, k in expr.items() if k and u != "rest" and k in test), "rest")] += s
    measured = [s for s in took.values() if s]
    return {u: s or (sum(measured) / len(measured) if measured else 1.0) for u, s in took.items()}


def shards(model=True, mech=True):
    """[{shard, units, tests}]: tests is the shard's pytest arguments (PYTEST_ADDOPTS), empty when it has none."""
    weight = {u: s for u, s in seconds(json.load(open(DURATIONS))).items() if u in units(model, mech)}
    loads = [[] for _ in range(N)]
    for unit in sorted(weight, key=lambda u: (-weight[u], u)):
        min(loads, key=lambda load: sum(weight[u] for u in load)).append(unit)
    expr = units()
    out = []
    for load in filter(None, loads):
        picks = [f"({expr[u]})" for u in load if expr[u]]
        out.append(
            {"shard": " ".join(load), "units": load, "tests": shlex.join(["-k", " or ".join(picks)]) if picks else ""}
        )
    return out


def packed(weight):
    """The units, longest first, each into the first bin it fits, no bin longer than the longest unit."""
    cap, bins = max(weight.values(), default=0), []
    for unit in sorted(weight, key=lambda u: (-weight[u], u)):
        fits = next((b for b in bins if sum(weight[u] for u in b) + weight[unit] <= cap), None)
        if fits:
            fits.append(unit)
        else:
            bins.append([unit])
    return bins


def measured(folder):
    """{"blender <unit>": seconds} from each bin's JSON files under folder, the slower where two bins measured one key
    (the hero's frame shards); {} without any."""
    took = {}
    for f in glob.glob(os.path.join(folder, "*", "*.json")):
        for k, s in json.load(open(f)).items():
            took[k] = max(s, took.get(k, 0))
    return took


def frame_ranges(frames, frame_seconds):
    """The hero's frames as contiguous [first, end) ranges, as many as make each about SHARD_SECONDS of render."""
    k = max(1, round(frames * frame_seconds / SHARD_SECONDS))
    return [(i * frames // k, (i + 1) * frames // k) for i in range(k)]


def blender(pictures=True, viewer=True, preview=False):
    """[{bin, motions, stages, viewer, images, frames}]: stages are what the bin's just trajectories bakes (TRAJ_DOCS),
    every Stage (empty) with the viewer, whose just web bakes them all; images, whether its motions put site pictures in
    model/build/images; frames, whether it holds a frame shard. preview: the pictures are the preview alone (a PR's).
    The hero renders in frame shards (frame_ranges), motions `hero:<first>-<end>` whose frames the Hero job joins
    (#537)."""
    from model.render.pictures import hero_frames, motions  # Blender's side only: the model shards need none of it

    stages_of = {m["motion"]: m["stages"].split() for m in motions(preview)} if pictures else {}
    took = json.load(open(DURATIONS)) | measured(MEASURED)
    if "hero" in stages_of:
        n, per, setup = hero_frames(), took["blender hero frame"], took["blender hero setup"]
        # every shard pays the setup: the parts, Blender's start, the first frame's shader compile
        for a, b in frame_ranges(n, per):
            stages_of[f"hero:{a}-{b}"], took[f"blender hero:{a}-{b}"] = stages_of["hero"], setup + (b - a) * per
        del stages_of["hero"]
    cold = [*stages_of, "viewer"] if viewer else [*stages_of]
    known = [took[f"blender {u}"] for u in cold if f"blender {u}" in took] or [1.0]
    weight = {u: took.get(f"blender {u}", sum(known) / len(known)) for u in cold}  # unmeasured: the mean
    out = []
    for b in packed(weight):
        moving = [u for u in b if u in stages_of]
        baked = "" if "viewer" in b else " ".join(sorted({s for m in moving for s in stages_of[m]}))
        out.append(
            {
                "bin": " ".join(b),
                "motions": " ".join(moving),
                "stages": baked,
                "viewer": "viewer" in b,
                "images": any(":" not in m for m in moving),
                "frames": any(":" in m for m in moving),
            }
        )
    return out


if __name__ == "__main__":
    import sys

    on = {g: os.environ.get(g.upper()) != "false" for g in ("model", "mech", "pictures", "viewer")}
    if sys.argv[1:] == ["blender"]:
        print(json.dumps(blender(on["pictures"], on["viewer"], os.environ.get("PREVIEW") == "true")))
    else:
        print(json.dumps(shards(on["model"], on["mech"])))
